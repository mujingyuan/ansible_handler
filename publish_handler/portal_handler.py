from tornado.web import RequestHandler
from tornado.escape import json_decode, json_encode
import json
import copy
import uuid
from publish_handler.base import PublishTask, TargetPublishTask, PublishJob
from base.configuration import get_publish_task_config, get_task_id_prefix, config_dict
from base import TargetStatus, TaskStatus

# curl -XPOST -H "Content-Type: application/json" -d '{"job_id":"jobid_20170207173800", "environment":"test", "bu":"jpol", "module": "mb-inrpc", "hosts":["10.99.70.61"], "version":"v1.6.16", "build": 48}' 10.99.70.73:8100/publish_version
class PublishHandler(RequestHandler):
    def post(self, *args, **kwargs):
        body = json_decode(self.request.body)
        job_id = body.get('job_id', '')
        environment = body.get('environment', '')
        bu = body.get('bu', '')
        module = body.get('module', '')
        hosts = body.get('hosts', [])
        version = body.get('version', '')
        build = body.get('build', '')
        job_type = body.get('job_type', '')
        job_sequence = body.get('job_sequence', config_dict['publish_task_sequence'])
        job_value = {
                    "jobid": job_id,
                    "job_type": job_type,
                    "environment": environment,
                    "bu": bu,
                    "module": module,
                    "version": version,
                    "build": build,
                    "load_balancing": [{"host":"10.99.70.51"},{"host":"10.99.70.52"}],
                    "targets": hosts,
                    "parameters": [{"k1":"v1"},{"k2":"v3"},{"k3":"v3"}],
                    "parallel": 1,
                    "fail_rate": 0,
                    # task callback url 暂时没用
                    "callback_url": config_dict['task_callback_url']
                }
        if job_id == '' or environment == '' or bu == '' or module == '' or hosts == [] or version == '' or build == '':
            self.write('argument is null')
            self.finish()
        else:
            ret = self.add_task_to_scheduler(job_id, job_value, hosts, job_sequence)
            if ret:
                if self.start_job(job_id):
                    self.write('job receive success')
                    self.finish()

    @staticmethod
    def get_task_id(task_name):
        prefix = get_task_id_prefix()
        return prefix + task_name + '_' + uuid.uuid4().hex

    def add_task_to_scheduler(self, job_id, job_value, hosts, job_sequence):
        print("add task to scheduler")
        zk = self.application.zk
        sequence = copy.deepcopy(job_sequence)

        if not zk.is_job_exist(job_id):
            ret = zk.create_new_job(job_id, job_value)
            if ret:
                for host in hosts:
                    first_task_id = self.get_task_id(sequence[0]["task_name"])
                    target_value = {
                        "status": TargetStatus.init.value,
                        "current_task": first_task_id
                    }
                    ret = zk.create_new_target(job_id, host, target_value)
                    if ret:
                        # 生成任务单链执行顺序
                        sequence_index = 0
                        ret = False
                        next_task_id = ''
                        while sequence_index < len(sequence) and next_task_id is not None:
                            task = sequence[sequence_index]
                            next_task = task['next_task']
                            if sequence_index == 0:
                                task['task_id'] = first_task_id
                            else:
                                task['task_id'] = next_task_id
                            if next_task is None:
                                next_task_id = None
                            else:
                                next_task_id = self.get_task_id(next_task)
                            task['next_task'] = next_task_id
                            sequence_index += 1
                            ret = zk.create_new_task(job_id, host, task)
                            if not ret:
                                return ret
                        return ret

    def start_job(self, job_id):
        ret = self.application.zk.create_job_signal(job_id)
        return ret




