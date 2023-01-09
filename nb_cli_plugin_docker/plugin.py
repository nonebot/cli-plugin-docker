from nb_cli.cli import cli

from .cli import docker


def install():
    cli.add_command(docker)
