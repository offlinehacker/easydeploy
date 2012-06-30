from __future__ import with_statement
from fabric.api import local, settings, abort, run, cd
from fabric.contrib.console import confirm
from fabric.context_managers import show
from fabric.api import env

from easydeploy.core import state

@state(provides="custom.fail")
def fail():
    print "That will failed"
    run("exit 1")
    return None

@state(provides="custom.fail1", depends="custom.fail")
def fail1():
    print "Executing unsatisfied test"
    run("exit 1")
    return None

@state(provides="custom.succ")
def success():
    print "Will success"
    run("exit 0")
    return None

@state(provides="custom.succ1", depends="custom.succ")
def success1():
    print "Should happen"
    run("exit 0")
    return None
