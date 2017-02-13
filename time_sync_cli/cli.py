from time_sync_cli.commands import init
from time_sync_cli.commands import server
from time_sync_cli.commands import clients
from time_sync_cli.commands import teardown
from time_sync_cli.commands import bootstrap

import click


@click.group('tsc')
def _tsc():
    pass


def _add_commands():
    _tsc.add_command(init.init)
    _tsc.add_command(bootstrap.bootstrap)
    _tsc.add_command(teardown.teardown)

    _tsc.add_command(clients.clients)
    clients.clients.add_command(clients.add)
    clients.clients.add_command(clients.get)
    clients.clients.add_command(clients.remove)
    clients.clients.add_command(clients.tail)
    clients.clients.add_command(clients.list)
    clients.clients.add_command(clients.get_master)

    _tsc.add_command(server.server)
    server.server.add_command(server.tail)


_add_commands()

if __name__ == '__main__':
    _tsc()
