from pathlib import Path
from typing import Optional

from noneprompt import ConfirmPrompt


async def safe_write_file(
    file_path: Path, content: str, force: bool = False
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
    return file_path.write_text(content)
