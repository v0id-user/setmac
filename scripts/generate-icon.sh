#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:-Resources/icon.png}"
OUTPUT="Resources/AppIcon.icns"
ICONSET_DIR="Resources/AppIcon.iconset"

if [ ! -f "$INPUT" ]; then
    echo "Error: $INPUT not found."
    echo "Usage: bash scripts/generate-icon.sh [path/to/1024x1024.png]"
    echo ""
    echo "Provide a 1024x1024 PNG and this script will generate all sizes."
    exit 1
fi

echo "==> Generating .icns from $INPUT..."
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

sizes=(16 32 64 128 256 512 1024)
for size in "${sizes[@]}"; do
    sips -z $size $size "$INPUT" --out "$ICONSET_DIR/icon_${size}x${size}.png" > /dev/null 2>&1
    half=$((size / 2))
    if [ $half -ge 16 ]; then
        cp "$ICONSET_DIR/icon_${size}x${size}.png" "$ICONSET_DIR/icon_${half}x${half}@2x.png"
    fi
done

iconutil -c icns "$ICONSET_DIR" -o "$OUTPUT"
rm -rf "$ICONSET_DIR"

echo "==> Icon generated at $OUTPUT"
