from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class CompressionKind(str, Enum):
    GZIP = "gzip"
    XZ = "xz"


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

