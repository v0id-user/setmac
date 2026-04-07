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
    /usr/bin/log stream --predicate 'subsystem == "com.v0id.setmac"' --level debug --style compact &
    .build/debug/{{app_name}}
    -kill %1 2>/dev/null

# Check all build-time dependencies are present and valid
check-deps:
    @command -v swift >/dev/null 2>&1 \
        || (echo "✗ swift not found — install Xcode Command Line Tools: xcode-select --install" && exit 1)
    @swift --version >/dev/null 2>&1 \
        || (echo "✗ swift is not functional — check Xcode CLT installation" && exit 1)
    @command -v uv >/dev/null 2>&1 \
        || (echo "✗ uv not found — install with: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1)
    @command -v python3 >/dev/null 2>&1 \
        || (echo "✗ python3 not found — install via Homebrew: brew install python@3.14" && exit 1)
    @python3 -c "import sys; assert sys.version_info >= (3,11), 'python3.11+ required'" 2>/dev/null \
        || (echo "✗ python3.11+ required (found $(python3 --version))" && exit 1)
    @python3 -m json.tool Resources/tools.json >/dev/null 2>&1 \
        || (echo "✗ Resources/tools.json is invalid JSON" && exit 1)
    @python3 -m py_compile cli/src/setmac/registry.py cli/src/setmac/cli.py \
        cli/src/setmac/installers/base.py cli/src/setmac/commands/install.py \
        cli/src/setmac/commands/status.py cli/src/setmac/commands/configs.py \
        2>/dev/null \
        || (echo "✗ Python syntax error in CLI source — run: python3 -m py_compile <file>" && exit 1)
    @echo "✓ All dependencies OK"

# Build debug binary (incremental)
build: check-deps
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

# Verify release signatures and CLI startup
release-verify:
    codesign --verify --deep --strict --verbose=2 dist/Setmac.app
    codesign --verify --verbose=2 dist/Setmac.dmg
    cli/dist/setmac-cli --help

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
