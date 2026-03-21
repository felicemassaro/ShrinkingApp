from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class CompressionKind(str, Enum):
    GZIP = "gzip"
    XZ = "xz"


class CaptureSourceKind(str, Enum):
    BLOCK_DEVICE = "block_device"
    IMAGE_FILE = "image_file"


class EndpointKind(str, Enum):
    BLOCK_DEVICE = "block_device"
    FILESYSTEM = "filesystem"


class EndpointCapability(str, Enum):
    READABLE = "readable"
    WRITABLE = "writable"
    BROWSABLE = "browsable"
    REMOVABLE = "removable"
    EXTERNAL = "external"


@dataclass(slots=True)
class BlockDeviceInfo:
    name: str
    path: Path
    size_bytes: int
    model: str | None
    transport: str | None
    removable: bool
    readonly: bool
    device_type: str
    filesystem: str | None = None
    mountpoints: tuple[str, ...] = field(default_factory=tuple)
    children: tuple["BlockDeviceInfo", ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class StorageEndpoint:
    label: str
    path: Path
    kind: EndpointKind
    capabilities: frozenset[EndpointCapability] = field(default_factory=frozenset)
    size_bytes: int | None = None
    model: str | None = None
    transport: str | None = None
    device_type: str | None = None

    def supports(self, *required: EndpointCapability) -> bool:
        return all(capability in self.capabilities for capability in required)


@dataclass(slots=True)
class ShrinkJobSpec:
    source_image: Path
    output_image: Path | None = None
    compression: CompressionKind | None = None
    parallel_compression: bool = False
    repair: bool = False
    enable_first_boot_expand: bool = False
    log_path: Path | None = None


@dataclass(slots=True)
class PartitionInfo:
    number: int
    start_bytes: int
    end_bytes: int
    size_bytes: int
    filesystem: str | None = None
    name: str | None = None
    flags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class DiskLayout:
    image_path: Path
    partition_table: str
    logical_sector_size: int | None
    physical_sector_size: int | None
    partitions: list[PartitionInfo]


@dataclass(slots=True)
class ExtFilesystemInfo:
    block_count: int
    block_size: int
    filesystem_state: str | None = None


@dataclass(slots=True)
class ShrinkResult:
    source_image: Path
    output_image: Path
    manifest_path: Path
    log_path: Path
    original_size: int
    final_size: int
    checksum_sha256: str
    started_at: datetime
    finished_at: datetime
    compression: CompressionKind | None = None


@dataclass(slots=True)
class CaptureJobSpec:
    source_path: Path
    output_image: Path
    compression: CompressionKind | None = None
    parallel_compression: bool = False
    log_path: Path | None = None


@dataclass(slots=True)
class CaptureResult:
    source_path: Path
    source_kind: CaptureSourceKind
    output_image: Path
    manifest_path: Path
    log_path: Path
    bytes_captured: int
    final_size: int
    checksum_sha256: str
    started_at: datetime
    finished_at: datetime
    compression: CompressionKind | None = None


@dataclass(slots=True)
class RestoreJobSpec:
    source_image: Path
    target_device: Path
    log_path: Path | None = None


@dataclass(slots=True)
class RestoreResult:
    source_image: Path
    target_device: Path
    manifest_path: Path
    log_path: Path
    source_size: int
    target_size: int
    checksum_sha256: str
    started_at: datetime
    finished_at: datetime
