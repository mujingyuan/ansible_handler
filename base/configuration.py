from collections import deque, namedtuple
import logging


def get_publish_task_config():
    tasks = deque(['check_version', 'offline', 'stop_service', 'update_version', 'start_service', 'check_service', 'online', 'last_check'])
    publish_task_config = deque()
    while len(tasks) > 0:
        job_name = tasks.popleft()
        parameters = ''
        callback = ''
        config = {
            'job_name': job_name,
            'parameters': parameters,
            'callback': callback
        }
        publish_task_config.append(config)
    return publish_task_config

def get_task_id_prefix():
    return 'publish_'


task_callback_url = 'http://10.99.70.73:8100/jobscallback'

config_dict = {
    "env": "test",
    "zookeeper_ip": "10.99.70.73",
    "callback_url": "http://10.99.7.15:83",
    "post_task_url": 'http://10.99.70.73:8100/module_update',
    "task_callback_url": task_callback_url,
    "publish_task_sequence" : [
        {
            "task_id": 0,
            "status": 0,
            "task_name": "check_version",
            "parameters": [],
            "callback_url": "",
            "next_task": "offline_host",
        },
        {
            "task_id": 0,
            "status": 0,
            "task_name": "offline_host",
            "parameters": [],
            "callback_url": "",
            "next_task": "stop_service",
        },
        {
            "task_id": 0,
            "status": 0,
            "task_name": "stop_service",
            "parameters": [],
            "callback_url": "",
            "next_task": "update_version",
        },
        {
            "task_id": 0,
            "status": 0,
            "task_name": "update_version",
            "parameters": [],
            "callback_url": "",
            "next_task": "start_service",
        },
        {
            "task_id": 0,
            "status": 0,
            "task_name": "start_service",
            "parameters": [],
            "callback_url": "",
            "next_task": "check_service",
        },
        {
            "task_id": 0,
            "status": 0,
            "task_name": "check_service",
            "parameters": [],
            "callback_url": "",
            "next_task": "online_host",
        },
        {
            "task_id": 0,
            "status": 0,
            "task_name": "online_host",
            "parameters": [],
            "callback_url": "",
            "next_task": "check_host",
        },
        {
            "task_id": 0,
            "status": 0,
            "task_name": "check_host",
            "parameters": [],
            "callback_url": "",
            "next_task": None,
        },
    ]
}




LOG_SETTINGS = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'stream': 'ext://sys.stdout',
        },
        'portal_handler_file': {
            'class': 'logging.handlers.FileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': '/data/logs/eju_release/portal_handler.log',
            'mode': 'a',
        },
        'module_action_file': {
            'class': 'logging.handlers.FileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': '/data/logs/eju_release/module_action.log',
            'mode': 'a',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': '/data/logs/eju_release/junk.log',
            'mode': 'a',
            'maxBytes': 10485760,
            'backupCount': 2,
        },

    },
    'formatters': {
        'detailed': {
            'format': '%(asctime)s %(module)-17s line:%(lineno)-4d ' \
            '%(levelname)-8s %(message)s',
        },
        'email': {
            'format': 'Timestamp: %(asctime)s\nModule: %(module)s\n' \
            'Line: %(lineno)d\nMessage: %(message)s',
        },
    },
    'loggers': {
        'extensive': {
            'level':'DEBUG',
            'handlers': ['console','file']
            },
        'module_action': {
            'level': 'DEBUG',
            'handlers': ['console', 'module_action_file']
        }
    }
}


