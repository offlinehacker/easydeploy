from fabric.api import env
from fabric.api import sudo
from fabric.api import task
from fabric.contrib.console import confirm
from fabric.contrib.files import append
from fabric.contrib.files import exists
from fabric.contrib.files import sed
from fabric.contrib.files import uncomment
from fabric.context_managers import settings
from fabric.operations import prompt
from fabric.contrib.files import comment
from cuisine import dir_ensure
from cuisine import mode_sudo

from easydeploy.core import err
from easydeploy.core import upload_template_jinja2
from easydeploy.core import get_envvar
from easydeploy.tasks.ubuntu.core import apt_get
from easydeploy.tasks.ubuntu.core import add_startup

import os

@task
def raid_monitoring(email=None):
    """
    Configure monitoring of our RAID-1 field. If anything goes wrong,
    send an email!

    Default section: admin

    :param email: Email to send reports
    :type email: str
    """
    opts = dict(
        email=email
                or get_envvar('email',section='admin')
                or err('Email must be set'),
    )

    # enable email notifications from mdadm raid monitor
    append('/etc/mdadm/mdadm.conf', 'MAILADDR %(email)s' % opts, use_sudo=True)

    # enable email notification for SMART disk monitoring
    apt_get('smartmontools')
    uncomment('/etc/default/smartmontools', '#start_smartd=yes', use_sudo=True)

@task
def install_sendmail(email=None):
    """
    Prepare a localhost SMTP server for sending out system notifications
    to admins

    Default section: admin

    :param email: Email to send reports
    :type email: str
    """
    opts = dict(
        email=email
                or get_envvar('email',section='admin')
                or err('Email must be set'),
    )

    # install sendmail
    apt_get('sendmail')

    # all email should be sent to maintenance email
    append('/etc/aliases', 'root:           %(email)s' % opts, use_sudo=True)


@task
def install_dnsmasq():
    """Installs local dns server"""
    apt_get("dnsmasq")
    add_startup("dnsmasq")

@task
def configure_dnsmasq(path=None):
    """
    Configures local dns server

    :param path: Template folder
    :type path: str
    """
    opts = dict(
        path=path or env.get('path') or err("env.path must be set"),
    )

    upload_template_jinja2("%(path)s/etc/dnsmasq.con" % opts,
            '/etc/dnsmasq.conf', use_sudo=True)
    sudo('service nginx restart')

@task
def install_rkhunter(email=None):
    """
    Install and configure RootKit Hunter

    Default section: admin

    :param email: Email to send reports
    :type email: str
    """
    opts = dict(
        email=email
                or get_envvar('email',section='admin')
                or err('Email must be set'),
    )

    # install RKHunter
    apt_get('rkhunter')

    # send emails on warnings
    uncomment('/etc/rkhunter.conf', '#MAIL-ON-WARNING=me@mydomain   root@mydomain', use_sudo=True)
    sed('/etc/rkhunter.conf', 'me@mydomain   root@mydomain', opts['email'], use_sudo=True)

    # ignore some Ubuntu specific files
    uncomment('/etc/rkhunter.conf', '#ALLOWHIDDENDIR=\/dev\/.udev', use_sudo=True)
    uncomment('/etc/rkhunter.conf', '#ALLOWHIDDENDIR=\/dev\/.static', use_sudo=True)
    uncomment('/etc/rkhunter.conf', '#ALLOWHIDDENDIR=\/dev\/.initramfs', use_sudo=True)

@task
def install_mysql(password=None):
    """
    Install MySQL database server

    Default section: mysql

    :param password: Root mysql password ( ``envdefault="default_password"`` )
    :type password: str
    """

    opts = dict(
        password=password
                or get_envvar('password',section='mysql',envdefault='default_password')
                or err("No password for mysql set")
    )

    # first set root password in advance so we don't get the package
    # configuration dialog
    sudo('echo "mysql-server-5.0 mysql-server/root_password password %(password)s" | debconf-set-selections' % opts)
    sudo('echo "mysql-server-5.0 mysql-server/root_password_again password %(password)s" | debconf-set-selections' % opts)

    # install MySQL along with php drivers for it
    apt_get('mysql-server mysql-client')

@task
def configure_mysql_backups(password=None, time=None):
    """Example task for mysql backups"""
    opts = dict(
        password=password
                or get_envvar('password',section='mysql',envdefault='default_password')
                or err("No password for mysql set"),
        time=time
                or get_envvar('time',section='mysql')
                or err("No backup time for mysql set")
    )
    # configure daily dumps of all databases
    sudo('mkdir /var/backups/mysql')
    sudo("echo %(time)s mysqldump -u root -p%(password)s --all-databases | gzip > /var/backups/mysql/mysqldump_$(date +%%Y-%%m-%%d).sql.gz' > /etc/cron.d/mysqldump" % opts)

@task
def install_munin_node(add_to_master=True):
    """Install and configure Munin node, which gathers system information
    and sends it to Munin master."""

    # install munin-node
    apt_get('munin-node')

    # add allow IP to munin-node.conf -> allow IP must be escaped REGEX-style
    ip = '%(hq)s' % env
    ip.replace('.', '\\\.')
    sed('/etc/munin/munin-node.conf', '127\\\.0\\\.0\\\.1', '%s' % ip, use_sudo=True)
    sudo('service munin-node restart')

    # add node to munin-master on Headquarters server so
    # system information is actually collected
    if add_to_master:
        with settings(host_string='%(hq)s:22' % env):
            path = '/etc/munin/munin.conf'
            append(path, '[%(hostname)s]' % env, use_sudo=True)
            append(path, '    address %(server_ip)s' % env, use_sudo=True)
            append(path, ' ', use_sudo=True)

@task
def install_postgres():
    """Install and configure Postgresql database server."""
    sudo('apt-get -yq install postgresql libpq-dev')

@task
def configure_postgres():
    """Upload Postgres configuration from ``etc/`` and restart the server."""

    # pg_hba.conf
    comment('/etc/postgresql/8.4/main/pg_hba.conf',
            'local   all         postgres                          ident',
            use_sudo=True)
    sed('/etc/postgresql/8.4/main/pg_hba.conf',
        'local   all         all                               ident',
        'local   all         all                               md5',
        use_sudo=True)

    # postgres.conf
    uncomment('/etc/postgresql/8.4/main/postgresql.conf', '#autovacuum = on', use_sudo=True)
    uncomment('/etc/postgresql/8.4/main/postgresql.conf', '#track_activities = on', use_sudo=True)
    uncomment('/etc/postgresql/8.4/main/postgresql.conf', '#track_counts = on', use_sudo=True)
    sed('/etc/postgresql/8.4/main/postgresql.conf',
        "#listen_addresses",
        "listen_addresses",
        use_sudo=True)

    # restart server
    sudo('/etc/init.d/postgresql-8.4 restart')

@task
def initialize_postgres():
    """Initialize the main database."""
    # temporarily allow root access from localhost
    sudo('mv /etc/postgresql/8.4/main/pg_hba.conf /etc/postgresql/8.4/main/pg_hba.conf.bak')
    sudo('echo "local all postgres ident" > /etc/postgresql/8.4/main/pg_hba.conf')
    sudo('cat /etc/postgresql/8.4/main/pg_hba.conf.bak >> /etc/postgresql/8.4/main/pg_hba.conf')
    sudo('service postgresql-8.4 restart')

    # set password
    password = prompt('Enter a new database password for user `postgres`:')
    sudo('psql template1 -c "ALTER USER postgres with encrypted password \'%s\';"' % password, user='postgres')

    # configure daily dumps of all databases
    with mode_sudo():
        dir_ensure('/var/backups/postgresql', recursive=True)
    sudo("echo 'localhost:*:*:postgres:%s' > /root/.pgpass" % password)
    sudo('chmod 600 /root/.pgpass')
    sudo("echo '0 7 * * * pg_dumpall --username postgres --file /var/backups/postgresql/postgresql_$(date +%%Y-%%m-%%d).dump' > /etc/cron.d/pg_dump")

    # remove temporary root access
    comment('/etc/postgresql/8.4/main/pg_hba.conf', 'local all postgres ident', use_sudo=True)
    sudo('service postgresql-8.4 restart')

@task
def install_avahi():
    """Installs avahi for mdns support"""
    apt_get("avahi-daemon")
    add_startup("avahi-daemon")

@task
def configure_avahi(path=None):
    """Configure avahi for mdns support"""
    opts = dict(
        path = path or env.get("path") or err("env.path must be set")
    )

    upload_template_jinja2("%(path)s/etc/avahi/avahi-daemon.conf" % opts,
                    "/etc/avahi/avahi-daemon.conf")

    #Allow other domains
    upload_template_jinja2("%(path)s/etc/mdns.allow" % opts,
                    "/etc/mdns.allow")

    #For ipv6 mdns support
    upload_template_jinja2("%(path)s/etc/nsswitch.conf" % opts,
                    "/etc/nsswitch.conf")

    sudo("service avahi-daemon restart")

@task
def install_aiccu():
    "Installs aiccu. Hartbeat monitor for sixxs ipv6 tunnel"

    apt_get("aiccu")

@task
def configure_aiccu(path=None):
    "Configures aiccu. Hartbeat monitor for sixxs ipv6 tunnel"
    opts = dict(
        path=path or env.get('path') or err("env.path must be set"),
    )

    upload_template_jinja2("%(path)s/etc/aiccu.conf" % opts, "/etc/aiccu.conf")
    sudo("/etc/init.d/aiccu restart")
    sudo("update-rc.d aiccu defaults")

