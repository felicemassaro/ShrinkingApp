from __future__ import annotations

import errno
import os
import shutil
import tempfile
import textwrap
from contextlib import contextmanager
from pathlib import Path

from shrinkingapp.models import ExtFilesystemInfo
from shrinkingapp.system.commands import CommandError, run_command


AUTOEXPAND_MARKER = "## PiShrink https://github.com/Drewsif/PiShrink ##"
AUTOEXPAND_RC_LOCAL = textwrap.dedent(
    """\
    #!/bin/bash
    ## PiShrink https://github.com/Drewsif/PiShrink ##
    do_expand_rootfs() {
      ROOT_PART=$(mount | sed -n 's|^/dev/\\(.*\\) on / .*|\\1|p')

      PART_NUM=${ROOT_PART#mmcblk0p}
      if [ "$PART_NUM" = "$ROOT_PART" ]; then
        echo "$ROOT_PART is not an SD card. Don't know how to expand"
        return 0
      fi

      PART_START=$(parted /dev/mmcblk0 -ms unit s p | grep "^${PART_NUM}" | cut -f 2 -d: | sed 's/[^0-9]//g')
      [ "$PART_START" ] || return 1
      fdisk /dev/mmcblk0 <<EOF
    p
    d
    $PART_NUM
    n
    p
    $PART_NUM
    $PART_START

    p
    w
    EOF

    cat <<EOF > /etc/rc.local &&
    #!/bin/sh
    echo "Expanding /dev/$ROOT_PART"
    resize2fs /dev/$ROOT_PART
    rm -f /etc/rc.local; cp -fp /etc/rc.local.bak /etc/rc.local && /etc/rc.local

    EOF
    reboot
    exit
    }
    raspi_config_expand() {
    /usr/bin/env raspi-config --expand-rootfs
    if [[ $? != 0 ]]; then
      return -1
    else
      rm -f /etc/rc.local; cp -fp /etc/rc.local.bak /etc/rc.local && /etc/rc.local
      reboot
      exit
    fi
    }
    raspi_config_expand
    echo "WARNING: Using backup expand..."
    sleep 5
    do_expand_rootfs
    echo "ERROR: Expanding failed..."
    sleep 5
    if [[ -f /etc/rc.local.bak ]]; then
      cp -fp /etc/rc.local.bak /etc/rc.local
      /etc/rc.local
    fi
    exit 0
    """
)


def read_ext_filesystem_info(device: str, *, logger=None) -> ExtFilesystemInfo:
    result = run_command(["tune2fs", "-l", device], logger=logger)
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        values[key.strip()] = raw_value.strip()

    try:
        block_count = int(values["Block count"])
        block_size = int(values["Block size"])
    except KeyError as exc:
        raise RuntimeError(f"Unable to parse ext filesystem details for {device}") from exc

    return ExtFilesystemInfo(
        block_count=block_count,
        block_size=block_size,
        filesystem_state=values.get("Filesystem state"),
    )


def check_filesystem(device: str, *, repair: bool, logger=None) -> None:
    first_pass = run_command(["e2fsck", "-pf", device], check=False, logger=logger)
    if first_pass.returncode < 4:
        return

    logger.info("Filesystem error detected; attempting recovery")
    second_pass = run_command(["e2fsck", "-y", device], check=False, logger=logger)
    if second_pass.returncode < 4:
        return

    if repair:
        logger.info("Normal recovery failed; trying advanced repair mode")
        third_pass = run_command(
            ["e2fsck", "-fy", "-b", "32768", device],
            check=False,
            logger=logger,
        )
        if third_pass.returncode < 4:
            return

    raise RuntimeError("Filesystem recovery failed.")


def minimum_size_blocks(device: str, *, logger=None) -> int:
    result = run_command(["resize2fs", "-P", device], logger=logger)
    _, value = result.stdout.rsplit(":", 1)
    return int(value.strip())


def shrink_ext_filesystem(device: str, blocks: int, *, logger=None) -> None:
    run_command(["resize2fs", "-p", device, str(blocks)], logger=logger)


@contextmanager
def mounted_device(device: str, *, logger=None):
    mount_dir = Path(tempfile.mkdtemp(prefix="shrinkingapp-mount-"))
    try:
        run_command(["mount", "-o", "rw", device, mount_dir], logger=logger)
        yield mount_dir
    finally:
        run_command(["umount", mount_dir], check=False, logger=logger)
        shutil.rmtree(mount_dir, ignore_errors=True)


def write_zero_fill_file(device: str, *, logger=None) -> None:
    try:
        with mounted_device(device, logger=logger) as mount_dir:
            zero_file = mount_dir / "ShrinkingApp_zero_fill"
            written = 0
            try:
                with zero_file.open("wb") as handle:
                    chunk = b"\0" * (1024 * 1024)
                    while True:
                        handle.write(chunk)
                        written += len(chunk)
            except OSError as exc:
                if exc.errno != errno.ENOSPC:
                    raise
            finally:
                if zero_file.exists():
                    zero_file.unlink()
            if logger is not None:
                logger.info("Zero-filled %s bytes of free space", written)
    except CommandError as exc:
        if logger is not None:
            logger.warning("Skipping free-space zero fill: %s", exc)


def enable_first_boot_expand(device: str, *, logger=None) -> None:
    with mounted_device(device, logger=logger) as mount_dir:
        etc_dir = mount_dir / "etc"
        if not etc_dir.is_dir():
            raise RuntimeError("Unable to enable first boot expand: /etc not found in image.")

        rc_local = etc_dir / "rc.local"
        backup = etc_dir / "rc.local.bak"
        if rc_local.exists():
            content = rc_local.read_text(encoding="utf-8", errors="ignore")
            if AUTOEXPAND_MARKER in content:
                if logger is not None:
                    logger.info("First boot expand marker already present; skipping patch")
                return
            shutil.copy2(rc_local, backup)

        rc_local.write_text(AUTOEXPAND_RC_LOCAL, encoding="utf-8")
        os.chmod(rc_local, 0o755)
        if logger is not None:
            logger.info("Patched %s for first boot expansion", rc_local)

