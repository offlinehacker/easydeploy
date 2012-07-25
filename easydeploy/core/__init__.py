import md5
#import hashlib

from Crypto.Cipher import ARC4
from fabric.api import env, execute, settings
from fabric.contrib.files import upload_template
from fabric.utils import abort
from fabric.utils import warn
from fabric.utils import error
from fabric.utils import puts
from fabric.contrib.console import confirm

def err(msg):
    """
    Raises Attribute error

    :param msg: Error messasage
    :type msg: str

    :returns: None
    :rtype: None
    """
    raise AttributeError(msg)

def upload_template_jinja2(template, destination, use_sudo=True):
    """
    Uploads template using jinja2

    :param template: Local path to template
    :type template: str
    :param destination: Remote destination path
    :type destination: str
    :param use_sudo: Should we use sudo
    :type use_sudo: bool

    :returns: Whatever upload_template returns
    """

    return upload_template(template, destination, context=env, use_sudo=use_sudo, use_jinja=True)

def encpass(key, keypass=None):
    """
    Encripts password using key

    :param key: Key to enrypt with
    :type key: str
    :param keypass: Password to encrypt
    :type keypass: str

    :returns: Encrypted password
    :rtype: str
    """
    opts = dict (
            keypass=keypass or env.get("keypass") or err("env.keypass is not set")
            )

    RC4= ARC4.new(opts["keypass"])
    RC4.encrypt(md5.new(opts["keypass"]).digest()) #hashlib.md5 instead md5.new
    RC4.encrypt(key)

def decpass(key, keypass=None):
    """
    Decripts password using key

    :param key: Key using to decrypt
    :type key: str
    :param keypass: Password using to decript
    :type keypass: str

    :returns: Plaintext
    :rtype: str
    """

    opts = dict (
            keypass=keypass or env.get("keypass") or err("env.keypass is not set")
            )

    RC4= ARC4.new(opts["keypass"])
    RC4.decrypt(md5.new(opts["keypass"]).digest())
    return RC4.decrypt(key)

def save_status():
    status = yaml.dump((env.state))
    totalPath = os.path.realpath(__file__)
    directory, fname = os.path.split(totalPath)
    saveName = directory+".fabstate"
    # 
    while True:
        try:
            file(saveName,"wb").write(status)
            puts("Status saved successfully", flush=True)
            break
        except IOError,e:
            if hasattr(env,"state_ask") and env.state_ask:
                if not confirm(("Error when saving to file %s: %s (%i)\n" % (saveName, e.args[1], e.args[0]))+
                                "Do you want to specify new path (unless status won't saved)?"):
                    warn("Status didn't saved.")
                    break
                else:
                    # get new path
                    while True:
                        saveName = raw_input("Please specify absolute path where status of easydeploy can be saved"+
                                                  " or write \"abort\" if you want to abort saving status\n"+
                                             "eg. /home/john/.fabstate or ~/.fabstate : ")
                        if saveName == "abort" or len(saveName) > 0 and (saveName[0] == "/" or saveName[0] == "~")):
                            break
                    # break also second while
                    if saveName == "abort":
                        break
            else:
                warn("Error when saving to file %s: %s (%i)" % (saveName, e.args[1], e.args[0])
                break
    return

def load_status():
    
    return

class state(object):
    """
    Decorator for handling states and its errors.

    .. note::

        Its main task is to provide a system for checking for provided dependencies
        among different tasks. So if some task fails, execution can continue and
        tasks that depends on whatever failed task provides won't run.

    .. warning::

        This decorator will not install task dependencies instead of you, its main
        task is to track which tasks has completed and which not.

    ``env.state`` list tells which states for which hosts are already provided.
    It is a simple dictionary of ``{"host_name": {"provided1", "provided2",...}}``

    * Set ``env.state_warn_only`` to only warn about failed state.
    * Set ``env.state_ask`` if you want to be asked if you want to continue on failed state.
    * if ``env.state_skip`` is set tasks gets skipped when provided states are in env.state list

    Example::

        @task
        @state(provides="apt.update")
        def apt_update():
            sudo("apt-get -y update")

        @task
        @state(provides=['nginx.nginx','nginx.config'],depends=['apt.update'])
        def nginx():
            apt-get("install nginx")

        ...

    """

    def __init__(self, provides=[], depends=[]):
        """
        Decorator input parameters

        :param provides: List of provided items
        :type provides: list, str
        :param depends: List of dependecies
        :type depends: list, str

        :returns: None
        """

        self.depends = depends if not isinstance(depends,basestring) else [depends]
        self.provides = provides if not isinstance(provides,basestring) else [provides]

    def __call__(self, fn):
        self.fn=fn
        def wrapper(*args):
            continoueFlag = 1
            # add state dictionary (happens first time only)
            if not hasattr(env,"state"):
                env.state={}
            # add empty list for saving installed stuff (happens first time only)
            if not env.state.has_key(env.host):
                env.state[env.host]=[]

            # if function doesn't have provides, skip it
            if not self.provides:
                warn("This task doesn't provide anything")

            # Check if task should be skipped if it is already provided
            # with what state provides
            if hasattr(env,"state_skip") and env.state_skip:
                if all(x in env.state[env.host] for x in self.provides):
                    puts("This task has already been executed, so we decide to skip it")
                    return

                # if function doesn't have provides, skip it
                if not self.provides:
                    return

            # check that all dependences are installed
            if not all(x in env.state[env.host] for x in self.depends):
                # if state_warn_only is set skip that package
                if hasattr(env,"state_warn_only") and env.state_warn_only:
                    continoueFlag = 0
                    warn("Not all dependencies satisfied for task %s.%s"
                         " providing %s" % (fn.__module__,fn.__name__, self.provides) )

                    if hasattr(env,"state_ask") and env.state_ask:
                        if not confirm("Do you want to continue with deploy?"):
                            abort("Deploy for host %s stopped" % (env.host,))
                # state_warn_only isn't set so abort
                else:
                    abort("Not all dependencies satisfied for task %s.%s"
                          "providing %s" % (fn.__module__,fn.__name__, self.provides) )

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
                    env.state[env.host]= list(set(env.state[env.host]+self.provides))

        wrapper.func_name = fn.func_name
        if hasattr(fn, '__name__'):
            wrapper.__name__ = self.name = fn.__name__
        if hasattr(fn, '__doc__'):
            wrapper.__doc__ = fn.__doc__
        if hasattr(fn, '__module__'):
            wrapper.__module__ = fn.__module__

        return wrapper

def provide(provides=[]):
    """
    Provides someting and saves it to env.state

    :param provides: List of items to provide
    :type provides: list

    :returns: None
    """

    # add state dictionary (happens first time only)
    if not hasattr(env,"state"):
        env.state={}

    # Check if task should be skipped if it is already provided
    # with what state provides
    if hasattr(env,"state_skip") and env.state_skip:
        if all(x in env.state[env.host] for x in provides):
            puts("This task has already been executed, so we decide to skip it")
            return

    # add empty list for saving installed stuff (happens first time only)
    if not env.state.has_key(env.host):
        env.state[env.host]=[]
    provides=provides if not isinstance(provides,basestring) else [provides]

    env.state[env.host]= list(set(env.state[env.host]+provides))

def unprovide(provides=[]):
    env.state[env.host]= filter(lambda el: el not in provides, env.state[env.host])

def get_envvar(varname, section=None):
    """
    Function for smarter retrival of variables from ``env``, with section support
    and defaults

    First it searches for variable ``varname`` in ``env.settings[section]`` in
    case section is specified, if not found it searches for ``varname`` in
    ``env.settings``. Multiple sections can be specified delimited by comma.
    In that case it first searches for ``varname`` in first section and than
    in other sections::

        >>> env.settings={"admin":{"email":"a"}, "info":{"email":"b"}}
        >>> get_envvar("email","admin,info")
        a

        >>> env.settings={"admin":{}, "email":"b"}
        >>> get_envvar("email","admin")
        b

    ``env.section`` overrides section specified to this function

    :param varname: Name of variable to take from env or its sections
    :type varname: str
    :param section: Name of section to lookup or comma separated, prioritized
                    from more to less importancy sections to lookup
    :type section: str

    :returns: Value of env variable
    """

    se= env.get("settings") or err("env.settings not set")

    # Tries to get varname from section defined in env.section or
    # from the first section that matches those listed in section
    # or from envdefault or just by taking value from varname in env.
    return (env.get("section") \
                and isinstance(se.get(env.get("section")),dict) \
                and se.get(env.get("section")).get(varname)) or \
           (section \
                #Takes first section that matches
                and next(iter([se.get(j).get(varname) for j in section.split(",") if \
                     isinstance(se.get(j),dict) and se.get(j).get(varname)]), None))  or \
            se.get(varname)

def execute_tasks(tasks):
    """
    Executes tasks,
    provided as list of tasks with arguments and parameters::

        [
          "task1",
         ("task2", "val1", "val2"),
         ("task3", {"kwparam1":"val1", "kwparam2":"val2"}),
         {"task": "task4",
          "params":["val1","val2"],
          "settings":{"warn_only":True}},
         {"task": "task5",
          "params":{"kwparam1":"val1", "kwparam2":"val2"},
          "settings":{"warn_only":True}}
         ]

    or as dictionary of namespaces and its list of tasks with
    arguments and parameters::

        {"namespace":
            [
              "task1",
             ("task2", "val1", "val2"),
             ("task3", {"kwparam1":"val1", "kwparam2":"val2"}),
             {"task": "task4",
              "params":["val1","val2"],
              "settings":{"warn_only":True}},
             {"task": "task5",
              "params":{"kwparam1":"val1", "kwparam2":"val2"},
              "settings":{"warn_only":True}}
             ]
          }

    :param tasks: List or dict of tasks
    :type tasks: list, dict

    :returns: None
    """

    if isinstance(tasks, dict):
        for task_namespace in tasks:
            for task in tasks[task_namespace]:
                _execute_task(task,task_namespace)
    else:
        for task in tasks:
            _execute_task(task)

def _execute_task(task, namespace=""):
    if namespace:
        namespace=namespace.rstrip(".")+"."
    if not isinstance(task,basestring):
        _name=""
        _params= {}
        _settings= {}
        if isinstance(task,dict):
            _name= task.get("name")
            _params=  task.get("params") or {}
            _settings= task.get("settings") or {}
        elif isinstance(task[1],dict) and len(task)==2:
            _name= task[0]
            _params= task[1]
        else:
            _name= task[0]
            _params= task[1:]

        with settings(**_settings):
            if isinstance(_params,dict):
                execute(namespace+_name, **_params)
            else:
                execute(namespace+_name, *_params)
    else:
        execute(namespace+task)
