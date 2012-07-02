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
from easydeploy.tasks.ubuntu.core import apt_get
from easydeploy.tasks.ubuntu.core import add_startup

import os

@task
def install_finch():
    """Installs finch, console client port of pidgin"""
    apt_get("finch")

@task
def configure_finch(home=None, username=None):
    """Configures finch, console client port of pidign"""
    opts = dict(
        home=home or env.get('home') or err("env.home must be set"),
        username=username or env.get('username') or err("env.username must be set")
    )

    #Account and preferences
    dir_ensure("/home/%(username)s/.purple" % opts)
    upload_template_jinja2("%(home)s/.purple/prefs.xml" % opts, 
            "/home/%(username)s/.purple/prefs.xml" % opts)
    upload_template_jinja2("%(home)s/.purple/accounts.xml" % opts, 
            "/home/%(username)s/.purple/accounts.xml" % opts)

    #Mouse support
    upload_template_jinja2("%(home)s/.gntrc" % opts, "/home/%(username)s/.gntrc" % opts)
