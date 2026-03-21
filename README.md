# ShrinkingApp

ShrinkingApp is a Linux desktop application for Raspberry Pi SD-card workflows.

The current milestone in this repository is a backend CLI for Ubuntu 24.04 that
captures a raw Pi image, shrinks an existing image, restores a raw image to an
SD card, writes logs, emits manifests next to the final artifacts, and exposes
an initial PySide6 desktop shell on top of those workflows.

## Current Scope

- Capture a raw `.img` from a removable block device
- Shrink an existing `.img`
- Restore a raw `.img` to a removable block device
- PySide6 desktop UI with live job monitor and destination confirmations
- Optional `gzip` or `xz` compression
- Structured logging
- Manifest output
- Ubuntu 24.04 bootstrap scripts

Compressed-image restore is not implemented yet; restore currently expects a raw
`.img` file.

## Ubuntu 24.04 Bootstrap

Run the bootstrap script on the Ubuntu VM:

```bash
bash scripts/bootstrap-ubuntu.sh
```

Or install manually:

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  python3 python3-venv \
  policykit-1 \
  parted e2fsprogs util-linux fdisk \
  gzip xz-utils \
  rsync \
  dosfstools psmisc
```

## Development Workflow

Sync the Mac project into a native Linux directory, then work from Linux:

```bash
rsync -av --delete /media/psf/<SharedFolder>/ShrinkingApp/ ~/dev/shrinkingapp/
cd ~/dev/shrinkingapp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e .
```

Run the CLI:

```bash
shrinkingapp shrink /path/to/source.img
```

Capture from a removable source device:

```bash
sudo shrinkingapp capture /dev/sdb /path/to/pi-source.img
```

Shrink into a new file with compression:

```bash
shrinkingapp shrink /path/to/source.img \
  --output /path/to/output.img \
  --compression xz
```

Restore a raw image to a removable target device:

```bash
sudo shrinkingapp restore /path/to/output.img /dev/sde
```

Run the desktop UI:

```bash
shrinkingapp-ui
```

The UI launches backend jobs through the same CLI. Capture, shrink, and restore
operations will request elevated privileges through the desktop policy prompt
when needed.

## Safety Notes

- The shrink workflow must run as root because it uses `losetup`, `mount`,
  `e2fsck`, and `resize2fs`.
- This milestone is intended to run on Ubuntu 24.04, not on macOS.
- Test the generated image on a Raspberry Pi before trusting it operationally.

## Tests

The unit tests cover parsing and path logic only:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/unit -p 'test_*.py'
```
