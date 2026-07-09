#!/bin/bash
# MY.LAB — Wrapper cron pour sync_takemoto.py
# Exécution hebdomadaire depuis le VPS
set -euo pipefail

REPO_ROOT="/opt/mylab-theme"
VENV="$REPO_ROOT/.venv"
LOG="/var/log/mylab-takemoto-sync.log"
ALERT_EMAIL="yoann@mylab-shop.com"
GEMINI_KEY="${GEMINI_API_KEY:-}"

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(timestamp)] $*" | tee -a "$LOG"; }

alert() {
    local subject="$1"
    local body="$2"
    log "ALERT: $subject"
    # Send via simple mail if configured, else log only
    if command -v mail >/dev/null 2>&1; then
        echo -e "$body\n\nSee $LOG" | mail -s "[MyLab] $subject" "$ALERT_EMAIL" || true
    fi
}

log "=== Sync Takemoto start ==="

cd "$REPO_ROOT" || { alert "sync_takemoto: cd failed" "Cannot cd to $REPO_ROOT"; exit 1; }

# Pull latest code
if ! git pull origin master 2>&1 | tee -a "$LOG"; then
    alert "sync_takemoto: git pull failed" "Cannot pull latest from master"
    exit 2
fi

# Load Shopify token from .env.sync if present
if [ -f "$REPO_ROOT/.env.sync" ]; then
    # shellcheck source=/dev/null
    set -a; source "$REPO_ROOT/.env.sync"; set +a
fi

# Activate venv
if [ ! -d "$VENV" ]; then
    log "Creating venv..."
    python3 -m venv "$VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"

# Ensure deps
pip install --quiet --upgrade pip
pip install --quiet requests beautifulsoup4 playwright
python -m playwright install --with-deps chromium >> "$LOG" 2>&1 || true

# Run sync
if ! python scripts/sync_takemoto.py 2>&1 | tee -a "$LOG"; then
    alert "sync_takemoto: run failed" "Script sync_takemoto.py exited non-zero"
    exit 3
fi

# Commit any changes (bulk-data-bottles.json updated)
if ! git diff --quiet assets/bulk-data-bottles.json; then
    log "Committing updated bottles JSON..."
    git add assets/bulk-data-bottles.json
    git -c user.email="sync@mylab-shop.com" -c user.name="MyLab Sync Bot" \
        commit -m "Auto-sync Takemoto catalog ($(date +%Y-%m-%d))" 2>&1 | tee -a "$LOG"
    git push origin master 2>&1 | tee -a "$LOG" || log "WARN: git push failed (non-fatal)"
else
    log "No changes to bottles JSON"
fi

log "=== Sync Takemoto done ==="
