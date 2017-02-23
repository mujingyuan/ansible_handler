from tornado.web import RequestHandler, asynchronous
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from tornado.httpclient import AsyncHTTPClient
import requests
import json
import os
from base.ansible_api import ANSRunner
import logging
import time
from base.resource_config import inventory_data
from base.configuration import LOG_SETTINGS

publish_base_dir = '/home/admin/publish'

logging.config.dictConfig(LOG_SETTINGS)
logger = logging.getLogger('module_action')

class ModuleUpdateHandler(RequestHandler):
    executor = ThreadPoolExecutor(8)
    report_url = 'http://10.99.7.15:83/api/release/create'
    playbooks_dir = os.path.join(publish_base_dir, 'playbooks')

    @asynchronous
    @coroutine
    def post(self):
        logger.info("receive module update post")
        body = self.request.body.decode()
        body = json.loads(body)
        logger.info("post body: {}".format(body))
        content = body.get('content', '')
        environment = content.get('environment', '')
        project = content.get('project', '')
        module = content.get('module', '')
        # 兼容新旧版hosts参数
        host_list = body.get('host_list', [])
        hosts = body.get('hosts', [])
        if not host_list:
            for host in hosts:
                if isinstance(host, str):
                    host_list.append(host)
                elif isinstance(host, dict):
                    host_list.append(host['host'])
        resource = body.get('resource', inventory_data[project])
        jobid = body.get('jobid', '')
        task_id = body.get('taskid', '')
        jobname = body.get('jobname', '')
        task_callback_url = body.get('callback', '')
        playbook_name = jobname + '.yml'
        logger.info('playbook_name:{}'.format(playbook_name))
        if not environment or not project or not module or not host_list or not resource:
            self.write('argument is null')
            logger.info('argument is null')
            self.finish()
        else:
            module_id = self.get_module_id(project, module)
            if module_id:
                report_responses_status = yield self.report_tasks_status(module_id, jobname, 0)
            else:
                logging.info('{} module_id is null'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
                self.write('module_id is null')
                self.finish()
            if report_responses_status:
                extra_vars = {
                                 "host": host_list
                             }
                playbook_path = os.path.join(self.playbooks_dir, environment, project, module, playbook_name)
                result_data = yield self.run_ansible(resource, extra_vars, playbook_path)
                print('callback {}'.format(task_callback_url))
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
                    callback_status = yield self.callback(task_callback_url, jobid, task_id, jobname, status, callback_messages)
                    if callback_status:
                        print(callback_status)
                        print('callback success')
                    else:
                        print('callback fail')
                if result_data:
                    # 这里是阻塞的，返回都为成功
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
                logging.info('{} mark task fail'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
                self.write('mark task fail')
                self.finish()

    @run_on_executor
    def run_ansible(self, resource, extra_vars, playbook_path):
        ansible_runner = ANSRunner(resource)
        ansible_runner.run_playbook(extra_vars=extra_vars,playbook_path=playbook_path)
        result_data = ansible_runner.get_playbook_result()
        return json.loads(result_data)

    def get_module_id(self, project, module):
       return project +'/' + module

    @run_on_executor
    def report_tasks_status(self, module_id, action, status_code):
        payload = {"module_id": module_id,
                   "action": action,
                   "status": status_code}
        return True
        # res = requests.post(self.report_url, json=payload)
        # print(res.status_code)
        # context = res.json()
        # if res.status_code == requests.codes.ok and context['status'] == 1 :
        #     return True
        # else:
        #     print(context)
        #     return False

    @run_on_executor
    def callback(self, callback_url, jobid, task_id, jobname, status, messages):
        print("task callback")
        payload = {
            "jobid": jobid,
            "taskid": task_id,
            "jobname": jobname,
            "status": status,
            "messages": messages
        }
        res = requests.post(callback_url, json=payload)
        if res.status_code == requests.codes.ok:
            context = res.json()
            print("##########")
            print(context)
            if context['status'] == 1:
                return True
            else:
                return False
        else:
            return False

