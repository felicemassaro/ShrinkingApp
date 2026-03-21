# ShrinkingApp

ShrinkingApp is a Linux desktop application for Raspberry Pi SD-card workflows.

This repository is currently an alpha-stage Ubuntu 24.04 project. It can
capture a raw Pi image, shrink an existing image, restore a raw image to an SD
card, write logs and manifests next to the final artifacts, and run those
workflows through a PySide6 desktop UI.

## Status

- Stage: alpha
- Supported desktop platform: Ubuntu 24.04
- Primary use case: Raspberry Pi SD-card imaging workflows
- Warning: test generated media on real hardware before trusting it for
  production use

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
  python3 python3-venv python3-pip \
  policykit-1 \
  parted e2fsprogs util-linux fdisk \
  gzip xz-utils \
  rsync \
  dosfstools psmisc
```

Then create the virtual environment and install the app:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e .
```

## Required Packages

The app depends on both Ubuntu system packages and Python packages.

### Ubuntu System Packages

These are required for the workflows implemented today:

```bash
sudo apt install -y \
  build-essential \
  python3 python3-venv python3-pip \
  policykit-1 \
  parted \
  e2fsprogs \
  util-linux \
  fdisk \
  gzip \
  xz-utils \
  rsync \
  dosfstools \
  psmisc
```

What they are used for:

- `policykit-1`: desktop privilege prompts via `pkexec`
- `parted`: partition inspection and partition-table rewrite during shrink
- `e2fsprogs`: `e2fsck`, `resize2fs`, `tune2fs`
- `util-linux`: `lsblk`, `losetup`, `mount`, `umount`, `findmnt`
- `fdisk`: partition/device support utilities on Ubuntu
- `gzip`, `xz-utils`: optional output compression
- `rsync`: project sync/bootstrap workflow
- `dosfstools`, `psmisc`: useful Linux media helpers for Ubuntu image workflows

### Python Packages

Installed through `pip install -e .`:

- `PySide6`: desktop UI

### Optional Tools

Not required, but useful:

```bash
sudo apt install -y pigz
```

- `pigz`: faster parallel gzip compression when that mode is enabled later

## Development Workflow

Clone the repository into a native Linux directory, then work from Linux:

```bash
git clone <repo-url> ~/dev/shrinkingapp
cd ~/dev/shrinkingapp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e .
```

If you are developing from a macOS host into an Ubuntu VM, you can still use a
shared-folder sync workflow as an alternative:

```bash
rsync -av --delete /media/psf/<SharedFolder>/ShrinkingApp/ ~/dev/shrinkingapp/
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

Quitting the app does not need a dedicated on-screen button. Linux users already
expect the window close control and `Ctrl+Q`, so the UI provides a standard
`File -> Quit` action instead.

## Linux Launcher

The repository now includes a desktop-launcher installer:

```bash
bash scripts/install-desktop-launcher.sh
```

That installs:

- a desktop entry in `~/.local/share/applications/shrinkingapp.desktop`
- an app icon in `~/.local/share/icons/hicolor/scalable/apps/shrinkingapp.svg`

The launcher points to the repo-local virtualenv executable:

- `./.venv/bin/shrinkingapp-ui`

So it assumes you already ran:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

If you also want a clickable icon on the Linux desktop, the installer prints
the copy commands for `~/Desktop/`.

The UI launches backend jobs through the same CLI. Capture, shrink, and restore
operations will request elevated privileges through the desktop policy prompt
when needed.

## Safety Notes

- The shrink workflow must run as root because it uses `losetup`, `mount`,
  `e2fsck`, and `resize2fs`.
- Capture and restore also need elevated privileges when they access raw block
  devices directly.
- This milestone is intended to run on Ubuntu 24.04, not on macOS.
- Parallels shared folders under `/media/psf/...` are supported as image
  storage locations, but they can report filesystem metadata differently from
  native Linux mounts.
- Test the generated image on a Raspberry Pi before trusting it operationally.
- This software is provided as-is. Review the code and test carefully before
  using it on important media.

## Tests

The unit tests cover parsing and path logic only:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/unit -p 'test_*.py'
```
