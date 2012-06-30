from fabric.api import local, settings, abort, run, lcd, cd, put
from easydeploy.core import state

@state(provides="apache.apache")
def apache():
    """
    Installs apache

    :returns : None
    :rtype: None
    """
    #run("apt-get -y install apache2")
    

    return None

@state(provides="apache.plugin.mod_python", depends="apache.apache")
def mod_python():
    
    return None
