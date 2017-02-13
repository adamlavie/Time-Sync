import click

from time_sync_cli.bootstrap import TimeSyncBootstrapper
from time_sync_cli.local_storage import storage


@click.command(name='teardown', help='Teardown the Time-Sync application.')
def teardown():
    bootstrapper = TimeSyncBootstrapper()
    bootstrapper.teardown()
    if storage.get_local_data():
        storage.set_rabbitmq_ip('')
        storage.set_redis_ip('')
