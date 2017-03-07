def record_target_status(jobid, target, status):
    return True

import requests
from base import CallbackLevel, CallbackResponseStatus
from base.configuration import LOG_SETTINGS
import logging.config


logging.config.dictConfig(LOG_SETTINGS)
logger = logging.getLogger('release_record')


class PortalCallback(object):
    def __init__(self, job_id, job_info):
        self.job_id = job_id
        self.job_callback_info = job_info
        self.job_callback_info["targets"] = dict()

    def _get_job_callback(self):
        return self.job_callback_info["callback"]["callback_job_url"]

    def _get_target_callback(self):
        return self.job_callback_info["callback"]["callback_target_url"]

    @staticmethod
    def _post_callback(post_url, payload):
        res = requests.post(post_url, json=payload)
        if res and res.status_code == requests.codes.ok:
            context = res.json()
            if context['status'] == CallbackResponseStatus.success.value:
                logger.info("post callback: response context status success, context={}".format(context))
                return True
            else:
                logger.error("post callback: response context status fail, context={}".format(context))
                return False
        else:
            logger.error("post callback: response status fail, response={}".format(res))
            return False

    def _job_callback(self, callback_info):
        logger.info("job callback, callback_info={}".format(callback_info))
        job_callback_url = self._get_job_callback()
        payload = {
            "job_id": callback_info["job_id"],
            "status": callback_info["status"],
            "messages": callback_info["messages"]
        }
        if self._post_callback(job_callback_url, payload):
            return True
        else:
            return False

    def _target_callback(self, callback_info):
        logger.info("target callback, callback_info={}".format(callback_info))
        target_callback_url = self._get_target_callback()
        payload = {
            "job_id": callback_info["job_id"],
            "target": callback_info["target"],
            "status": callback_info["status"],
            "messages": callback_info["messages"]
        }
        if self._post_callback(target_callback_url, payload):
            return True
        else:
            return False

    def _task_callback(self, callback_info):
        logger.info("task callback, callback_info={}".format(callback_info))
        task_callback_url = self._get_target_callback()
        payload = {
            "job_id": callback_info["job_id"],
            "target": callback_info["target"],
            "status": callback_info["status"],
            "messages": callback_info["messages"]
        }
        if self._post_callback(task_callback_url, payload):
            return True
        else:
            return False

    def _update_job(self, status, messages=None):
        self.job_callback_info["status"] = status
        if messages is not None:
            self.job_callback_info["messages"] = messages

    def _update_job_target(self, target, status, messages=None):
        self.job_callback_info.setdefault("targets", dict())
        target_callback_info = self.job_callback_info["targets"].get(target, dict())
        if target_callback_info:
            target_callback_info["status"] = status
            if messages is not None:
                target_callback_info["message"] = messages
        else:
            target_callback_info = {
                "status": status,
                "messages": messages,
                "steps": dict()
            }
        self.job_callback_info["targets"][target] = target_callback_info

    def _update_job_task(self, target, task_name, status, messages=None):
        self.job_callback_info.setdefault("targets", dict())
        target_callback_info = self.job_callback_info["targets"].get(target, dict())
        if target_callback_info:
            target_callback_info.setdefault("tasks", dict())
            task_callback_info = target_callback_info["tasks"].get(task_name, dict())
            if task_callback_info:
                task_callback_info["status"] = status
                if messages is not None:
                    task_callback_info["messages"] = messages
            else:
                task_callback_info = {
                    "status": status,
                    "messages": messages
                }
            self.job_callback_info["targets"][target][task_name] = task_callback_info
        else:
            logger.error("update job task failed: target is not exit, job_id={}, target={}, task_id={}".format(self.job_id, target, task_name))

    def post_callback(self, callback_value):
        callback_level = callback_value["callback_level"]
        callback_info = callback_value["callback_info"]
        status = callback_info["status"]
        messages = callback_info.get("messages", None)
        if callback_level == CallbackLevel.job.value:
            self._update_job(status, messages)
            if self._job_callback(callback_info):
                return True
        elif callback_level == CallbackLevel.target.value:
            target = callback_info['target']
            self._update_job_target(target, status, messages)
            if self._target_callback(callback_info):
                return True
        elif callback_level == CallbackLevel.task.value:
            target = callback_info['target']
            task_name = callback_info["task_name"]
            self._update_job_task(target, task_name, status, messages)
            if self._task_callback(callback_info):
                return True
        else:
            logger.error("post callback:fail, callback_level={}".format(callback_level))
