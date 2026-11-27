#!/bin/bash
# Double-click after adding or changing anything in projects/.
# Compresses new images/videos (originals go to ../Website-originals/projects),
# rebuilds the project pages and the project list on the homepage.
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Needs: brew install ffmpeg webp
echo "Updating projects (big videos can take a few minutes)..."
python3 scripts/build-projects.py

echo ""
echo "Done. You can close this window."
