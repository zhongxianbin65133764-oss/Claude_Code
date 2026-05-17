#!/usr/bin/env bash
#
# Register the bot + dashboard as macOS LaunchAgents:
#   - Start at user login
#   - Restart automatically on crash (KeepAlive)
#   - Logs to data/bot.log and data/dashboard.log
#
# Uses the native Python path (.venv/bin/python). Prerequisites:
#   1. .venv has been created and `pip install -r requirements.txt` ran
#      (running scripts/mac/mac_start.sh once accomplishes this)
#   2. .env exists in the project root
#
# Usage:  ./scripts/mac/install_launchd.sh
# Undo:   ./scripts/mac/uninstall_launchd.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LAUNCH_DIR="$HOME/Library/LaunchAgents"

# ---- Preflight ----
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "✗ No .venv at $PROJECT_DIR/.venv"
    echo "  Run ./scripts/mac/mac_start.sh once first to set up the Python environment."
    exit 1
fi
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "✗ No .env at $PROJECT_DIR/.env"
    echo "  cp .env.example .env  (then edit if needed)"
    exit 1
fi

mkdir -p "$LAUNCH_DIR"
mkdir -p "$PROJECT_DIR/data"

for SVC in bot dashboard; do
    PLIST_NAME="com.polymarket-arb.$SVC.plist"
    TEMPLATE="$SCRIPT_DIR/$PLIST_NAME"
    DEST="$LAUNCH_DIR/$PLIST_NAME"

    if [ ! -f "$TEMPLATE" ]; then
        echo "✗ Template missing: $TEMPLATE"
        exit 1
    fi

    # Substitute project path into the template
    sed "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" "$TEMPLATE" > "$DEST"

    # Reload: unload first in case there's an existing one
    launchctl unload "$DEST" 2>/dev/null || true
    launchctl load "$DEST"

    echo "✓ Installed $PLIST_NAME"
done

echo
echo "Done. Services are now running and will:"
echo "  - Start automatically at user login"
echo "  - Restart automatically if they crash"
echo
echo "Useful commands:"
echo "  Check status :  launchctl list | grep polymarket-arb"
echo "  View logs    :  tail -f data/bot.log data/dashboard.log"
echo "  Dashboard    :  open http://localhost:5000"
echo "  Uninstall    :  ./scripts/mac/uninstall_launchd.sh"
