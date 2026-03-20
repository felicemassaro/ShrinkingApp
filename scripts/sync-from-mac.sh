#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <mac-shared-source-dir> <linux-target-dir>" >&2
  exit 1
fi

SOURCE_DIR="$1"
TARGET_DIR="$2"

mkdir -p "$TARGET_DIR"
rsync -av --delete "$SOURCE_DIR"/ "$TARGET_DIR"/

