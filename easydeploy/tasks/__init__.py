import ubuntu

import os

from fabric.api import task
from fabric.api import env
from easydeploy.core import upload_template_jinja2
from easydeploy.core import err

@task
def upload_template(location, use_sudo=True):
    """
    Uploads template using jinja2

    Idea is that your local template is located in a same relative path as on
    remote side. To make this work you have to set `env.path` to your location
    of templates.

    .. note::
        This function should be called as task using execute fabric api.
        Otherwise use :py:func:`easydeploy.core.upload_template_jinja2`.

    :param location: Local and remote path to template
    :type location: str
    :param use_sudo: Should we use sudo
    :type use_sudo: bool

    :returns: Whatever upload_template returns
    """

    path= env.get("path") or err("env.path must be set")
    return upload_template_jinja2(os.path.join(path,location), location, use_sudo)
