from collections import deque
# 基类
"""
Request
{
    "jobid":"",
    "hosts" : [{"host":"10.99.70.51"},{"host":"10.99.70.52"}], 	// 服务器地址，json数组方式传递
    "jobname" : "demo",
    "parameters" : [{"k1":"v1"},{"k2":"v3"},{"k3":"v3"}],	// 参数，json数组方式传递
    "callback":"url"    // 用于返回此次发布状态
}

Response
{
    "jobid":"",
    "hosts" : [{"host":"10.99.70.51"},{"host":"10.99.70.52"}],
    "jobname" : "demo",
    "parameters" : [{"k1":"v1"},{"k2":"v3"},{"k3":"v3"}],
    "callback":"url"
    "status":"" // 1：参数接收成功，2：参数接收失败
}
"""
class TaskBase(object):
    def __int__(self):
        pass

class PublishTask(TaskBase):
    def __init__(self, task_id, job_name, parameters, callback):
        self.task_id = task_id
        self.job_name = job_name
        self.parameters = parameters
        self.callback = callback
        self._status = None

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status_code):
        self._status = str(status_code)

class TargetPublishTask(object):
    def __init__(self, host):
        self.host = host
        self.tasks = deque()
        self._status = None

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status_code):
        self._status = str(status_code)

    @property
    def current_task(self):
        return self._current_task

    @current_task.setter
    def current_task(self, task):
        self._current_task = task

    @property
    def next_task(self):
        task = self._tasks.popleft()
        self.current_task = task
        return self._tasks.popleft()

    def add_task(self, task):
        if isinstance(task, PublishTask):
            self._tasks.append(task)

    def add_tasks(self, tasks):
        if isinstance(tasks, list):
            for task in tasks:
                self.add_task(task)


class JobBase(object):
    def __init__(self):
        pass


class PublishJob(JobBase):
    def __init__(self, jid):
        self.__job_id = jid
        self._current_running_host = None
        self._target_queue = deque()

    @property
    def job_id(self):
        return self._job_id

    @job_id.setter
    def job_id(self, jid):
        self._job_id = jid

    @property
    def current_running_host(self):
        return self._current_running_host

    @current_running_host.setter
    def current_running_host(self, target):
        self._current_running_host = target

    @property
    def next_host(self):
        target = self._target_queue.popleft()
        self.current_running_host = target
        return self._target_queue.popleft()

    def add_target(self, target):
        if isinstance(target, TargetPublishTask):
            self._target_queue.append(target)

    def add_targets(self, targets):
        if isinstance(targets, list):
            for target in targets:
                self.add_target(target)
