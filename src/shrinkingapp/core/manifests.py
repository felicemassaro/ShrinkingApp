from __future__ import annotations

import json
from pathlib import Path

from shrinkingapp.models import (
    CaptureJobSpec,
    CaptureResult,
    RestoreJobSpec,
    RestoreResult,
    ShrinkJobSpec,
    ShrinkResult,
)


def build_shrink_manifest(
    spec: ShrinkJobSpec,
    result: ShrinkResult,
    *,
    tool_versions: dict[str, str | None],
) -> dict[str, object]:
    return {
        "job_type": "shrink",
        "source_image": str(spec.source_image),
        "output_image": str(result.output_image),
        "original_size_bytes": result.original_size,
        "final_size_bytes": result.final_size,
        "compression": result.compression.value if result.compression else None,
        "checksum": {
            "algorithm": "sha256",
            "value": result.checksum_sha256,
        },
        "timestamps": {
            "started_at": result.started_at.isoformat(),
            "finished_at": result.finished_at.isoformat(),
        },
        "artifacts": {
            "manifest_path": str(result.manifest_path),
            "log_path": str(result.log_path),
        },
        "options": {
            "repair": spec.repair,
            "enable_first_boot_expand": spec.enable_first_boot_expand,
            "parallel_compression": spec.parallel_compression,
        },
        "tool_versions": tool_versions,
    }


def write_manifest(manifest_path: Path, manifest: dict[str, object]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def build_capture_manifest(
    spec: CaptureJobSpec,
    result: CaptureResult,
    *,
    tool_versions: dict[str, str | None],
) -> dict[str, object]:
    return {
        "job_type": "capture",
        "source_device": str(spec.source_device),
        "output_image": str(result.output_image),
        "bytes_captured": result.bytes_captured,
        "final_size_bytes": result.final_size,
        "compression": result.compression.value if result.compression else None,
        "checksum": {
            "algorithm": "sha256",
            "value": result.checksum_sha256,
        },
        "timestamps": {
            "started_at": result.started_at.isoformat(),
            "finished_at": result.finished_at.isoformat(),
        },
        "artifacts": {
            "manifest_path": str(result.manifest_path),
            "log_path": str(result.log_path),
        },
        "options": {
            "parallel_compression": spec.parallel_compression,
        },
        "tool_versions": tool_versions,
    }


def build_restore_manifest(
    spec: RestoreJobSpec,
    result: RestoreResult,
    *,
    tool_versions: dict[str, str | None],
) -> dict[str, object]:
    return {
        "job_type": "restore",
        "source_image": str(spec.source_image),
        "target_device": str(spec.target_device),
        "source_size_bytes": result.source_size,
        "target_size_bytes": result.target_size,
        "checksum": {
            "algorithm": "sha256",
            "value": result.checksum_sha256,
        },
        "timestamps": {
            "started_at": result.started_at.isoformat(),
            "finished_at": result.finished_at.isoformat(),
        },
        "artifacts": {
            "manifest_path": str(result.manifest_path),
            "log_path": str(result.log_path),
        },
        "tool_versions": tool_versions,
    }
