import os
from tornado.ioloop import IOLoop
from tornado.options import parse_command_line, parse_config_file, options

from publish_handler import make_app
from job_handler.job_handler import JobsCallback
from publish_handler.portal_handler import PublishHandler
from publish_handler.module_action import ModuleUpdateHandler

Handlers = [
    (r'/jobscallback', JobsCallback),
    (r'/module_update', ModuleUpdateHandler),
    (r'/publish_version', PublishHandler)
]

if __name__ == '__main__':
    if os.path.exists('./eju_publish.config'):
        parse_config_file('./eju_publish.config')
    parse_command_line()
    app  = make_app(Handlers, debug=True)
    app.listen(options.port, address=options.bind)
    try:
        print('starting')
        app.zk.start()
        IOLoop.current().start()
    except KeyboardInterrupt:
        IOLoop.current().stop()