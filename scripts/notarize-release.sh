#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Setmac"
DIST_DIR="${DIST_DIR:-dist}"
APP_BUNDLE="${APP_BUNDLE:-$DIST_DIR/$APP_NAME.app}"
DMG_PATH="${DMG_PATH:-$DIST_DIR/$APP_NAME.dmg}"
SIGNING_IDENTITY="${APPLE_SIGNING_IDENTITY:-${CODESIGN_IDENTITY:--}}"

if [ ! -f "$DMG_PATH" ]; then
    echo "==> Skipping notarization: $DMG_PATH does not exist"
    exit 0
fi

if [ "$SIGNING_IDENTITY" = "-" ]; then
    echo "==> Skipping notarization: ad-hoc signed builds cannot be notarized"
    exit 0
fi

if [ -z "${APPLE_ID:-}" ] || [ -z "${APPLE_APP_SPECIFIC_PASSWORD:-}" ] || [ -z "${APPLE_TEAM_ID:-}" ]; then
    echo "==> Skipping notarization: Apple notarization secrets are not configured"
    exit 0
fi

echo "==> Notarizing $DMG_PATH"
xcrun notarytool submit \
    "$DMG_PATH" \
    --apple-id "$APPLE_ID" \
    --password "$APPLE_APP_SPECIFIC_PASSWORD" \
    --team-id "$APPLE_TEAM_ID" \
    --wait

if [ -d "$APP_BUNDLE" ]; then
    echo "==> Stapling notarization ticket to $APP_BUNDLE"
    xcrun stapler staple "$APP_BUNDLE"
fi

echo "==> Stapling notarization ticket to $DMG_PATH"
xcrun stapler staple "$DMG_PATH"
