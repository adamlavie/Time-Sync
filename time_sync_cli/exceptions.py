import click


class CLIParameterException(click.ClickException):
    pass


class CLIUnexpectedStateException(click.ClickException):
    pass
