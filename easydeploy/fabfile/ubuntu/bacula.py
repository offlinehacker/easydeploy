from fabric.api import env
from fabric.api import sudo
from fabric.api import task
from fabric.context_managers import settings
from cuisine import dir_ensure
from cuisine import mode_sudo

from easydeploy.core import err
from easydeploy.core import upload_template_jinja2
from core import apt_get

@task
def install_bacula_master():
    """Install and configure Bacula Master."""
    apt_get('bacula-console bacula-director-pgsql bacula-sd-pgsql')

@task
def configure_bacula_master(path=None):
    """Upload configuration files for Bacula Master."""
    opts = dict(
        path=path or env.get('path') or err('env.path must be set'),
    )

    upload_template_jinja2('%(path)s/etc/bacula-dir.conf' % opts,
                    '/etc/bacula/bacula-dir.conf',
                    use_sudo=True)
    upload_template_jinja2('%(path)s/etc/pool_defaults.conf' % opts,
                    '/etc/bacula/pool_defaults.conf',
                use_sudo=True)
    upload_template_jinja2('%(path)s/etc/pool_full_defaults.conf' % opts,
                '/etc/bacula/pool_full_defaults.conf',
                use_sudo=True)
    upload_template_jinja2('%(path)s/etc/pool_diff_defaults.conf' % opts,
                '/etc/bacula/pool_diff_defaults.conf',
                use_sudo=True)
    upload_template_jinja2('%(path)s/etc/pool_inc_defaults.conf' % opts,
                '/etc/bacula/pool_inc_defaults.conf',
                use_sudo=True)

    sudo('service bacula-director restart')

@task
def install_bacula_client():
    """Install and configure Bacula backup client, which listens for
    instructions from Bacula master and backups critical data
    when told to do so."""

    apt_get('bacula-fd')

    # this folder is needed
    with mode_sudo():
        dir_ensure('/var/spool/bacula', recursive=True)

@task
def configure_bacula_client(path=None):
    """Upload configuration for Bacula File Deamon (client)
    and restart it."""
    opts = dict(
        path=path or env.get('path') or err('env.path must be set'),
    )

    upload_template_jinja2('%(path)s/etc/bacula-fd.conf' % opts, '/etc/bacula/bacula-fd.conf', use_sudo=True)
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
        upload_template_jinja2(
            '%(path)s/etc/bacula-master.conf' % opts,
            '/etc/bacula/clients/%(shortname)s.conf' % opts,
            use_sudo=True)

        # reload bacula master configuration
        sudo("service bacula-director restart")

