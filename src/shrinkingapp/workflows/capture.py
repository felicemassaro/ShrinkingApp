from __future__ import annotations

from datetime import datetime, timezone

from shrinkingapp.core.manifests import build_capture_manifest, write_manifest
from shrinkingapp.core.progress import log_phase
from shrinkingapp.core.validators import ensure_root, resolve_capture_source, validate_output_path
from shrinkingapp.logging_utils import derive_log_path, derive_manifest_path, setup_job_logger
from shrinkingapp.models import CaptureJobSpec, CaptureResult, CaptureSourceKind
from shrinkingapp.system.commands import detect_tool_versions, require_commands, run_command
from shrinkingapp.system.compression import compress_image
from shrinkingapp.system.devices import ensure_removable_disk, unmount_device_tree
from shrinkingapp.system.images import copy_image, file_size_bytes, normalize_output_image_path, sha256_file
from shrinkingapp.system.storage import describe_storage_path


BLOCK_DEVICE_REQUIRED_TOOLS = ["dd", "lsblk", "umount", "sync"]
IMAGE_FILE_REQUIRED_TOOLS = ["dd", "sync"]


def _required_tools_for(spec: CaptureJobSpec) -> list[str]:
    source_path, source_kind = resolve_capture_source(spec.source_path)
    tools = list(BLOCK_DEVICE_REQUIRED_TOOLS if source_kind is CaptureSourceKind.BLOCK_DEVICE else IMAGE_FILE_REQUIRED_TOOLS)
    if spec.compression is not None:
        if spec.compression.value == "gzip":
            tools.append("gzip")
        else:
            tools.append("xz")
    return tools


def run_capture_job(spec: CaptureJobSpec) -> CaptureResult:
    require_commands(_required_tools_for(spec))

    source_path, source_kind = resolve_capture_source(spec.source_path)
    if source_kind is CaptureSourceKind.BLOCK_DEVICE:
        ensure_root()
    output_image = validate_output_path(
        normalize_output_image_path(source_path, spec.output_image, spec.compression)
    )
    if source_kind is CaptureSourceKind.IMAGE_FILE and source_path == output_image:
        raise ValueError("Source image and output image must be different paths.")
    if output_image.exists():
        raise FileExistsError(f"Refusing to overwrite existing output image: {output_image}")

    log_path = derive_log_path(output_image, spec.log_path)
    logger = setup_job_logger("shrinkingapp.capture", log_path)

    bytes_captured: int
    if source_kind is CaptureSourceKind.BLOCK_DEVICE:
        device_info = ensure_removable_disk(source_path, logger=logger)
        bytes_captured = device_info.size_bytes
        logger.info("Starting capture job from device %s (%s bytes)", device_info.path, device_info.size_bytes)
    else:
        bytes_captured = file_size_bytes(source_path)
        logger.info("Starting capture job from image file %s (%s bytes)", source_path, bytes_captured)

    destination_context = describe_storage_path(output_image.parent, logger=logger)
    if destination_context.free_bytes is not None and bytes_captured > destination_context.free_bytes:
        raise ValueError(
            f"Destination path {output_image.parent} has only {destination_context.free_bytes} free bytes, "
            f"but the capture requires at least {bytes_captured} bytes."
        )
    started_at = datetime.now(timezone.utc)

    if source_kind is CaptureSourceKind.BLOCK_DEVICE:
        log_phase(logger, "prepare", "validating source device and output path")
        log_phase(logger, "unmount", f"unmounting {source_path}")
        unmount_device_tree(source_path, logger=logger)
        log_phase(logger, "capture", f"capturing {source_path} to {output_image}")
        run_command(
            [
                "dd",
                f"if={source_path}",
                f"of={output_image}",
                "bs=8M",
                "status=progress",
                "conv=fsync",
            ],
            logger=logger,
        )
    else:
        log_phase(logger, "prepare", "validating source image and output path")
        log_phase(logger, "copy", f"copying {source_path} to {output_image}")
        copy_image(source_path, output_image, logger=logger)
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
        source_path=source_path,
        source_kind=source_kind,
        output_image=final_artifact,
        manifest_path=manifest_path,
        log_path=log_path,
        bytes_captured=bytes_captured,
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
    logger.info("Capture job completed: %s -> %s", source_path, final_artifact)
    return result
