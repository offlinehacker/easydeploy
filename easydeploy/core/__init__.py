import md5, yaml, os
#import hashlib

from StringIO import StringIO

from Crypto.Cipher import ARC4
from fabric.api import env, execute, settings, put
from fabric.contrib.files import upload_template
from fabric.utils import abort
from fabric.utils import warn
from fabric.utils import error
from fabric.utils import puts
from fabric.contrib.console import confirm

from jinja2 import Environment, FileSystemLoader

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

    env.get("path") or err("env.path not set")

    jenv= Environment(loader=FileSystemLoader(env.path))
    jenv.globals["get_envvar"]= get_envvar
    text= jenv.get_template(template).render(**env.get("settings") or {})

    put(
        local_path=StringIO(text),
        remote_path= destination,
        use_sudo=use_sudo
    )

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

def save_status(fileName=""):
    """
    Saves status of easydeploy to fabstate file.
    
    :parm fileName: name of fabstate file.\n
    Example: ``easydeploy/core/snake.fabstate`` if ``fileName = "snake"``\n
    or\n
    ``easydeploy/core/.fabstate`` if ``fileName = ""``\n
    :type fileName: str
    
    :returns: None
    
    Example (status is saved at ``easydeploy/core/.fabstate``)::
    
        from easydeploy.core import load_status, save_status
        #
        # There can be code which doesn't using state decorator.
        #
        # Load previous status::
        load_status()
        #
        # Do additional operations and save new status::
        #
        # save status to fabstate file at easydeploy/core/.fabstate
        save_status()
    
    Example (status is saved at ``easydeploy/core/snake.fabstate``)::
    
        from easydeploy.core import load_status, save_status
        #
        # There can be code which doesn't using state decorator.
        #
        # Load previous status::
        load_status("snake")
        #
        # Do additional operations and save new status::
        #
        # save status to fabstate file at easydeploy/core/snake.fabstate
        save_status("snake")
    """
    # dump state variable
    status = yaml.dump((env.state if hasattr(env, "state") else None,
                        env.config if hasattr(env, "config") else None))
    # get current directory
    totalPath = os.path.realpath(__file__)
    directory = os.path.split(totalPath)[0]+"/"
    # full path of the file
    saveName = directory+fileName+".fabstate"
    # saving loop
    while True:
        try:
            file(saveName,"wb").write(status)
            puts("Status saved successfully", flush=True)
            break
        except IOError,e:
            errmessage = "Error when saving to file %s: %s (%i)" % (saveName, e.args[1], e.args[0])
            if not (hasattr(env,"state_ask") and env.state_ask):
                warn(errmessage)
                break
            else:
                if not confirm(errmessage+"\nDo you want to specify new path (unless status won't saved)?"):
                    warn("Status didn't saved.")
                    break
                else:
                    # get new path
                    saveName_previous = saveName
                    while True:
                        saveName = raw_input(("Please choose one of the following options:\n"+
                                              "    Enter absolute path where status of easydeploy can be saved\n"+
                                              "        eg. /home/john/%s.fabstate or ~/%s.fabstate\n"+
                                              "    \"print\" if you want that status will be printed\n"+
                                              "        Note: status can be very long at big configuration\n"+
                                              "    \"abort\" if you want to abort saving status\n"+
                                              ": ") % (fileName, fileName)
                                             )
                        # if match expected input then we have expected input (break the asking loop)
                        if saveName == "print" or saveName == "abort" or len(saveName) > 0 and (saveName[0] == "/" or saveName[0] == "~"):
                            break

                    if saveName == "print":
                        puts("\n============ CUT HERE =================\n"+status+"\n============ CUT HERE =================\n")
                        saveName = saveName_previous
                        # saftly don't break saving loop if scrollback for printed status is too short

                    # break also saving loop
                    if saveName == "abort":
                        break
    return

def load_status(fileName=""):
    """
    Loads status of easydeploy to fabstate file.
    
    :parm fileName: name of fabstate file.\n
    Example: ``easydeploy/core/snake.fabstate`` if ``fileName = "snake"``\n
    or\n
    ``easydeploy/core/.fabstate`` if ``fileName = ""``\n
    :type fileName: str
    
    :returns: None
    
    Example (status is loaded from ``easydeploy/core/.fabstate``)::
    
        from easydeploy.core import load_status, save_status
        #
        # There can be code which doesn't using state decorator.
        #
        # Load previous status::
        load_status()
        #
        # Do additional operations and save new status::
        #
        # save status to fabstate file at easydeploy/core/.fabstate
        save_status()
    
    Example (status is loaded from ``easydeploy/core/snake.fabstate``)::
    
        from easydeploy.core import load_status, save_status
        #
        # There can be code which doesn't using state decorator.
        #
        # Load previous status::
        load_status("snake")
        #
        # Do additional operations and save new status::
        #
        # save status to fabstate file at easydeploy/core/snake.fabstate
        save_status("snake")
    """
    # get current directory
    totalPath = os.path.realpath(__file__)
    directory = os.path.split(totalPath)[0]+"/"
    # full path of the file
    saveName = directory+fileName+".fabstate"

    while True:
        try:
            # read the file
            content = file(saveName,"rb").read()
            # convert content to python variable
            state, config = yaml.load(content)
            if state != None:
                env.state = state
            if config != None:
                env.config = config

            puts("Status loaded successfully", flush=True)
            break

        except IOError,e:
            errmessage = "Error when reading file %s: %s (%i)\n" % (saveName, e.args[1], e.args[0])
            if not (hasattr(env,"state_ask") and env.state_ask):
                abort(errmessage)
            else:
                warn(errmessage)
                if not confirm("Do you want to specify new path (unless new status will be used)?"):
                    puts("New status used.", flush=True)
                    break
                else:
                    # get new path
                    saveName = raw_input(("Enter absolute path of easydeploy\n"+
                                          "    eg. /home/john/%s.fabstate or ~/%s.fabstate\n"+
                                          ": ") % (fileName, fileName))
        except yaml.parser.ParserError, e:
            abort("yaml.parser.ParserError: "+str(e.context)+"\n"+
                  str(e.context_mark)+"\n"+
                  str(e.problem)+"\n"+
                  str(e.problem_mark))

    return


class state(object):
    """
    Decorator for handling states and its errors.

    .. note::

        Its main task is to provide a system for checking for provided dependencies
        among different tasks. So if some task fails, execution can continue and
        tasks that depends on whatever failed task provides won't run.

    .. warning::

        This decorator will not run task dependencies instead of you, its main
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
            if hasattr(env,"state_ignore") and env.state_ignore:
                return fn(*args)

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
                if self.provides and \
                    all(x in env.state[env.host] for x in self.provides):
                    puts("This task has already been executed, so we decide to skip it")
                    return

            # check that all dependences are installed
            if self.depends and (not all(x in env.state[env.host] for x in self.depends)):
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

    if hasattr(env,"state_ignore") and env.state_ignore:
        return

    # add state dictionary (happens first time only)
    if not hasattr(env,"state"):
        env.state={}

    provides=provides if not isinstance(provides,basestring) else [provides]

    # Check if task should be skipped if it is already provided
    # with what state provides
    if hasattr(env,"state_skip") and env.state_skip:
        if provides and all(x in env.state[env.host] for x in provides):
            puts("This task has already been executed, so we decide to skip it")
            return

    # Check if task should be skipped if it is already provided
    # with what state provides
    if hasattr(env,"state_skip") and env.state_skip:
        if provides and all(x in env.state[env.host] for x in provides):
            puts("This task has already been executed, so we decide to skip it")
            return

    # add empty list for saving installed stuff (happens first time only)
    if not env.state.has_key(env.host):
        env.state[env.host]=[]

    env.state[env.host]= list(set(env.state[env.host]+provides))

def unprovide(provides=[]):
    env.state[env.host]= filter(lambda el: el not in provides, env.state[env.host])

def get_envvar(varname, group=None, envdefault=None, domain=None):
    """
    Function for smarter retrival of variables from ``env``, with support of
    domains, groups and defaults. It gives user an option to organize
    settings in a tree.

    .. note::
            To understand how this function work you have to understand the
            philosophy behind it.

    **Philosophy:**

        When you are deploying systems you usually have to deal with a lot of input
        variables to your tasks and its templates. Usually you would stick everything
        to `env`, but this way you would end up with a deploy system with long and
        wierd variable names. This may sometimes be okay, but with systems deployment
        it usually gets a nightmare. At the same time you sometimes want to have an
        option to use default variable or task speciffic ones, based on some
        heuristics.

        This function tries to satisfy all the needs that you will end up when
        writing your deployment tasks and gives you a tool to organize your input.

    **Usage:**

        Because we don't want to stick everything to `env` we decided to stick
        everything to `env.settings`, that's because `env` has a lot of settings
        in it and you could easily override some needed option.

        .. note::
            You have to store all variables in ``env.settings``, not in ``env``.

        Lets say that you want to organize your options just a little bit. Well
        what you could do is to make an organization in a domains::

            >>> env.settings={"admin":{"email":"somemail@somedomain"}}

        Well now how to get that variable out is to issue something like::

            >>> env.get("settings").get("admin").get("email")
            somemail@somedomain

        Pretty long line of code i would say. That's where ``get_envvar`` could
        help you::

            >>> get_envvar("email", "admin")
            somemail@somedomain

        Well let's say that sometimes, some option exists in some domain, but
        sometimes it does no, and you want to get option from multiple domains,
        but prioritized. This could be usefull for example if you sometimes want
        to have task speciffic options, but sometimes not::

            >>> env.settings={"admin":{"email":"somemail@somedomain"},"sometask":{"email":"othermail@somedomain"}}
            >>> get_envvar("email","sometask,admin")
            othermail@somedomain

        In this case get_envvar will first look in ``sometask`` domain and then in
        ``admin`` domain. And of course::

            >>> env.settings={"admin":{"email":"somemail@somedomain"}}
            >>> get_envvar("email", "sometask,admin")
            somemail@somedomain

        Sometimes you want to have subdomains of domains::

            >>> env.settings={"admin":{"contacts":{"email":"somemail@somedomain"}}}
            >>> get_envvar("email","admin.contacts")
            somemail@somedomain

            >>> env.settings={"admin":{"contacts":{"email":"somemail@somedomain"}},"admin2":{"email":"othermail@somedomain"}}
            >>> get_envvar("email","admin.contacts,admin2")
            somemail@somedomain

        It works in as many depths as you want::

            >>> env.settings={"domain1":{"domain2":{"domain3":{"email":"somemail@somedomain"}}}}
            >>> get_envvar("email","domain1.domain2.domain3")
            somemail@somedomain

        Let's say that you want to have some variable name that is default and
        stored in ``env.settings``, for example ``default_password``, and still
        have some task speciffic variables like ``password``. What you could do is::

            >>> env.settings={"default_password":"pass1", "sometask":{"password":"pass2"}}
            >>> get_envvar("pass", "sometask", envdefault="default_password")
            pass2

            >>> env.settings={"default_password":"pass2"}
            >>> get_envvar("pass", "sometask", envdefault="default_password")
            pass1

        In some cases you don't only have options for single domain, but you want
        to have distinct options for different domains. For example you have to
        install your app per user basis. In this cases it's usually good to have
        your options in something like ``env.settings.$domain``, where domain is
        for example username::

            >>> env.settings={"somedomain":{"usertask":{"password":"somepass"}}}
            >>> get_envvar("password", "usertask", domain="somedomain")
            somepass

    **Basic way of operation:**

        - if domain and group are provided it searches for all comma sepeated
          groups in a domain located in settings for the group that has varname set.
        - if not found and domain is set it searches for varname in domain.
        - if not found and group is set it searches for all comma separated
        - groups in a settings for the group that has varname set.
        - if not found it searches for envdefault in settings and
        - at last if that is not found it searches for varname in settings

    :param varname: Name of variable to take from env or its groups
    :type varname: str
    :param group: Name of group to lookup or comma separated, prioritized
                    from more to less importancy groups to lookup.
                    Can also be in a dot separated format to lookup tree organized
                    groups.
    :type group: str
    :param envdefault: Default envvariable name if not found in groups/domains
    :type envdefault: str
    :param domain: Name of domain to search in.
                   Can also be in a dot separated format to lookup tree organized
                   domains.
    :type domain: str

    :returns: Value of setting variable
    """

    se= env.get("settings") or err("env.settings not set")
    group= env.get("group") or group
    domain= env.get("domain") or domain

    # first element of dot separated list
    f = lambda x: x.split(".")[0]
    # other elements of dot separated list(everything, but first)
    o = lambda x: ".".join(x.split(".")[1:])
    # recursivly checks if path p is in tree t and gets its value
    intree = lambda p,t: p and ( f(p) and (f(p) in t) and isinstance(t,dict) \
                     and intree(o(p),t[f(p)]) ) or (not p and t) or {}

    # checks if varname v in group t is in tree t and gets its value
    insects= lambda s,t,v: next(iter([intree(sect, t).get(v) for sect \
                           in s.split(",") if intree(sect, t).get(v)]), None)

    # if domain and group are provided it searches for all comma sepeated
    # groups in a domain located in settings for the group that has varname set.
    # if not found and domain is set it searches for varname in domain.
    # if not found and group is set it searches for all comma separated
    # groups in a settings for the group that has varname set.
    # if not found it searches for envdefault in settings and
    # at last if that is not found it searches for varname in settings.
    return (domain and group and
            insects(group,intree(domain,se),varname)) or \
           (domain and intree(domain,se).get(varname)) or \
           (group and insects(group,se,varname)) or \
            se.get(envdefault) or se.get(varname)

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
