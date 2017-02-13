import os

import click

from time_sync.constants import SERVER_LOG_FILE
from time_sync_cli.exceptions import CLIUnexpectedStateException
from time_sync_cli.utils import tail_file


@click.group('server', help='Server operations')
def server():
    pass


@click.command(name='tail', help='Tail the server logs')
@click.option('--follow', '-f', is_flag=True, help='Block tail operation.')
@click.option('--verbose', '-v', is_flag=True, help='Include DEBUG logs.')
def tail(follow, verbose):
    if not os.path.isfile(SERVER_LOG_FILE):
        raise CLIUnexpectedStateException('Server logs were not found at {0}'
                                          .format(SERVER_LOG_FILE))
    tail_file(SERVER_LOG_FILE, follow=follow, verbose=verbose)
