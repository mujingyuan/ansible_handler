from tornado.options import parse_command_line, define
from tornado.web import Application

define('port', default=9201, type=int, help='server port')
define('bind', default='127.0.0.1', type=str, help='server bind')


def make_app(handlers, **setting):
    parse_command_line()
    app = Application(handlers, **setting)
    return app