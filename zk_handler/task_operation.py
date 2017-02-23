import json
import threading
import uuid
import logging.config
from functools import partial
from kazoo.client import KazooClient
from kazoo.recipe.watchers import ChildrenWatch, DataWatch
from base.configuration import LOG_SETTINGS

logging.config.dictConfig(LOG_SETTINGS)
logger = logging.getLogger('zkhandler')

class ZkOperation(object):
    def __init__(self, zk_hosts, zk_root):
        self.zk = KazooClient(zk_hosts)
        self.root = zk_root
        self.tasks = set()
        self.event = threading.Event()

    def start(self):
        if self.zk.exists:
            self.zk.start()
            self.zk.add_auth('digest', 'publish:publish')
        if self.zk.connected:
            self.zk.ensure_path(self.root)

    def is_job_exist(self, job_id):
        if job_id == '':
            raise Exception('job_id is ""')
        node = self.root + '/jobs/' + job_id
        return self.zk.exists(node)

    def check_task_status(self, path):
        if path == '':
            raise Exception('path is ""')
        node = self.root + path
        data, _ = self.zk.get(node)
        return data['Status']

    def _create_node(self, node, value=None):
        if value is None:
            value = ''
        value = json.dumps(value)
        if self.zk.connected and not self.zk.exists(node):
            self.zk.create(node, makepath=True, value=value.encode())
            return True
        else:
            logger.error('zk not connected or node is exists')
            return False

    def create_new_job(self, job_id, job_value=None):
        if job_value is None:
            job_value = ''
        if job_id != '':
            node = self.root + '/jobs/' + job_id
            ret = self._create_node(node, job_value)
            return ret
        else:
            logger.error('job_id is null')
            return False

    def create_new_target(self, job_id, target, target_value):
        node = '/{}/jobs/{}/targets/{}'.format(self.root, job_id, target)
        ret = self._create_node(node, target_value)
        return ret

    def create_new_task(self, job_id, target, task):
        node = '/{}/jobs/{}/targets/{}/tasks/{}'.format(self.root, job_id, target, task['task_id'])
        ret = self._create_node(node, task)
        return ret

    def create_job_signal(self, job_id):
        node = '/{}/signal/{}'.format(self.root, job_id)
        ret = self._create_node(node, uuid.uuid4().hex)
        return ret

    def update_job_status(self, job_id, task):
        if job_id != '' and task is not None:
            node = self.root + '/signal/' + job_id
        else:
            raise Exception('job_id is ""')
        if self.zk.connected and self.is_job_exist(job_id):
            tx = self.zk.transaction()
            tx.set_data(node, task.encode())
            tx.commit()

    def handler_task(self, job_id, task_id, status):
        # 为不必传回target, 遍历任务节点
        if not self.is_job_exist(job_id):
            logger.error("can not find this jobid: {}".format(job_id))
            return False
        job_node = "{}/jobs/{}/targets".format(self.root, job_id)
        for target in self.zk.get_children(job_node):
            target_node = "{}/{}/tasks".format(job_node, target)
            for task in self.zk.get_children(target_node):
                if task == task_id:
                    task_node = "{}/{}".format(target_node, task)
                    task_value, _ = self.zk.get(task_node)
                    new_task_value = json.loads(task_value.decode())
                    new_task_value['status'] = status
                    tx = self.zk.transaction()
                    tx.set_data(task_node, json.dumps(new_task_value).encode())
                    tx.commit()
                    task_value, _ = self.zk.get(task_node)
                    return True
        logger.error("can not find this taskid: {} in {}".format(task_id, job_id))
        return False

    def send_signal(self, job_id):
        node = '{}/signal/{}'.format(self.root, job_id)
        logger.info("send singal : {}".format(job_id))
        tx = self.zk.transaction()
        tx.set_data(node, uuid.uuid4().bytes)
        tx.commit()