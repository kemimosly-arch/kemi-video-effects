#!/usr/bin/env bash
# Builds reel-editor-space.zip: everything the Hugging Face Space needs, with the Space README on top.
set -e
cd "$(dirname "$0")/.."
rm -rf /tmp/reel-editor-space && mkdir -p /tmp/reel-editor-space
cp -r app app.py scripts fonts models assets requirements.txt packages.txt LICENSE /tmp/reel-editor-space/
cp deploy/SPACE_README.md /tmp/reel-editor-space/README.md
find /tmp/reel-editor-space -name '__pycache__' -prune -exec rm -rf {} +
rm -f reel-editor-space.zip && (cd /tmp/reel-editor-space && zip -qr "$OLDPWD/reel-editor-space.zip" .)
echo "Built reel-editor-space.zip"
