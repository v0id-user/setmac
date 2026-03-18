#!/usr/bin/env bash
# Run during semantic-release version step. NEW_VERSION is set by semantic-release.
set -euo pipefail

VERSION="${NEW_VERSION:-1.0.0}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Syncing version $VERSION across files..."

# scripts/bundle.sh
sed -i '' "s/^VERSION=.*/VERSION=\"$VERSION\"/" scripts/bundle.sh

# cli/src/setmac/__init__.py
sed -i '' "s/^__version__ = .*/__version__ = \"$VERSION\"/" cli/src/setmac/__init__.py

# justfile
sed -i '' "s/^version      := .*/version      := \"$VERSION\"/" justfile

echo "==> Building release artifacts..."
export VERSION="$VERSION"
swift build -c release
bash scripts/build-cli.sh
bash scripts/bundle.sh
bash scripts/dmg.sh

echo "==> Release build complete: dist/Setmac.dmg, cli/dist/setmac-cli"
