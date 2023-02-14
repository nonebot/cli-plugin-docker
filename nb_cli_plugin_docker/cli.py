import asyncio
from pathlib import Path
from typing import List, cast

import click
from nb_cli import _
from noneprompt import Choice, ListPrompt, CancelledError
from nb_cli.cli import CLI_DEFAULT_STYLE, ClickAliasedGroup, run_sync, run_async
from nb_cli.handlers import (
    detect_virtualenv,
    terminate_process,
    get_python_version,
    remove_signal_handler,
    register_signal_handler,
)

from .utils import safe_write_file
from .handler import (
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
    choices: List[Choice[click.Command]] = []
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
@click.option("-d", "--cwd", default=".", type=Path, help="The working directory.")
@click.option(
    "--venv/--no-venv",
    default=True,
    help=_("Auto detect virtual environment."),
    show_default=True,
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Force to re-generate the Dockerfile.",
)
@run_async
async def generate(cwd: Path, venv: bool, force: bool):
    """Generate Dockerfile and docker-compose.yml."""
    if python_path := detect_virtualenv() if venv else None:
        click.secho(
            _("Using virtual environment: {python_path}").format(
                python_path=python_path
            ),
            fg="green",
        )

    python_version = await get_python_version(python_path)
    python_version = f"{python_version['major']}.{python_version['minor']}"
    is_reverse = await get_driver_type(python_path=python_path, cwd=cwd)
    build_backend = await get_build_backend()

    dockerfile = await generate_dockerfile(
        python_version=python_version,
        is_reverse=is_reverse,
        build_backend=build_backend,
    )
    await safe_write_file(cwd / "Dockerfile", dockerfile, force=force)

    compose_file = await generate_compose_file(is_reverse=is_reverse)
    await safe_write_file(cwd / "docker-compose.yml", compose_file, force=force)

    if not is_reverse:
        return

    for file in (Path(__file__).parent / "docker").iterdir():
        await safe_write_file(cwd / "docker" / file.name, file.read_text(), force=force)


@docker.command(aliases=["run"], context_settings={"ignore_unknown_options": True})
@click.option("-d", "--cwd", default=".", type=Path, help="The working directory.")
@click.option(
    "--venv/--no-venv",
    default=True,
    help=_("Auto detect virtual environment."),
    show_default=True,
)
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
async def up(
    ctx: click.Context, cwd: Path, venv: bool, force: bool, compose_args: List[str]
):
    """Deploy the bot."""
    if (
        force
        or not Path(cwd, "Dockerfile").exists()
        or not Path(cwd, "docker-compose.yml").exists()
    ):
        await run_sync(ctx.invoke)(generate)

    should_exit = asyncio.Event()

    def shutdown(signum, frame):
        should_exit.set()

    async def wait_for_shutdown():
        await should_exit.wait()
        await terminate_process(proc)

    register_signal_handler(shutdown)
    proc = await compose_up(compose_args, cwd=cwd)
    task = asyncio.create_task(wait_for_shutdown())
    await proc.wait()
    should_exit.set()
    await task
    remove_signal_handler(shutdown)


@docker.command(aliases=["stop"], context_settings={"ignore_unknown_options": True})
@click.option("-d", "--cwd", default=".", type=Path, help="The working directory.")
@click.argument("compose_args", nargs=-1)
@run_async
async def down(cwd: Path, compose_args: List[str]):
    """Undeploy the bot."""
    should_exit = asyncio.Event()

    def shutdown(signum, frame):
        should_exit.set()

    async def wait_for_shutdown():
        await should_exit.wait()
        await terminate_process(proc)

    register_signal_handler(shutdown)
    proc = await compose_down(compose_args, cwd=cwd)
    task = asyncio.create_task(wait_for_shutdown())
    await proc.wait()
    should_exit.set()
    await task
    remove_signal_handler(shutdown)


@docker.command(context_settings={"ignore_unknown_options": True})
@click.option("-d", "--cwd", default=".", type=Path, help="The working directory.")
@click.argument("compose_args", nargs=-1)
@run_async
async def build(cwd: Path, compose_args: List[str]):
    """Build the bot image."""
    should_exit = asyncio.Event()

    def shutdown(signum, frame):
        should_exit.set()

    async def wait_for_shutdown():
        await should_exit.wait()
        await terminate_process(proc)

    register_signal_handler(shutdown)
    proc = await compose_build(compose_args, cwd=cwd)
    task = asyncio.create_task(wait_for_shutdown())
    await proc.wait()
    should_exit.set()
    await task
    remove_signal_handler(shutdown)


@docker.command(context_settings={"ignore_unknown_options": True})
@click.option("-d", "--cwd", default=".", type=Path, help="The working directory.")
@click.argument("compose_args", nargs=-1)
@run_async
async def logs(cwd: Path, compose_args: List[str]):
    """View the bot logs."""
    should_exit = asyncio.Event()

    def shutdown(signum, frame):
        should_exit.set()

    async def wait_for_shutdown():
        await should_exit.wait()
        await terminate_process(proc)

    register_signal_handler(shutdown)
    proc = await compose_logs(compose_args, cwd=cwd)
    task = asyncio.create_task(wait_for_shutdown())
    await proc.wait()
    should_exit.set()
    await task
    remove_signal_handler(shutdown)
