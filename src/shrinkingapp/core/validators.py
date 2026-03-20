from __future__ import annotations

import os
from pathlib import Path


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

