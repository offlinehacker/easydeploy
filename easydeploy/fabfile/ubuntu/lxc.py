from fabric.api import env
from fabric.api import sudo
from fabric.api import put
from fabric.api import task
from fabric.contrib.console import confirm
from fabric.contrib.files import append
from fabric.contrib.files import exists
from fabric.contrib.files import sed
from fabric.contrib.files import uncomment
from fabric.contrib.files import upload_template_jinja2
from fabric.operations import prompt
from cuisine import dir_ensure

from easydeploy.core import err
from core import apt_get

import core

@task
def install_lxc():
    apt_get("lxc vlan bridge-utils")
    uncomment('/etc/default/lxc', '#RUN=yes', use_sudo=True)
    run("git clone https://github.com/dereks/lxc-ubuntu-x.git")
