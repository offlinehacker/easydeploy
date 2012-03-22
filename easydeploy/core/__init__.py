import md5

from Crypto.Cipher import ARC4
from fabric.api import env
from fabric.contrib.files import upload_template

def err(msg):
    raise AttributeError(msg)

def upload_template_jinja2(template, destination, use_sudo=True):
    return upload_template(template, destination, context=env, use_sudo=use_sudo, use_jinja=True)

def encpass(key, keypass=None):
    opts = dict (
            keypass=keypass or env.get("keypass") or err("env.keypass is not set")
            )

    RC4= ARC4.new(opts["keypass"])
    RC4.encrypt(md5.new(opts["keypass"]).digest())
    RC4.encrypt(key)

def decpass(key, keypass=None):
    opts = dict (
            keypass=keypass or env.get("keypass") or err("env.keypass is not set")
            )

    RC4= ARC4.new(opts["keypass"])
    RC4.decrypt(md5.new(opts["keypass"]).digest())
    return RC4.decrypt(key)
