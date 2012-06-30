from __future__ import with_statement
from fabric.api import local, settings, abort, run, cd, task
from fabric.contrib.console import confirm
from fabric.context_managers import show
from fabric.api import env
from fabric.api import execute

from easydeploy.core import state, execute_tasks

if hasattr(env,"show_all") and env.show_all:
    import easydeploy.tasks

env.hosts = ["127.0.0.1"]

env.warn_only = False

env.state_warn_only = True
env.state_skip = True
#env.state_ask = False

basic={
       "tasks": [
                 {"easydeploy.tasks.ubuntu.core":
                                [
                                 "apt_update",
                                 "apt_upgrade",
                                 "create_admin_accounts",
                                 "set_hostname",
                                 "set_system_time"
                                 ]
                  }
                 ]
       }

@task
@state(provides="deploy.basic")
def deploy_basic():
    with settings(**basic):
        execute_tasks(env.tasks)

server_basic={
       "tasks": [
                 {"easydeploy.tasks.ubuntu.core":
                                [
                                 "install_unattended_upgrades",
                                 "harden_sshd",
                                 "disable_root_login"
                                 ]
                  }
                 ]
       }

@task
@state(requiers="deploy.basic",provides="deploy.server_basic")
def deploy_server_basic():
    execute(deploy_basic) 
    with settings(**server_basic):
        pass

