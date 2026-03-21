from __future__ import annotations

import getpass
import os
from pathlib import Path

from shrinkingapp.models import EndpointCapability, EndpointKind, StorageEndpoint


def _is_external_path(path: Path) -> bool:
    external_roots = (
        Path("/media/psf"),
        Path("/media"),
        Path("/run/media"),
        Path("/mnt"),
    )
    return any(path == root or path.is_relative_to(root) for root in external_roots)


def discover_storage_locations() -> list[StorageEndpoint]:
    locations: list[StorageEndpoint] = []
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
        capabilities = {
            EndpointCapability.READABLE,
            EndpointCapability.WRITABLE,
            EndpointCapability.BROWSABLE,
        }
        if _is_external_path(path):
            capabilities.add(EndpointCapability.EXTERNAL)
        locations.append(
            StorageEndpoint(
                label=label,
                path=path,
                kind=EndpointKind.FILESYSTEM,
                capabilities=frozenset(capabilities),
            )
        )

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
