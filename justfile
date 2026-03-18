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
    swift package clean
    swift build
    log stream --predicate 'subsystem == "com.v0id.setmac"' --level debug --style compact &
    .build/debug/{{app_name}}
    -kill %1 2>/dev/null

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

# Generate .icns from icon.png (1024x1024)
icon:
    bash scripts/generate-icon.sh

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
