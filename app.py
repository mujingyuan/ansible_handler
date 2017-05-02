from tornado.ioloop import IOLoop
from tornado.options import options

from ansible_handler import make_app
from ansible_handler.module_handler import ModuleHandler

Handlers = [
    (r'/module_handler', ModuleHandler),
]

if __name__ == '__main__':
    app = make_app(Handlers, debug=True)
    app.listen(options.port, address=options.bind)
    try:
        print('ansible_resource handler starting')
        IOLoop.current().start()
    except KeyboardInterrupt:
        IOLoop.current().stop()