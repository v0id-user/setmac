#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Setmac"
BUNDLE_ID="com.v0id.setmac"
VERSION="${VERSION:-1.0.0}"
BUILD_DIR=".build/release"
DIST_DIR="dist"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"

echo "==> Creating app bundle..."
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Copy main binary
cp "$BUILD_DIR/$APP_NAME" "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

# Copy CLI binary if it exists
if [ -f "cli/dist/setmac-cli" ]; then
    cp "cli/dist/setmac-cli" "$APP_BUNDLE/Contents/MacOS/setmac-cli"
    echo "    Embedded CLI binary"
fi

# Copy app icon if it exists
if [ -f "Resources/AppIcon.icns" ]; then
    cp "Resources/AppIcon.icns" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
fi

# Copy tools.json manifest
if [ -f "Resources/tools.json" ]; then
    cp "Resources/tools.json" "$APP_BUNDLE/Contents/Resources/tools.json"
    echo "    Embedded tools.json"
fi

# Copy SwiftPM resource bundles so packaged apps can resolve Bundle.module resources.
for resource_bundle in "$BUILD_DIR"/*.bundle; do
    if [ -d "$resource_bundle" ]; then
        cp -R "$resource_bundle" "$APP_BUNDLE/Contents/Resources/"
        echo "    Embedded $(basename "$resource_bundle")"
    fi
done

# Copy bundled configs if they exist
if [ -d "Resources/configs" ]; then
    cp -R "Resources/configs" "$APP_BUNDLE/Contents/Resources/configs"
    echo "    Embedded configs"
fi

# Info.plist comes from Resources/Info.plist with the release version stamped in.
cp "Resources/Info.plist" "$APP_BUNDLE/Contents/Info.plist"
plutil -replace CFBundleShortVersionString -string "$VERSION" "$APP_BUNDLE/Contents/Info.plist"
plutil -replace CFBundleVersion -string "$VERSION" "$APP_BUNDLE/Contents/Info.plist"

echo "==> App bundle created at $APP_BUNDLE"
echo "    Run with: open $APP_BUNDLE"
