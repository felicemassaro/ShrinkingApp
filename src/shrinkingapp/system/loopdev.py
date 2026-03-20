from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from shrinkingapp.system.commands import run_command


@contextmanager
def offset_loop_device(image_path: Path, offset_bytes: int, *, logger=None):
    result = run_command(
        ["losetup", "-f", "--show", "-o", str(offset_bytes), image_path],
        logger=logger,
    )
    loop_device = result.stdout.strip()
    try:
        yield loop_device
    finally:
        run_command(["losetup", "-d", loop_device], check=False, logger=logger)

