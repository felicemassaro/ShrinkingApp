from __future__ import annotations

from pathlib import Path

from shrinkingapp.models import DiskLayout, PartitionInfo
from shrinkingapp.system.commands import run_command


def _split_machine_line(line: str) -> list[str]:
    line = line.strip()
    if line.endswith(";"):
        line = line[:-1]
    return line.split(":")


def _parse_int_bytes(raw_value: str) -> int:
    value = raw_value.strip().rstrip("B")
    return int(value)


def parse_parted_machine_output(image_path: Path, output: str) -> DiskLayout:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("Unexpected parted output: missing disk metadata")

    disk_fields = _split_machine_line(lines[1])
    if len(disk_fields) < 6:
        raise ValueError("Unexpected parted output: malformed disk metadata")

    logical_sector_size = int(disk_fields[3]) if disk_fields[3].isdigit() else None
    physical_sector_size = int(disk_fields[4]) if disk_fields[4].isdigit() else None
    partition_table = disk_fields[5]

    partitions: list[PartitionInfo] = []
    for line in lines[2:]:
        fields = _split_machine_line(line)
        if not fields or not fields[0].isdigit():
            continue

        flags = tuple(flag for flag in fields[6].split(",") if flag) if len(fields) > 6 else ()
        partitions.append(
            PartitionInfo(
                number=int(fields[0]),
                start_bytes=_parse_int_bytes(fields[1]),
                end_bytes=_parse_int_bytes(fields[2]),
                size_bytes=_parse_int_bytes(fields[3]),
                filesystem=fields[4] or None,
                name=fields[5] or None,
                flags=flags,
            )
        )

    if not partitions:
        raise ValueError(f"No partitions found in image: {image_path}")

    return DiskLayout(
        image_path=image_path,
        partition_table=partition_table,
        logical_sector_size=logical_sector_size,
        physical_sector_size=physical_sector_size,
        partitions=partitions,
    )


def inspect_image_layout(image_path: Path, *, logger=None) -> DiskLayout:
    result = run_command(["parted", "-ms", image_path, "unit", "B", "print"], logger=logger)
    return parse_parted_machine_output(image_path, result.stdout)


def select_shrink_partition(layout: DiskLayout) -> PartitionInfo:
    return max(layout.partitions, key=lambda part: (part.end_bytes, part.number))


def partition_kind(layout: DiskLayout, partition: PartitionInfo) -> str:
    if layout.partition_table.lower() in {"msdos", "dos"} and partition.number > 4:
        return "logical"
    return "primary"


def shrink_partition_entry(
    image_path: Path,
    *,
    partition_number: int,
    partition_kind_name: str,
    partition_start_bytes: int,
    new_partition_end_bytes: int,
    logger=None,
) -> None:
    run_command(
        ["parted", "-s", image_path, "rm", str(partition_number)],
        logger=logger,
    )
    run_command(
        [
            "parted",
            "-s",
            image_path,
            "unit",
            "B",
            "mkpart",
            partition_kind_name,
            str(partition_start_bytes),
            str(new_partition_end_bytes),
        ],
        logger=logger,
    )


def read_truncation_point_bytes(image_path: Path, *, logger=None) -> int:
    result = run_command(
        ["parted", "-ms", image_path, "unit", "B", "print", "free"],
        logger=logger,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) < 3:
        raise ValueError("Unexpected parted free-space output")

    last_line = _split_machine_line(lines[-1])
    if len(last_line) < 2:
        raise ValueError("Unable to determine truncation point")
    return _parse_int_bytes(last_line[1])

