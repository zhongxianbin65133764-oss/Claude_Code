#!/usr/bin/env bash
#
# Stop services started by mac_start.sh (native Python path).
# For Docker, use `docker-compose down` instead.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

stopped_any=0
for SVC in bot dashboard; do
    pidfile="data/$SVC.pid"
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "Stopped $SVC (pid $pid)"
            stopped_any=1
        else
            echo "$SVC pid $pid no longer running"
        fi
        rm -f "$pidfile"
    fi
done

if [ $stopped_any -eq 0 ]; then
    echo "Nothing was running. (Try docker-compose down if you started with Docker.)"
fi
