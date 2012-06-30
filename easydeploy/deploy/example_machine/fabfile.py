from __future__ import with_statement
from fabric.api import local, settings, abort, run, cd
from fabric.contrib.console import confirm
from fabric.context_managers import show
from fabric.api import env

env.hosts = ["192.168.2.70",
# "192.168.2.118"
]
env.key_filename = ["/root/.ssh/id_rsa_test_ubuntu1", 
#"/root/.ssh/id_rsa_proxy"
]

env.warn_only = False

env.state_warn_only = True
env.state_ask = False

from easydeploy.templates.ubuntu import apache

# custom library
from custom import test

# linear
def linear():
    apache.apache()
    apache.mod_python()
    
    test.fail()
    test.fail1()
    test.success()
    test.success1()
    

print "Finish :)"

