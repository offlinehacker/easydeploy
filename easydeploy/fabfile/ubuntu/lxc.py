from fabric.api import env
from fabric.api import sudo
from fabric.api import put
from fabric.api import task
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

import core

@task
def install_lxc():
    """Installs LXC"""
    apt_get("lxc vlan bridge-utils")
    uncomment('/etc/default/lxc', '#RUN=yes', use_sudo=True)
    add_startup("lxc")

@task
def create_instance(name=None, template=None, config=None, autostart=None):
    """
    Creates new lxc instance. 
    Params: name, template, config, autostart
    """
    opts = dict(
            name=name or env.get("name") or err("env.name must be set"),
            template=template or env.get("template") or "ubuntu",
            config=config or env.get("config") or None,
            autostart=autostart or env.get("autostart") or True
            )
    if opts["config"]:
        put(opts["config"], "/tmp/lxc_config.conf")
        sudo("lxc-create -n %(name)s -t %(template)s -f /tmp/lxc_config.conf" % opts)
    else:
        sudo("lxc-create -n %(name)s -t %(template)s" % opts)

    #Change root password
    sudo("chroot /var/lib/lxc/%(name)s/rootfs/ passwd" % opts)

@task
def destroy_instance(name=None):
    """
    Destroys lxc instance.
    Params: name
    """
    opts = dict(
            name=name or env.get("name") or err("env.name must be set")
            )

    #First remove bootstart
    sudo("rm /etc/lxc/auto/%(name)s.conf" % opts)

    sudo("lxc-destroy -n %(name)s" % opts)

@task
def toggle_bootstart(name=None):
    """
    Toggles bootstart of lxc instance.
    Params: name
    """
    opts = dict(
            name=name or env.get("name") or err("env.name must be set")
            )

    if not exists("/etc/lxc/auto/%(name)s.conf" % opts):
        sudo("cp /var/lib/lxc/%(name)s/config /etc/lxc/auto/%(name)s.conf" % opts)
    else:
        sudo("rm /etc/lxc/auto/%(name)s.conf" % opts)

