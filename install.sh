#!/bin/bash
set -e

echo "=== Installing COOPIXEL ==="

# 1. Check if uv is installed
if ! command -v uv &> /dev/null && [ ! -f "$HOME/.local/bin/uv" ]; then
    echo "Installing uv (fast python package installer)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Ensure ~/.local/bin is in execution PATH for this session
export PATH="$HOME/.local/bin:$PATH"

# 2. Install coopixel itself as an editable tool inside ~/.sww/bin
echo "Installing coopixel tool..."
BIN_DIR="${UV_TOOL_BIN_DIR:-$HOME/.local/bin}"
TOOL_DIR="${UV_TOOL_DIR:-$HOME/.local/share/uv/tools}"

UV_TOOL_DIR="$TOOL_DIR" UV_TOOL_BIN_DIR="$BIN_DIR" uv tool install --editable . --force

# 3. Install icon and desktop file
echo "Installing desktop entry and icon..."
ICON_DIR="$HOME/.local/share/icons/hicolor/512x512/apps"
DESKTOP_DIR="$HOME/.local/share/applications"

mkdir -p "$ICON_DIR" "$DESKTOP_DIR"
if [ -f "src/coopixel/icon.png" ]; then
    cp src/coopixel/icon.png "$ICON_DIR/coopixel.png"
    cp src/coopixel/icon.png "$HOME/.local/share/icons/coopixel.png"
fi

EXEC_PATH="$BIN_DIR/coopixel"

cat << EOF > "$DESKTOP_DIR/coopixel.desktop"
[Desktop Entry]
Name=Coopixel
Comment=Dark-mode Pixel Art Editor
Exec=$EXEC_PATH %F
Icon=coopixel
Terminal=false
Type=Application
Categories=Graphics;2DGraphics;RasterGraphics;
MimeType=image/png;image/jpeg;image/bmp;x-scheme-handler/pix;
StartupWMClass=coopixel
EOF

chmod +x "$DESKTOP_DIR/coopixel.desktop"

echo "============================================="
echo "Installation complete!"
echo "Please restart your terminal or run:"
echo "  source ~/.bashrc"
echo "to start using the 'coopixel' command anywhere!"
echo "============================================="
