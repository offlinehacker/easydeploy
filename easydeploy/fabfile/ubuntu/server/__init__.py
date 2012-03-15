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
from easydeploy.fabfile.ubuntu.core import apt_get

import os

@task
def raid_monitoring(email=None):
    """Configure monitoring of our RAID-1 field. If anything goes wrong,
    send an email!"""
    opts = dict(
        email=email or env.get('email') or err('env.email must be set'),
    )

    # enable email notifications from mdadm raid monitor
    append('/etc/mdadm/mdadm.conf', 'MAILADDR %(email)s' % opts, use_sudo=True)

    # enable email notification for SMART disk monitoring
    apt_get('smartmontools')
    uncomment('/etc/default/smartmontools', '#start_smartd=yes', use_sudo=True)

@task
def install_nginx(nginx_conf=None):
    """Install and configure Nginx webserver."""
    apt_get("ngingx", "ppa:nginx/stable")

    configure_nginx()

@task
def configure_nginx(nginx_conf=None):
    """Upload Nginx configuration and restart Nginx so this configuration takes
    effect."""
    opts = dict(
        nginx_conf=nginx_conf or env.get('nginx_conf') or '%s/etc/nginx.conf' % os.getcwd(),
    )

    upload_template_jinja2(opts['nginx_conf'], '/etc/nginx/nginx.conf', use_sudo=True)
    sudo('service nginx restart')

@task
def install_sendmail(email=None):
    """Prepare a localhost SMTP server for sending out system notifications
    to admins."""
    opts = dict(
        email=email or env.get('email') or err('env.email must be set'),
    )

    # install sendmail
    apt_get('sendmail')

    # all email should be sent to maintenance email
    append('/etc/aliases', 'root:           %(email)s' % opts, use_sudo=True)

@task
def install_rkhunter(email=None):
    """Install and configure RootKit Hunter."""
    opts = dict(
        email=email or env.get('email') or err('env.email must be set'),
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
def generate_selfsigned_ssl(hostname=None):
    """Generate self-signed SSL certificates and provide them to Nginx."""
    opts = dict(
        hostname=hostname or env.get('hostname') or 'STAR.niteoweb.com',
    )

    if not exists('mkdir /etc/nginx/certs'):
        sudo('mkdir /etc/nginx/certs')

    sudo('openssl genrsa -des3 -out server.key 2048')
    sudo('openssl req -new -key server.key -out server.csr')
    sudo('cp server.key server.key.password')
    sudo('openssl rsa -in server.key.password -out server.key')
    sudo('openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt')
    sudo('cp server.crt /etc/nginx/certs/%(hostname)s.crt' % opts)
    sudo('cp server.key /etc/nginx/certs/%(hostname)s.key' % opts)

@task
def install_php():
    """Install FastCGI interface for running PHP scripts via Nginx."""

    # install php-fpm, php process manager
    apt_get(['php5-fpm', 'php5-curl', 'php5-mysql', 'php5-gd'], 'ppa:brianmercer/php')

    # the command above also pulls in apache, which we cannot remove -> make id not start at bootup
    sudo('update-rc.d -f apache2 remove')

    # security harden PHP5
    sed('/etc/php5/cgi/php.ini', ';cgi\.fix_pathinfo=1', 'cgi\.fix_pathinfo=0', use_sudo=True)
    sed('/etc/php5/cgi/php.ini', '; allow_call_time_pass_reference', 'allow_call_time_pass_reference = Off', use_sudo=True)
    sed('/etc/php5/cgi/php.ini', '; display_errors', 'display_errors = Off', use_sudo=True)
    sed('/etc/php5/cgi/php.ini', '; html_errors', 'html_errors = Off', use_sudo=True)
    sed('/etc/php5/cgi/php.ini', '; magic_quotes_gpc', 'magic_quotes_gpc = Off', use_sudo=True)
    sed('/etc/php5/cgi/php.ini', '; log_errors', 'log_errors = On', use_sudo=True)

    # restart for changes to apply
    sudo('/etc/init.d/php5-fpm restart')

@task
def install_mysql(default_password=None):
    """Install MySQL database server."""
    opts = dict(
        default_password=default_password or env.get('default_password') or 'secret'
    )

    # first set root password in advance so we don't get the package
    # configuration dialog
    sudo('echo "mysql-server-5.0 mysql-server/root_password password %(default_password)s" | debconf-set-selections' % opts)
    sudo('echo "mysql-server-5.0 mysql-server/root_password_again password %(default_password)s" | debconf-set-selections' % opts)

    # install MySQL along with php drivers for it
    apt_get('mysql-server mysql-client')

    if not env.get('confirm'):
        confirm("You will now start with interactive MySQL secure installation."
                " Current root password is '%(default_password)s'. Change it "
                "and save the new one to your password managere. Then answer "
                "with default answers to all other questions. Ready?" % opts)
    sudo('/usr/bin/mysql_secure_installation')

    # restart mysql and php-fastcgi
    sudo('service mysql restart')
    sudo('/etc/init.d/php-fastcgi restart')

    # configure daily dumps of all databases
    sudo('mkdir /var/backups/mysql')
    password = prompt('Please enter your mysql root password so I can configure daily backups:')
    sudo("echo '0 7 * * * mysqldump -u root -p%s --all-databases | gzip > /var/backups/mysql/mysqldump_$(date +%%Y-%%m-%%d).sql.gz' > /etc/cron.d/mysqldump" % password)

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
    configure_postgres()
    initialize_postgres()

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
def install_avahi(path=None):
    opts = dict( 
        path = path or env.get("path") or err("env.path must be set")
    )

    apt_get("avahi-daemon")

    upload_template_jinja2("%(path)s/etc/avahi/avahi-daemon.conf" % opts,
                    "/etc/avahi/avahi-daemon.conf")
    #Allow other domains
    upload_template_jinja2("%(path)s/etc/mdns.allow" % opts,
                    "/etc/mdns.allow")

@task
def configure_hetzner_backup(duplicityfilelist=None, duplicitysh=None):
    """Hetzner gives us 100GB of backup storage. Let's use it with
    Duplicity to backup the whole disk."""
    opts = dict(
        duplicityfilelist=duplicityfilelist or env.get('duplicityfilelist') or '%s/etc/duplicityfilelist.conf' % os.getcwd(),
        duplicitysh=duplicitysh or env.get('duplicitysh') or '%s/etc/duplicity.sh' % os.getcwd(),
    )

    # install duplicity and dependencies
    apt_get('duplicity ncftp')

    # what to exclude
    upload_template_jinja2(opts['duplicityfilelist'], '/etc/duplicityfilelist.conf', use_sudo=True)

    # script for running Duplicity
    upload_template_jinja2(opts['duplicitysh'], '/usr/sbin/duplicity.sh', use_sudo=True)
    sudo('chmod +x /usr/sbin/duplicity.sh')

    # cronjob
    sudo("echo '0 8 * * * root /usr/sbin/duplicity.sh' > /etc/cron.d/duplicity ")

    if not env.get('confirm'):
        confirm("You need to manually run a full backup first time. Noted?")
