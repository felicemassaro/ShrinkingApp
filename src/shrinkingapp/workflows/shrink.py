from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from shrinkingapp.core.manifests import build_shrink_manifest, write_manifest
from shrinkingapp.core.validators import ensure_root, validate_output_path, validate_source_image
from shrinkingapp.logging_utils import derive_log_path, derive_manifest_path, setup_job_logger
from shrinkingapp.models import ShrinkJobSpec, ShrinkResult
from shrinkingapp.system.commands import detect_tool_versions, require_commands
from shrinkingapp.system.compression import compress_image
from shrinkingapp.system.filesystems import (
    check_filesystem,
    enable_first_boot_expand,
    minimum_size_blocks,
    read_ext_filesystem_info,
    shrink_ext_filesystem,
    write_zero_fill_file,
)
from shrinkingapp.system.images import (
    copy_image,
    file_size_bytes,
    normalize_output_image_path,
    sha256_file,
    truncate_image,
)
from shrinkingapp.system.loopdev import offset_loop_device
from shrinkingapp.system.partitions import (
    inspect_image_layout,
    partition_kind,
    read_truncation_point_bytes,
    select_shrink_partition,
    shrink_partition_entry,
)


BASE_REQUIRED_TOOLS = [
    "parted",
    "losetup",
    "tune2fs",
    "e2fsck",
    "resize2fs",
    "truncate",
    "mount",
    "umount",
    "cp",
]


def _required_tools_for(spec: ShrinkJobSpec) -> list[str]:
    tools = list(BASE_REQUIRED_TOOLS)
    if spec.compression is not None:
        if spec.compression.value == "gzip":
            tools.append("gzip")
        else:
            tools.append("xz")
    return tools


def _target_block_count(current_blocks: int, minimum_blocks: int) -> int:
    if current_blocks == minimum_blocks:
        return current_blocks

    extra_space = current_blocks - minimum_blocks
    target_blocks = minimum_blocks
    for candidate in (5000, 1000, 100):
        if extra_space > candidate:
            target_blocks += candidate
            break
    return target_blocks


def run_shrink_job(spec: ShrinkJobSpec) -> ShrinkResult:
    ensure_root()

    source_image = validate_source_image(spec.source_image)
    working_image = normalize_output_image_path(source_image, spec.output_image, spec.compression)
    if spec.output_image is not None:
        working_image = validate_output_path(working_image)

    log_path = derive_log_path(working_image, spec.log_path)
    logger = setup_job_logger("shrinkingapp.shrink", log_path)
    require_commands(_required_tools_for(spec))

    logger.info("Starting shrink job for %s", source_image)
    started_at = datetime.now(timezone.utc)

    if spec.output_image is not None:
        logger.info("Copying %s to %s", source_image, working_image)
        copy_image(source_image, working_image, logger=logger)
    else:
        working_image = source_image

    original_size = file_size_bytes(working_image)
    layout = inspect_image_layout(working_image, logger=logger)
    target_partition = select_shrink_partition(layout)
    kind = partition_kind(layout, target_partition)
    logger.info(
        "Selected partition %s (%s) starting at %s bytes",
        target_partition.number,
        kind,
        target_partition.start_bytes,
    )

    shrunk_partition = False
    new_image_size = original_size
    current_info = None

    with offset_loop_device(working_image, target_partition.start_bytes, logger=logger) as loop_device:
        logger.info("Attached loop device %s", loop_device)
        current_info = read_ext_filesystem_info(loop_device, logger=logger)
        check_filesystem(loop_device, repair=spec.repair, logger=logger)

        minimum_blocks = minimum_size_blocks(loop_device, logger=logger)
        target_blocks = _target_block_count(current_info.block_count, minimum_blocks)
        logger.info(
            "Filesystem blocks: current=%s minimum=%s target=%s",
            current_info.block_count,
            minimum_blocks,
            target_blocks,
        )

        if target_blocks < current_info.block_count:
            shrink_ext_filesystem(loop_device, target_blocks, logger=logger)
            write_zero_fill_file(loop_device, logger=logger)
            if spec.enable_first_boot_expand:
                if kind == "logical":
                    logger.warning("Skipping first boot expand patch for logical partition")
                else:
                    enable_first_boot_expand(loop_device, logger=logger)

            new_partition_end = target_partition.start_bytes + (target_blocks * current_info.block_size)
            logger.info("Shrinking partition table entry to end at %s bytes", new_partition_end)
            shrink_partition_entry(
                working_image,
                partition_number=target_partition.number,
                partition_kind_name=kind,
                partition_start_bytes=target_partition.start_bytes,
                new_partition_end_bytes=new_partition_end,
                logger=logger,
            )
            new_image_size = read_truncation_point_bytes(working_image, logger=logger)
            shrunk_partition = True
        else:
            logger.info("Filesystem already at minimum size; skipping shrink")
            if spec.enable_first_boot_expand:
                if kind == "logical":
                    logger.warning("Skipping first boot expand patch for logical partition")
                else:
                    enable_first_boot_expand(loop_device, logger=logger)

    if shrunk_partition:
        logger.info("Truncating %s to %s bytes", working_image, new_image_size)
        truncate_image(working_image, new_image_size, logger=logger)

    final_artifact = working_image
    if spec.compression is not None:
        logger.info("Compressing %s using %s", working_image, spec.compression.value)
        final_artifact = compress_image(
            working_image,
            spec.compression,
            parallel=spec.parallel_compression,
            logger=logger,
        )

    checksum = sha256_file(final_artifact)
    final_size = file_size_bytes(final_artifact)
    manifest_path = derive_manifest_path(final_artifact)
    finished_at = datetime.now(timezone.utc)

    result = ShrinkResult(
        source_image=source_image,
        output_image=final_artifact,
        manifest_path=manifest_path,
        log_path=log_path,
        original_size=original_size,
        final_size=final_size,
        checksum_sha256=checksum,
        started_at=started_at,
        finished_at=finished_at,
        compression=spec.compression,
    )

    manifest = build_shrink_manifest(
        spec,
        result,
        tool_versions=detect_tool_versions(
            ["parted", "losetup", "e2fsck", "resize2fs", "tune2fs"]
        ),
    )
    write_manifest(manifest_path, manifest)
    logger.info("Shrink job completed: %s -> %s", source_image, final_artifact)
    return result
