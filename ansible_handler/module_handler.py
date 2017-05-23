import json
import logging.config
import os
import time
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count

import requests
from tornado.concurrent import run_on_executor
from tornado.gen import coroutine
from tornado.web import RequestHandler, asynchronous

from ansible_handler.ansible_api import LocalInventory, ANSRunner
from base import TargetStatus
from base.configuration import LOG_SETTINGS, common_config_dict

logging.config.dictConfig(LOG_SETTINGS)
logger = logging.getLogger('module_action')


class ModuleHandler(RequestHandler):
    executor = ThreadPoolExecutor(cpu_count())
    ansible_resource_dir = common_config_dict["ansible_resource_dir"]
    playbooks_dir = common_config_dict["playbook_base"]

    @asynchronous
    @coroutine
    def post(self):
        """
        content:
        hosts:
        parameters:
        version_info:
        jobid:
        taskid:
        jobname:
        :return:
        """
        logger.info("receive module handler post")
        body = self.request.body.decode()
        body = json.loads(body)
        logger.info("post body: {}".format(body))
        # 解析参数
        content = body.get('content', '')
        environment = content.get('environment', '')
        project = content.get('project', '')
        module = content.get('module', '')
        hostnames = body.get('hostnames', [])
        parameters = body.get('parameters')
        extend_key = body.get("extend_key", dict())
        is_local_inventory = parameters.get("is_local_inventory", False)
        if is_local_inventory:
            logger.info("###$$$")
            try:
                local_inventory = LocalInventory(environment, project)
            except Exception as e:
                logger.error(e)
            try:
                group = extend_key["group"]
                hostnames = local_inventory.host_list_by_group_module(group, module)
            except KeyError:
                logger.error("using local inventory, but group is null")
                response_data = {
                        "status": 2,
                        "message": "using local inventory, but group is null"
                    }
                self.write(response_data)
                self.finish()
            except FileNotFoundError:
                logger.error("using local inventory, but inventory file not found")
                response_data = {
                        "status": 2,
                        "message": "using local inventory, but inventory file not found"
                    }
                self.write(response_data)
                self.finish()
            except Exception :
                logger.exception("Exception Logged")
        if not hostnames:
            logger.error("hostnames is null")
            response_data = {
                        "status": 2,
                        "message": "hostnames is null"
                    }
            self.write(response_data)
            self.finish()
        version_info = body.get('version_info', '')
        version = version_info['version']
        build = version_info['build']
        file_list = version_info['file_list']
        resource = {
            "default": {
                 "hosts": hostnames,
                 "vars": {
                          "env": environment,
                          "project": project,
                          "module": module,
                          "version": version,
                          "build": build,
                          "file_list": file_list,
                          "extend_key": extend_key,
                          }
             },
        }
        logger.info(resource)
        jobid = body.get('jobid', '')
        task_id = body.get('taskid', '')
        jobname = body.get('jobname', '')
        task_callback_url = body.get('callback', '')
        playbook_name = jobname + '.yml'
        if not environment or not project or not module or not hostnames or not resource:
            message = "argument is null"
            logger.error(message)
            response_data = {
                        "status": 2,
                        "message": message
                    }
            self.write(response_data)
            self.finish()
        elif environment != common_config_dict["env"]:
            message = "environment is wrong"
            logger.error(message)
            response_data = {
                        "status": 2,
                        "message": message
                    }
            self.write(response_data)
            self.finish()
        else:
            host_list = []
            for host in hostnames:
                host_list.append(host['hostname'])
            # host字段用于playbook
            extra_vars = {
                             "host": host_list,
                             "ansible_resource_dir": self.ansible_resource_dir
                         }
            logger.info(extra_vars)
            result_data = yield self.run_ansible(resource, extra_vars, environment, project, module, playbook_name)
            logger.info("run ansible_resource result data: {}".format(result_data))
            if task_callback_url:
                status = TargetStatus.success.value
                messages = result_data.get('status', '')
                for host_status in messages.values():
                    if host_status['unreachable'] > 0 or host_status['failed'] > 0:
                        status = TargetStatus.fail.value
                call_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                callback_messages = []
                for host in messages.keys():
                    callback_message = dict()
                    callback_message['host'] = host
                    callback_message['message'] = dict()
                    callback_message['message']['success'] = []
                    for msg in result_data.get('ok').get(host, []):
                        call_msg = "{},{},{},{}".format(call_time, jobname, msg['task'], 'success')
                        callback_message['message']['success'].append(call_msg)
                    callback_message['message']['failed'] = []
                    for msg in result_data.get('failed').get(host, []):
                        call_msg = "{},{},{},{}".format(call_time, jobname, msg['task'], 'failed')
                        callback_message['message']['failed'].append(call_msg)
                    callback_message['message']['unreachable'] = []
                    for msg in result_data.get('unreachable').get(host, []):
                        call_msg = "{},{},{},{}".format(call_time, jobname, msg['task'], 'unreachable')
                        callback_message['message']['unreachable'].append(call_msg)
                    if messages[host]['failed'] > 0 or messages[host]['unreachable'] > 0:
                        callback_message['status'] = 2
                    else:
                        callback_message['status'] = 1
                    callback_messages.append(callback_message)
                # 阻塞
                yield self.callback(task_callback_url, jobid, task_id, jobname, status, callback_messages)
                if result_data:
                    # 这里是阻塞的，返回都为成功, 后续要加异步队列
                    """
                    **Response Syntax**

                    ```
                    Content-Type: application/json
                    {
                        "jobid":"",
                        "hosts" : [{"host":"10.99.70.51"},{"host":"10.99.70.52"}],
                        "jobname" : "demo",
                        "content":{"bu":"","group":"","model":""},
                        "parameters" : [{"k1":"v1"},{"k2":"v3"},{"k3":"v3"}],
                        "callback":"url"
                        "status":"" // 1：参数接收成功，2：参数接收失败
                    }
                    """
                    response_data = {
                        "jobid": jobid,
                        "taskid": task_id,
                        "status": 1
                    }
                    self.write(response_data)
                    self.finish()
            else:
                logger.info('do not need callback')
                response_data = {
                        "jobid": jobid,
                        "taskid": task_id,
                        "status": 1,
                        "message": result_data
                    }
                self.write(response_data)
                self.finish()

    @run_on_executor
    def run_ansible(self, resource, extra_vars, environment, project, module, playbook_name):
        playbook_path = os.path.join(self.playbooks_dir, project, module, playbook_name)
        logger.info('playbook_name:{}'.format(playbook_path))
        ansible_runner = ANSRunner(resource, environment, project, module)
        ansible_runner.run_playbook(extra_vars=extra_vars,playbook_path=playbook_path)
        result_data = ansible_runner.get_playbook_result()
        return json.loads(result_data)

    @run_on_executor
    def callback(self, callback_url, jobid, task_id, jobname, status, messages):
        payload = {
            "jobid": jobid,
            "taskid": task_id,
            "jobname": jobname,
            "status": status,
            "messages": messages
        }
        logger.info("module action callback: payload={}".format(payload))
        res = requests.post(callback_url, json=payload)
        if res.status_code == requests.codes.ok:
            context = res.json()
            logger.info("callback success:{}".format(context))
            if context['status'] == 1:
                return True
            else:
                return False
        else:
            logger.error("callback fail: {}".format(payload))
            return False

