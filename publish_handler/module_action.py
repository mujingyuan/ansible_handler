from tornado.web import RequestHandler, asynchronous
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from tornado.httpclient import AsyncHTTPClient
import requests
import json
import os
from base.ansible_api import ANSRunner
import logging.config
import time
from base.resource_config import inventory_data
from base.configuration import LOG_SETTINGS

publish_base_dir = '/home/admin/publish'
logging.config.dictConfig(LOG_SETTINGS)
logger = logging.getLogger('module_action')

class ModuleUpdateHandler(RequestHandler):
    executor = ThreadPoolExecutor(8)
    playbooks_dir = os.path.join(publish_base_dir, 'playbooks')

    @asynchronous
    @coroutine
    def post(self):
        logger.info("receive module update post")
        body = self.request.body.decode()
        body = json.loads(body)
        logger.info("post body: {}".format(body))
        # 解析参数
        content = body.get('content', '')
        environment = content.get('environment', '')
        project = content.get('project', '')
        module = content.get('module', '')
        hosts = body.get('hosts')
        parameters = body.get('parameters')
        version_info = body.get('version_info', '')
        version = version_info['version']
        build = version_info['build']
        host_list = []
        for host in hosts:
            host_dict = dict()
            host_dict["hostname"] = host['host']
            host_list.append(host_dict)
        resource =  {
            "default": {
                 "hosts": host_list,
                 "vars": {
                          "env": environment,
                          "project": project,
                          "module": module,
                          "version": version,
                          "build": build,
                          }
             },
        }
        jobid = body.get('jobid', '')
        task_id = body.get('taskid', '')
        jobname = body.get('jobname', '')
        task_callback_url = body.get('callback', '')
        playbook_name = jobname + '.yml'
        if not environment or not project or not module or not host_list or not resource:
            self.write('argument is null')
            logger.info('argument is null')
            self.finish()
        else:
            hostlist = []
            for host in hosts:
                hostlist.append(host['host'])
            extra_vars = {
                             "host": hostlist
                         }
            playbook_path = os.path.join(self.playbooks_dir, environment, project, module, playbook_name)
            logger.info('playbook_name:{}'.format(playbook_path))
            result_data = yield self.run_ansible(resource, extra_vars, playbook_path)
            logger.info("run ansible result data: {}".format(result_data))
            if task_callback_url:
                if result_data['failed'] and result_data['unreachable']:
                    status = 2
                else:
                    status = 1
                messages = result_data.get('status', '')
                callback_messages = []
                for host in messages.keys():
                    callback_message = dict()
                    callback_message['host'] = host
                    callback_message['message'] = result_data.get('ok')[host]
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
                        "status": 1
                    }
                self.write(response_data)
                self.finish()

    @run_on_executor
    def run_ansible(self, resource, extra_vars, playbook_path):
        ansible_runner = ANSRunner(resource)
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

