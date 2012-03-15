from fabric.api import env
from fabric.contrib.files import upload_template

def err(msg):
    raise AttributeError(msg)

def upload_template_jinja2(template, destination, use_sudo=True):
    return upload_template(template, destination, context=env, use_sudo=use_sudo, use_jinja=True)
