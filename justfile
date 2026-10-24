app_name     := "Setmac"
bundle_id    := "com.v0id.setmac"
version      := "1.0.0"
build_dir    := ".build"
release_dir  := "dist"
app_bundle   := release_dir / app_name + ".app"
cli_dir      := "cli"

# ─── Development ──────────────────────────────────────────────

# Clean build and run with live os.log streaming
dev:
    #!/usr/bin/env bash
    set -eu
    swift package clean
    swift build
    /usr/bin/log stream --predicate 'subsystem == "com.v0id.setmac"' --level debug --style compact &
    log_pid=$!
    trap 'kill $log_pid 2>/dev/null' EXIT
    .build/debug/{{app_name}}

# Build debug binary (incremental)
build:
    swift build

# Clean all build artifacts
clean:
    swift package clean
    rm -rf {{release_dir}}
    rm -rf {{cli_dir}}/dist {{cli_dir}}/build

# ─── Release ──────────────────────────────────────────────────

# Build optimized release binary
release:
    swift build -c release

# Create .app bundle with embedded CLI
bundle: release cli-build
    bash scripts/bundle.sh

# Create DMG for distribution
dmg: bundle
    bash scripts/dmg.sh

# ─── CLI ──────────────────────────────────────────────────────

# Set up Python CLI dev environment
cli-setup:
    cd {{cli_dir}} && uv sync

# Run CLI in dev mode
cli-dev:
    cd {{cli_dir}} && uv run setmac --help

# Build standalone CLI binary with PyInstaller
cli-build:
    bash scripts/build-cli.sh

# ─── Status & Configs ─────────────────────────────────────

# Check install status of all tools
status:
    cd {{cli_dir}} && uv run setmac status

# Capture current system configs into bundle
capture-configs:
    cd {{cli_dir}} && uv run setmac configs capture

# Apply bundled configs to system
apply-configs:
    cd {{cli_dir}} && uv run setmac configs apply

# ─── Icon ─────────────────────────────────────────────────────

# Redraw Resources/icon.png (reproducible: same seed, same pixels)
icon-draw variant="sprout":
    swift scripts/draw-icon.swift {{variant}} Resources/icon.png

# Generate .build/icon/AppIcon.icns from icon.png (bundle.sh does this itself)
icon:
    bash scripts/generate-icon.sh

# ─── Release ──────────────────────────────────────────────────

# Generate CHANGELOG.md from commits (no version bump)
changelog:
    uv run semantic-release changelog

# Dry-run: show next version and changelog without publishing
release-dry:
    uv run semantic-release --noop version

# Dry-run canary prerelease (run from canary branch)
release-dry-canary:
    uv run semantic-release --noop version --as-prerelease --prerelease-token canary

# Dry-run beta prerelease (run from beta branch)
release-dry-beta:
    uv run semantic-release --noop version --as-prerelease --prerelease-token beta

# Smoke test: build artifacts with test version (no publish)
release-build-test:
    NEW_VERSION="9.99.99-test" bash scripts/release-build.sh
    @echo "Artifacts: dist/Setmac.dmg, cli/dist/setmac-cli"
    file dist/Setmac.dmg cli/dist/setmac-cli

# Verify release signatures, the app icon (in the app and inside the DMG), and CLI startup
release-verify: (verify-icon "dist/Setmac.app")
    #!/usr/bin/env bash
    set -euo pipefail
    codesign --verify --deep --strict --verbose=2 dist/Setmac.app
    codesign --verify --verbose=2 dist/Setmac.dmg
    mount=$(mktemp -d)
    hdiutil attach -nobrowse -readonly -mountpoint "$mount" dist/Setmac.dmg > /dev/null
    trap 'hdiutil detach "$mount" -quiet' EXIT
    just verify-icon "$mount/Setmac.app"
    cli/dist/setmac-cli --help

# Check that an app bundle carries a complete AppIcon.icns
verify-icon app=app_bundle:
    #!/usr/bin/env bash
    set -euo pipefail
    plist="{{app}}/Contents/Info.plist"
    icns="{{app}}/Contents/Resources/AppIcon.icns"
    plutil -lint "$plist"
    test "$(plutil -extract CFBundleIconFile raw "$plist")" = "AppIcon"
    test -s "$icns"
    work=$(mktemp -d)
    trap 'rm -rf "$work"' EXIT
    iconutil -c iconset "$icns" -o "$work/AppIcon.iconset"
    count=$(ls "$work/AppIcon.iconset" | wc -l | tr -d ' ')
    test "$count" -eq 10 || { echo "expected 10 icon images, found $count" >&2; exit 1; }
    largest=$(sips -g pixelWidth "$work/AppIcon.iconset/icon_512x512@2x.png" | awk '/pixelWidth/ {print $2}')
    test "$largest" -eq 1024 || { echo "largest icon is ${largest}px, expected 1024" >&2; exit 1; }
    echo "Icon OK: $icns"

# ─── Utilities ────────────────────────────────────────────────

# Format Swift source files
format:
    swift format --in-place --recursive Sources/

# Count lines of code
loc:
    @echo "Swift:"; find Sources -name '*.swift' | xargs wc -l | tail -1
    @echo "Python:"; find cli/src -name '*.py' | xargs wc -l | tail -1

# Show project structure
tree:
    tree -I '.build|.venv|__pycache__|dist|build|.git' --dirsfirst
