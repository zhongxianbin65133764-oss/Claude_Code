#!/usr/bin/env bash
#
# macOS one-shot launcher. Detects Docker; falls back to native Python.
# Idempotent: safe to re-run.
#
# Usage:  ./scripts/mac/mac_start.sh
#
set -euo pipefail

# Resolve project root regardless of where the script was called from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

# Colors
if [ -t 1 ]; then
    G='\033[32m'; R='\033[31m'; Y='\033[33m'
    BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'
else
    G=''; R=''; Y=''; BOLD=''; DIM=''; RESET=''
fi

say() { printf "%b%s%b\n" "$1" "$2" "$RESET"; }
hdr() { echo; printf "%b" "$BOLD"; echo "$1"; printf "%b" "$RESET"; printf '%.0s-' {1..40}; echo; }

# ---- 0. Sanity ----
if [ "$(uname -s)" != "Darwin" ]; then
    say "$R" "✗ This script is for macOS. On Linux, just: docker-compose up -d"
    exit 1
fi

say "$BOLD" "Polymarket Arb Bot — macOS launcher"
echo "Project: $PROJECT_DIR"

# ---- 1. .env ----
hdr "Step 1/4: .env"
if [ ! -f .env ]; then
    cp .env.example .env
    say "$G" "✓ Created .env from .env.example (defaults are safe; DRY_RUN=true)"
    echo "  → Edit .env now if you want to customise. Press enter to continue."
    read -r _ || true
else
    say "$G" "✓ .env already exists"
fi

# ---- 2. Network ----
hdr "Step 2/4: Network reachability"
if ! python3 scripts/check_network.py; then
    say "$Y" "⚠ Network check found issues. Continue anyway? [y/N]"
    read -r ans
    [ "${ans:-N}" = "y" ] || { say "$DIM" "Aborted."; exit 1; }
fi

# ---- 3. Launch ----
hdr "Step 3/4: Starting services"
mkdir -p data

USE_DOCKER=0
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    USE_DOCKER=1
fi

if [ "$USE_DOCKER" = "1" ]; then
    say "$G" "✓ Docker detected. Using docker-compose."
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose up -d --build
    else
        docker compose up -d --build
    fi
    say "$DIM" "  Logs:        docker-compose logs -f"
    say "$DIM" "  Stop:        docker-compose down"
    say "$DIM" "  Restart:     docker-compose restart"
else
    say "$Y" "⚠ Docker not running. Falling back to native Python."

    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
        say "$R" "✗ Python 3.11+ required."
        say "$DIM" "  Install with:  brew install python@3.11"
        exit 1
    fi

    if [ ! -d .venv ]; then
        say "$DIM" "  Creating virtualenv..."
        python3 -m venv .venv
    fi
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install -q -r requirements.txt

    # Stop anything from a previous run
    if [ -f data/bot.pid ]; then
        kill "$(cat data/bot.pid)" 2>/dev/null || true
        rm -f data/bot.pid
    fi
    if [ -f data/dashboard.pid ]; then
        kill "$(cat data/dashboard.pid)" 2>/dev/null || true
        rm -f data/dashboard.pid
    fi

    say "$DIM" "  Starting bot (caffeinate keeps Mac awake)..."
    nohup caffeinate -i .venv/bin/python -m polymarket_arb.main \
        > data/bot.log 2>&1 &
    echo $! > data/bot.pid
    say "$G" "✓ Bot PID $(cat data/bot.pid)  →  tail -f data/bot.log"

    say "$DIM" "  Starting dashboard..."
    nohup .venv/bin/python -m polymarket_arb.dashboard --host 0.0.0.0 --port 5000 \
        > data/dashboard.log 2>&1 &
    echo $! > data/dashboard.pid
    say "$G" "✓ Dashboard PID $(cat data/dashboard.pid)  →  http://localhost:5000"
    say "$DIM" "  Stop:        ./scripts/mac/mac_stop.sh"
fi

# ---- 4. Open dashboard ----
hdr "Step 4/4: Dashboard"
sleep 2
open "http://localhost:5000" 2>/dev/null || \
    say "$DIM" "  Could not auto-open browser. Visit http://localhost:5000 manually."

echo
say "$BOLD" "Done."
echo "  Dashboard:  http://localhost:5000"
echo "  Weekly review (after some runtime):  python3 scripts/weekly_review.py"
echo
