import os
import time
import socket
import logging
from functools import wraps
from contextlib import contextmanager

import pika


@contextmanager
def open_channel(rabbit_host_ip,
                 rabbit_port=5672,
                 rabbit_username='guest',
                 rabbit_password='guest'):
    creds = pika.credentials.PlainCredentials(username=rabbit_username,
                                              password=rabbit_password)
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbit_host_ip,
                                      port=rabbit_port,
                                      credentials=creds))
        channel = connection.channel()
        yield channel
    except Exception as e:
        print 'Error connecting to queue: {message}' \
            .format(message=e.message)
    finally:
        channel.close()


def retry(exception, tries=10, delay=3, backoff=0.1):
    """Retry calling the decorated function using an exponential backoff.
    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exception as ex:
                    print "{0}, Retrying in {1} seconds...".format(ex, mdelay)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry  # true decorator
    return deco_retry


@retry(IOError)
def wait_for_port(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if not sock.connect_ex((host, port)) == 0:
        raise IOError('Failed connecting to {host} on {port}'
                      .format(host=host, port=port))
    return True


def create_logger(name, path=None, level=logging.DEBUG):
    logger = logging.getLogger(name)
    if path:
        _make_dir(path)
        file_handler = logging.FileHandler(path)
        logger.addHandler(file_handler)
    logger.addHandler(logging.StreamHandler())
    logger.level = level
    return logger


def _make_dir(path):
    path_dir = os.path.dirname(path)
    if not os.path.isdir(path_dir):
        os.mkdir(path_dir)
