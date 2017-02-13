import logging
import os
import pickle
import socket
import threading
import time
import uuid

from pika import ConnectionParameters, BlockingConnection, exceptions

from time_sync.constants import (CLIENT_MASTER_UPDATE_QUEUE_ENV,
                                 RABBITMQ_HOST_IP_ENV,
                                 CLIENT_MESSAGING_QUEUE,
                                 CLIENT_FANOUT_EXCHANGE,
                                 CLIENT_LOGS_PATH,
                                 BROKER_PORT)
from utils import open_channel, create_logger

MY_MESSAGE_QUEUE = os.getenv(CLIENT_MASTER_UPDATE_QUEUE_ENV)
BROKER_HOST_IP = os.getenv(RABBITMQ_HOST_IP_ENV)

CLIENT_CONTAINER_IP = socket.gethostbyname(socket.gethostname())
CLIENT_ID = str(uuid.uuid4())
_CLIENT_QUEUE_ID = str(uuid.uuid4())

# Master client time value. This variable will be shared between the threads.
# This variable will only be updated by the consumer thread, and read by the
# The publisher thread.
curr_master_data = {}

logger = create_logger('client_logger',
                       path=os.path.join(CLIENT_LOGS_PATH, CLIENT_ID),
                       level=logging.DEBUG)


class OnConsumeCallback(object):
    def __call__(self, ch, method, properties, body):
        global curr_master_data
        master_data = pickle.loads(body)
        logger.debug('Master client ID:\'{0}\', IP:\'{1}\', Time:\'{2}\'.'
                     .format(master_data.get('id'),
                             master_data.get('ip'),
                             master_data.get('time')))
        if master_data.get('id') == CLIENT_ID:
            logger.info('I\'m the master DAWG. Just so we\'re clear, '
                        'my ID is {0} and my IP is {1}'
                        .format(CLIENT_CONTAINER_IP, CLIENT_ID))
            curr_master_data = {}
        else:
            logger.info('I\'m just a simple client. This is my master: {0}'
                        .format(curr_master_data.get('id')))
            # Update the latest master client time
            curr_master_data = master_data


class ConsumerThread(threading.Thread):
    def start_thread(self):
        thread = self._create_consumer_thread()
        thread.start()
        return thread

    def _create_consumer_thread(self):
        connection = BlockingConnection(ConnectionParameters(
            host=BROKER_HOST_IP, port=int(BROKER_PORT)))
        channel = connection.channel()
        channel.basic_consume(OnConsumeCallback(),
                              queue=_CLIENT_QUEUE_ID,
                              no_ack=True)
        return threading.Thread(target=self._consume_master_client_data,
                                args=[channel])

    # called by thread
    def _consume_master_client_data(self, channel):
        logger.info(' [*] Waiting for messages from server')
        try:
            channel.start_consuming()
        except exceptions.ConnectionClosed:
            logger.error('Connection closed. Restarting consumer thread')
            self.start_thread()


class TimePublisherThread(threading.Thread):
    @staticmethod
    def _send_my_time():
        while True:
            global curr_master_data
            my_time = {'id': CLIENT_ID,
                       'ip': CLIENT_CONTAINER_IP,
                       'time': time.time(),
                       'master_time': curr_master_data.get('time'),
                       'master_id': curr_master_data.get('id')}
            logger.debug('Sending my time message: {}'.format(str(my_time)))
            with open_channel(BROKER_HOST_IP) as _channel:
                _channel.basic_publish(exchange='',
                                       routing_key=CLIENT_MESSAGING_QUEUE,
                                       body=pickle.dumps(my_time))
            # Sleep for one second before resending
            time.sleep(1)

    def start_thread(self):
        thread = threading.Thread(target=self._send_my_time)
        thread.start()
        return thread


class ClientBootstrapper(object):
    def __init__(self):
        # Declare the global queue exchange if one does not exist.
        self._create_exchange()
        # Create a client queue
        result = self._create_queue()
        # Add the appropriate bindings
        self._add_bindings(result)

    @staticmethod
    def _create_queue():
        with open_channel(BROKER_HOST_IP) as _channel:
            return _channel.queue_declare(queue=_CLIENT_QUEUE_ID,
                                          durable=True)

    @staticmethod
    def _create_exchange():
        with open_channel(BROKER_HOST_IP) as _channel:
            # This action is completely idempotent
            _channel.exchange_declare(exchange=CLIENT_FANOUT_EXCHANGE,
                                      type='fanout')

    @staticmethod
    def _add_bindings(queue):
        with open_channel(BROKER_HOST_IP) as _channel:
            _channel.queue_bind(exchange=CLIENT_FANOUT_EXCHANGE,
                                queue=queue.method.queue)

    def start(self):
        consumer = ConsumerThread()
        consumer.start_thread()

        publisher = TimePublisherThread()
        t = publisher.start_thread()
        t.join()


if __name__ == '__main__':
    client = ClientBootstrapper()
    client.start()
