"""
.. module:: lxc
   :platform: Unix
   :synopsis: Fabric tasks for managing of lxc container virtualization.

.. moduleauthor:: Jaka Hudoklin <jakahudoklin@gmail.com>


"""

import os

from fabric.api import env
from fabric.api import sudo
from fabric.api import put
from fabric.api import task
from fabric.api import local
from fabric.api import cd
from fabric.api import settings
from fabric.contrib.console import confirm
from fabric.contrib.files import append
from fabric.contrib.files import exists
from fabric.contrib.files import sed
from fabric.contrib.files import uncomment
from fabric.contrib.files import upload_template
from fabric.operations import prompt
from cuisine import dir_ensure

from easydeploy.core import err
from core import apt_get
from core import add_startup
from core import get_envvar

import core

@task
def install_lxc():
    """Installs LXC virtualization"""

    apt_get("lxc vlan bridge-utils")
    uncomment('/etc/default/lxc', '#RUN=yes', use_sudo=True)

@task
def create_instance(name, template="ubuntu", config=None, autostart=False):
    """
    Creates new lxc instance.

    .. note::
        Variables for this function cannot be set using env

    :param name: Lxc instance name
    :type name: str
    :param template: Name of template
    :type template: str
    :param config: Path to additional config file
    :type config: str
    :param autostart: Should this instance be started at startup
    :type autostart: bool
    """
    opts = dict(
            name=name,
            template=template,
            config=config,
            autostart=autostart
            )
    if opts["config"]:
        put(opts["config"], "/tmp/lxc_config.conf")
        sudo("lxc-create -n %(name)s -t %(template)s -f /tmp/lxc_config.conf" % opts)
    else:
        sudo("lxc-create -n %(name)s -t %(template)s" % opts)

    #Change root password
    sudo("chroot /var/lib/lxc/%(name)s/rootfs/ passwd" % opts)

    if opts["autostart"]:
        toggle_bootstart(name)

@task
def install_instance(path):
    """Installs instance from already created instance archive"""
    if path.endswith("tar.gz"):
        put(path, "/tmp/container.tar.gz")
    else:
        spath= os.path.split(path)
        with cd(spath[0]):
            local("tar -cpvzf /tmp/container.tar.gz %s" % spath[1], use_sudo=True)
        put("/tmp/container.tar.gz", "/tmp/container.tar.gz")

    sudo("mv /tmp/container.tar.gz /var/lib/lxc")
    with cd("/var/lib/lxc"):
        sudo("tar -xvf container.tar.gz")
        sudo("rm container.tar.gz")

    local("rm /tmp/container.tar.gz", use_sudo=True)

@task
def destroy_instance(name):
    """
    Destroys lxc instance

    .. note::
        Variables for this function cannot be set using env

    :param name: Lxc instance name
    :type name: str
    """
    opts = dict(
            name=name
            )

    #First remove bootstart
    with settings(warn_only=True):
        sudo("rm /etc/lxc/auto/%(name)s.conf" % opts)
    sudo("lxc-destroy -n %(name)s" % opts)

@task
def toggle_bootstart(name):
    """
    Toggles bootstart of lxc instance

    .. note::
        Variables for this function cannot be set using env

    :param name: Lxc instance name
    :type name: str
    """
    opts = dict(
            name=name)

    if not exists("/etc/lxc/auto/%(name)s.conf" % opts):
        sudo("cp /var/lib/lxc/%(name)s/config /etc/lxc/auto/%(name)s.conf" % opts)
    else:
        sudo("rm /etc/lxc/auto/%(name)s.conf" % opts)
