import md5

from Crypto.Cipher import ARC4
from fabric.api import env
from fabric.contrib.files import upload_template

def err(msg):
    """
    Raises Attribute error

    :param msg: Error messasage
    :type msg: str

    :returns : None
    :rtype: None
    """
    raise AttributeError(msg)

def upload_template_jinja2(template, destination, use_sudo=True):
    """
    Uploads template using jinja2

    :param template:
    :type template: a
    :param destination: a
    :type destination: a
    :param use_sudo: a
    :type use_sudo: a

    :returns : a
    :rtype: a
    """

    return upload_template(template, destination, context=env, use_sudo=use_sudo, use_jinja=True)

def encpass(key, keypass=None):
    """
    Encripts password using key

    :param key: a
    :type key: a
    :param keypass: a
    :type keypass: a

    :returns : a
    :rtype: a
    """
    opts = dict (
            keypass=keypass or env.get("keypass") or err("env.keypass is not set")
            )

    RC4= ARC4.new(opts["keypass"])
    RC4.encrypt(md5.new(opts["keypass"]).digest())
    RC4.encrypt(key)

def decpass(key, keypass=None):
    """
    Decripts password using key

    :param key: Key using to decrypt
    :type key: str
    :param keypass: Password using to decript
    :type keypass: str

    :returns : Plaintext
    :rtype: str
    """

    opts = dict (
            keypass=keypass or env.get("keypass") or err("env.keypass is not set")
            )

    RC4= ARC4.new(opts["keypass"])
    RC4.decrypt(md5.new(opts["keypass"]).digest())
    return RC4.decrypt(key)
