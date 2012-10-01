from __future__ import with_statement

import unittest, os, time

from easydeploy.core import state
from easydeploy.core import load_status, save_status

from fabric.api import local, settings, abort, run, cd
from fabric.contrib.console import confirm
from fabric.context_managers import show
from fabric.api import env


class TestLoadSaveStatus(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # direcotry of fabstate files
        totalPath = os.path.realpath(__file__)
        self.fabstate_directory = os.path.split(totalPath)[0]+"/../core/"

        # backup old statuses
        for fname in os.listdir(self.fabstate_directory):
            if fname.endswith(".fabstate"):
                os.rename(self.fabstate_directory+fname, self.fabstate_directory+fname+".fabstate_backup")
        # no return here

    @classmethod
    def tearDownClass(self):
        # restore old statuses
        for fname in os.listdir(self.fabstate_directory):
            if fname.endswith(".fabstate_backup"):
                os.rename(self.fabstate_directory+fname, self.fabstate_directory+fname[:-len(".fabstate_backup")])

    def setUp(self):
        # env flags
        env.warn_only = False
        env.state_warn_only = False
        env.state_ask = False
        env.state_skip = True
        if hasattr(env, "config"):
            del env.config

    def tearDown(self):
        # remove test fabstate files
        for fname in os.listdir(self.fabstate_directory):
            if fname.endswith(".fabstate"):
                os.remove(self.fabstate_directory+fname)
    def doPerms(self, prefix=""):
        os.chmod(self.fabstate_directory+prefix+".fabstate", 0664)

    def revokePerms(self, prefix=""):
        os.chmod(self.fabstate_directory+prefix+".fabstate", 0000)

    def createEmptyFabstate(self, prefix=""):
        file(self.fabstate_directory+prefix+".fabstate", "wb").write("")

    def testSaveLoad(self):
        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0

        # example function
        @state(provides="custom.something")
        def fun1():
            self.flag1 = 1

        # call
        fun1()

        # function should be executed
        assert self.flag1 == 1

        save_status()

        # reset status
        env.state={}
        
        load_status()

        # reset flag
        self.flag1 = 0

        # call
        fun1()

        # function shouldn't be called because status is already provided
        assert self.flag1 == 0

    def testCustomName(self):
        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0

        # example function
        @state(provides="custom.something")
        def fun1():
            self.flag1 = 1

        # call
        fun1()

        # function should be executed
        assert self.flag1 == 1

        save_status("snake")

        # reset status
        env.state={}
        
        load_status("snake")

        # reset flag
        self.flag1 = 0

        # call
        fun1()

        # function shouldn't be called because status is already provided
        assert self.flag1 == 0

    def testReadPermissions(self):
        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0
        self.flag2 = 0

        # example function
        @state(provides="custom.something")
        def fun1():
            self.flag1 = 1

        # call
        fun1()

        # function should be executed
        assert self.flag1 == 1

        save_status("snake")

        # reset status
        env.state={}

        self.revokePerms("snake")
        try:
            load_status("snake")
        except SystemExit,e:
            self.flag2 = 1
        self.doPerms("snake")

        # deploying is halted because loader can't read status file
        assert self.flag2 == 1

    def testUnparsableFile(self):
        # reset status
        env.state={}

        # flag if function will be executed
        self.flag1 = 0
        self.flag2 = 0

        # example function
        @state(provides="custom.something")
        def fun1():
            self.flag1 = 1

        # call
        fun1()

        # function should be executed
        assert self.flag1 == 1

        save_status("snake")

        # reset status
        env.state={}

        # doInvalidFile
        file(self.fabstate_directory+"snake.fabstate", "wb").write('{9: la, a: 4\n')

        try:
            load_status("snake")
        except SystemExit,e:
            self.flag2 = 1
        self.doPerms("snake")

        # deploying is halted because loader can't read status file
        assert self.flag2 == 1

#    def testPrintStatus(self):
#        # reset status
#        env.state={}
#        env.state_ask=True
#
#        # flag if function will be executed
#        self.flag1 = 0
#        self.flag2 = 0
#        self.flag3 = 0
#
#        # example function
#        @state(provides="custom.something")
#        def fun1():
#            self.flag1 = 1
#
#        # call
#        fun1()
#
#        # function should be executed
#        assert self.flag1 == 1
#
#        self.createEmptyFabstate("snake")
#        self.revokePerms("snake")
#        try: # on some way interactive session must be tested
#            save_status("snake")
#        except SystemExit,e:
#            self.flag2 = 1
#
#        self.doPerms("snake")
#
#        # deploying is halted because loader can't read status file
#        assert self.flag2 == 1

