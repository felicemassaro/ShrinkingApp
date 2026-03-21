from __future__ import annotations

from datetime import datetime, timezone

from shrinkingapp.core.manifests import build_restore_manifest, write_manifest
from shrinkingapp.core.progress import log_phase
from shrinkingapp.core.validators import ensure_root, validate_block_device, validate_source_image
from shrinkingapp.logging_utils import derive_log_path, derive_manifest_path, setup_job_logger
from shrinkingapp.models import RestoreJobSpec, RestoreResult
from shrinkingapp.system.commands import detect_tool_versions, require_commands, run_command
from shrinkingapp.system.devices import ensure_removable_disk, unmount_device_tree
from shrinkingapp.system.images import file_size_bytes, sha256_file


BASE_REQUIRED_TOOLS = ["dd", "lsblk", "umount", "sync"]


def run_restore_job(spec: RestoreJobSpec) -> RestoreResult:
    ensure_root()
    require_commands(BASE_REQUIRED_TOOLS)

    source_image = validate_source_image(spec.source_image)
    if source_image.suffix in {".gz", ".xz"}:
        raise ValueError("Compressed-image restore is not implemented yet. Restore from a raw .img file.")

    target_device = validate_block_device(spec.target_device)
    log_path = derive_log_path(source_image.with_name(f"{source_image.name}.restore"), spec.log_path)
    logger = setup_job_logger("shrinkingapp.restore", log_path)

    device_info = ensure_removable_disk(target_device, logger=logger)
    source_size = file_size_bytes(source_image)
    if source_size > device_info.size_bytes:
        raise ValueError(
            f"Source image ({source_size} bytes) does not fit on target device "
            f"{target_device} ({device_info.size_bytes} bytes)"
        )

    logger.info("Starting restore job from %s to %s", source_image, target_device)
    started_at = datetime.now(timezone.utc)

    log_phase(logger, "prepare", "validating source image and target device")
    log_phase(logger, "unmount", f"unmounting {target_device}")
    unmount_device_tree(target_device, logger=logger)
    log_phase(logger, "restore", f"writing {source_image} to {target_device}")
    run_command(
        [
            "dd",
            f"if={source_image}",
            f"of={target_device}",
            "bs=8M",
            "status=progress",
            "conv=fsync",
        ],
        logger=logger,
    )
    log_phase(logger, "sync", "flushing restored image to disk")
    run_command(["sync"], logger=logger)

    checksum = sha256_file(source_image)
    manifest_path = derive_manifest_path(source_image.with_name(f"{source_image.name}.restore"))
    finished_at = datetime.now(timezone.utc)

    result = RestoreResult(
        source_image=source_image,
        target_device=target_device,
        manifest_path=manifest_path,
        log_path=log_path,
        source_size=source_size,
        target_size=device_info.size_bytes,
        checksum_sha256=checksum,
        started_at=started_at,
        finished_at=finished_at,
    )

    log_phase(logger, "finalize", "writing manifest")
    manifest = build_restore_manifest(
        spec,
        result,
        tool_versions=detect_tool_versions(["dd", "lsblk"]),
    )
    write_manifest(manifest_path, manifest)
    log_phase(logger, "done", "restore completed successfully")
    logger.info("Restore job completed: %s -> %s", source_image, target_device)
    return result
