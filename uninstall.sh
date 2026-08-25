#!/bin/bash
set -e

echo "=== Uninstalling COOPIXEL ==="

export PATH="$HOME/.local/bin:$PATH"

BIN_DIR="${UV_TOOL_BIN_DIR:-$HOME/.local/bin}"
TOOL_DIR="${UV_TOOL_DIR:-$HOME/.local/share/uv/tools}"

# Uninstall coopixel tool
echo "Uninstalling COOPIXEL tool..."
if command -v uv &> /dev/null; then
    UV_TOOL_DIR="$TOOL_DIR" UV_TOOL_BIN_DIR="$BIN_DIR" uv tool uninstall coopixel || true
    echo "COOPIXEL uninstalled via uv."
elif command -v pip &> /dev/null; then
    pip uninstall -y coopixel || true
    echo "COOPIXEL uninstalled via pip."
else
    echo "Neither uv nor pip found — skipping tool uninstall."
fi

# Remove desktop entry and icon files
echo "Removing desktop entry and icons..."
rm -f "$HOME/.local/share/applications/coopixel.desktop"
rm -f "$HOME/.local/share/icons/hicolor/512x512/apps/coopixel.png"
rm -f "$HOME/.local/share/icons/coopixel.png"

echo "============================================="
echo "Uninstallation complete!"
echo "============================================="
