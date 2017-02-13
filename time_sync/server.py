import os
import shlex
import pickle
import logging

from celery import Celery, bootsteps
from kombu import Exchange, Queue, Consumer

from redis_client import instance as storage_manager
from time_sync.constants import (RABBITMQ_HOST_IP_ENV,
                                 BROKER_PORT,
                                 CLIENT_MESSAGING_QUEUE,
                                 CLIENT_FANOUT_EXCHANGE,
                                 NUMBER_OF_SERVER_WORKERS_ENV,
                                 DEFAULT_NUM_SERVER_WORKERS,
                                 SERVER_LOGS_PATH)
from utils import open_channel, create_logger

# TODO: raise on None or set default?
BROKER_HOST_IP = os.getenv(RABBITMQ_HOST_IP_ENV)
NUMBER_OF_SERVER_WORKERS = os.getenv(NUMBER_OF_SERVER_WORKERS_ENV,
                                     DEFAULT_NUM_SERVER_WORKERS)
CELERY_START_COMMAND = 'celery worker --concurrency {} -B'\
                        .format(NUMBER_OF_SERVER_WORKERS)


logger = create_logger('server_logger',
                       path=os.path.join(SERVER_LOGS_PATH, 'server.json'),
                       level=logging.DEBUG)

# Init the Celery app
app = Celery(broker='amqp://guest:guest@{host_ip}:{port}//'
             .format(host_ip=BROKER_HOST_IP, port=BROKER_PORT))


############################
# Time message related tasks
############################


@app.task(name='is_master_client')
def handle_client_message_task(msg):
    """
    This task will be executed whenever a client message is picked up from
    the queue by the consumer. This task may be executed by multiple processes.
    """
    storage_manager.set_client_data(data=pickle.loads(msg))


class ServerConsumerStep(bootsteps.ConsumerStep):

    def get_consumers(self, channel):
        queue = Queue(name=CLIENT_MESSAGING_QUEUE,
                      exchange=Exchange(''),
                      routing_key=CLIENT_MESSAGING_QUEUE,
                      no_declare=True)
        return [Consumer(channel,
                         queues=[queue],
                         callbacks=[self.handle_time_message],
                         accept=['json'])]

    def handle_time_message(self, body, message):
        handle_client_message_task.delay(body)
        message.ack()


# add the consumer to celery app
app.steps['consumer'].add(ServerConsumerStep)

############################
# Master client clock delivery to clients is handled here
############################


@app.task
def send_master_time_to_clients():
    """
    This task will be registered to be executed periodically by one on the
    celery processes.
    :return:
    """
    master_data = storage_manager.get_master_data()
    if not master_data:
        master_data = storage_manager.elect_leader() or {}

    if master_data:
        logger.debug('Master client ID:\'{0}\', IP:\'{1}\', Time:\'{2}\'.'
                     .format(master_data.get('id'),
                             master_data.get('ip'),
                             master_data.get('time')))

        with app.producer_or_acquire() as producer:
            producer.publish(
                pickle.dumps(master_data),
                exchange=Exchange(CLIENT_FANOUT_EXCHANGE, type='fanout'),
                routing_key='',
                retry=True,
            )
    else:
        logger.info('Electing master client, no data available..')


# Register a periodic task for fanout exchange to clients
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Sends message to client queues every second
    sender.add_periodic_task(1.0, send_master_time_to_clients.s(),
                             name='Sends the master time to client exchange '
                                  'using fanout every second')


class ServerBootstrapper(object):
    def __init__(self):
        # Create the message exchange for client queues
        self._create_exchange()
        # Create the queue to which all client messages will be sent to.
        # A client registered with this server will be in-charge of creating
        # It's own message queue and bind it with the exchange.
        self._create_queue()

    @staticmethod
    def start():
        app.start(shlex.split(CELERY_START_COMMAND))

    @staticmethod
    def _create_queue():
        with open_channel(BROKER_HOST_IP) as _channel:
            return _channel.queue_declare(queue=CLIENT_MESSAGING_QUEUE,
                                          durable=True)

    @staticmethod
    def _create_exchange():
        with open_channel(BROKER_HOST_IP) as _channel:
            _channel.exchange_declare(exchange=CLIENT_FANOUT_EXCHANGE,
                                      type='fanout')


if __name__ == '__main__':
    server = ServerBootstrapper()
    server.start()
