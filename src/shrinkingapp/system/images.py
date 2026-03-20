from __future__ import annotations

import hashlib
from pathlib import Path

from shrinkingapp.models import CompressionKind
from shrinkingapp.system.commands import run_command


def normalize_output_image_path(
    source_image: Path,
    requested_output: Path | None,
    compression: CompressionKind | None,
) -> Path:
    if requested_output is None:
        return source_image

    output_image = requested_output.expanduser()
    if compression is CompressionKind.GZIP and output_image.suffix == ".gz":
        output_image = output_image.with_suffix("")
    if compression is CompressionKind.XZ and output_image.suffix == ".xz":
        output_image = output_image.with_suffix("")
    return output_image.resolve()


def copy_image(source_image: Path, output_image: Path, *, logger=None) -> None:
    output_image.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        ["cp", "--reflink=auto", "--sparse=always", source_image, output_image],
        logger=logger,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_size_bytes(path: Path) -> int:
    return path.stat().st_size


def truncate_image(path: Path, size_bytes: int, *, logger=None) -> None:
    run_command(["truncate", "-s", str(size_bytes), path], logger=logger)

