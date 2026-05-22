#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== Building Time Tracker for macOS ==="
echo ""

# Build with PyInstaller using the spec file
./env/bin/pyinstaller \
    --noconfirm \
    --log-level=WARN \
    build.spec

echo ""
echo "=== Build complete ==="
echo "Output: dist/Time Tracker.app"
echo ""
echo "To run: open dist/Time Tracker.app"
