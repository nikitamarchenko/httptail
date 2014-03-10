__author__ = 'nmarchenko'

import os
import time
import logging

import tornado.ioloop
import tornado.web
import tornado.log
from tornado.options import define, options


LOG = logging.getLogger()

define("bind_address", default="0.0.0.0", help="Bind Address")
define("port", default=8888, help="Port")
define("config_file", help="Configuration File")
define("root_dir", default=None, help="File root directory")
define("syslog_adress", default='/dev/log', help="Syslog socket address")
define("syslog", default=False, help="Enable syslog logging")


class MainHandler(tornado.web.RequestHandler):

    def __init__(self, application, request, **kwargs):
        super(MainHandler, self).__init__(application, request, **kwargs)
        self._file = None
        self._tail = None
        self._connection_alive = True

    @tornado.web.asynchronous
    def get(self, path):
        log_file_path = os.path.abspath(os.path.join(options.root_dir, path))

        if not log_file_path.startswith(options.root_dir):
            self.send_error(403)
            LOG.warning('invalid filename {} (file path doesn\'t start from root)'.format(log_file_path))
            return

        if not os.path.isfile(log_file_path):
            self.send_error(404)
            LOG.warning('File not found')
            return

        try:
            self._file = open(log_file_path)
        except IOError as error:
            self.send_error(403)
            LOG.warning('File not found: {}'.format(str(error)))
            return

        self.write('<pre>')

        lines = self._file.readlines()
        for line in lines:
            self.write(line)
        self.flush()

        def tail_f(log_file):
            while True:
                where = log_file.tell()
                line = log_file.readline()
                if not line:
                    log_file.seek(where)
                yield line

        self._tail = tail_f(self._file)
        self._read_file()

    def on_connection_close(self):
        self._connection_alive = False

    def _read_file(self):
        while True:
            line = self._tail.next()
            if line:
                self.write(line)
                self.flush()
            else:
                break

        if self._connection_alive:
            tornado.ioloop.IOLoop.instance().add_timeout(time.time() + 1, self._read_file)
        else:
            self._file.close()


application = tornado.web.Application([(r"/(.*)", MainHandler)])


def configure_syslog():
    syslog_format = 'httptail : [%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d] %(message)s'
    syslog_handler = logging.handlers.SysLogHandler(options.syslog_adress)
    syslog_handler.setFormatter(tornado.log.LogFormatter(fmt=syslog_format))
    LOG.addHandler(syslog_handler)

if __name__ == "__main__":
    tornado.options.parse_command_line()

    if options.config_file:
        tornado.options.parse_config_file(options.config_file)
        tornado.options.parse_command_line()

    if options.syslog and options.syslog_adress:
        configure_syslog()

    if options.root_dir:
        LOG.error("test")
        application.listen(options.port, options.bind_address)
        tornado.ioloop.IOLoop.instance().start()
    else:
        print "Error: --root-dir is mandatory\n"
        tornado.options.print_help()
