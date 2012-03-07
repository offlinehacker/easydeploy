from fabric.api import env
from fabric.api import sudo
from fabric.contrib.console import confirm
from fabric.contrib.files import append
from fabric.contrib.files import exists
from fabric.contrib.files import sed
from fabric.contrib.files import uncomment
from fabric.contrib.files import upload_template
from fabric.context_managers import settings
from fabric.operations import prompt
from fabric.contrib.files import comment
from niteoweb.fabfile import err
from cuisine import dir_ensure
from cuisine import mode_sudo

import os

def raid_monitoring(email=None):
    """Configure monitoring of our RAID-1 field. If anything goes wrong,
    send an email!"""
    opts = dict(
        email=email or env.get('email') or err('env.email must be set'),
    )

    # enable email notifications from mdadm raid monitor
    append('/etc/mdadm/mdadm.conf', 'MAILADDR %(email)s' % opts, use_sudo=True)

    # enable email notification for SMART disk monitoring
    sudo('apt-get -yq install smartmontools')
    uncomment('/etc/default/smartmontools', '#start_smartd=yes', use_sudo=True)


def install_nginx(nginx_conf=None):
    """Install and configure Nginx webserver."""

    sudo('add-apt-repository ppa:nginx/stable')
    sudo('apt-get update')
    sudo('apt-get -yq install nginx')

    configure_nginx()


def configure_nginx(nginx_conf=None):
    """Upload Nginx configuration and restart Nginx so this configuration takes
    effect."""
    opts = dict(
        nginx_conf=nginx_conf or env.get('nginx_conf') or '%s/etc/nginx.conf' % os.getcwd(),
    )

    upload_template(opts['nginx_conf'], '/etc/nginx/nginx.conf', use_sudo=True)
    sudo('service nginx restart')


def install_sendmail(email=None):
    """Prepare a localhost SMTP server for sending out system notifications
    to admins."""
    opts = dict(
        email=email or env.get('email') or err('env.email must be set'),
    )

    # install sendmail
    sudo('apt-get -yq install sendmail')

    # all email should be sent to maintenance email
    append('/etc/aliases', 'root:           %(email)s' % opts, use_sudo=True)


def install_rkhunter(email=None):
    """Install and configure RootKit Hunter."""
    opts = dict(
        email=email or env.get('email') or err('env.email must be set'),
    )

    # install RKHunter
    sudo('apt-get -yq install rkhunter')

    # send emails on warnings
    uncomment('/etc/rkhunter.conf', '#MAIL-ON-WARNING=me@mydomain   root@mydomain', use_sudo=True)
    sed('/etc/rkhunter.conf', 'me@mydomain   root@mydomain', opts['email'], use_sudo=True)

    # ignore some Ubuntu specific files
    uncomment('/etc/rkhunter.conf', '#ALLOWHIDDENDIR=\/dev\/.udev', use_sudo=True)
    uncomment('/etc/rkhunter.conf', '#ALLOWHIDDENDIR=\/dev\/.static', use_sudo=True)
    uncomment('/etc/rkhunter.conf', '#ALLOWHIDDENDIR=\/dev\/.initramfs', use_sudo=True)


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


def install_php():
    """Install FastCGI interface for running PHP scripts via Nginx."""

    # add aditional repositories so we can install php5-fpm
    sudo('add-apt-repository ppa:brianmercer/php')
    sudo('apt-get update')

    # install php-fpm, php process manager
    sudo('apt-get -yq install php5-fpm php5-curl php5-mysql php5-gd')

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
    sudo('sudo apt-get -yq install mysql-server mysql-client')

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


def install_munin_node(add_to_master=True):
    """Install and configure Munin node, which gathers system information
    and sends it to Munin master."""

    # install munin-node
    sudo('apt-get -yq install munin-node')

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


def install_postgres():
    """Install and configure Postgresql database server."""
    sudo('apt-get -yq install postgresql libpq-dev')
    configure_postgres()
    initialize_postgres()


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


def install_bacula_master():
    """Install and configure Bacula Master."""
    # Official repos only have version 5.0.1, we need 5.0.3
    sudo('add-apt-repository ppa:mario-sitz/ppa')
    sudo('apt-get update')
    sudo('apt-get -yq install bacula-console bacula-director-pgsql bacula-sd-pgsql')
    configure_bacula_master()

def configure_bacula_master(path=None):
    """Upload configuration files for Bacula Master."""
    opts = dict(
        path=path or env.get('path') or err('env.path must be set'),
    )

    upload_template('%(path)s/etc/bacula-dir.conf' % opts,
                    '/etc/bacula/bacula-dir.conf',
                    use_sudo=True)
    upload_template('%(path)s/etc/pool_defaults.conf' % opts,
                    '/etc/bacula/pool_defaults.conf',
                    use_sudo=True)
    upload_template('%(path)s/etc/pool_full_defaults.conf' % opts,
                    '/etc/bacula/pool_full_defaults.conf',
                    use_sudo=True)
    upload_template('%(path)s/etc/pool_diff_defaults.conf' % opts,
                    '/etc/bacula/pool_diff_defaults.conf',
                    use_sudo=True)
    upload_template('%(path)s/etc/pool_inc_defaults.conf' % opts,
                    '/etc/bacula/pool_inc_defaults.conf',
                    use_sudo=True)

    sudo('service bacula-director restart')


def install_bacula_client():
    """Install and configure Bacula backup client, which listens for
    instructions from Bacula master and backups critical data
    when told to do so."""

    # Official repos only have version 5.0.1, we need 5.0.3
    sudo('add-apt-repository ppa:mario-sitz/ppa')
    sudo('apt-get update')
    sudo('apt-get -yq install bacula-fd')

    # this folder is needed
    with mode_sudo():
        dir_ensure('/var/spool/bacula', recursive=True)

    configure_bacula_client()


def configure_bacula_client(path=None):
    """Upload configuration for Bacula File Deamon (client)
    and restart it."""
    opts = dict(
        path=path or env.get('path') or err('env.path must be set'),
    )

    upload_template('%(path)s/etc/bacula-fd.conf' % opts, '/etc/bacula/bacula-fd.conf', use_sudo=True)
    sudo('service bacula-fd restart')


def add_to_bacula_master(shortname=None, path=None, bacula_host_string=None):
    """Add this server's Bacula client configuration to Bacula master."""
    opts = dict(
        shortname=shortname or env.get('shortname') or err('env.shortname must be set'),
        path=path or env.get('path') or err('env.path must be set'),
        bacula_host_string=bacula_host_string or env.get('bacula_host_string') or err('env.bacula_host_string must be set')
    )

    with settings(host_string=opts['bacula_host_string']):

        # upload project-specific configuration
        upload_template(
            '%s/etc/bacula-master.conf' % opts,
            '/etc/bacula/clients/%(shortname)s.conf' % opts,
            use_sudo=True)

        # reload bacula master configuration
        sudo("service bacula-director restart")


def configure_hetzner_backup(duplicityfilelist=None, duplicitysh=None):
    """Hetzner gives us 100GB of backup storage. Let's use it with
    Duplicity to backup the whole disk."""
    opts = dict(
        duplicityfilelist=duplicityfilelist or env.get('duplicityfilelist') or '%s/etc/duplicityfilelist.conf' % os.getcwd(),
        duplicitysh=duplicitysh or env.get('duplicitysh') or '%s/etc/duplicity.sh' % os.getcwd(),
    )

    # install duplicity and dependencies
    sudo('apt-get -yq install duplicity ncftp')

    # what to exclude
    upload_template(opts['duplicityfilelist'], '/etc/duplicityfilelist.conf', use_sudo=True)

    # script for running Duplicity
    upload_template(opts['duplicitysh'], '/usr/sbin/duplicity.sh', use_sudo=True)
    sudo('chmod +x /usr/sbin/duplicity.sh')

    # cronjob
    sudo("echo '0 8 * * * root /usr/sbin/duplicity.sh' > /etc/cron.d/duplicity ")

    if not env.get('confirm'):
        confirm("You need to manually run a full backup first time. Noted?")
