from typing import cast
from pathlib import Path

import click
from nb_cli import _
from nb_cli.config import ConfigManager
from noneprompt import Choice, ListPrompt, CancelledError
from nb_cli.cli import CLI_DEFAULT_STYLE, ClickAliasedGroup, run_sync, run_async
from nb_cli.handlers import get_project_root, get_default_python, get_python_version

from .utils import safe_copy_dir, safe_write_file
from .handler import (
    compose_ps,
    compose_up,
    compose_down,
    compose_logs,
    compose_build,
    get_driver_type,
    get_build_backend,
    generate_dockerfile,
    generate_compose_file,
)


@click.group(cls=ClickAliasedGroup, invoke_without_command=True)
@click.pass_context
@run_async
async def docker(ctx: click.Context):
    """Manage Bot Deployment with Docker."""
    if ctx.invoked_subcommand is not None:
        return

    command = cast(ClickAliasedGroup, ctx.command)

    # auto discover sub commands and scripts
    choices: list[Choice[click.Command]] = []
    for sub_cmd_name in await run_sync(command.list_commands)(ctx):
        if sub_cmd := await run_sync(command.get_command)(ctx, sub_cmd_name):
            choices.append(
                Choice(
                    sub_cmd.help
                    or _("Run subcommand {sub_cmd.name!r}").format(sub_cmd=sub_cmd),
                    sub_cmd,
                )
            )

    try:
        result = await ListPrompt(
            _("What do you want to do?"), choices=choices
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    except CancelledError:
        ctx.exit()

    sub_cmd = result.data
    await run_sync(ctx.invoke)(sub_cmd)


@docker.command()
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Force to re-generate the Dockerfile.",
)
@click.pass_context
@run_async
async def generate(ctx: click.Context, force: bool):
    """Generate Dockerfile and docker-compose.yml."""
    python_path = await get_default_python()
    cwd = get_project_root()

    python_version = await get_python_version(python_path=python_path)
    python_version = f"{python_version['major']}.{python_version['minor']}"

    is_asgi = await get_driver_type(python_path=python_path, cwd=cwd)
    build_backend = await get_build_backend(
        config_manager=ConfigManager(working_dir=cwd, python_path=python_path)
    )

    try:
        dockerfile = await generate_dockerfile(
            python_version=python_version,
            is_asgi=is_asgi,
            build_backend=build_backend,
        )
        await safe_write_file(cwd / "Dockerfile", dockerfile, force=force)

        compose_file = await generate_compose_file(is_asgi=is_asgi)
        await safe_write_file(cwd / "docker-compose.yml", compose_file, force=force)

        await safe_copy_dir(
            Path(__file__).parent / "static" / "common", cwd, force=force
        )

        if is_asgi:
            await safe_copy_dir(
                Path(__file__).parent / "static" / "reverse", cwd, force=force
            )
    except CancelledError:
        ctx.exit()


@docker.command(aliases=["run"], context_settings={"ignore_unknown_options": True})
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Force to re-generate the Dockerfile.",
)
@click.argument("compose_args", nargs=-1)
@click.pass_context
@run_async
async def up(ctx: click.Context, force: bool, compose_args: list[str]):
    """Deploy the bot."""
    cwd = get_project_root()

    if (
        force
        or not Path(cwd, "Dockerfile").exists()
        or not Path(cwd, "docker-compose.yml").exists()
    ):
        await run_sync(ctx.invoke)(generate)

    proc = await compose_up(compose_args, cwd=cwd)
    await proc.wait()


@docker.command(aliases=["stop"], context_settings={"ignore_unknown_options": True})
@click.argument("compose_args", nargs=-1)
@run_async
async def down(compose_args: list[str]):
    """Undeploy the bot."""
    proc = await compose_down(compose_args)
    await proc.wait()


@docker.command(context_settings={"ignore_unknown_options": True})
@click.argument("compose_args", nargs=-1)
@run_async
async def build(compose_args: list[str]):
    """Build the bot image."""
    proc = await compose_build(compose_args)
    await proc.wait()


@docker.command(context_settings={"ignore_unknown_options": True})
@click.argument("compose_args", nargs=-1)
@run_async
async def logs(compose_args: list[str]):
    """View the bot logs."""
    proc = await compose_logs(compose_args)
    await proc.wait()


@docker.command(context_settings={"ignore_unknown_options": True})
@click.argument("compose_args", nargs=-1)
@run_async
async def ps(compose_args: list[str]):
    """View the bot service status."""
    proc = await compose_ps(compose_args)
    await proc.wait()
