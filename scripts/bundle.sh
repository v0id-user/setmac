#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Setmac"
BUNDLE_ID="com.v0id.setmac"
VERSION="1.0.0"
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

# Copy bundled configs if they exist
if [ -d "Resources/configs" ]; then
    cp -R "Resources/configs" "$APP_BUNDLE/Contents/Resources/configs"
    echo "    Embedded configs"
fi

# Generate Info.plist
cat > "$APP_BUNDLE/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>26.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSSupportsAutomaticTermination</key>
    <true/>
    <key>NSSupportsSuddenTermination</key>
    <true/>
</dict>
</plist>
EOF

echo "==> App bundle created at $APP_BUNDLE"
echo "    Run with: open $APP_BUNDLE"
