from fabric.api import env
from fabric.api import sudo
from fabric.api import task
from fabric.contrib.console import confirm
from fabric.contrib.files import append
from fabric.contrib.files import exists
from fabric.contrib.files import sed
from fabric.contrib.files import uncomment
from fabric.contrib.files import upload_template
from fabric.context_managers import settings
from fabric.operations import prompt
from fabric.contrib.files import comment
from cuisine import dir_ensure
from cuisine import mode_sudo

from easydeploy.core import err

import os

@task
def install_bacula_master():
    """Install and configure Bacula Master."""
    # Official repos only have version 5.0.1, we need 5.0.3
    sudo('add-apt-repository ppa:mario-sitz/ppa')
    sudo('apt-get update')
    sudo('apt-get -yq install bacula-console bacula-director-pgsql bacula-sd-pgsql')
    configure_bacula_master()

@task
def configure_bacula_master(path=None):
    """Upload configuration files for Bacula Master."""
    opts = dict(
        path=path or env.get('path') or err('env.path must be set'),
    )

    upload_template('%(path)s/etc/bacula-dir.conf' % opts,
                    '/etc/bacula/bacula-dir.conf',
                    use_sudo=True)
    upload_template('%(path)s/etc/pool_defaults.conf' % opts,
                    '/etc/bacula/pool_defaults.conf',
                    use_sudo=True)
    upload_template('%(path)s/etc/pool_full_defaults.conf' % opts,
                    '/etc/bacula/pool_full_defaults.conf',
                    use_sudo=True)
    upload_template('%(path)s/etc/pool_diff_defaults.conf' % opts,
                    '/etc/bacula/pool_diff_defaults.conf',
                    use_sudo=True)
    upload_template('%(path)s/etc/pool_inc_defaults.conf' % opts,
                    '/etc/bacula/pool_inc_defaults.conf',
                    use_sudo=True)

    sudo('service bacula-director restart')

@task
def install_bacula_client():
    """Install and configure Bacula backup client, which listens for
    instructions from Bacula master and backups critical data
    when told to do so."""

    # Official repos only have version 5.0.1, we need 5.0.3
    sudo('add-apt-repository ppa:mario-sitz/ppa')
    sudo('apt-get update')
    sudo('apt-get -yq install bacula-fd')

    # this folder is needed
    with mode_sudo():
        dir_ensure('/var/spool/bacula', recursive=True)

    configure_bacula_client()

@task
def configure_bacula_client(path=None):
    """Upload configuration for Bacula File Deamon (client)
    and restart it."""
    opts = dict(
        path=path or env.get('path') or err('env.path must be set'),
    )

    upload_template('%(path)s/etc/bacula-fd.conf' % opts, '/etc/bacula/bacula-fd.conf', use_sudo=True)
    sudo('service bacula-fd restart')

@task
def add_to_bacula_master(shortname=None, path=None, bacula_host_string=None):
    """Add this server's Bacula client configuration to Bacula master."""
    opts = dict(
        shortname=shortname or env.get('shortname') or err('env.shortname must be set'),
        path=path or env.get('path') or err('env.path must be set'),
        bacula_host_string=bacula_host_string or env.get('bacula_host_string') or err('env.bacula_host_string must be set')
    )

    with settings(host_string=opts['bacula_host_string']):

        # upload project-specific configuration
        upload_template(
            '%s/etc/bacula-master.conf' % opts,
            '/etc/bacula/clients/%(shortname)s.conf' % opts,
            use_sudo=True)

        # reload bacula master configuration
        sudo("service bacula-director restart")

