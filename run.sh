#!/bin/bash
# Daily Security Jobs — wrapper script for cron delivery
# Strips debug output, surfaces MEDIA path for Telegram delivery
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if available, otherwise use system python
if [ -d "venv" ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

OUTPUT=$($PYTHON -m src.main --hours 24 2>&1)

# Extract the MEDIA line
MEDIA_LINE=$(echo "$OUTPUT" | grep "^📎 MEDIA:" || echo "")
if [ -n "$MEDIA_LINE" ]; then
    MEDIA_PATH=$(echo "$MEDIA_LINE" | sed 's/^📎 MEDIA://')
    echo "🔐 Security Jobs Digest — $(date '+%Y-%m-%d %H:%M UTC')"
    echo ""
    echo "$OUTPUT" | grep -E "^📋 Filter results:" -A 5 | tail -4
    echo ""
    echo "MEDIA:$MEDIA_PATH"
else
    echo "⚠️ Scraper run completed but no jobs found or no DOCX generated."
    echo "$OUTPUT" | tail -20
fi
