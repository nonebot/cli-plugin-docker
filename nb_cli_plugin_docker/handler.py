import json
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import IO, TYPE_CHECKING, Any, List, Tuple, Union, Literal, Optional, cast

import click
from nb_cli import cache
from jinja2 import Environment, FileSystemLoader
from nb_cli.config import GLOBAL_CONFIG, SimpleInfo
from nb_cli.handlers import templates as cli_templates
from nb_cli.handlers import (
    requires_nonebot,
    get_default_python,
    get_nonebot_config,
    get_python_version,
)

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
        stderr=stderr,
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
        stderr=stderr,
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
        stderr=stderr,
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
        stderr=stderr,
    )


@requires_nonebot
async def get_driver_type(
    adapters: Optional[List[SimpleInfo]] = None,
    builtin_plugins: Optional[List[str]] = None,
    python_path: Optional[str] = None,
    cwd: Optional[Path] = None,
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
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise GetDriverTypeError(stderr)

    return json.loads(stdout.strip())


async def get_build_backend() -> Optional[Literal["poetry", "pdm", "pip"]]:
    if data := GLOBAL_CONFIG._get_data():
        backend = data.get("build-system", {}).get("build-backend", "")
        if "poetry" in backend:
            return "poetry"
        elif "pdm" in backend:
            return "pdm"
    if (GLOBAL_CONFIG.file.parent / "requirements.txt").exists():
        return "pip"


async def generate_dockerfile(
    python_version: str,
    is_reverse: bool,
    build_backend: Optional[str],
    output_dir: Optional[Path] = None,
):
    path = (output_dir or Path.cwd()) / "Dockerfile"

    t = templates.get_template(
        "docker/reverse.Dockerfile.jinja"
        if is_reverse
        else "docker/forward.Dockerfile.jinja"
    )
    path.write_text(
        await t.render_async(python_version=python_version, build_backend=build_backend)
    )


async def generate_compose_file(
    is_reverse: bool,
    output_dir: Optional[Path] = None,
):
    path = (output_dir or Path.cwd()) / "docker-compose.yml"

    t = templates.get_template("docker/docker-compose.yml.jinja")
    path.write_text(await t.render_async(is_reverse=is_reverse))


async def generate_config_file(
    adapters: Optional[List[SimpleInfo]] = None,
    builtin_plugins: Optional[List[str]] = None,
    python_path: Optional[str] = None,
    cwd: Optional[Path] = None,
):
    python_version = await get_python_version(python_path)
    python_version = f"{python_version['major']}.{python_version['minor']}"
    is_reverse = await get_driver_type(adapters, builtin_plugins, python_path, cwd)
    build_backend = await get_build_backend()

    if build_backend is None:
        click.secho(
            "No build backend found, requirements will not be installed! "
            'Use one of "poetry", "pdm", "requirements.txt" to install requirements.',
            fg="yellow",
        )

    await generate_dockerfile(python_version, is_reverse, build_backend, cwd)
    await generate_compose_file(is_reverse, cwd)
