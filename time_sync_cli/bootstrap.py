import logging
import os
import uuid

import time_sync_cli.docker_helper as docker
from time_sync.constants import (RABBITMQ_HOST_IP_ENV,
                                 REDIS_HOST_IP_ENV,
                                 NUMBER_OF_SERVER_WORKERS_ENV,
                                 RABBITMQ_DOCKER_IMAGE,
                                 PYTHON_DOCKER_IMAGE,
                                 REDIS_DOCKER_IMAGE,
                                 BROKER_PORT,
                                 REDIS_PORT,
                                 DEFAULT_NUM_OF_CLIENTS,
                                 CLIENT_LOGS_PATH,
                                 SERVER_LOGS_PATH)
from time_sync.utils import wait_for_port

logger = logging.getLogger('bootstrap_logger')
logger.addHandler(logging.StreamHandler())
logger.level = logging.INFO

CLIENT_CONT_NAME_PREFIX = 'client_container'
SERVER_TS_CONT_NAME = 'server_ts_container'
RABBITMQ_TS_CONT_NAME = 'rabbitmq_ts_container'
REDIS_TS_CONT_NAME = 'redis_ts_container'


class TimeSyncBootstrapper(object,):
    def __init__(self, rabbit_host_ip=None, redis_host_ip=None):
        self.rabbit_host_ip = rabbit_host_ip
        self.redis_host_ip = redis_host_ip

    def bootstrap(self, num_clients, num_workers, project_dir=None):
        self._pull_base_images()
        self._start_redis_container()
        self._start_rabbitmq_container()
        self.start_client_containers(num_clients, project_dir=project_dir)
        self._start_server_container(num_workers, project_dir=project_dir)

    @staticmethod
    def teardown():
        logger.info('Terminating client containers..')
        docker.remove_container_by_name('{}*'.format(CLIENT_CONT_NAME_PREFIX))
        logger.info('Terminating server container..')
        docker.remove_container_by_name(SERVER_TS_CONT_NAME)
        logger.info('Terminating Rabbitmq container')
        docker.remove_container_by_name(RABBITMQ_TS_CONT_NAME)
        logger.info('Terminating redis container')
        docker.remove_container_by_name(REDIS_TS_CONT_NAME)

    @staticmethod
    def kill_client_by_ip(ip):
        return docker.remove_container_by_ip(ip=ip)

    @staticmethod
    def _pull_base_images(verbose=True):
        logger.info('Pulling required docker images..')

        if not docker.image_exists(PYTHON_DOCKER_IMAGE):
            logger.info('Pulling {python} base image..'
                        .format(python=PYTHON_DOCKER_IMAGE))
            python_image, tag = PYTHON_DOCKER_IMAGE.split(':')
            docker.pull_image(name=python_image, tag=tag, stream=verbose)

        if not docker.image_exists(REDIS_DOCKER_IMAGE):
            logger.info('Pulling {redis} image..'
                        .format(redis=REDIS_DOCKER_IMAGE))
            redis_image, tag = REDIS_DOCKER_IMAGE.split(':')
            docker.pull_image(name=redis_image, tag=tag, stream=verbose)

        if not docker.image_exists(RABBITMQ_DOCKER_IMAGE):
            logger.info('Pulling rabbitmq image:{}'
                        .format(RABBITMQ_DOCKER_IMAGE))
            rabbit_image, tag = RABBITMQ_DOCKER_IMAGE.split(':')
            docker.pull_image(name=rabbit_image, tag=tag, stream=verbose)

    def _start_server_container(self, num_workers='', project_dir=None):
        # Install and start the server
        proj_root = project_dir or self._get_project_root()
        cmd = ['sh', '-c', '-e',
               'pip install {0} && '
               'python {0}/time_sync/server.py'.format(proj_root)]
        env = {
            RABBITMQ_HOST_IP_ENV: self.rabbit_host_ip,
            REDIS_HOST_IP_ENV: self.redis_host_ip,
            NUMBER_OF_SERVER_WORKERS_ENV: num_workers

        }
        volumes, volume_binds = self._get_service_volumes(proj_root,
                                                          SERVER_LOGS_PATH)
        docker.create_and_start_container(
                              PYTHON_DOCKER_IMAGE,
                              name=SERVER_TS_CONT_NAME,
                              command=cmd,
                              environment=env,
                              volumes=volumes,
                              volume_binds=volume_binds)

    @staticmethod
    def _get_service_volumes(proj_root, logs_path):
        # Used to install a Time-Sync server/client service at bootstrap
        # using latest code
        project_volume, project_volume_binds = docker.get_volume(proj_root)
        # Used to sync service logs with host
        logs_volume, logs_binds = docker.get_volume(logs_path, ro=False)

        volumes = {}
        volumes.update(project_volume)
        volumes.update(logs_volume)

        volume_binds = {}
        volume_binds.update(project_volume_binds)
        volume_binds.update(logs_binds)

        return volumes, volume_binds

    def start_client_containers(self,
                                num_clients=None,
                                project_dir=None):
        num_clients = num_clients or DEFAULT_NUM_OF_CLIENTS
        proj_root = project_dir or self._get_project_root()
        logger.info('Starting {} client containers..'.format(num_clients))
        # Install the client on each of the containers
        cmd = ['sh', '-c', '-e',
               'pip install {0} && '
               'python {0}/time_sync/client.py'.format(proj_root)]
        # create a queue for each client
        volumes, volume_binds = self._get_service_volumes(proj_root,
                                                          CLIENT_LOGS_PATH)
        env = {
            RABBITMQ_HOST_IP_ENV: self.rabbit_host_ip,
            REDIS_HOST_IP_ENV: self.redis_host_ip
        }

        for i in xrange(num_clients):
            cid = docker.create_and_start_container(
                                   PYTHON_DOCKER_IMAGE,
                                   name='{0}_{1}'
                                        .format(CLIENT_CONT_NAME_PREFIX,
                                                str(uuid.uuid4())),
                                   volumes=volumes,
                                   environment=env,
                                   volume_binds=volume_binds,
                                   command=cmd)
            logger.info('Started new client at {}'
                        .format(docker.get_container_ip(cid)))

    def _start_rabbitmq_container(self):
        logger.info('Starting Rabbitmq service container..')
        container_id = docker.create_and_start_container(
            image=RABBITMQ_DOCKER_IMAGE,
            name=RABBITMQ_TS_CONT_NAME)

        self.rabbit_host_ip = docker.get_container_ip(container_id)
        logger.info('waiting for rabbitmq service port on {host}:{port}'
                    .format(host=self.rabbit_host_ip, port=BROKER_PORT))
        if not wait_for_port(self.rabbit_host_ip, BROKER_PORT):
            docker.remove_container(container_id)
            raise RuntimeError('Timed out waiting for rabbitmq service.')

    def _start_redis_container(self):
        logger.info('Starting Redis service container..')
        container_id = docker.create_and_start_container(
            image=REDIS_DOCKER_IMAGE,
            name=REDIS_TS_CONT_NAME)

        self.redis_host_ip = docker.get_container_ip(container_id)
        logger.info('waiting for redis service port on {host}:{port}'
                    .format(host=self.redis_host_ip, port=REDIS_PORT))
        if not wait_for_port(self.redis_host_ip, REDIS_PORT):
            docker.remove_container(container_id)
            raise RuntimeError('Timed out waiting for redis service.')

    @staticmethod
    def _get_project_root():
        curr_path = os.path.dirname(os.path.abspath(__file__))
        setup_py_path = os.path.join(curr_path, '..', 'setup.py')
        if not os.path.exists(setup_py_path):
            raise RuntimeError('Project root not found or does not contain a '
                               'setup.py file: {0}'.format(setup_py_path))
        return os.path.abspath(os.path.dirname(setup_py_path))


if __name__ == '__main__':
    app = TimeSyncBootstrapper()
    app.bootstrap(1, 3)
    # app.stop()
