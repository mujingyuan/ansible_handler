def record_target_status(jobid, target, status):
    return True

from base import CallbackLevel
from base.configuration import LOG_SETTINGS
import logging.config

logging.config.dictConfig(LOG_SETTINGS)
logger = logging.getLogger('release_record')

class PortalCallback(object):
    def __init__(self, callback):
        self.callback_info = callback

    def _job_callback(self):
        logger.info("job callback, callback_info={}".format(self.callback_info))
        return True

    def _target_callback(self):
        logger.info("target callback, callback_info={}".format(self.callback_info))
        return True

    def _task_callback(self):
        logger.info("task callback, callback_info={}".format(self.callback_info))
        return True

    def post_callback(self):
        callback_level = self.callback_info["callback_level"]
        callback_info = self.callback_info["callback_info"]
        if callback_level == CallbackLevel.job.value:
            if self._job_callback():
                return True
        elif callback_level == CallbackLevel.target.value:
            if self._target_callback():
                return True
        elif callback_level == CallbackLevel.task.value:
            if self._task_callback():
                return True
        else:
            logger.error("post callback:fail, callback_level={}".format(callback_level))
