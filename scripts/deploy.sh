#!/usr/bin/env bash
# Deploys main.py and scraper_main.py on the VM: pulls main, reinstalls
# deps, runs a safety check, restarts the systemd --user services, and
# rolls back automatically if the new code fails to import or fails to
# become healthy.
#
# Invoked over SSH by .github/workflows/deploy.yml (GitHub-hosted runner),
# via a forced-command deploy key that never needs sudo -- ce-bot/ce-scraper
# are systemd --user units for exactly this reason. See docs/superpowers/specs
# (local, gitignored) for the full design rationale, and deploy/SETUP.md for
# one-time VM setup.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SERVICES=(ce-bot ce-scraper)
PIP_BIN="${PIP_BIN:-pip}"
PYTHON_BIN="${PYTHON_BIN:-python}"
PYTEST_BIN="${PYTEST_BIN:-pytest}"
HEALTH_CHECK_RETRIES="${HEALTH_CHECK_RETRIES:-5}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-2}"

log() {
    echo "[deploy] $*"
}

rollback() {
    local prev_sha="$1"
    log "Rolling back to $prev_sha"
    git reset --hard "$prev_sha"
    "$PIP_BIN" install -r requirements.txt
    systemctl --user restart "${SERVICES[@]}"
}

services_healthy() {
    local svc
    for svc in "${SERVICES[@]}"; do
        if [[ "$(systemctl --user is-active "$svc")" != "active" ]]; then
            return 1
        fi
    done
    return 0
}

main() {
    local prev_sha attempt
    prev_sha="$(git rev-parse HEAD)"

    log "Fetching origin/main"
    git fetch origin main
    git reset --hard origin/main

    log "Installing dependencies"
    "$PIP_BIN" install -r requirements.txt

    log "Running import smoke test"
    if ! "$PYTHON_BIN" scripts/smoke_test_imports.py; then
        log "Smoke test failed"
        rollback "$prev_sha"
        exit 1
    fi

    log "Running pytest"
    if ! "$PYTEST_BIN" --ignore=tests/integration; then
        log "pytest failed"
        rollback "$prev_sha"
        exit 1
    fi

    log "Restarting services: ${SERVICES[*]}"
    systemctl --user restart "${SERVICES[@]}"

    # Poll HEALTH_CHECK_RETRIES times, sleeping HEALTH_CHECK_INTERVAL seconds
    # before *each* check (including the first). A Type=simple systemd unit
    # reports "active" the instant the process is forked, before it has had
    # any chance to crash on startup (e.g. failing to connect to Discord), so
    # checking immediately with no grace period would let that slip through
    # as a false positive. Success is determined only by whether the last
    # check in the window is healthy, not by the first "active" reading.
    local healthy=0
    attempt=0
    while (( attempt < HEALTH_CHECK_RETRIES )); do
        sleep "$HEALTH_CHECK_INTERVAL"
        attempt=$((attempt + 1))
        if services_healthy; then
            healthy=1
        else
            healthy=0
        fi
    done

    if (( healthy == 1 )); then
        log "Deploy succeeded at $(git rev-parse HEAD)"
        exit 0
    fi

    log "Services failed to become healthy after restart"
    rollback "$prev_sha"
    exit 1
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    cd "$REPO_DIR"
    main "$@"
fi
