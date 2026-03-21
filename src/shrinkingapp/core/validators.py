from __future__ import annotations

import os
import stat
from pathlib import Path

from shrinkingapp.models import CaptureSourceKind


def ensure_root() -> None:
    if os.geteuid() != 0:
        raise PermissionError("This command must be run as root.")


def validate_source_image(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Image not found: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"Not a regular file: {resolved}")
    return resolved


def validate_output_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def validate_block_device(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    stat_result = resolved.stat()
    if not stat.S_ISBLK(stat_result.st_mode):
        raise ValueError(f"Not a block device: {resolved}")
    return resolved


def resolve_capture_source(path: Path) -> tuple[Path, CaptureSourceKind]:
    resolved = path.expanduser().resolve()
    stat_result = resolved.stat()
    if stat.S_ISBLK(stat_result.st_mode):
        return resolved, CaptureSourceKind.BLOCK_DEVICE
    if stat.S_ISREG(stat_result.st_mode):
        return resolved, CaptureSourceKind.IMAGE_FILE
    raise ValueError(f"Unsupported capture source: {resolved}")
