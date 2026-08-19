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

echo "============================================="
echo "Installation complete!"
echo "Please restart your terminal or run:"
echo "  source ~/.bashrc"
echo "to start using the 'coopixel' command anywhere!"
echo "============================================="
