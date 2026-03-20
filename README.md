# ShrinkingApp

ShrinkingApp is a Linux desktop application for Raspberry Pi SD-card workflows.

The first milestone in this repository is a backend CLI for Ubuntu 24.04 that
shrinks an existing Pi image, writes a log, and emits a manifest next to the
final artifact.

## Current Scope

- Shrink an existing `.img`
- Optional `gzip` or `xz` compression
- Structured logging
- Manifest output
- Ubuntu 24.04 bootstrap scripts

Capture and restore flows are defined but not implemented in this milestone.

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

Shrink into a new file with compression:

```bash
shrinkingapp shrink /path/to/source.img \
  --output /path/to/output.img \
  --compression xz
```

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

