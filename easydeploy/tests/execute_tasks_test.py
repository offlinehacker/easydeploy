import unittest

from fabric import state
from fabric.api import task, env, settings, execute
from easydeploy.core import execute_tasks  

class TestTaksExecution(unittest.TestCase):
    def testSimpleTasksAndEnvVars(self):
        self.task1executed= False
        self.task2executed= False
        self.task1_2executed= False
        self.task_with_params_executed= False
        self.task_with_settings_executed= False
        
        @task
        def task1():
            self.task1executed= True
            self.assertEqual(env["first"],"first_var")        
            self.assertNotIn("second", env)
            
        @task
        def task1_2():
            self.task1_2executed= True
            self.assertEqual(env["first"],"first_var")        
            self.assertNotIn("second", env)
        
        @task    
        def task2():
            self.task2executed= True
            self.assertEqual(env["second"],"second_var")   
            self.assertNotIn("first", env)
            
        @task    
        def task_with_params(param1,param2):
            self.task_with_params_executed= True
            self.assertEqual(param1,"param1")   
            self.assertEqual(param2,"param2")
            
        @task    
        def task_with_settings1():
            self.task_with_settings_executed= True
            
        @task    
        def task_with_settings2(param1,param2):
            self.task_with_settings_executed= True
            self.assertEqual(param1,"param1")   
            self.assertEqual(param2,"param2")
            
        @task    
        def task_with_settings3(param1,param2):
            self.task_with_settings_executed= True
            self.assertEqual(param1,"param1")   
            self.assertEqual(param2,"param2")
            self.assertIn("my_setting", env)
            
        #Dirty hack to emulate known fab tasks
        state.commands.update({"task1":task1, "task1_2":task1_2, 
                               "task2":task2, "task_with_params": task_with_params,
                               "task_with_settings1": task_with_settings1,
                               "task_with_settings2": task_with_settings2,
                               "task_with_settings3": task_with_settings3})
        
        first={
               "first":"first_var",
               "tasks":[
                        "task1",
                        "task1_2"
                        ]
               }
        
        second={
               "second":"second_var",
               "tasks":[
                        "task2"
                        ]
               }
        
        params={
               "tasks":[
                        ("task_with_params","param1","param2"),
                        ("task_with_params",{"param1":"param1", "param2":"param2"})
                        ]
               }
        
        _settings={
                  "tasks":[
                              {"name": "task_with_settings1"},
                              {"name": "task_with_settings2",
                               "params": ["param1","param2"]},
                              {"name": "task_with_settings3",
                               "params": ["param1","param2"],
                               "settings": {"my_setting": True}},
                              ]
                  }
            
        @task
        def main_task():
            with settings(**first):
                execute_tasks(env.tasks)
                self.assertTrue(self.task1executed)  
                self.assertTrue(self.task1_2executed) 
            with settings(**second):
                execute_tasks(env.tasks)
                self.assertTrue(self.task2executed)
            with settings(**params):
                execute_tasks(env.tasks)
                self.assertTrue(self.task_with_params_executed)
            with settings(**_settings):
                execute_tasks(env.tasks)
                self.assertTrue(self.task_with_settings_executed)
                    
        execute(main_task)
        state.commands={}
        
    def testTasksWithNamespace(self):
        self.task1executed= False
        self.task2executed=False
        self.task_with_params_executed= False
        
        @task
        def task1():
            self.task1executed= True
        
        @task    
        def task2():
            self.task2executed= True
            
        @task    
        def task_with_params(param1,param2):
            self.task_with_params_executed= True
            self.assertEqual(param1,"param1")   
            self.assertEqual(param2,"param2")

        #Dirty hack to emulate fab            
        state.commands.update({"namespace":{"task1":task1, "task2":task2,
                                            "task_with_params":task_with_params}})
        
        first={
               "tasks":{"namespace":[
                                     "task1",
                                     "task2",
                                     ("task_with_params","param1","param2"),
                                     ("task_with_params",{"param1":"param1", "param2":"param2"})
                                     ]
                        }
               }
            
        @task
        def main_task():
            with settings(**first):
                    execute_tasks(env.tasks)
                    self.assertTrue(self.task1executed)
                    self.assertTrue(self.task2executed)
                    self.assertTrue(self.task_with_params_executed)
                    
        execute(main_task)
        state.commands={}
        