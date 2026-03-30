from __future__ import annotations

import getpass
import os
import shutil
from pathlib import Path

from shrinkingapp.models import EndpointCapability, EndpointKind, StorageEndpoint, StoragePathContext
from shrinkingapp.system.commands import run_command
from shrinkingapp.system.devices import get_parent_disk


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
        with os.scandir(path) as entries:
            next(entries, None)
        readable = True
    except OSError:
        readable = False

    if os.access(path, os.W_OK):
        writable = True
    return readable, writable


def _safe_sorted_children(path: Path) -> list[Path]:
    try:
        return sorted(path.iterdir())
    except OSError:
        return []


def _mount_is_writable(path: Path) -> bool | None:
    try:
        result = run_command(
            [
                "findmnt",
                "--json",
                "--target",
                str(path),
                "-o",
                "OPTIONS",
            ],
            check=False,
        )
    except OSError:
        return None

    if result.returncode != 0 or not result.stdout.strip():
        return None

    import json

    try:
        payload = json.loads(result.stdout)
        filesystems = payload.get("filesystems") or []
        if not filesystems:
            return None
        options = filesystems[0].get("options")
        if not isinstance(options, str):
            return None
        option_set = {item.strip() for item in options.split(",") if item.strip()}
        if "rw" in option_set:
            return True
        if "ro" in option_set:
            return False
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    return None


def discover_storage_locations() -> list[StorageEndpoint]:
    locations: list[StorageEndpoint] = []
    seen: set[str] = set()

    def add(label: str, path: Path, *, discovered: bool = False) -> None:
        try:
            if discovered:
                readable, writable = _probe_directory(path)
                mount_writable = _mount_is_writable(path)
                if mount_writable is True:
                    writable = True
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
        for child in _safe_sorted_children(shared_root):
            add(f"Shared: {child.name}", child, discovered=True)

    media_root = Path("/media")
    if media_root.exists():
        for child in _safe_sorted_children(media_root):
            if child.name == "psf":
                continue
            if child.is_dir():
                add(f"Mounted: {child.name}", child, discovered=True)
                for grandchild in _safe_sorted_children(child):
                    add(f"Mounted: {grandchild.name}", grandchild, discovered=True)

    run_media_root = Path("/run/media") / getpass.getuser()
    if run_media_root.exists():
        for child in _safe_sorted_children(run_media_root):
            add(f"Mounted: {child.name}", child, discovered=True)

    mnt_root = Path("/mnt")
    if mnt_root.exists():
        for child in _safe_sorted_children(mnt_root):
            add(f"Mounted: {child.name}", child, discovered=True)

    return locations


def _best_matching_location(path: Path) -> StorageEndpoint | None:
    resolved = path.expanduser().resolve(strict=False)
    best: StorageEndpoint | None = None
    best_length = -1
    for endpoint in discover_storage_locations():
        try:
            resolved.relative_to(endpoint.path)
        except ValueError:
            continue
        length = len(endpoint.path.parts)
        if length > best_length:
            best = endpoint
            best_length = length
    return best


def _parse_findmnt_value(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or stripped == "?":
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def describe_storage_path(path: Path, *, logger=None) -> StoragePathContext:
    resolved = path.expanduser().resolve(strict=False)
    context = StoragePathContext(selected_path=resolved)

    location = _best_matching_location(resolved)
    if location is not None:
        context = StoragePathContext(
            selected_path=context.selected_path,
            location_label=location.label,
            location_root=location.path,
        )

    try:
        result = run_command(
            [
                "findmnt",
                "--json",
                "--bytes",
                "--target",
                str(resolved),
                "-o",
                "TARGET,SOURCE,FSTYPE,SIZE,AVAIL",
            ],
            check=False,
            logger=logger,
        )
    except OSError:
        result = None

    if result is not None and result.returncode == 0 and result.stdout.strip():
        import json

        try:
            payload = json.loads(result.stdout)
            filesystems = payload.get("filesystems") or []
            if filesystems:
                fs = filesystems[0]
                mount_source = fs.get("source")
                mount_target = fs.get("target")
                filesystem_type = fs.get("fstype")
                total_bytes = _parse_findmnt_value(fs.get("size"))
                free_bytes = _parse_findmnt_value(fs.get("avail"))

                backing_disk_path = None
                backing_disk_model = None
                backing_disk_size = None
                if isinstance(mount_source, str) and mount_source.startswith("/dev/"):
                    try:
                        parent_disk = get_parent_disk(Path(mount_source), logger=logger)
                        backing_disk_path = parent_disk.path
                        backing_disk_model = parent_disk.model
                        backing_disk_size = parent_disk.size_bytes
                    except ValueError:
                        backing_disk_path = Path(mount_source)

                context = StoragePathContext(
                    selected_path=context.selected_path,
                    location_label=context.location_label,
                    location_root=context.location_root,
                    mount_point=Path(mount_target) if mount_target else None,
                    mount_source=mount_source,
                    filesystem_type=filesystem_type,
                    total_bytes=total_bytes,
                    free_bytes=free_bytes,
                    backing_disk_path=backing_disk_path,
                    backing_disk_model=backing_disk_model,
                    backing_disk_size_bytes=backing_disk_size,
                )
            return context
        except (ValueError, TypeError, json.JSONDecodeError):
            return context

    if context.total_bytes is None or context.free_bytes is None:
        try:
            usage = shutil.disk_usage(resolved)
            usage_total = usage.total if hasattr(usage, "total") else usage[0]
            usage_free = usage.free if hasattr(usage, "free") else usage[2]
            context = StoragePathContext(
                selected_path=context.selected_path,
                location_label=context.location_label,
                location_root=context.location_root,
                mount_point=context.mount_point,
                mount_source=context.mount_source,
                filesystem_type=context.filesystem_type,
                total_bytes=context.total_bytes if context.total_bytes is not None else usage_total,
                free_bytes=context.free_bytes if context.free_bytes is not None else usage_free,
                backing_disk_path=context.backing_disk_path,
                backing_disk_model=context.backing_disk_model,
                backing_disk_size_bytes=context.backing_disk_size_bytes,
            )
        except OSError:
            pass

    return context
