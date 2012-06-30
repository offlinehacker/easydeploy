from fabric.api import env
from fabric.api import sudo
from fabric.api import task
from fabric.contrib.console import confirm
from fabric.contrib.files import append
from fabric.contrib.files import exists
from fabric.contrib.files import sed
from fabric.contrib.files import uncomment
from fabric.operations import prompt

from easydeploy.core import err
from easydeploy.core import upload_template_jinja2

@task
def apt_get(pkg_name, repo=None):
    """Install package"""
    opts = dict(
        pkg_name = pkg_name or env.get("pkg_name") or err("env.pkg_name must be set"),
        repo = repo or env.get("repo") or None
    )

    if opts["repo"]:
        sudo("apt-add-repository -y %(repo)s"% opts)

    if repo:
        sudo("apt-get update")

    if isinstance(opts["pkg_name"], (tuple, list, dict, set)):
        sudo("apt-get -yq install", opts["pkg_name"].join(" "))
    else:
        sudo("apt-get -yq install %(pkg_name)s" % opts)

@task
def add_startup(service=None):
    """Adds service to startup"""
    opts = dict(
        service=service or env.get("service") or err("env.service must be set")
        )

    if isinstance(opts["sevice"], (tuple, list, dict, set)):
        for service in opts["service"]:
            sudo("update-rc.d %s defaults", service)
    else:
        sudo("update-rc.d %(service)s defaults" % opts)

@task
def create_admin_accounts(admins=None, default_password=None):
    """Create admin accounts, so admins can access the server."""
    opts = dict(
        admins=admins or env.get('admins') or err("env.admins must be set"),
        default_password=default_password or env.get('default_password') or 'secret',
    )

    for admin in opts["admins"]:
        create_admin_account(admin, default_password=default_password)

    if not env.get('confirm'):
        confirm("Users %(admins)s were successfully created. Notify"
                "them that they must login and change their default password "
                "(%(default_password)s) with the ``passwd`` command. Proceed?" % opts)

@task
def create_admin_account(admin, default_password=None):
    """Create an account for an admin to use to access the server."""
    opts = dict(
        admin=admin,
        default_password=default_password or env.get('default_password') or 'secret',
    )

    # create user
    sudo('egrep %(admin)s /etc/passwd || adduser %(admin)s --disabled-password --gecos ""' % opts)

    # add public key for SSH access
    if not exists('/home/%(admin)s/.ssh' % opts):
        sudo('mkdir /home/%(admin)s/.ssh' % opts)

    opts['pub'] = prompt("Paste %(admin)s's public key or leave alone: " % opts)
    if opts['pub']:
        sudo("echo '%(pub)s' > /home/%(admin)s/.ssh/authorized_keys" % opts)

    opts['priv'] = prompt("Paste %(admin)s's private key or leave alone: " % opts)
    if opts['priv']:
        sudo("echo '%(priv)s' > /home/%(admin)s/.ssh/id_rsa" % opts)

    # allow this user in sshd_config
    append("/etc/ssh/sshd_config", 'AllowUsers %(admin)s@*' % opts, use_sudo=True)

    # allow sudo for maintenance user by adding it to 'sudo' group
    sudo('usermod -a -G sudo %(admin)s' % opts)

    # set default password for initial login
    sudo('echo "%(admin)s:%(default_password)s" | chpasswd' % opts)

@task
def harden_sshd():
    """Security harden sshd."""

    # Disable password authentication
    sed('/etc/ssh/sshd_config',
        '#PasswordAuthentication yes',
        'PasswordAuthentication no',
        use_sudo=True)

    # Deny root login
    sed('/etc/ssh/sshd_config',
        'PermitRootLogin yes',
        'PermitRootLogin no',
        use_sudo=True)

@task
def install_ufw(rules=None):
    """Install and configure Uncomplicated Firewall."""
    apt_get('ufw')

@task
def configure_ufw(rules=None):
    """Configure Uncomplicated Firewall."""
    # reset rules so we start from scratch
    sudo('ufw --force reset')

    rules = rules or env.rules or err("env.rules must be set")
    for rule in rules:
        sudo(rule)

    # re-enable firewall and print rules
    sudo('ufw --force enable')
    sudo('ufw status verbose')

@task
def disable_root_login():
    """Disable `root` login for even more security. Access to `root` account
    is now possible by first connecting with your dedicated maintenance
    account and then running ``sudo su -``."""
    sudo('passwd --lock root')

@task
def set_hostname(server_ip=None, hostname=None):
    """Set server's hostname."""
    opts = dict(
        server_ip=server_ip or env.server_ip or err("env.server_ip must be set"),
        hostname=hostname or env.hostname or err("env.hostname must be set"),
    )

    sudo('echo "\n%(server_ip)s %(hostname)s" >> /etc/hosts' % opts)
    sudo('echo "%(hostname)s" > /etc/hostname' % opts)
    sudo('hostname %(hostname)s' % opts)

@task
def set_system_time(timezone=None):
    """Set timezone and install ``ntp`` to keep time accurate."""

    opts = dict(
        timezone=timezone or env.get('timezone') or '/usr/share/zoneinfo/UTC',
    )

    # set timezone
    sudo('cp %(timezone)s /etc/localtime' % opts)

    # install NTP
    apt_get('ntp')

@task
def install_system_libs(additional_libs=None):
    """Install a bunch of stuff we need for normal operation such as
    ``gcc``, ``rsync``, ``vim``, ``libpng``, etc."""

    opts = dict(
        additional_libs=additional_libs or env.get('additional_libs') or '',
    )

    sudo('apt-get -yq install '

             # tools
             'lynx '
             'curl '
             'rsync '
             'telnet '
             'build-essential '
             'python-software-properties '  # to get add-apt-repositories command

             # imaging, fonts, compression, encryption, etc.
             'libjpeg-dev '
             'libjpeg62-dev '
             'libfreetype6-dev '
             'zlib1g-dev '
             'libreadline5-dev '
             'zlib1g-dev '
             'libbz2-dev '
             'libssl-dev '
             'libjpeg62-dev '
             '%(additional_libs)s' % opts
             )

@task
def install_unattended_upgrades(email=None):
    """Configure Ubuntu to automatically install security updates."""
    opts = dict(
        email=email or env.get('email') or err('env.email must be set'),
    )

    apt_get('unattended-upgrades')
    sed('/etc/apt/apt.conf.d/50unattended-upgrades',
        '//Unattended-Upgrade::Mail "root@localhost";',
        'Unattended-Upgrade::Mail "%(email)s";' % opts,
        use_sudo=True)

    sed('/etc/apt/apt.conf.d/10periodic',
        'APT::Periodic::Download-Upgradeable-Packages "0";',
        'APT::Periodic::Download-Upgradeable-Packages "1";',
        use_sudo=True)

    sed('/etc/apt/apt.conf.d/10periodic',
        'APT::Periodic::AutocleanInterval "0";',
        'APT::Periodic::AutocleanInterval "7";',
        use_sudo=True)

    append('/etc/apt/apt.conf.d/10periodic',
           'APT::Periodic::Unattended-Upgrade "1";',
           use_sudo=True)

@task
def install_network_config(path=None):
    opts = dict(
            path=path or env.get("path") or err('env.path must be set')
            )

    upload_template_jinja2("%(path)/etc/network/interfaces" % opts,
                           "/etc/network/interfaces")
