from tornado.web import RequestHandler
from tornado.escape import json_decode, json_encode
import requests
import json
import uuid
import logging
from requests.exceptions import ConnectionError, ConnectTimeout
from base import ResponseStatus, JobStatus, JobCallbackResponseStatus


# curl -XPOST -H "Content-Type: application/json" -d '{"jobid":"201701171136001", "jobname":"offline", "status":"1", "messages": [{"host": "10.10.10.10","status": "1", "message": "anything right"}]}' 10.99.70.73:8100/jobscallback

logging.basicConfig(filename='job_handler.log', level=logging.INFO)

class PostPublishJob(object):
    def __init__(self, post_url):
        self.post_url = post_url

    def post_job(self, task):
        payload = task.payload
        res = requests.post(self.post_url, json=payload)
        try:
            context = res.json()
            if res.status_code == requests.codes.ok and context['status'] == ResponseStatus.success:
                return True
            else:
                return False
        except (ConnectionError, ConnectTimeout) as e:
            print(e)


class JobsCallback(RequestHandler):
    def post(self):
        """
        jobid:
        jobname:
        status:
        message: []
        :return:
        """
        body = json_decode(self.request.body)
        print(body)
        job_id = body.get('jobid', '')
        task_id = body.get('taskid', '')
        job_name = body.get('jobname', '')
        job_status = body.get('status', '')
        job_message = body.get('messages', [])
        if job_id == '' or job_name == '' or job_status == '' or job_message == []:
            res = {"status": JobCallbackResponseStatus.fail.value, "message": "some argument is null"}
            self.write(json.dumps(res))
            self.finish()
        else:
            logging.info('Job_ID: {}, Task_id: {}, Job_Step: {}, Job_Status: {}'.format(job_id, task_id, job_name, job_status))
            for message in job_message:
                logging.info('"Host": {}, "status": {}, "message": {}'.format(message['host'], message['status'], message['message']))
            if self.application.zk.handler_task(job_id, task_id, job_status):
                logging.info("handler task success after callback")
                self.application.zk.send_signal(job_id)
                res = {"status": JobCallbackResponseStatus.success.value,
                       "message": "callback receive success, and handler task success after callback"}
            else:
                logging.info("handler task fail after callback")
                res = {"status": JobCallbackResponseStatus.success.value,
                       "message": "callback receive success, but handler task fail after callback"}
            self.write(json_encode(res))
            self.finish()



