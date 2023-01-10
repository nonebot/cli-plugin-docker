import json
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import IO, TYPE_CHECKING, Any, List, Tuple, Union, Optional, cast

from nb_cli import cache
from nb_cli.config import SimpleInfo
from jinja2 import Environment, FileSystemLoader
from nb_cli.handlers import templates as cli_templates
from nb_cli.handlers import get_default_python, get_nonebot_config

from .exception import GetDriverTypeError, ComposeNotAvailable

templates = Environment(
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
    loader=FileSystemLoader(
        [
            Path(__file__).parent / "template",
            *cast(FileSystemLoader, cli_templates.loader).searchpath,
        ]
    ),
    enable_async=True,
)


@dataclass
class Compose:
    command: Tuple[str, ...]
    info: str


if TYPE_CHECKING:

    async def get_compose_command() -> Compose:
        ...

else:

    @cache(ttl=None)
    async def get_compose_command() -> Compose:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "version", stdout=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            return Compose(command=("docker", "compose"), info=stdout.decode())

        proc = await asyncio.create_subprocess_exec(
            "docker-compose", "version", stdout=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            return Compose(command=("docker-compose",), info=stdout.decode())

        raise ComposeNotAvailable


async def compose_up(
    compose_args: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
    stdin: Optional[Union[IO[Any], int]] = None,
    stdout: Optional[Union[IO[Any], int]] = None,
    stderr: Optional[Union[IO[Any], int]] = None,
) -> asyncio.subprocess.Process:
    compose = await get_compose_command()
    return await asyncio.create_subprocess_exec(
        *compose.command,
        "up",
        "-d",
        "--build",
        *(compose_args or []),
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr
    )


async def compose_down(
    compose_args: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
    stdin: Optional[Union[IO[Any], int]] = None,
    stdout: Optional[Union[IO[Any], int]] = None,
    stderr: Optional[Union[IO[Any], int]] = None,
) -> asyncio.subprocess.Process:
    compose = await get_compose_command()
    return await asyncio.create_subprocess_exec(
        *compose.command,
        "down",
        *(compose_args or []),
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr
    )


async def compose_build(
    compose_args: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
    stdin: Optional[Union[IO[Any], int]] = None,
    stdout: Optional[Union[IO[Any], int]] = None,
    stderr: Optional[Union[IO[Any], int]] = None,
) -> asyncio.subprocess.Process:
    compose = await get_compose_command()
    return await asyncio.create_subprocess_exec(
        *compose.command,
        "build",
        *(compose_args or []),
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr
    )


async def compose_log(
    compose_args: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
    stdin: Optional[Union[IO[Any], int]] = None,
    stdout: Optional[Union[IO[Any], int]] = None,
    stderr: Optional[Union[IO[Any], int]] = None,
) -> asyncio.subprocess.Process:
    compose = await get_compose_command()
    return await asyncio.create_subprocess_exec(
        *compose.command,
        "log",
        *(compose_args or []),
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr
    )


async def get_driver_type(
    adapters: Optional[List[SimpleInfo]] = None,
    builtin_plugins: Optional[List[str]] = None,
    python_path: Optional[str] = None,
) -> bool:
    bot_config = get_nonebot_config()
    if adapters is None:
        adapters = bot_config.adapters
    if builtin_plugins is None:
        builtin_plugins = bot_config.builtin_plugins
    if python_path is None:
        python_path = await get_default_python()

    t = templates.get_template("docker/get_driver_type.py.jinja")
    proc = await asyncio.create_subprocess_exec(
        python_path,
        "-W",
        "ignore",
        "-c",
        await t.render_async(adapters=adapters, builtin_plugins=builtin_plugins),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise GetDriverTypeError(stderr)

    return json.loads(stdout.strip())


async def generate_config_file():
    ...
