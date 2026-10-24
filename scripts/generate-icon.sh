#!/usr/bin/env bash
# Turns a 1024x1024 PNG into AppIcon.icns with the standard macOS iconset:
# 16, 32, 128, 256 and 512 points at 1x and 2x (512@2x is the 1024 source).
# Usage: bash scripts/generate-icon.sh [input.png] [output.icns]
set -euo pipefail

INPUT="${1:-Resources/icon.png}"
OUTPUT="${2:-.build/icon/AppIcon.icns}"

if [ ! -f "$INPUT" ]; then
    echo "Error: $INPUT not found." >&2
    echo "Usage: bash scripts/generate-icon.sh [path/to/1024x1024.png] [output.icns]" >&2
    exit 1
fi

width=$(sips -g pixelWidth "$INPUT" | awk '/pixelWidth/ {print $2}')
height=$(sips -g pixelHeight "$INPUT" | awk '/pixelHeight/ {print $2}')
if [ "$width" != "1024" ] || [ "$height" != "1024" ]; then
    echo "Error: $INPUT is ${width}x${height}, expected 1024x1024." >&2
    exit 1
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
iconset="$work/AppIcon.iconset"
mkdir -p "$iconset"

echo "==> Generating $OUTPUT from $INPUT..."
for size in 16 32 128 256 512; do
    double=$((size * 2))
    sips -z "$size" "$size" "$INPUT" --out "$iconset/icon_${size}x${size}.png" > /dev/null
    if [ "$double" -eq 1024 ]; then
        cp "$INPUT" "$iconset/icon_${size}x${size}@2x.png"
    else
        sips -z "$double" "$double" "$INPUT" --out "$iconset/icon_${size}x${size}@2x.png" > /dev/null
    fi
done

mkdir -p "$(dirname "$OUTPUT")"
iconutil -c icns "$iconset" -o "$OUTPUT"
if [ ! -s "$OUTPUT" ]; then
    echo "Error: iconutil did not write $OUTPUT." >&2
    exit 1
fi

echo "==> Icon generated at $OUTPUT"
