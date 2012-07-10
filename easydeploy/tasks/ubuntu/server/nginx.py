import os

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

@task
def install_nginx(nginx_conf=None):
    """Installs nginx webserver."""
    apt_get("ngingx", "ppa:nginx/stable")
    add_startup("nginx")

@task
def configure_nginx(path=None):
    """Upload Nginx configuration and restart Nginx so this configuration takes
    effect."""
    opts = dict(
        path=path or env.get('path') or err("env.path must be set"),
    )

    if os.path.exists("%(path)s/etc/nignx/nginx.conf"):
        upload_template_jinja2("%(path)s/etc/nignx/nginx.conf" % opts,
                '/etc/nginx/nginx.conf', use_sudo=True)
        sudo('service nginx restart')
    
@task
def install_php():
    """Install FastCGI interface for running PHP scripts via Nginx."""

    # install php-fpm, php process manager
    apt_get(['php5-fpm', 'php5-curl', 'php5-mysql', 'php5-gd'])

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
def generate_selfsigned_ssl(hostname=None):
    """Generate self-signed SSL certificates and provide them to Nginx."""
    opts = dict(
        hostname=hostname 
                or get_envvar('hostname',section='nginx')
                or err("Hostname must be set"),
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