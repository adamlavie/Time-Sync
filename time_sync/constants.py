import os
# TODO: Move to project root

# Environment vars that will be injected to the clients
RABBITMQ_HOST_IP_ENV = 'RABBITMQ_HOST_IP_ENV'
REDIS_HOST_IP_ENV = 'REDIS_HOST_IP_ENV'
CLIENT_MASTER_UPDATE_QUEUE_ENV = 'CLIENT_MASTER_UPDATE_QUEUE_ENV'
NUMBER_OF_SERVER_WORKERS_ENV = 'NUMBER_OF_SERVER_WORKERS_ENV'


# Messaging queue used to pass time json messages
CLIENT_MESSAGING_QUEUE = 'client_messaging_queue'
CLIENT_FANOUT_EXCHANGE = 'client_fanout_exchange'

# Bootstrap defaults
DEFAULT_NUM_SERVER_WORKERS = '4'
DEFAULT_NUM_OF_CLIENTS = 4
BROKER_PORT = 5672
REDIS_PORT = 6379


# Execution docker images
RABBITMQ_DOCKER_IMAGE = 'rabbitmq:latest'
PYTHON_DOCKER_IMAGE = 'python:2.7'
REDIS_DOCKER_IMAGE = 'redis:latest'


# CLI local storage constants
CLI_WORKDIR = os.path.join(os.path.expanduser("~"), '.tsc')
SERVER_LOGS_PATH = '/tmp/ts_server_logs'
CLIENT_LOGS_PATH = '/tmp/ts_client_logs'
SERVER_LOG_FILE = os.path.join(SERVER_LOGS_PATH, 'server.json')
CLI_LOCAL_DATA_FILE = os.path.join(CLI_WORKDIR, 'data.json')


# Logging constants
