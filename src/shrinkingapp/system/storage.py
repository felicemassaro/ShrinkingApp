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


def _probe_directory(path: Path) -> tuple[bool, bool]:
    readable = False
    writable = False
    try:
        list(path.iterdir())
        readable = True
    except OSError:
        readable = False

    if os.access(path, os.W_OK):
        writable = True
    return readable, writable


def discover_storage_locations() -> list[StorageEndpoint]:
    locations: list[StorageEndpoint] = []
    seen: set[str] = set()

    def add(label: str, path: Path, *, discovered: bool = False) -> None:
        try:
            if discovered:
                readable, writable = _probe_directory(path)
                if not readable and str(path).startswith("/media/psf/"):
                    readable = True
                    writable = True
            else:
                if not path.exists() or not path.is_dir():
                    return
                readable, writable = _probe_directory(path)
            if not readable and not writable:
                return
        except OSError:
            return

        key = os.path.realpath(path)
        if key in seen:
            return
        seen.add(key)
        capabilities = set()
        if readable:
            capabilities.add(EndpointCapability.READABLE)
            capabilities.add(EndpointCapability.BROWSABLE)
        if writable:
            capabilities.add(EndpointCapability.WRITABLE)
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
            add(f"Shared: {child.name}", child, discovered=True)

    media_root = Path("/media")
    if media_root.exists():
        for child in sorted(media_root.iterdir()):
            if child.name == "psf":
                continue
            if child.is_dir():
                add(f"Mounted: {child.name}", child, discovered=True)
                for grandchild in sorted(child.iterdir()):
                    add(f"Mounted: {grandchild.name}", grandchild, discovered=True)

    run_media_root = Path("/run/media") / getpass.getuser()
    if run_media_root.exists():
        for child in sorted(run_media_root.iterdir()):
            add(f"Mounted: {child.name}", child, discovered=True)

    mnt_root = Path("/mnt")
    if mnt_root.exists():
        for child in sorted(mnt_root.iterdir()):
            add(f"Mounted: {child.name}", child, discovered=True)

    return locations
