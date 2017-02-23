#!/usr/bin/env python
# -*- coding=utf-8 -*-

# ansible-playbook run_script.yml -e "env=test project=jpol module=mb-inprc version=v1.6.16 build=37 host=['10.99.70.75','10.99.70.73'] script_name=1.py " --ask-pass --ssh-extra-args='-o StrictHostKeyChecking=no'

import json,sys,os
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory,Host,Group
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
from ansible.executor.playbook_executor import PlaybookExecutor
from base.resource_config import inventory_data
import logging
import time

class MyInventory(Inventory):
    def __init__(self, resource, loader, variable_manager):
        self.resource = resource
        self.inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=[])
        self.dynamic_inventory()

    def add_dynamic_group(self, hosts, groupname, groupvars=None):
        my_group = Group(name=groupname)
        if groupvars:
            for key, value in groupvars.items():
                my_group.set_variable(key, value)
        for host in hosts:
            # set connection variables
            hostname = host.get("hostname")
            hostip = host.get('ip', hostname)
            hostport = host.get("port")
            username = host.get("username")
            password = host.get("password")
            ssh_key = host.get("ssh_key")
            my_host = Host(name=hostname, port=hostport)
            my_host.set_variable('ansible_ssh_host', hostip)
            my_host.set_variable('ansible_ssh_port', hostport)
            my_host.set_variable('ansible_ssh_user', username)
            my_host.set_variable('ansible_ssh_pass', password)
            my_host.set_variable('ansible_ssh_private_key_file', ssh_key)
            for key, value in host.items():
                if key not in ["hostname", "port", "username", "password"]:
                    my_host.set_variable(key, value)
            my_group.add_host(my_host)

        self.inventory.add_group(my_group)

    def dynamic_inventory(self):
        if isinstance(self.resource, list):
            self.add_dynamic_group(self.resource, 'default_group')
        elif isinstance(self.resource, dict):
            for groupname, hosts_and_vars in self.resource.items():
                self.add_dynamic_group(hosts_and_vars.get("hosts"), groupname, hosts_and_vars.get("vars"))


class ModelResultsCollector(CallbackBase):

    def __init__(self, *args, **kwargs):
        super(ModelResultsCollector, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}

    def v2_runner_on_unreachable(self, result):
        self.host_unreachable[result._host.get_name()] = result

    def v2_runner_on_ok(self, result,  *args, **kwargs):
        self.host_ok[result._host.get_name()] = result

    def v2_runner_on_failed(self, result,  *args, **kwargs):
        self.host_failed[result._host.get_name()] = result

class PlayBookResultsCollector(CallbackBase):
    CALLBACK_VERSION = 2.0
    """
    {
        "failed": {"10.99.70.61": []},
        "ok": {
            "10.99.70.61": [{"task": "0.1 MAKE DIR"}, {"task": "1. UPDATE VERSION"}]
            },
        "unreachable": {},
        "skipped": {},
        "status": {
            "10.99.70.61": {
                "failed": 1, "skipped": 0, "unreachable": 0, "ok": 2, "changed": 0
                }
            }
        }
    """
    def __init__(self,taskList, *args, **kwargs):
        super(PlayBookResultsCollector, self).__init__(*args, **kwargs)
        self.task_ok = {}
        self.task_skipped = {}
        self.task_failed = {}
        self.task_status = {}
        self.task_unreachable = {}

    def v2_runner_on_ok(self, result, *args, **kwargs):
        if result._host.get_name() in taskList:
            data = {}
            data['task'] = str(result._task).replace("TASK: ","")
            taskList[result._host.get_name()].get('ok').append(data)
        self.task_ok[result._host.get_name()]  = taskList[result._host.get_name()]['ok']

    def v2_runner_on_failed(self, result, *args, **kwargs):
        if result._host.get_name() in taskList:
            data = {}
            data['task'] = str(result._task).replace("TASK: ","")
            msg = result._result.get('stderr')
            if msg is None:
                results = result._result.get('results')
                if result:
                    task_item = {}
                    for rs in results:
                        msg = rs.get('msg')
                        if msg:
                            task_item[rs.get('item')] = msg
                            data['msg'] = task_item
                    taskList[result._host.get_name()]['failed'].append(data)
                else:
                    msg = result._result.get('msg')
                    data['msg'] = msg
                    taskList[result._host.get_name()].get('failed').append(data)
        else:
            data = {}
            msg = result._result.get('stderr')
            data['msg'] = msg
            taskList[result._host.get_name()].get('failed').append(data)
        self.task_failed[result._host.get_name()] = taskList[result._host.get_name()]['failed']

    def v2_runner_on_unreachable(self, result):
        self.task_unreachable[result._host.get_name()] = result

    def v2_runner_on_skipped(self, result):
        if result._host.get_name() in taskList:
            data = {}
            data['task'] = str(result._task).replace("TASK: ","")
            taskList[result._host.get_name()].get('skipped').append(data)
        self.task_ok[result._host.get_name()]  = taskList[result._host.get_name()]['skipped']

    def v2_playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            self.task_status[h] = {
                                       "ok":t['ok'],
                                       "changed" : t['changed'],
                                       "unreachable":t['unreachable'],
                                       "skipped":t['skipped'],
                                       "failed":t['failures']
                                   }

class ANSRunner(object):
    def __init__(self,resource,*args, **kwargs):
        self.resource = resource
        self.inventory = None
        self.variable_manager = None
        self.loader = None
        self.options = None
        self.passwords = None
        self.callback = None
        self.__initializeData()
        self.results_raw = {}

    def __initializeData(self):
        Options = namedtuple('Options', ['connection','module_path', 'forks', 'timeout',  'remote_user',
                'ask_pass', 'private_key_file', 'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args',
                'scp_extra_args', 'become', 'become_method', 'become_user', 'ask_value_pass', 'verbosity',
                'check', 'listhosts', 'listtasks', 'listtags', 'syntax'])

        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        remote_user = 'admin'
        private_key_file = '/home/admin/.ssh/id_rsa'
        ssh_extra_args = '-o StrictHostKeyChecking=no'
        self.options = Options(connection='smart', module_path=None, forks=100, timeout=10,
                remote_user=remote_user, ask_pass=False, private_key_file=private_key_file, ssh_common_args=None, ssh_extra_args=ssh_extra_args,
                sftp_extra_args=None, scp_extra_args=None, become=None, become_method=None,
                become_user='root', ask_value_pass=False, verbosity=None, check=False, listhosts=False,
                listtasks=False, listtags=False, syntax=False)

        self.passwords = dict(sshpass=None, becomepass=None)
        self.inventory = MyInventory(self.resource, self.loader, self.variable_manager).inventory
        self.variable_manager.set_inventory(self.inventory)

    def run_model(self, host_list, module_name, module_args):
        """
        run module from andible ad-hoc.
        module_name: ansible module_name
        module_args: ansible module args
        """
        play_source = dict(
                name="Ansible Play",
                hosts=host_list,
                gather_facts='no',
                tasks=[dict(action=dict(module=module_name, args=module_args))]
        )
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)
        tqm = None
        self.callback = ModelResultsCollector()
        try:
            tqm = TaskQueueManager(
                    inventory=self.inventory,
                    variable_manager=self.variable_manager,
                    loader=self.loader,
                    options=self.options,
                    passwords=self.passwords,
            )
            tqm._stdout_callback = self.callback
            result = tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()

    def run_playbook(self, extra_vars, playbook_path, ):
        """
        run ansible playbook
        """
        global taskList
        taskList = {}
        self.variable_manager.extra_vars = extra_vars
        host_list = extra_vars.get('host', [])
        logging.info('{} run playbook {}'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), playbook_path))

        for host in host_list:
            taskList[host] = {}
            taskList[host]['ok'] = []
            taskList[host]['failed'] = []
            taskList[host]['skppied'] = []
            logging.info('{} run at host {}'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), host))
        try:
            self.callback = PlayBookResultsCollector(taskList)
            executor = PlaybookExecutor(
                playbooks=[playbook_path], inventory=self.inventory, variable_manager=self.variable_manager, loader=self.loader,
                options=self.options, passwords=self.passwords,
            )
            executor._tqm._stdout_callback = self.callback
            executor.run()
        except Exception as e:
            print(e)
            return False

    def get_model_result(self):
        self.results_raw = {'success':{}, 'failed':{}, 'unreachable':{}}
        for host, result in self.callback.host_ok.items():
            self.results_raw['success'][host] = result._result

        for host, result in self.callback.host_failed.items():
            self.results_raw['failed'][host] = result._result

        for host, result in self.callback.host_unreachable.items():
            self.results_raw['unreachable'][host]= result._result
        return json.dumps(self.results_raw)

    def get_playbook_result(self):
        self.results_raw = {'skipped':{}, 'failed':{}, 'ok':{},"status":{},'unreachable':{}}

        for host, result in self.callback.task_ok.items():
            self.results_raw['ok'][host] = result

        for host, result in self.callback.task_failed.items():
            self.results_raw['failed'][host] = result

        for host, result in self.callback.task_status.items():
            self.results_raw['status'][host] = result

        for host, result in self.callback.task_skipped.items():
            self.results_raw['skipped'][host] = result

        for host, result in self.callback.task_unreachable.items():
            self.results_raw['unreachable'][host] = result._result
        return json.dumps(self.results_raw)



if __name__ == '__main__':
    #resource = [
    #             {"hostname": "192.168.100.4", "port": "22", "username": "root", "password": "pw"},
    #             {"hostname": "192.168.100.5", "port": "22", "username": "root", "password": "pw"},
    #                 {"hostname": "192.168.1.1", "port": "22", "username": "root", "password": "pw"}
    #             ]
    resource =  inventory_data['jpol']

    rbt = ANSRunner(resource)
    #rbt.run_model(host_list=["10.99.70.73", "10.99.70.75"],module_name='ping',module_args="")
    extra_vars = {
                "host": ['10.99.70.61']
                 }
    playbook_path='/home/admin/publish/playbooks/test/jpol/mb-inprc/update.yml'
    rbt.run_playbook(extra_vars=extra_vars,playbook_path=playbook_path)
    data = rbt.get_playbook_result()
    print(data)

