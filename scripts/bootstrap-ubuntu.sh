#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo apt update
sudo apt install -y \
  build-essential \
  python3 python3-venv python3-pip \
  policykit-1 \
  parted e2fsprogs util-linux fdisk \
  gzip xz-utils \
  rsync \
  dosfstools psmisc

cd "$ROOT_DIR"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e .

echo
echo "Bootstrap complete."
echo "Activate the environment with:"
echo "  source \"$ROOT_DIR/.venv/bin/activate\""
