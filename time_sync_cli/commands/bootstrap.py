import os
import subprocess

import click

from time_sync.constants import (DEFAULT_NUM_SERVER_WORKERS,
                                 DEFAULT_NUM_OF_CLIENTS)
from time_sync_cli.bootstrap import TimeSyncBootstrapper
from time_sync_cli.exceptions import CLIParameterException
from time_sync_cli.local_storage import storage


@click.command(name='bootstrap', help='Bootstrap the Time-Sync application.')
@click.option('-c', '--number-of-clients', required=False, type=int,
              help='The number of clients to start. Default is set to: {}.'
                    .format(DEFAULT_NUM_OF_CLIENTS))
@click.option('-w', '--number-of-workers', required=False, type=int,
              help='The number of workers running on the Time-Sync server.'
                   ' Default is set to: {}'.format(DEFAULT_NUM_SERVER_WORKERS))
def bootstrap(number_of_clients,
              number_of_workers):
    local_data = storage.get_local_data()
    if not local_data or not os.path.isdir(storage.get_project_root()):
        raise CLIParameterException('Not initialized. Run \'tsc init\'.')

    if not _docker_installed():
        raise CLIParameterException('The tsc CLI requires having docker '
                                    'installed.')

    if not _docker_privileged():
        raise CLIParameterException('tsc CLI can not run docker containers in '
                                    'privileged mode. Please run '
                                    '\'sudo usermod -aG docker $USER\''
                                    ' and start a new bash session.')

    if storage.get_rabbitmq_ip() or storage.get_redis_ip():
        raise CLIParameterException('Environment not clean. Teardown before '
                                    're-bootstrapping using the '
                                    '\'tsc teardown\' command.')

    bootstrapper = TimeSyncBootstrapper()
    bootstrapper.bootstrap(num_clients=number_of_clients,
                           num_workers=number_of_workers,
                           project_dir=storage.get_project_root())

    storage.set_rabbitmq_ip(bootstrapper.rabbit_host_ip)
    storage.set_redis_ip(bootstrapper.redis_host_ip)


def _docker_installed():
    result = subprocess.call('which docker', shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result == 0


def _docker_privileged():
    result = subprocess.call('docker images', shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result == 0
