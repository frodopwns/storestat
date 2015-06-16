import sys
import os
import multiprocessing
from subprocess import Popen, PIPE
import server


if __name__ == '__main__':
    base_path = os.path.abspath(os.path.dirname(__file__))
    args = sys.argv
    server = multiprocessing.Process(target=server.main, args=(args,))
    server.start()
    # call tests
    a = Popen("python %s/client.py --d 20 --c 10000000" % base_path, stdout=PIPE, stderr=PIPE, shell=True)
    b = Popen("python %s/client.py --dest /tmp/other" % base_path, stdout=PIPE, stderr=PIPE, shell=True)
    c = Popen("python %s/client.py --d 40 --c 5000000 --f 15000000" % base_path, stdout=PIPE, stderr=PIPE, shell=True)
    # wait for them to finish
    astdout, astderr = a.communicate()
    bstdout, bstderr = b.communicate()
    cstdout, cstderr = c.communicate()

    #kill server
    server.terminate()
    print astdout
    print bstdout
    print cstdout