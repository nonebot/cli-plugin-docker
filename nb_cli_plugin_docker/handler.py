import json
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import IO, TYPE_CHECKING, Any, Union, Literal, Optional, cast

from nb_cli import cache
from jinja2 import Environment, FileSystemLoader
from nb_cli.handlers import templates as cli_templates
from nb_cli.config import GLOBAL_CONFIG, SimpleInfo, ConfigManager
from nb_cli.handlers import (
    get_project_root,
    requires_nonebot,
    get_default_python,
    get_nonebot_config,
    ensure_process_terminated,
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
templates.globals.update(cli_templates.globals)
templates.filters.update(cli_templates.filters)


@dataclass
class Compose:
    command: tuple[str, ...]
    info: str


if TYPE_CHECKING:

    async def get_compose_command() -> Compose: ...

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


@ensure_process_terminated
async def call_compose(
    compose_args: Optional[list[str]] = None,
    cwd: Optional[Path] = None,
    stdin: Optional[Union[IO[Any], int]] = None,
    stdout: Optional[Union[IO[Any], int]] = None,
    stderr: Optional[Union[IO[Any], int]] = None,
) -> asyncio.subprocess.Process:
    if cwd is None:
        cwd = get_project_root()

    compose = await get_compose_command()
    return await asyncio.create_subprocess_exec(
        *compose.command,
        *(compose_args or []),
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


async def compose_up(
    compose_args: Optional[list[str]] = None,
    cwd: Optional[Path] = None,
    stdin: Optional[Union[IO[Any], int]] = None,
    stdout: Optional[Union[IO[Any], int]] = None,
    stderr: Optional[Union[IO[Any], int]] = None,
) -> asyncio.subprocess.Process:
    return await call_compose(
        ["up", "-d", "--build", *(compose_args or [])],
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


async def compose_down(
    compose_args: Optional[list[str]] = None,
    cwd: Optional[Path] = None,
    stdin: Optional[Union[IO[Any], int]] = None,
    stdout: Optional[Union[IO[Any], int]] = None,
    stderr: Optional[Union[IO[Any], int]] = None,
) -> asyncio.subprocess.Process:
    return await call_compose(
        ["down", *(compose_args or [])],
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


async def compose_build(
    compose_args: Optional[list[str]] = None,
    cwd: Optional[Path] = None,
    stdin: Optional[Union[IO[Any], int]] = None,
    stdout: Optional[Union[IO[Any], int]] = None,
    stderr: Optional[Union[IO[Any], int]] = None,
) -> asyncio.subprocess.Process:
    return await call_compose(
        ["build", *(compose_args or [])],
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


async def compose_logs(
    compose_args: Optional[list[str]] = None,
    cwd: Optional[Path] = None,
    stdin: Optional[Union[IO[Any], int]] = None,
    stdout: Optional[Union[IO[Any], int]] = None,
    stderr: Optional[Union[IO[Any], int]] = None,
) -> asyncio.subprocess.Process:
    return await call_compose(
        ["logs", *(compose_args or [])],
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


async def compose_ps(
    compose_args: Optional[list[str]] = None,
    cwd: Optional[Path] = None,
    stdin: Optional[Union[IO[Any], int]] = None,
    stdout: Optional[Union[IO[Any], int]] = None,
    stderr: Optional[Union[IO[Any], int]] = None,
) -> asyncio.subprocess.Process:
    return await call_compose(
        ["ps", *(compose_args or [])],
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


@requires_nonebot
async def get_driver_type(
    adapters: Optional[list[SimpleInfo]] = None,
    builtin_plugins: Optional[list[str]] = None,
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
    if cwd is None:
        cwd = get_project_root()

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
        raise GetDriverTypeError(stdout, stderr)

    try:
        return json.loads(stdout.strip())
    except Exception as e:
        raise GetDriverTypeError(stdout, stderr) from e


async def get_build_backend(
    config_manager: Optional[ConfigManager] = None,
) -> Optional[Literal["poetry", "pdm", "pip"]]:
    if config_manager is None:
        config_manager = GLOBAL_CONFIG

    if data := config_manager._get_data():
        backend = data.get("build-system", {}).get("build-backend", "")
        if "poetry" in backend:
            return "poetry"
        elif "pdm" in backend:
            return "pdm"
    if (config_manager.project_root / "requirements.txt").exists():
        return "pip"


async def generate_dockerfile(
    python_version: str, is_asgi: bool, build_backend: Optional[str]
):
    t = templates.get_template(
        "docker/reverse.Dockerfile.jinja"
        if is_asgi
        else "docker/forward.Dockerfile.jinja"
    )
    return await t.render_async(
        python_version=python_version, build_backend=build_backend
    )


async def generate_compose_file(is_asgi: bool):
    t = templates.get_template("docker/docker-compose.yml.jinja")
    return await t.render_async(is_asgi=is_asgi)
