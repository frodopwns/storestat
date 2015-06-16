#!/usr/bin/env python
import sys, os
import uuid
import optparse
import urllib2
from urllib import urlencode
import logging
import time
from threading import Thread
from subprocess import Popen, PIPE


logging.basicConfig(
    level=logging.DEBUG,
    format='%(created)f [%(levelname)s] (%(threadName)-10s) %(message)s',
    filename='client.log',
)


def heartbeat(fqdn, duration, test_id):
    """
    Send heart beats ever 5 seconds
    """
    beats = 0
    start = time.time()
    while time.time() - start < duration:
        elapsed = time.time() - start
        resp = urllib2.urlopen("%s/beat?id=%s&elapsed=%d" % (fqdn, test_id, int(elapsed))).read()
        beats += 1
        if beats >= duration/5:
            return
        time.sleep(5)


def getusage(fqdn, duration, test_id, pid):
    """
    Get cpu/mem usage ever 10 sec
    """
    beats = 0
    start = time.time()
    while time.time() - start < duration:
        a = Popen("top -p %d -b -n 1 | grep python | awk '{print $9,$10}'" % pid, stdout=PIPE, stderr=PIPE, shell=True)
        stdout, stderr = a.communicate()
        cpu, mem = stdout.rstrip().split()
        payload = urlencode({
            'id': test_id,
            'cpu': cpu,
            'mem': mem,
            'elapsed': int(time.time() - start),
        })
        resp = urllib2.urlopen("%s/usage?%s" % (fqdn, payload)).read()
        beats += 1
        if beats >= duration/10:
            return
        time.sleep(10)


def writer(fqdn, pid, test_id, duration, chunk_size, file_size, dest):
    """
    Write files in chunks until the duration runs out
    """
    chunk_count = file_size / chunk_size
    start = time.time()
    count = 0
    while time.time() - start < duration:
        cmd_list = [
            'dd',
            'if=/dev/zero',
            'of=%s/%d-%d' % (dest, pid, count),
            'bs=%d' % chunk_size,
            'count=%d' % chunk_count,
            'conv=fdatasync',
        ]
        # use the dd command to test writes
        a = Popen(cmd_list, stdout=PIPE, stderr=PIPE)
        stdout, stderr = a.communicate()
        # get response from cmd and send to server
        result = stderr.split("\n")[2]
        total_copied, time_taken, write_rate = result.split(",")
        payload = urlencode({
            'id': test_id,
            'rate': write_rate.split()[0],
            'elapsed': time.time() - start,
        })

        resp = urllib2.urlopen("%s/write?%s" % (fqdn, payload)).read()

        logging.debug("%s - file rollover" % test_id)
        count +=1


def main(fqdn, duration, file_size, chunk_size, dest):
    """
    Sets up the threads needed to get the test done
    """
    # get process id of current client for use with resource monitoring
    pid = os.getpid()
    # set max/min speed assumption
    max_write_speed = 1000000000 #assuming 1000MB/s
    min_write_speed = 10000000 #assuming 10MB/s
    test_id = uuid.uuid4()
    # check if 2 rollovers can be made
    if ((duration * max_write_speed) < (2 * file_size)) or ((duration * min_write_speed) < (2 * file_size)):
        raise Exception("You need a duration that allows for at least 2 rollovers!")

    logging.debug('test start')
    resp = urllib2.urlopen("%s/status?id=%s&status=start" % (fqdn, test_id)).read()
    # start heartbeat thread
    heart = Thread(target=heartbeat, args=(fqdn, duration, test_id))
    heart.setDaemon(True)
    heart.start()
    # start Write thread
    disk_writer = Thread(target=writer, kwargs=dict(
        pid=pid,
        test_id=test_id,
        duration=duration,
        chunk_size=chunk_size,
        file_size=file_size,
        dest=dest,
        fqdn=fqdn
    ))
    disk_writer.start()
    # start usage monitor
    usage = Thread(target=getusage, args=(fqdn, duration, test_id, pid))
    usage.setDaemon(True)
    usage.start()
    # make them all finish before moving on
    heart.join()
    disk_writer.join()
    usage.join()
    # clean up files that were created
    os.system("rm %s/%s-*" % (dest, pid))
    # tell user where to find the report
    print "test complete!"
    print "please open %s in a browser" % os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'reports', str(test_id), 'index.html'
    )
    logging.debug('test stop')
    # send cdata to server fo ruse in report
    payload = urlencode({
        'id': test_id,
        'file_size': file_size,
        'chunk_size': chunk_size,
        'dest': dest,
        'status': 'stop',
    })
    resp = urllib2.urlopen("%s/status?%s" % (fqdn, payload)).read()


if __name__ == '__main__':
    # Handle options passed via command line
    parser = optparse.OptionParser()
    parser.add_option('--d', action="store", dest="duration", type="int", help="Number of seconds the test should run (default is 30)")
    parser.add_option('--f', action="store", dest="file_size", type="int", help="max size in bytes for files to be written (default 10000000)")
    parser.add_option('--c', action="store", dest="chunk_size", type="int", help="size of chunks to be written (default 1000000)")
    parser.add_option('--dest', action="store", dest="dest", help="destination to write to (default /tmp)")
    parser.add_option('--fqdn', action="store", dest="fqdn", help="server address (default http://localhost:8000)")
    args = parser.parse_args(sys.argv)[0]

    # Set defaults
    fqdn = args.fqdn if args.fqdn else 'http://localhost:8000'
    duration = args.duration if args.duration else 30
    file_size = args.file_size if args.file_size else 10000000
    chunk_size = args.chunk_size if args.chunk_size else 1000000
    dest = args.dest if args.dest else "/tmp"
    # create dest if it doesnt exist...hopefully the runner has proper permissions
    if not os.path.exists(dest):
        os.makedirs(dest)
    # Start test
    main(fqdn, duration, file_size, chunk_size, dest)























