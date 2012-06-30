import md5

from Crypto.Cipher import ARC4
from fabric.api import env
from fabric.contrib.files import upload_template
from fabric.utils import abort
from fabric.utils import warn
from fabric.utils import error
from fabric.contrib.console import confirm

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

class state(object):
    """
    Decorator for handling states and its errors.

    Set ``env.state_warn_only`` to only warn about failed state.
    Set ``env.state_ask`` if you want to be asked if you want to continue on
    failed state.

    ``env.state`` list tells which states for wich hosts are already provided,
    if ``env.state_skip`` is set tasks gets skipped when provided states are
    in env.state list.

        @state(provides=['nginx.nginx','nginx.config'],depends=['apt.update'])
        def nginx():
            apt-get("install nging")

        ...

    """

    def __init__(self, provides=None, depends=None):
        self.depends = depends if depends != None else []
        self.provides = provides if provides != None else []

    def __call__(self, fn):

        def wrapper(*args):
            continoueFlag = 1
            # add state dictionary (happens first time only)
            if not hasattr(env,"state"):
                env.state={}
            # add empty list for saving installed stuff (happens first time only)
            if not env.state.has_key(env.host):
                env.state[env.host]=[]
            
            # check that all dependences are installed
            if not all(x in env.state[env.host] for x in self.depends):
                # if state_warn_only is set skip that package
                if hasattr(env,"state_warn_only") and env.state_warn_only:
                    continoueFlag = 0
                    warn("Not all dependencies satisfied for task %s.%s \
providing %s" % (fn.__module__,fn.__name__, self.provides) )

                    if hasattr(env,"state_ask") and env.state_ask:
                        if not confirm("Do you want to continue with deploy?"):
                            abort("Deploy for host %s stopped" % (env.host,))
                # warn_only isn't set so abort
                else:
                    abort("Not all dependencies satisfied for task %s.%s \
providing %s" % (fn.__module__,fn.__name__, self.provides) )

            # flag for updating status
            successfullyExecuted = 0
            # if dependences satisfied execute the task
            if continoueFlag:
                try:
                    # execute decorated function
                    fn(*args)
                    # last operation confirm successfully completed task
                    successfullyExecuted = 1
                except:
                    if hasattr(env,"state_warn_only") and env.state_warn_only:
                        warn("Problems running task %s.%s"
                             % (fn.__module__, fn.__name__))
                    else:
                        raise

                # update status if task successfully completed
                if successfullyExecuted == 1:
                    if isinstance(self.depends, basestring):
                       env.state[env.host]+= [self.provides,]
                    else:
                       env.state[env.host]+= self.provides

        return wrapper
