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

import core

@task
def install_badvpn(cert_folder=None, path=None):
    """Installs and configures badvpn client and server"""
    opts= dict(
            cert_folder = cert_folder or "/etc/badvpn/nssdb",
            path=path or env.get('path') or err('env.path must be set')
            )

    """Install package"""
    core.apt_get("badvpn","ppa:ambrop7/badvpn")
    core.apt_get(["libnss3-tools"])

    """Install all configs"""
    sudo("cp /etc/init.d/badvpn-server /etc/init.d/badvpn-client")
    upload_template("%(path)s/etc/init/badvpn-client" % opts,
             "/etc/init/badvpn-client", use_sudo=True)
    dir_ensure(opts["cert_folder"], recursive=True)
    upload_template("%(path)s/etc/default/badvpn-client" % opts,
             "/etc/default/badvpn-client", use_sudo=True)
    upload_template("%(path)s/etc/init/badvpn-server" % opts,
             "/etc/default/badvpn-server", use_sudo=True)

    """Create cert database"""
    put("%(path)s/ca.pem" % opts, "~/")
    sudo("certutil -d sql:%(cert_folder)s -N" % opts)
    sudo('certutil -d sql:%(cert_folder)s -A -t "CT,," -n "vpnca" -i ~/ca.pem' % opts)
