import json
import uuid
import threading
import requests
import uuid
from functools import partial
from kazoo.client import KazooClient
from kazoo.protocol.states import WatchedEvent
from kazoo.recipe.watchers import ChildrenWatch, DataWatch
from kazoo.recipe.lock import Lock, LockTimeout
from portal_handler.release_record import record_target_status
from base import JobStatus, TargetStatus, TaskStatus, ResponseStatus, configuration


def count_targets(job_targets, statuses):
    return len([x for x in job_targets.values() if x['status'] in statuses])


def choose_target(targets, count):
    c = 0
    for target, data in targets.items():
        if data['status'] == TargetStatus.init.value and c < count:
            c += 1
            yield target


class Scheduler:
    def __init__(self, zk_hosts, zk_root):
        self.zk = KazooClient(zk_hosts)
        self.root = zk_root
        self.jobs = set()
        self.event = threading.Event()

    def add_callback(self, job_id):
        node = '/{}/callback/{}'.format(self.root, job_id)
        self.zk.ensure_path(node)

    def get_targets(self, job_id):
        result = {}
        node = '/{}/jobs/{}/targets'.format(self.root, job_id)
        for target in self.zk.get_children(node):
            path = '{}/{}'.format(node, target)
            print(path)
            status, _ = self.zk.get(path)
            print(status)
            result[target] = json.loads(status.decode())
            print(result)
        return result

    def schedule(self, job_id):
        print("schedule start")
        node = '/{}/jobs/{}'.format(self.root, job_id)
        lock_node = '{}/lock'.format(node)
        self.zk.ensure_path(lock_node)
        lock = Lock(self.zk, lock_node)
        try:
            if lock.acquire(timeout=1):
                data, _ = self.zk.get(node)
                job = json.loads(data.decode())
                print(job)
                """
                {
                    "jobid":"",
                    "ud": "jpol",
                    "module": "mb-inrpc",
                    "load_balancing": [{"host":"10.99.70.51"},{"host":"10.99.70.52"}]，
                    "targets" : [{"host":"10.99.70.51"},{"host":"10.99.70.52"}], 	// 服务器地址，json数组方式传递
                    "parameters" : [{"k1":"v1"},{"k2":"v3"},{"k3":"v3"}],	// 参数，json数组方式传递
                    "parallel": 1 //并行数量
                    "fail_rate": 0 // 容错数量
                }
                """
                parallel = job.get('parallel', 1)
                fail_rate = job.get('fail_rate', 0)
                #  当前在运行主机状态
                job_targets = self.get_targets(job_id)
                # 如果失败次数大于设定值退出
                # 并发大于一，失败数可能等于并发数
                if count_targets(job_targets, (TargetStatus.fail.value,)) > fail_rate:
                    return self.add_callback(job_id)
                # 修改指定target状态为running
                wait_schedule = choose_target(job_targets, parallel - count_targets(job_targets, (TargetStatus.running.value,)))
                for wait_target in wait_schedule:
                    self.set_target_status(job_id, wait_target, TargetStatus.running.value)
                self.handle_running_target(job_id)

        except LockTimeout:
            print('LockTimeout')
        finally:
            lock.release()

    def set_target_status(self, job_id, target, status, current_task=None):
        print("set target status")
        node = '{}/jobs/{}/targets/{}'.format(self.root, job_id, target)
        data, _ = self.zk.get(node)
        data = json.loads(data.decode())
        data['status'] = status
        if current_task is not None:
            data['current_task'] = current_task
        print(data)
        tx = self.zk.transaction()
        tx.set_data('{}/jobs/{}/targets/{}'.format(self.root, job_id, target), json.dumps(data).encode())
        tx.commit()
        if record_target_status(job_id, target, status):
            print("record_target_status success")
        else:
            print("record_target_status fail")

    def handle_running_target(self, job_id):
        print("handle_running_target start")
        node = '{}/jobs/{}/targets'.format(self.root, job_id)
        # 这里遍历了job下所有的主机状态，主机数量多的话，要考虑性能问题
        targets = self.zk.get_children(node)
        target_success_count = 0
        for target in targets:
            path = '{}/{}'.format(node, target)
            target_value, _ = self.zk.get(path)
            target_value = json.loads(target_value.decode())
            """
            target_value = {
                "status" = 0,
                "current_task" = "offline"，
                "next_task" = "stop_service",
            }
            """
            target_status = target_value['status']
            target_running_task = target_value['current_task']
            # 处理running的target
            if target_status == TargetStatus.running.value:
                self.handle_running_task(job_id, target, target_running_task)
            elif target_status == TargetStatus.success.value:
                target_success_count += 1
        print("target_success_count: {}, targets number: {}".format(target_success_count, len(targets)))
        if target_success_count == len(targets):
            self.add_callback(job_id)

    def get_task_status(self, job_id, target, target_running_task):
        node = '{}/jobs/{}/targets/{}/tasks/{}'.format(self.root, job_id, target, target_running_task)
        task_value, _ = self.zk.get(node)
        task_value = task_value.decode()
        return json.loads(task_value)

    @staticmethod
    def get_publish_next_task(target_running_task, task_sequence=None):
        publish_task_sequence = [
            "check_version", "offline_host,", "stop_service", "update_version",
            "start_service", "check_service", "online_host",  "check_host"]
        if task_sequence is None:
            task_sequence = publish_task_sequence
        running_task_index = publish_task_sequence.index(task_sequence)
        if running_task_index >= len(publish_task_sequence) - 1 :
            return None
        else:
            return publish_task_sequence[running_task_index + 1]

    def handle_running_task(self, job_id, target, target_running_task):
        print("handle running task start")
        node = '{}/jobs/{}/targets/{}/tasks/{}'.format(self.root, job_id, target, target_running_task)
        task_value, _ = self.zk.get(node)
        task_value = json.loads(task_value.decode())
        """
        task_value = {
            "task_name" :"check_version"
            "status" : 0,
            "next_task" : "offline",
            "parameters" : [{"k1":"v1"},{"k2":"v3"},{"k3":"v3"}],
            "callback_url":"url"
        }
        """
        # target第一个任务
        print(task_value)
        if task_value['status'] == TaskStatus.init.value:
            self.add_new_task(job_id, target, task_value['task_id'])
        elif task_value['status'] == TaskStatus.success.value:
            if task_value['next_task'] is not None:
                next_task_id = task_value['next_task']
                self.add_new_task(job_id, target, next_task_id)
            else:
                # target执行成功，重新查找新target执行
                self.set_target_status(job_id, target, TargetStatus.success.value, current_task="")
                self.send_signal(job_id)
        elif task_value['status'] == TaskStatus.fail.value:
            # 任务失败 job失败上报
            self.add_callback(job_id)
        else:
            pass

    def add_new_task(self, job_id, target, new_task_id):
        # 修改新任务状态
        print("add new task")
        job_node = '{}/jobs/{}'.format(self.root, job_id)
        job_value, _ = self.zk.get(job_node)
        job_value = json.loads(job_value.decode())
        bu = job_value['bu']
        module = job_value['module']
        environment = job_value['environment']
        callback_url = job_value['callback_url']
        load_balancing_hosts = job_value['load_balancing']
        new_task_node = '{}/jobs/{}/targets/{}/tasks/{}'.format(self.root, job_id, target, new_task_id)
        new_task_value, _ = self.zk.get(new_task_node)
        new_task_value = json.loads(new_task_value.decode())
        tx = self.zk.transaction()
        new_task_value['status'] = TaskStatus.running.value
        tx.set_data(new_task_node, json.dumps(new_task_value).encode())
        # 修改主机状态
        target_node = '{}/jobs/{}/targets/{}'.format(self.root, job_id, target)
        target_value, _ = self.zk.get(target_node)
        target_value = json.loads(target_value.decode())
        target_value['status'] = TargetStatus.running.value
        target_value['current_task'] = new_task_id
        tx.set_data(target_node, json.dumps(target_value).encode())

        hosts = [{"host":target}]
        job_name = new_task_value['task_name']
        # 处理异机逻辑
        content = {
            "environment": environment,
            "bu": bu,
            "module": module,
        }
        if job_name == 'offline':
            payload = {
                "jobid": job_id,
                "taskid": new_task_id,
                "content": content,
                "hosts": load_balancing_hosts,
                "jobname": job_name,
                "parameters": [{"offline": hosts}],
                "callback_url": callback_url,
            }
        else:
            payload = {
                "jobid": job_id,
                "taskid": new_task_id,
                "content": content,
                "hosts": hosts,
                "jobname": job_name,
                "parameters": [{"k1":"v1"},{"k2":"v3"},{"k3":"v3"}],
                "callback_url": callback_url,
            }
        print("%%%%%%%%%%%%%%%")
        print(target_value)
        tx.commit()
        if self.post_task(payload):
            self.post_job_status(job_id)
        else:
            # 发起新任务失败，job终止，上报
            self.add_callback(job_id)

    def post_job_status(self, job_id):
        print("{} post job status".format(job_id))

    def send_signal(self, job_id):
        node = '{}/signal/{}'.format(self.root, job_id)
        tx = self.zk.transaction()
        tx.set_data(node, uuid.uuid4().bytes)
        tx.commit()

    def post_task(self, payload):
        """
       **Request Syntax**
       ```
        POST /jobs  HTTP/1.1
        Content-Type: application/json
        {
            "jobid":"",
            "hosts" : [{"host":"10.99.70.51"},{"host":"10.99.70.52"}], 	// 服务器地址，json数组方式传递
            "content":{"bu":"","group":"","model":""}, // 上下文信息
            "jobname" : "demo",
            "parameters" : [{"k1":"v1"},{"k2":"v3"},{"k3":"v3"}],	// 参数，json数组方式传递
            "callback":"url"    // 用于返回此次发布状态
        }

        ```
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
        res = requests.post(configuration.config_dict['post_task_url'], json=payload)
        context = res.json()
        if res.status_code == requests.codes.ok and context['status'] == ResponseStatus.success.value:
            return True
        else:
            return False

    def handle_new_job(self, jobs):
        """
        处理新的任务
        对新的任务添加监听
        :param jobs:
        :return:
        """
        for job_id in set(jobs).difference(self.jobs):
            print("handler new job {}".format(job_id))
            DataWatch(self.zk, '{}/signal/{}'.format(self.root, job_id),
                      partial(self.handle_exist_job, job_id=job_id))
            self.schedule(job_id)
        self.jobs = jobs
        return not self.event.is_set()

    def watch(self):
        """
        监听portal那里插入的新任务
        :return:
        """
        print("scheduler watch start")
        ChildrenWatch(self.zk, '{}/signal'.format(self.root), self.handle_new_job)

    def handle_exist_job(self, data, stat, event, job_id):
        '''
        收到signal后，进入job处理逻辑， 如果已有callback，监听退出
        :param job_id:
        :param args:
        :return:
        '''

        if isinstance(event, WatchedEvent) and event.type == 'CHANGED':
            if self.zk.exists('{}/callback/{}'.format(self.root, job_id)):
                return False
            self.schedule(job_id)
            return True
        else:
            print(event)

    def handle_callback(self, job_id):
        # report_status_to_mysql()
        pass

    def start(self):
        self.zk.start()
        self.watch()
        self.event.wait()
        # while not self.event.is_set():
        #     print("event is not set")
        #     self.event.wait(10)

    def shutdown(self):
        self.event.set()
        self.zk.stop()
        self.zk.close()


if __name__== '__main__':
    zk_connect = '127.0.0.1:2181'
    zk_root = '/eju_publish'
    scheduler = Scheduler(zk_connect, zk_root)
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()
