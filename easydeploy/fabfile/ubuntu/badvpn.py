from fabric.api import env
from fabric.api import sudo
from fabric.api import put
from fabric.api import task
from fabric.contrib.console import confirm
from fabric.contrib.files import append
from fabric.contrib.files import exists
from fabric.contrib.files import sed
from fabric.contrib.files import uncomment
from fabric.operations import prompt
from cuisine import dir_ensure

from easydeploy.core import err
from easydeploy.core import upload_template_jinja2

import core

@task
def install_badvpn(path=None):
    """Installs and configures badvpn client and server"""
    opts= dict(
            cert_folder = "/etc/badvpn/nssdb",
            path=path or env.get('path') or err('env.path must be set')
            )

    """Install package"""
    core.apt_get("badvpn","ppa:ambrop7/badvpn")
    core.apt_get(["libnss3-tools"])

    """Install all configs"""
    sudo("cp /etc/init.d/badvpn-server /etc/init.d/badvpn-client")
    upload_template_jinja2("%(path)s/etc/init/badvpn-client" % opts,
             "/etc/init/badvpn-client", use_sudo=True)
    dir_ensure(opts["cert_folder"], recursive=True)
    upload_template_jinja2("%(path)s/etc/badvpn/badvpn-client" % opts,
             "/etc/badvpn/badvpn-client", use_sudo=True)
    sudo("ln -s /etc/badvpn/badvpn-client /etc/default/badvpn-client")
    upload_template_jinja2("%(path)s/etc/badvpn/badvpn-server" % opts,
             "/etc/badvpn/badvpn-server", use_sudo=True)
    sudo("ln -s /etc/badvpn/badvpn-server /etc/default/badvpn-server")

    """Create cert database"""
    put("%(path)s/ca.pem" % opts, "~/")
    sudo("certutil -d sql:%(cert_folder)s -N" % opts)
    sudo('certutil -d sql:%(cert_folder)s -A -t "CT,," -n "vpnca" -i ~/ca.pem' % opts)
