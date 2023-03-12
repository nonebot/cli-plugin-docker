from pathlib import Path
from typing import Union, Optional

from noneprompt import ConfirmPrompt


async def safe_write_file(
    file_path: Path, content: Union[str, bytes], force: bool = False
) -> Optional[int]:
    directory = file_path.parent
    if not directory.exists():
        directory.mkdir(exist_ok=True, parents=True)
    elif not directory.is_dir():
        raise RuntimeError(f"File {directory} already exists and is not a directory")

    if (
        file_path.exists()
        and not force
        and not await ConfirmPrompt(
            f"File {file_path} already exists, overwrite?",
            default_choice=False,
        ).prompt_async()
    ):
        return

    return (
        file_path.write_text(content, encoding="utf-8")
        if isinstance(content, str)
        else file_path.write_bytes(content)
    )


async def safe_copy_dir(source: Path, destination: Path, force: bool = False):
    if not source.exists():
        raise RuntimeError(f"Directory {source} does not exist")
    if not source.is_dir():
        raise RuntimeError(f"Path {source} is not a directory")

    if not destination.exists():
        destination.mkdir(exist_ok=True, parents=True)
    elif not destination.is_dir():
        raise RuntimeError(f"File {destination} already exists and is not a directory")

    for file in source.iterdir():
        if file.is_dir():
            await safe_copy_dir(file, destination / file.name, force=force)
        else:
            await safe_write_file(
                destination / file.name, file.read_bytes(), force=force
            )
