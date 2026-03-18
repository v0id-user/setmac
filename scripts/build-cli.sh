#!/usr/bin/env bash
set -euo pipefail

CLI_DIR="cli"
DIST_DIR="cli/dist"

echo "==> Building CLI binary..."

if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

cd "$CLI_DIR"

# Install with dev deps (includes pyinstaller)
uv sync --group build

# Build standalone binary
uv run pyinstaller \
    --onefile \
    --name setmac \
    --clean \
    --noconfirm \
    --strip \
    --distpath dist \
    --add-data "../Resources/tools.json:." \
    src/setmac/__main__.py

echo "==> CLI binary built at $DIST_DIR/setmac"
echo "    Test with: $DIST_DIR/setmac --help"
