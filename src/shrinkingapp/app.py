from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from shrinkingapp.models import CaptureJobSpec, CompressionKind, RestoreJobSpec, ShrinkJobSpec
from shrinkingapp.workflows.capture import run_capture_job
from shrinkingapp.workflows.restore import run_restore_job
from shrinkingapp.workflows.shrink import run_shrink_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shrinkingapp",
        description="Backend CLI for Raspberry Pi image shrink workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser(
        "capture",
        help="Create a working image from a removable block device or an existing image file.",
    )
    capture_parser.add_argument(
        "source",
        type=Path,
        help="Source block device or source image file.",
    )
    capture_parser.add_argument("output", type=Path, help="Output image path.")
    capture_parser.add_argument(
        "--compression",
        choices=[kind.value for kind in CompressionKind],
        help="Compress the final artifact after capture.",
    )
    capture_parser.add_argument(
        "--parallel-compression",
        action="store_true",
        help="Use multi-core compression where supported.",
    )
    capture_parser.add_argument(
        "--log-file",
        type=Path,
        help="Optional explicit log file path.",
    )

    shrink_parser = subparsers.add_parser(
        "shrink",
        help="Shrink an existing Raspberry Pi image.",
    )
    shrink_parser.add_argument("image", type=Path, help="Source .img file.")
    shrink_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write to a new image path instead of shrinking in place.",
    )
    shrink_parser.add_argument(
        "--compression",
        choices=[kind.value for kind in CompressionKind],
        help="Compress the final artifact after shrinking.",
    )
    shrink_parser.add_argument(
        "--parallel-compression",
        action="store_true",
        help="Use multi-core compression where supported.",
    )
    shrink_parser.add_argument(
        "--repair",
        action="store_true",
        help="Use the advanced filesystem repair pass if the normal one fails.",
    )
    shrink_parser.add_argument(
        "--enable-first-boot-expand",
        action="store_true",
        help="Patch /etc/rc.local so the Pi expands the root filesystem on first boot.",
    )
    shrink_parser.add_argument(
        "--log-file",
        type=Path,
        help="Optional explicit log file path.",
    )

    restore_parser = subparsers.add_parser(
        "restore",
        help="Restore a raw image to a removable block device.",
    )
    restore_parser.add_argument("image", type=Path, help="Source raw .img file.")
    restore_parser.add_argument("device", type=Path, help="Target block device, for example /dev/sde.")
    restore_parser.add_argument(
        "--log-file",
        type=Path,
        help="Optional explicit log file path.",
    )

    return parser


def _build_capture_spec(args: argparse.Namespace) -> CaptureJobSpec:
    compression = CompressionKind(args.compression) if args.compression else None
    return CaptureJobSpec(
        source_path=args.source,
        output_image=args.output,
        compression=compression,
        parallel_compression=args.parallel_compression,
        log_path=args.log_file,
    )


def _build_shrink_spec(args: argparse.Namespace) -> ShrinkJobSpec:
    compression = CompressionKind(args.compression) if args.compression else None
    return ShrinkJobSpec(
        source_image=args.image,
        output_image=args.output,
        compression=compression,
        parallel_compression=args.parallel_compression,
        repair=args.repair,
        enable_first_boot_expand=args.enable_first_boot_expand,
        log_path=args.log_file,
    )


def _build_restore_spec(args: argparse.Namespace) -> RestoreJobSpec:
    return RestoreJobSpec(
        source_image=args.image,
        target_device=args.device,
        log_path=args.log_file,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "capture":
        result = run_capture_job(_build_capture_spec(args))
        summary = {
            "status": "ok",
            "source_path": str(result.source_path),
            "source_kind": result.source_kind.value,
            "output_image": str(result.output_image),
            "manifest_path": str(result.manifest_path),
            "log_path": str(result.log_path),
            "bytes_captured": result.bytes_captured,
            "final_size": result.final_size,
            "checksum_sha256": result.checksum_sha256,
        }
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "shrink":
        result = run_shrink_job(_build_shrink_spec(args))
        summary = {
            "status": "ok",
            "output_image": str(result.output_image),
            "manifest_path": str(result.manifest_path),
            "log_path": str(result.log_path),
            "original_size": result.original_size,
            "final_size": result.final_size,
            "checksum_sha256": result.checksum_sha256,
        }
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "restore":
        result = run_restore_job(_build_restore_spec(args))
        summary = {
            "status": "ok",
            "target_device": str(result.target_device),
            "manifest_path": str(result.manifest_path),
            "log_path": str(result.log_path),
            "source_size": result.source_size,
            "target_size": result.target_size,
            "checksum_sha256": result.checksum_sha256,
        }
        print(json.dumps(summary, indent=2))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
