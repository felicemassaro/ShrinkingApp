from __future__ import annotations

import json
from pathlib import Path

from shrinkingapp.models import BlockDeviceInfo
from shrinkingapp.system.commands import run_command


def _normalize_mountpoints(raw_mountpoints: object) -> tuple[str, ...]:
    if raw_mountpoints is None:
        return ()
    if isinstance(raw_mountpoints, list):
        return tuple(str(item) for item in raw_mountpoints if item)
    if isinstance(raw_mountpoints, str):
        return (raw_mountpoints,) if raw_mountpoints else ()
    return ()


def _build_block_device(raw_device: dict[str, object]) -> BlockDeviceInfo:
    children = tuple(_build_block_device(child) for child in raw_device.get("children", []))
    path = Path(str(raw_device.get("path") or f"/dev/{raw_device['name']}"))
    return BlockDeviceInfo(
        name=str(raw_device["name"]),
        path=path,
        size_bytes=int(raw_device.get("size") or 0),
        model=(str(raw_device["model"]).strip() or None) if raw_device.get("model") else None,
        transport=(str(raw_device["tran"]).strip() or None) if raw_device.get("tran") else None,
        removable=bool(int(raw_device.get("rm") or 0)),
        readonly=bool(int(raw_device.get("ro") or 0)),
        device_type=str(raw_device.get("type") or ""),
        filesystem=(str(raw_device["fstype"]).strip() or None) if raw_device.get("fstype") else None,
        mountpoints=_normalize_mountpoints(raw_device.get("mountpoints")),
        children=children,
    )


def parse_lsblk_json(payload: str) -> list[BlockDeviceInfo]:
    data = json.loads(payload)
    blockdevices = data.get("blockdevices")
    if not isinstance(blockdevices, list):
        raise ValueError("Unexpected lsblk JSON payload")
    return [_build_block_device(device) for device in blockdevices]


def list_block_devices(*, logger=None) -> list[BlockDeviceInfo]:
    result = run_command(
        [
            "lsblk",
            "--json",
            "-b",
            "-o",
            "NAME,PATH,SIZE,MODEL,TRAN,RM,RO,TYPE,FSTYPE,MOUNTPOINTS",
        ],
        logger=logger,
    )
    return parse_lsblk_json(result.stdout)


def iter_block_devices(devices: list[BlockDeviceInfo]):
    for device in devices:
        yield device
        if device.children:
            yield from iter_block_devices(list(device.children))


def get_block_device(device_path: Path, *, logger=None) -> BlockDeviceInfo:
    resolved = device_path.expanduser().resolve()
    for device in iter_block_devices(list_block_devices(logger=logger)):
        if device.path == resolved:
            return device
    raise ValueError(f"Block device not found in lsblk output: {resolved}")


def ensure_removable_disk(device_path: Path, *, logger=None) -> BlockDeviceInfo:
    device = get_block_device(device_path, logger=logger)
    if device.device_type != "disk":
        raise ValueError(f"Expected a disk device, got {device.device_type}: {device.path}")
    if not device.removable:
        raise ValueError(f"Refusing to operate on a non-removable device: {device.path}")
    if device.readonly:
        raise ValueError(f"Refusing to operate on a read-only device: {device.path}")
    return device


def unmount_device_tree(device_path: Path, *, logger=None) -> None:
    device = get_block_device(device_path, logger=logger)
    descendants = list(iter_block_devices(list(device.children)))
    for child in descendants:
        for mountpoint in child.mountpoints:
            run_command(["umount", mountpoint], check=False, logger=logger)
        run_command(["umount", child.path], check=False, logger=logger)

