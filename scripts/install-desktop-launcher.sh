#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_TEMPLATE="$ROOT_DIR/packaging/shrinkingapp.desktop.in"
ICON_SOURCE="$ROOT_DIR/packaging/shrinkingapp.svg"
LAUNCHER_EXEC="$ROOT_DIR/.venv/bin/shrinkingapp-ui"

APPLICATIONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
DESKTOP_FILE="$APPLICATIONS_DIR/shrinkingapp.desktop"
ICON_FILE="$ICON_DIR/shrinkingapp.svg"

mkdir -p "$APPLICATIONS_DIR" "$ICON_DIR"

if [[ ! -x "$LAUNCHER_EXEC" ]]; then
  echo "Missing launcher executable: $LAUNCHER_EXEC" >&2
  echo "Create the virtual environment and run 'pip install -e .' first." >&2
  exit 1
fi

install -m 0644 "$ICON_SOURCE" "$ICON_FILE"

sed \
  -e "s|__EXEC__|$LAUNCHER_EXEC|g" \
  -e "s|__ICON__|$ICON_FILE|g" \
  "$DESKTOP_TEMPLATE" > "$DESKTOP_FILE"

chmod 0644 "$DESKTOP_FILE"

echo "Desktop launcher installed:"
echo "  $DESKTOP_FILE"
echo
echo "If you also want a clickable desktop icon, copy it to ~/Desktop:"
echo "  cp \"$DESKTOP_FILE\" \"$HOME/Desktop/\""
echo "  chmod +x \"$HOME/Desktop/shrinkingapp.desktop\""
