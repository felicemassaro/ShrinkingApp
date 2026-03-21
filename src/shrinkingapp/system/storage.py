from __future__ import annotations

import getpass
import os
from pathlib import Path


def discover_storage_locations() -> list[tuple[str, Path]]:
    locations: list[tuple[str, Path]] = []
    seen: set[str] = set()

    def add(label: str, path: Path) -> None:
        try:
            if not path.exists() or not path.is_dir():
                return
            if not os.access(path, os.R_OK | os.W_OK):
                return
        except OSError:
            return

        key = os.path.realpath(path)
        if key in seen:
            return
        seen.add(key)
        locations.append((label, path))

    add("Home", Path.home())

    shared_root = Path("/media/psf")
    if shared_root.exists():
        for child in sorted(shared_root.iterdir()):
            add(f"Shared: {child.name}", child)

    media_root = Path("/media")
    if media_root.exists():
        for child in sorted(media_root.iterdir()):
            if child.name == "psf":
                continue
            if child.is_dir():
                add(f"Mounted: {child.name}", child)
                for grandchild in sorted(child.iterdir()):
                    add(f"Mounted: {grandchild.name}", grandchild)

    run_media_root = Path("/run/media") / getpass.getuser()
    if run_media_root.exists():
        for child in sorted(run_media_root.iterdir()):
            add(f"Mounted: {child.name}", child)

    mnt_root = Path("/mnt")
    if mnt_root.exists():
        for child in sorted(mnt_root.iterdir()):
            add(f"Mounted: {child.name}", child)

    return locations
