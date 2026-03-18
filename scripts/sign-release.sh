#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Setmac"
DIST_DIR="${DIST_DIR:-dist}"
APP_BUNDLE="${APP_BUNDLE:-$DIST_DIR/$APP_NAME.app}"
APP_BINARY="$APP_BUNDLE/Contents/MacOS/$APP_NAME"
EMBEDDED_CLI="$APP_BUNDLE/Contents/MacOS/setmac-cli"
STANDALONE_CLI="${STANDALONE_CLI:-cli/dist/setmac-cli}"
DMG_PATH="${DMG_PATH:-$DIST_DIR/$APP_NAME.dmg}"
ENTITLEMENTS="${ENTITLEMENTS:-Resources/Setmac.entitlements}"
SIGN_APP="${SIGN_APP:-1}"
SIGN_DMG="${SIGN_DMG:-1}"
SIGNING_IDENTITY="${APPLE_SIGNING_IDENTITY:-${CODESIGN_IDENTITY:--}}"

if ! command -v codesign >/dev/null 2>&1; then
    echo "Error: codesign is not available."
    exit 1
fi

if [ "$SIGNING_IDENTITY" = "-" ]; then
    echo "==> Using ad-hoc signing (-)"
else
    echo "==> Using signing identity: $SIGNING_IDENTITY"
fi

sign_binary() {
    local target="$1"

    if [ ! -e "$target" ]; then
        return 0
    fi

    echo "==> Signing $target"

    if [ "$SIGNING_IDENTITY" = "-" ]; then
        codesign --force --sign - "$target"
    else
        codesign --force --sign "$SIGNING_IDENTITY" --timestamp --options runtime "$target"
    fi
}

verify_signature() {
    local target="$1"

    if [ ! -e "$target" ]; then
        return 0
    fi

    codesign --verify --verbose=2 "$target"
}

if [ "$SIGN_APP" = "1" ]; then
    sign_binary "$STANDALONE_CLI"
    sign_binary "$EMBEDDED_CLI"
    sign_binary "$APP_BINARY"

    if [ -d "$APP_BUNDLE" ]; then
        echo "==> Signing $APP_BUNDLE"
        if [ "$SIGNING_IDENTITY" = "-" ]; then
            codesign --force --sign - "$APP_BUNDLE"
        else
            codesign \
                --force \
                --sign "$SIGNING_IDENTITY" \
                --timestamp \
                --options runtime \
                --entitlements "$ENTITLEMENTS" \
                "$APP_BUNDLE"
        fi

        codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE"
    fi
fi

if [ "$SIGN_DMG" = "1" ] && [ -f "$DMG_PATH" ]; then
    echo "==> Signing $DMG_PATH"
    if [ "$SIGNING_IDENTITY" = "-" ]; then
        codesign --force --sign - "$DMG_PATH"
    else
        codesign --force --sign "$SIGNING_IDENTITY" --timestamp "$DMG_PATH"
    fi

    verify_signature "$DMG_PATH"
fi
