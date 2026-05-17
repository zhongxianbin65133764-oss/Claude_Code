#!/usr/bin/env bash
#
# Remove the LaunchAgents installed by install_launchd.sh.
# Does NOT delete logs, data/positions.db, or .env.
#
set -euo pipefail

LAUNCH_DIR="$HOME/Library/LaunchAgents"
removed=0
for SVC in bot dashboard; do
    PLIST="$LAUNCH_DIR/com.polymarket-arb.$SVC.plist"
    if [ -f "$PLIST" ]; then
        launchctl unload "$PLIST" 2>/dev/null || true
        rm "$PLIST"
        echo "✓ Removed com.polymarket-arb.$SVC.plist"
        removed=$((removed + 1))
    fi
done

if [ $removed -eq 0 ]; then
    echo "Nothing to remove. (Were the agents installed?)"
fi
