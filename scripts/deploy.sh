#!/usr/bin/env bash
# Deploys main.py and scraper_main.py on the VM: pulls main, reinstalls
# deps, runs a safety check, restarts the systemd services, and rolls back
# automatically if the new code fails to import or fails to become healthy.
#
# Invoked by .github/workflows/deploy.yml on a self-hosted GitHub Actions
# runner registered on the VM. See docs/superpowers/specs (local, gitignored)
# for the full design rationale, and deploy/SETUP.md for one-time VM setup.
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
    systemctl restart "${SERVICES[@]}"
}

services_healthy() {
    local svc
    for svc in "${SERVICES[@]}"; do
        if [[ "$(systemctl is-active "$svc")" != "active" ]]; then
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
    systemctl restart "${SERVICES[@]}"

    attempt=0
    while (( attempt < HEALTH_CHECK_RETRIES )); do
        if services_healthy; then
            log "Deploy succeeded at $(git rev-parse HEAD)"
            exit 0
        fi
        sleep "$HEALTH_CHECK_INTERVAL"
        attempt=$((attempt + 1))
    done

    log "Services failed to become healthy after restart"
    rollback "$prev_sha"
    exit 1
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    cd "$REPO_DIR"
    main "$@"
fi
