from fabric.api import task, settings, sudo, env, run
from fabric.contrib.console import confirm
from fabric.contrib.files import append
from fabric.contrib.files import exists
from fabric.contrib.files import sed
from fabric.contrib.files import uncomment
from fabric.operations import prompt

from easydeploy.core import err, state
from easydeploy.core import upload_template_jinja2, get_envvar, provide

@task
@state(depends="admin.update")
def apt_get(pkg_name, repo=None):
    """
    Install package

    :param pkg_name: Name or list of packages
    :type pkg_name: list, str
    :param repo: Optional repository to use
    :type repo: str

    .. autojinja:: test.tpl
    """

    opts = dict(
        pkg_name = pkg_name or err("Pkg_name must be set"),
        repo = repo
    )

    if opts["repo"]:
        sudo("apt-add-repository -y %(repo)s"% opts)

    if repo:
        with settings(state_skip=False):
            sudo("apt-get update")

    if isinstance(opts["pkg_name"], basestring):
        sudo("apt-get -yq install %(pkg_name)s" % opts)
        provide("admin.packages.".join(opts["pkg_name"].split()))
    else:
        sudo("apt-get -yq install", " ".join(opts["pkg_name"]))
        provide("admin.packages.".join(opts["pkg_name"]))

@task
@state(provides="admin.update")
def apt_update():
    "Updates apt"
    sudo("apt-get -y update")

@task
@state(depends="admin.update", provides="admin.upgrade")
def apt_upgrade():
    "Upgrades apt"
    sudo("apt-get -y upgrade")

@task
def add_startup(service=None):
    """
    Adds service to startup

    :param service: Name of the service in /etc/init.d/
    :type service: str
    """
    opts = dict(
        service=service or err("Service must be set")
        )

    if isinstance(opts["sevice"], (tuple, list, dict, set)):
        for service in opts["service"]:
            sudo("update-rc.d %s defaults", service)
            provide("startup.%s" % service)
    else:
        sudo("update-rc.d %(service)s defaults" % opts)
        provide("startup.%(service)s" % opts)

@task
def create_accounts(users=None, default_password=None,
                    groups=None, admin=False):
    """
    Create accounts with same settings

    Default section: accounts, admin

    :param users: List of users
    :type users: str, list
    :param default_password: Their default password ( in ``admin`` )
    :type default_password: str
    :param groups: List or string of comma separated groups
    :type groups: list, str
    :param admin: Should be users admins or not
    :type admin: bool
    """

    opts = dict(
        users=users
                or get_envvar('usernames',section='accounts')
                or err("Users must be set"),
        default_password=default_password
                or get_envvar('default_password',section='accounts,admin')
                or err("Default_password must be set"),
        groups=groups
                or get_envvar('groups',section='accounts'),
        admin=admin or get_envvar('admin',section='accounts')
    )

    for username in opts["users"]:
        create_account(username, default_password=opts["default_password"], admin=opts["admin"])

@task
def create_account(username, default_password=None, groups=[],
                admin=False, priv= None, pub=None):
    """
    Creates account

    .. note::
         Variables for this function cannot be set using env

    :param username: Username
    :type username: str
    :param default_password: Default password or secret
    :type default_password: str
    :param groups: List or string of comma separated groups
    :type groups: list or str
    :param priv: private key
    :type priv: str
    :param pub: public key
    :type pub: str
    """

    opts = dict(
        username=username,
        default_password=default_password,
        admin=admin,
        groups= (",".join(groups)) if not isinstance(groups,basestring) else groups,
        priv=priv,
        pub=pub
    )

    # create user
    sudo('egrep %(username)s /etc/passwd || adduser %(username)s --disabled-password --gecos ""' % opts)

    if opts["groups"]:
        sudo('usermod -a -G  %(groups)s %(username)' % opts)

    # add public key for SSH access
    if not exists('/home/%(username)s/.ssh' % opts):
        sudo('mkdir /home/%(username)s/.ssh' % opts)

    if opts['pub']:
        sudo("echo '%(pub)s' > /home/%(username)s/.ssh/authorized_keys" % opts)

    if opts['priv']:
        sudo("echo '%(priv)s' > /home/%(username)s/.ssh/id_rsa" % opts)

    if opts['admin']:
        # allow sudo for maintenance user by adding it to 'sudo' group
        sudo('usermod -a -G sudo %(username)s' % opts)

    # set default password for initial login
    sudo('echo "%(username)s:%(default_password)s" | chpasswd' % opts)

    provide("account.%(username)s" % opts)

@task
@state(provide="network.sshd.x11forwarding")
def sshd_x11forwarding():
    """Enables X11 forwarding for ssh client and server"""
    sed('/etc/ssh/sshd_config',
        '#X11Forwarding yes',
        'X11Forwarding yes',
        use_sudo=True)

    sed('/etc/ssh/sshd_config',
        '#X11DisplayOffset 10',
        'X11DisplayOffset 10',
        use_sudo=True)

    sed('/etc/ssh/sshd_config',
        '#   ForwardX11 yes',
        '   ForwardX11 yes',
        use_sudo=True)

    sed('/etc/ssh/sshd_config',
        '#   ForwardX11Trusted yes',
        '   ForwardX11Trusted yes',
        use_sudo=True)

@task
@state(provide="network.sshd.security")
def sshd_secure():
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
def install_ufw():
    """Installs Uncomplicated Firewall."""
    apt_get('ufw')

@task
@state(depends="admin.package.ufw",provides="network.ufw")
def configure_ufw(rules=None):
    """
    Configures Uncomplicated Firewall.

    Default section: ufw,network

    :param rules: list of firewall rules
    :type rules: list, str
    """

    # reset rules so we start from scratch
    sudo('ufw --force reset')

    rules = rules or get_envvar("rules", section="ufw,network") \
                     or err("env.rules must be set")
    for rule in rules:
        sudo(rule)

    # re-enable firewall and print rules
    sudo('ufw --force enable')
    sudo('ufw status verbose')

@task
@state(provides="admin.disabled_root_login")
def disable_root_login():
    """
    Disable `root` login for even more security. Access to `root` account
    is now possible by first connecting with your dedicated maintenance
    account and then running ``sudo su -``.
    """
    sudo('passwd --lock root')

@task
@state(provide="admin.hostname")
def set_hostname(ip=None, hostname=None):
    """
    Set server's hostname

    Default section: network

    :param ip: ip
    :type ip: str
    :param hostname: hostname
    :type hostname: str
    """

    opts = dict(
        ip=ip or get_envvar("ip",section="network")
              or err("env.server_ip must be set"),
        hostname=hostname or get_envvar("hostname",section="network")
              or err("env.hostname must be set"),
    )

    sudo('echo "\n%(server_ip)s %(hostname)s" >> /etc/hosts' % opts)
    sudo('echo "%(hostname)s" > /etc/hostname' % opts)
    sudo('hostname %(hostname)s' % opts)

@task
@state(provides="admin.system_time")
def set_system_time(timezone=None):
    """
    Sets system timezone and installs ntp

    Default section: admin

    :param timezone: Timezone, for example ``/usr/share/zoneinfo/UTC``
    :type timezone: str
    """

    opts = dict(
        timezone=timezone or get_envvar("timezone", section="admin")
                          or '/usr/share/zoneinfo/UTC',
    )

    # set timezone
    sudo('cp %(timezone)s /etc/localtime' % opts)

    # install NTP
    apt_get('ntp')

@task
@state(provides="admin.unattended_upgrades")
def install_unattended_upgrades(email=None):
    """
    Configure Ubuntu to automatically install security updates.

    Default section: admin

    :param email: email where you want to receive info about updates
    :type email: str
    """

    opts = dict(
        email=email or get_envvar("email", section="admin")
                    or err('env.email must be set'),
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
@state(provides="network")
def install_network_config(path=None):
    """
    Installs network configuration, using jinja2 template and adds networking to
    startup.

    .. note:: This function won't restart your network by itself.

    .. autojinja:: /etc/network/interfaces

    :param path: Path to your template folder
    :type path: str
    """

    opts = dict(
            path=path or env.get("path") or err('env.path must be set')
            )

    upload_template_jinja2("%(path)/etc/network/interfaces" % opts,
                           "/etc/network/interfaces")
    add_startup("networking")
