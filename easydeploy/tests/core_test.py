from __future__ import with_statement

import unittest
import os

from fabric.api import local, settings, abort, run, cd
from fabric.contrib.console import confirm
from fabric.context_managers import show
from fabric.api import env

from easydeploy.core import state
from easydeploy.core import get_envvar

class TestStateDecorator(unittest.TestCase):
    def testUnsatisfiedDeps(self):
        # env flags
        env.warn_only = False
        env.state_warn_only = True
        env.state_ask = False

        # reset status
        env.state={}

        # flag if function will be executed
        self.fail_flag = 0

	# example function
        @state(provides="custom.something2", depends="custom.something1")
        def fail1():
            self.fail_flag = 1

        # call
        fail1()

        # function shouldn't be called, so flag shouldn't be changed
        assert self.fail_flag == 0

    def testFunctionWithoutDeps(self):
        # env flags
        env.warn_only = False
        env.state_warn_only = True
        env.state_ask = False

        # reset status
        env.state={}

        # flag if function will be executed
        self.succ_flag = 0

	# example function
        @state(provides="custom.something1")
        def succ():
            self.succ_flag = 1

        # call
        succ()

        # function should be called, so flag shouldn't be changed
        assert self.succ_flag == 1

    def testOneChain(self):
        # env flags
        env.warn_only = False
        env.state_warn_only = True
        env.state_ask = False

        # reset status
        env.state={}

        # flag if function will be executed
        self.succ1_flag = 0
        self.succ2_flag = 0

	# example functions
        @state(provides="custom.something1")
        def succ1():
            self.succ1_flag = 1
        @state(provides="custom.something2", depends="custom.something1")
        def succ2():
            self.succ2_flag = 1

        # call
        succ1()
        succ2()

        # function should be called, so flag shouldn't be changed
        assert self.succ1_flag == 1
        assert self.succ2_flag == 1

    def testRerunedDep(self):
        # env flags
        env.warn_only = False
        env.state_warn_only = True
        env.state_ask = False
        # task will be re-executed
        env.state_skip = False

        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0
        self.flag2 = 0
        self.flag3 = 0

	# example functions
        @state(provides="entry1")
        def fun1():
            self.flag1 = 1
        @state(provides="entry1")
        def fun2():
            self.flag2 = 1
        @state(provides="entry2", depends="entry1")
        def fun3():
            self.flag3 = 1

        # call
        fun1()
        fun2()
        fun3()

        # function should be called, so flag shouldn't be changed
        assert self.flag1 == 1
        assert self.flag2 == 1
        assert self.flag3 == 1

    def testRerunedDep1(self):
        # env flags
        env.warn_only = False
        env.state_warn_only = True
        env.state_ask = False
        # task will be re-executed
        env.state_skip = True

        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0
        self.flag2 = 0
        self.flag3 = 0

	# example functions
        @state(provides="entry1")
        def fun1():
            self.flag1 = 1
        @state(provides="entry1")
        def fun2():
            self.flag2 = 1
        @state(provides="entry2", depends="entry1")
        def fun3():
            self.flag3 = 1

        # call
        fun1()
        fun2()
        fun3()

        # function should be called, so flag shouldn't be changed
        assert self.flag1 == 1
        assert self.flag2 == 0
        assert self.flag3 == 1

    def testRerunedDep2(self):
        # env flags
        env.warn_only = False
        env.state_warn_only = True
        env.state_ask = False
        # task will be re-executed
        env.state_skip = True

        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0
        self.flag2 = 0
        self.flag3 = 0

	# example functions
        @state(provides=["entry1","entry2"])
        def fun1():
            self.flag1 = 1
        @state(provides="entry1")
        def fun2():
            self.flag2 = 1
        @state(provides="entry3", depends=["entry1","entry2"])
        def fun3():
            self.flag3 = 1

        # call
        fun1()
        fun2()
        fun3()

        # function should be called, so flag shouldn't be changed
        assert self.flag1 == 1
        assert self.flag2 == 0
        assert self.flag3 == 1

    def testRerunedDep3(self):
        # env flags
        env.warn_only = False
        env.state_warn_only = True
        env.state_ask = False
        # task won't be re-executed
        env.state_skip = True

        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0
        self.flag2 = 0
        self.flag3 = 0

	# example functions
        @state(provides=["entry1","entry2"])
        def fun1():
            self.flag1 = 1
        @state(provides=["entry1","entry2","entry3"])
        def fun2():
            self.flag2 = 1
        @state(provides="entry4", depends=["entry1","entry2","entry3"])
        def fun3():
            self.flag3 = 1

        # call
        fun1()
        fun2()
        fun3()

        # function should be called, so flag shouldn't be changed
        assert self.flag1 == 1
        assert self.flag2 == 1
        assert self.flag3 == 1

    def testProvidesIsntSpecified(self):
        # env flags
        env.warn_only = False
        env.state_warn_only = False
        env.state_ask = False
        # task will be re-executed
        env.state_skip = True

        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0
        self.flag2 = 0

	# function will abort
        @state(depends=["entry1","entry2"])
        def fun1():
            self.flag1 = 1

        # call
        try:
            fun1()
        except SystemExit,se:
            # message must be This task hasn't "provides"
            self.flag2 = 1

        # function should be called
        assert self.flag1 == 0
        # it won't crashed
        assert self.flag2 == 0

    def testProvidesIsntSpecified2(self):
        # env flags
        env.warn_only = False
        env.state_warn_only = False
        env.state_ask = False
        # task will be re-executed
        env.state_skip = True

        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0
        self.flag2 = 0

	# function will abort
        @state(depends=["entry1","entry2"])
        def fun1():
            self.flag1 = 1

        # call
        try:
            fun1()
        except SystemExit,se:
            # message must be This task hasn't "provides"
            self.flag2 = 1

        # function should be called
        assert self.flag1 == 0
        # it won't crashed
        assert self.flag2 == 0

    def testWarnOnlyFalse(self):
        # test will halt because dependences isn't satisfyed
        # env flags
        env.warn_only = False
        env.state_warn_only = False
        env.state_ask = False

        # task will be re-executed
        env.state_skip = True

        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0

	# function will abort
        @state(provides=["cheese"], depends=["entry1","entry2"])
        def fun1():
            self.flag1 = 1

        # call
        try:
            fun1()
        except SystemExit,se:
            # message must be This task hasn't "provides"
            self.flag1 = 0

        # function should be called, so flag shouldn't be changed
        assert self.flag1 == 0

class TestGetEnvVar(unittest.TestCase):
    def testGetFromRoot(self):
        env.settings={"email":"a", "admin":{}}
        self.assertEqual(get_envvar("email", "admin"), "a")

    def testGetFromGroup(self):
        env.settings={"email":"a", "admin":{"email":"b"}}
        self.assertEqual(get_envvar("email", "admin"), "b")
        env.settings={"email":"a", "admin":{}}
        self.assertEqual(get_envvar("email", "admin"), "a")

    def testOverrideGroup(self):
        with settings(group="info"):
            env.settings={"email":"a", "admin":{"email":"b"}, "info":{"email":"c"}}
            self.assertEqual(get_envvar("email", "admin"), "c")

    def testGetFromDomain(self):
        env.settings={"root":{ "admin":{"email":"a"}},"offlinehacker":{ "admin":{"email":"b"}}}
        self.assertEqual(get_envvar("email", "admin", domain="root"), "a")
        self.assertEqual(get_envvar("email", "admin", domain="offlinehacker"), "b")

    def testOverrideDomain(self):
        with settings(domain="offlinehacker"):
            env.settings={"root":{"email":"b"}, "offlinehacker":{"email":"c"}}
            self.assertEqual(get_envvar("email", domain="root"), "c")

    def testGetFromPriorityGroup(self):
        env.settings={"email":"a", "admin":{"email":"b"}, "info":{"email":"c"}}
        self.assertEqual(get_envvar("email", "admin,info"), "b")
        env.settings={"email":"a", "admin":{}, "info":{"email":"c"}}
        self.assertEqual(get_envvar("email", "admin,info"), "c")
        env.settings={"email":"a", "admin":{}, "info":{}}
        self.assertEqual(get_envvar("email", "admin,info"), "a")

    def testGetFromSubgroupGroup(self):
        env.settings={"group1":{"group11":{"val":"a"},
                                "group12":{"val":"b"}},
                      "group2":{"group21":{"val":"c"},
                                "group22":{"val":"d"}}}
        self.assertEqual(get_envvar("val","group2.group21"), "c")

    def testGetFromSubgroupPriorityGroup(self):
        env.settings={"email":"a", "group1":{"admin":{"email":"b"}},
                      "group2":{"info":{"email":"c"}}}
        self.assertEqual(get_envvar("email", "group1.admin,group2.info"), "b")
        env.settings={"email":"a", "group1":{"admin":{}},
                      "group2":{"info":{"email":"c"}}}
        self.assertEqual(get_envvar("email", "group1.admin,group2.info"), "c")
        env.settings={"email":"a", "group1":{"admin":{}}}
        self.assertEqual(get_envvar("email", "group1.admin,group2.info"), "a")

class TestUploadTemplateJinja2(unittest.TestCase):
    def write_template(self, fname, contents):
        f=open(fname,"w")
        f.write(contents)
        f.close

    def test_upload(self):
        template="""{{get_envvar('test','test')}}"""
        self.ret=""

        import easydeploy.core

        def dummy_put(local_path,remote_path,use_sudo):
            print local_path.getvalue()
            self.ret=local_path.getvalue()

        self.write_template("template.tpl", template)
        env.path="."
        env.settings={"test":{"test":"test2"}}
        easydeploy.core.put= dummy_put
        easydeploy.core.upload_template_jinja2("template.tpl", "/tmp/template.tpl")

        assert self.ret=="test2"

        os.unlink("template.tpl")
