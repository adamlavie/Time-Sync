import os

import click

from time_sync.constants import (CLIENT_LOGS_PATH,
                                 SERVER_LOGS_PATH)
from time_sync_cli.exceptions import CLIParameterException
from time_sync_cli.local_storage import storage


@click.command(name='init', help='Initialize local work environment')
@click.option('-p', '--project-root', required=False,
              help='Path to project root directory. For example '
              '\'~/dev/time-sync\'')
def init(project_root):
    print 'Initializing Time-Sync CLI local env.'
    local_data = storage.get_local_data()
    if not local_data:
        if not project_root:
            raise CLIParameterException('a Path to project root directory '
                                        'must be provided. For example: '
                                        '\'~/dev/time-sync\'')
        else:
            if not os.path.exists(os.path.join(project_root, 'setup.py')):
                raise CLIParameterException('Time-sync \'setup.py\' could not'
                                            ' be found in {0}'.format(
                                                os.path.abspath(project_root)))
            storage.init_local_storage(os.path.abspath(project_root))
    elif project_root:
            storage.set_project_root(os.path.abspath(project_root))

    # Create client and server log dirs on host
    if not os.path.isdir(CLIENT_LOGS_PATH):
        os.mkdir(CLIENT_LOGS_PATH)
    if not os.path.isdir(SERVER_LOGS_PATH):
        os.mkdir(SERVER_LOGS_PATH)

    print 'Time-Sync CLI environment initialized successfully.'
