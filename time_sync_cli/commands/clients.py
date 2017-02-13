import os
import pickle
import socket

import click

from time_sync.constants import CLIENT_LOGS_PATH, REDIS_PORT
from time_sync.redis_client import RedisClient
from time_sync_cli.bootstrap import TimeSyncBootstrapper
from time_sync_cli.exceptions import (CLIParameterException,
                                      CLIUnexpectedStateException)
from time_sync_cli.local_storage import storage
from time_sync_cli.utils import tail_file


@click.group('clients', help='Client operations')
def clients():
    pass


@click.command(name='add', help='Add clients to the cluster')
@click.option('--number-of-clients', '-n', required=True, type=int,
              help='The number of clients to add to the cluster.')
def add(number_of_clients):
    rabbitmq_ip = storage.get_rabbitmq_ip()
    redis_ip = storage.get_redis_ip()
    project_root = storage.get_project_root()

    if not rabbitmq_ip:
        raise CLIParameterException('Missing Rabbit IP address in local env.')
    if not redis_ip:
        raise CLIParameterException('Missing Redis IP address in local env.')
    if not project_root:
        raise CLIParameterException('Missing project root in local env.')

    bootstrapper = TimeSyncBootstrapper(rabbit_host_ip=rabbitmq_ip,
                                        redis_host_ip=redis_ip)
    bootstrapper.start_client_containers(
        num_clients=number_of_clients,
        project_dir=project_root)


@click.command(name='list', help='List all clients in the cluster.')
@click.option('--verbose', '-v', is_flag=True, help='Verbosity')
def list(verbose):
    server_storage = _get_server_storage()
    all_clients = server_storage.get_all_clients()
    print 'Found {0} clients in cluster:'.format(len(all_clients))
    for client in all_clients:
        if verbose:
            print_client_data(client)
        else:
            print client['id']


@click.command(name='get', help='Gets Client Details')
@click.option('--client-id', '-c', required=True,
              help='The client ID')
def get(client_id):
    print 'Getting data for client with ID {0}'.format(client_id)
    client_data = _get_client(client_id)
    print_client_data(client_data)


@click.command(name='remove', help='Remove a client from the cluster by ID.'
                                   'This currently supports one client per '
                                   'container.')
@click.option('--client-id', '-c', required=True,
              help='The client ID.')
def remove(client_id):
    client_data = _get_client(client_id)
    print 'Attempting to remove client with ID {0}'\
          .format(client_data['id'])
    result = TimeSyncBootstrapper.kill_client_by_ip(client_data['ip'])
    if not result:
        raise CLIUnexpectedStateException('Failed removing client with ID {0}'
                                          .format(client_id))
    print 'Client at IP {0} removed successfully'\
          .format(client_data['ip'])


@click.command(name='get-master', help='Get the master client ID as known by '
                                       'the Time-Sync server.')
@click.option('--verbose', '-v', is_flag=True, help='All master data.',
              default=False)
def get_master(verbose):
    server_storage = _get_server_storage()
    master_data = server_storage.get_master_data()
    if verbose:
        print_client_data(master_data)
    else:
        print master_data['id']


def print_client_data(data):
    print 'Client ID: {0}, IP Address {1}, Time {2}, Master Client ID {3}'\
          .format(data['id'], data['ip'], data['time'], data['master_id'])


@click.command(name='tail', help='Tail client logs by ID')
@click.option('--client-id', '-c', required=True, help='The client ID.')
@click.option('--follow', '-f', is_flag=True, help='Block tail operation.')
@click.option('--verbose', '-v', is_flag=True, help='Include DEBUG logs.')
def tail(client_id, follow, verbose):
    log_path = os.path.join(CLIENT_LOGS_PATH, client_id)
    if not os.path.isfile(log_path):
        raise CLIUnexpectedStateException('Client logs were not found at {0}'
                                          .format(log_path))
    tail_file(log_path, follow=follow, verbose=verbose)


def _get_server_storage():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if not sock.connect_ex((storage.get_redis_ip(), REDIS_PORT)) == 0:
        raise CLIUnexpectedStateException(
            'Redis service is not available on {ip}:{port}. Are you '
            'bootstrapped?'.format(ip=storage.get_redis_ip(), port=REDIS_PORT))
    redis_ip = storage.get_redis_ip()
    RedisClient(redis_host=redis_ip)
    return RedisClient(redis_host=redis_ip)


def _get_client(client_id):
    server_storage = _get_server_storage()
    client_data = server_storage.get_client_data(client_id)
    if not client_data:
        raise CLIParameterException('Client with ID {0} was not found.'
                                    .format(client_id))
    return pickle.loads(client_data)
