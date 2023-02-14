from typing import cast

from nb_cli.cli import CLIMainGroup, cli

from .cli import docker


def install():
    cli_ = cast(CLIMainGroup, cli)
    cli_.add_command(docker)
    cli_.add_aliases("docker", ["deploy", "compose"])
