__author__ = 'nmarchenko'

import time
import tornado.ioloop
import tornado.web


class MainHandler(tornado.web.RequestHandler):

    def __init__(self, application, request, **kwargs):
        super(MainHandler, self).__init__(application, request, **kwargs)
        self._file = None
        self._tail = None
        self._connection_alive = True

    @tornado.web.asynchronous
    def get(self):
        self.write('<pre>')
        self._file = open('/var/log/syslog')
        lines = self._file.readlines()
        for line in lines:
            self.write(line)
        self.flush()

        def tail_f(file):
            while True:
                where = file.tell()
                line = file.readline()
                if not line:
                    file.seek(where)
                yield line

        self._tail = tail_f(self._file)
        self._read_file()

    def on_connection_close(self):
        self._connection_alive = False

    def _read_file(self):
        line = self._tail.next()
        if line:
            self.write(line)
            self.flush()
        if self._connection_alive:
            tornado.ioloop.IOLoop.instance().add_timeout(time.time() + 1, self._read_file)
        else:
            self._file.close()


application = tornado.web.Application([
    (r"/", MainHandler),
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()