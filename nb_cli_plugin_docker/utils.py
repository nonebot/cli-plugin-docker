from anyio import Path
from noneprompt import ConfirmPrompt


async def safe_write_file(
    file_path: Path, content: str | bytes, force: bool = False
) -> int | None:
    directory = file_path.parent
    if not await directory.exists():
        await directory.mkdir(exist_ok=True, parents=True)
    elif not await directory.is_dir():
        raise RuntimeError(f"File {directory} already exists and is not a directory")

    if (
        await file_path.exists()
        and not force
        and not await ConfirmPrompt(
            f"File {file_path} already exists, overwrite?",
            default_choice=False,
        ).prompt_async()
    ):
        return

    return (
        await file_path.write_text(content, encoding="utf-8")
        if isinstance(content, str)
        else await file_path.write_bytes(content)
    )


async def safe_copy_dir(source: Path, destination: Path, force: bool = False):
    if not await source.exists():
        raise RuntimeError(f"Directory {source} does not exist")
    if not await source.is_dir():
        raise RuntimeError(f"Path {source} is not a directory")

    if not await destination.exists():
        await destination.mkdir(exist_ok=True, parents=True)
    elif not await destination.is_dir():
        raise RuntimeError(f"File {destination} already exists and is not a directory")

    async for file in source.iterdir():
        if await file.is_dir():
            await safe_copy_dir(file, destination / file.name, force=force)
        else:
            await safe_write_file(
                destination / file.name, await file.read_bytes(), force=force
            )
