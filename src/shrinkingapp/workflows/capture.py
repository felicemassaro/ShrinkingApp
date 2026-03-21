from __future__ import annotations

from datetime import datetime, timezone

from shrinkingapp.core.manifests import build_capture_manifest, write_manifest
from shrinkingapp.core.progress import log_phase
from shrinkingapp.core.validators import ensure_root, validate_block_device, validate_output_path
from shrinkingapp.logging_utils import derive_log_path, derive_manifest_path, setup_job_logger
from shrinkingapp.models import CaptureJobSpec, CaptureResult
from shrinkingapp.system.commands import detect_tool_versions, require_commands, run_command
from shrinkingapp.system.compression import compress_image
from shrinkingapp.system.devices import ensure_removable_disk, unmount_device_tree
from shrinkingapp.system.images import file_size_bytes, normalize_output_image_path, sha256_file


BASE_REQUIRED_TOOLS = ["dd", "lsblk", "umount", "sync"]


def _required_tools_for(spec: CaptureJobSpec) -> list[str]:
    tools = list(BASE_REQUIRED_TOOLS)
    if spec.compression is not None:
        if spec.compression.value == "gzip":
            tools.append("gzip")
        else:
            tools.append("xz")
    return tools


def run_capture_job(spec: CaptureJobSpec) -> CaptureResult:
    ensure_root()
    require_commands(_required_tools_for(spec))

    source_device = validate_block_device(spec.source_device)
    output_image = validate_output_path(
        normalize_output_image_path(source_device, spec.output_image, spec.compression)
    )
    if output_image.exists():
        raise FileExistsError(f"Refusing to overwrite existing output image: {output_image}")

    log_path = derive_log_path(output_image, spec.log_path)
    logger = setup_job_logger("shrinkingapp.capture", log_path)

    device_info = ensure_removable_disk(source_device, logger=logger)
    logger.info("Starting capture job from %s (%s bytes)", device_info.path, device_info.size_bytes)
    started_at = datetime.now(timezone.utc)

    log_phase(logger, "prepare", "validating source device and output path")
    log_phase(logger, "unmount", f"unmounting {source_device}")
    unmount_device_tree(source_device, logger=logger)
    log_phase(logger, "capture", f"capturing {source_device} to {output_image}")
    run_command(
        [
            "dd",
            f"if={source_device}",
            f"of={output_image}",
            "bs=8M",
            "status=progress",
            "conv=fsync",
        ],
        logger=logger,
    )
    log_phase(logger, "sync", "flushing capture output to disk")
    run_command(["sync"], logger=logger)

    final_artifact = output_image
    if spec.compression is not None:
        log_phase(logger, "compress", f"compressing with {spec.compression.value}")
        logger.info("Compressing %s using %s", output_image, spec.compression.value)
        final_artifact = compress_image(
            output_image,
            spec.compression,
            parallel=spec.parallel_compression,
            logger=logger,
        )

    checksum = sha256_file(final_artifact)
    final_size = file_size_bytes(final_artifact)
    manifest_path = derive_manifest_path(final_artifact)
    finished_at = datetime.now(timezone.utc)

    result = CaptureResult(
        source_device=source_device,
        output_image=final_artifact,
        manifest_path=manifest_path,
        log_path=log_path,
        bytes_captured=device_info.size_bytes,
        final_size=final_size,
        checksum_sha256=checksum,
        started_at=started_at,
        finished_at=finished_at,
        compression=spec.compression,
    )

    log_phase(logger, "finalize", "writing manifest and checksum")
    manifest = build_capture_manifest(
        spec,
        result,
        tool_versions=detect_tool_versions(["dd", "lsblk"]),
    )
    write_manifest(manifest_path, manifest)
    log_phase(logger, "done", "capture completed successfully")
    logger.info("Capture job completed: %s -> %s", source_device, final_artifact)
    return result
