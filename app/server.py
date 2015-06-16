import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient

import sys
import os
import redis
import logging
import logging.handlers
import pygal

from jinja2 import Environment, FileSystemLoader

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

logger2 = logging.getLogger("server")
handler = logging.FileHandler('server.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger2.addHandler(handler)


class BaseeHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.redis = redis.StrictRedis(host='localhost', port=6379, db=0)


class StatusHandler(BaseeHandler):
    """
    Handles start and stop messages. Kicks off report.
    """
    def get(self):
        test_id = self.get_argument('id')
        status = self.get_argument('status').lower()
        if status not in ['start', 'stop']:
            self.send_error(status_code=400)
        else:
            logger2.info('%s %s' % (status, test_id))
            if status == 'start':
                self.redis.set("%s:start" % test_id, self.request._start_time)
            elif status == 'stop':
                logger2.info("reporting %s" % test_id)
                self.redis.set("%s:stop" % test_id, self.request._start_time)
                file_size = self.get_argument('file_size')
                chunk_size = self.get_argument('chunk_size')
                dest = self.get_argument('dest')
                build_report(self.redis, test_id, dest, file_size, chunk_size)



class WriteHandler(BaseeHandler):
    """
    Handles info about file rollovers
    """
    def get(self):
        test_id = self.get_argument('id')
        rate = self.get_argument('rate')
        elapsed = self.get_argument('elapsed')
        self.redis.rpush("%s:write" % test_id, [elapsed, rate])


class BeatHandler(BaseeHandler):
    """
    Handles beat messages from client
    """
    def get(self):
        test_id = self.get_argument('id')
        logger2.info('beat %s' % test_id)
        elapsed = self.get_argument('elapsed')
        self.redis.rpush("%s:beat" % test_id, elapsed)
        self.write("beat %s" % test_id)


class UsageHandler(BaseeHandler):
    """
    Handles cpu/mem data from server
    """
    def get(self):
        test_id = self.get_argument('id')
        cpu = self.get_argument('cpu')
        mem = self.get_argument('mem')
        elapsed = self.get_argument('elapsed')
        self.redis.rpush("%s:usage" % test_id, [elapsed, cpu, mem])


def build_report(db, test_id, dest, file_size, chunk_size):
    """
    write report to reports/test_id/index.html
    """
    logger2.info('report written for %s' % test_id)
    directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'reports', test_id)
    if not os.path.exists(directory):
        os.makedirs(directory)

    env = Environment(loader=FileSystemLoader(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')))
    template = env.get_template('index.html')
    rollovers = db.llen("%s:write" % test_id) - 1

    test_start = float(db.get("%s:start" % test_id))
    test_stop = float(db.get("%s:stop" % test_id))
    duration = test_stop - test_start

    #heart beat
    heartbeats = db.lrange("%s:beat" % test_id, 0, -1)

    #writes
    writes = [eval(x) for x in db.lrange("%s:write" % test_id, 0, -1)]
    max_write = max([float(x[1]) for x in writes])
    min_write = min([float(x[1]) for x in writes])
    l = [float(x[1]) for x in writes]
    avg_write = sum(l) / len(l)

    xy_chart = pygal.XY(show_legend=False, stroke=False, style=pygal.style.LightStyle, height=400, wtest_idht=200)
    xy_chart.title = 'Writes (MB/s)'
    xy_chart.add('A', [(float(x[0]), float(x[1])) for x in writes])
    xy_chart.render_to_file(os.path.join(directory, 'write_rates.svg'))

    #resource usage
    usage = [eval(x) for x in db.lrange("%s:usage" % test_id, 0, -1)]

    with open(os.path.join(directory, "index.html"), "w") as ofile:
        ofile.write(template.render(
            test_id=test_id,
            duration=duration,
            rollovers=rollovers,
            heartbeats=heartbeats,
            usage=usage,
            max_write=max_write,
            min_write=min_write,
            avg_write=avg_write,
            dest=dest,
            file_size=file_size,
            chunk_size=chunk_size
        ))



def main(args):
    """
    Spin up tornado server
    """
    tornado.options.parse_command_line(args)
    app = tornado.web.Application(handlers=[
        (r"/status", StatusHandler),
        (r"/beat", BeatHandler),
        (r"/usage", UsageHandler),
        (r"/write", WriteHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    args = sys.argv
    #args.append("--log_file_prefix=my_app.log")
    main(args)
