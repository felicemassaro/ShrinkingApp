from __future__ import annotations

import shutil
from pathlib import Path

from shrinkingapp.models import CompressionKind
from shrinkingapp.system.commands import require_commands, run_command


def compress_image(
    image_path: Path,
    compression: CompressionKind,
    *,
    parallel: bool,
    logger=None,
) -> Path:
    if compression is CompressionKind.GZIP:
        compressor = "pigz" if parallel and shutil.which("pigz") else "gzip"
        require_commands([compressor])
        run_command([compressor, "-f9", image_path], logger=logger)
        return Path(f"{image_path}.gz")

    if compression is CompressionKind.XZ:
        require_commands(["xz"])
        args = ["xz", "-f", "-9"]
        if parallel:
            args.append("-T0")
        args.append(str(image_path))
        run_command(args, logger=logger)
        return Path(f"{image_path}.xz")

    raise ValueError(f"Unsupported compression: {compression}")

