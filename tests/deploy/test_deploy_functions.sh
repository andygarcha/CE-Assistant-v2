#!/usr/bin/env bash
# Tests for scripts/deploy.sh helper functions (rollback, services_healthy).
# Run with: bash tests/deploy/test_deploy_functions.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FAILURES=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAILURES=$((FAILURES + 1)); }

# --- fixture: fake bin dir with stub systemctl/pip so we never touch the real system ---
setup_stub_bin() {
    local bin_dir="$1"
    mkdir -p "$bin_dir"

    cat > "$bin_dir/systemctl" <<'EOF'
#!/usr/bin/env bash
# Stub systemctl. Records calls to $STUB_LOG. "is-active" reads desired
# state from $STUB_ACTIVE_SERVICES (space-separated list of active units).
echo "$*" >> "$STUB_LOG"
if [[ "$1" == "is-active" ]]; then
    svc="$2"
    for active in $STUB_ACTIVE_SERVICES; do
        if [[ "$active" == "$svc" ]]; then
            echo "active"
            exit 0
        fi
    done
    echo "inactive"
    exit 3
fi
exit 0
EOF
    chmod +x "$bin_dir/systemctl"

    cat > "$bin_dir/pip" <<'EOF'
#!/usr/bin/env bash
echo "pip $*" >> "$STUB_LOG"
exit 0
EOF
    chmod +x "$bin_dir/pip"
}

# --- test: services_healthy returns true when all services active ---
test_services_healthy_all_active() {
    local tmp
    tmp="$(mktemp -d)"
    export STUB_LOG="$tmp/log"
    : > "$STUB_LOG"
    setup_stub_bin "$tmp/bin"
    export STUB_ACTIVE_SERVICES="ce-bot ce-scraper"
    export PATH="$tmp/bin:$PATH"

    # shellcheck source=/dev/null
    source "$REPO_ROOT/scripts/deploy.sh"
    SERVICES=(ce-bot ce-scraper)

    if services_healthy; then
        pass "services_healthy: true when all active"
    else
        fail "services_healthy: expected true when all active"
    fi
    rm -rf "$tmp"
}

# --- test: services_healthy returns false when one service inactive ---
test_services_healthy_one_inactive() {
    local tmp
    tmp="$(mktemp -d)"
    export STUB_LOG="$tmp/log"
    : > "$STUB_LOG"
    setup_stub_bin "$tmp/bin"
    export STUB_ACTIVE_SERVICES="ce-bot"
    export PATH="$tmp/bin:$PATH"

    # shellcheck source=/dev/null
    source "$REPO_ROOT/scripts/deploy.sh"
    SERVICES=(ce-bot ce-scraper)

    if services_healthy; then
        fail "services_healthy: expected false when ce-scraper inactive"
    else
        pass "services_healthy: false when ce-scraper inactive"
    fi
    rm -rf "$tmp"
}

# --- test: rollback resets to prev_sha, reinstalls deps, restarts services ---
test_rollback_resets_and_restarts() {
    local tmp repo
    tmp="$(mktemp -d)"
    repo="$tmp/repo"
    mkdir -p "$repo"
    (
        cd "$repo"
        git init -q
        git config user.email test@test.com
        git config user.name test
        echo "v1" > file.txt
        git add file.txt
        git commit -q -m "v1"
        prev_sha="$(git rev-parse HEAD)"
        echo "v2 (broken)" > file.txt
        git add file.txt
        git commit -q -m "v2"

        export STUB_LOG="$tmp/log"
        : > "$STUB_LOG"
        setup_stub_bin "$tmp/bin"
        export STUB_ACTIVE_SERVICES="ce-bot ce-scraper"
        export PATH="$tmp/bin:$PATH"
        export PIP_BIN="pip"

        # shellcheck source=/dev/null
        source "$REPO_ROOT/scripts/deploy.sh"
        SERVICES=(ce-bot ce-scraper)

        rollback "$prev_sha"

        current_sha="$(git rev-parse HEAD)"
        content="$(cat file.txt)"

        if [[ "$current_sha" == "$prev_sha" && "$content" == "v1" ]]; then
            pass "rollback: HEAD and working tree reset to prev_sha"
        else
            fail "rollback: expected HEAD=$prev_sha content=v1, got HEAD=$current_sha content=$content"
        fi

        if grep -q "^pip install -r requirements.txt$" "$STUB_LOG"; then
            pass "rollback: reinstalled dependencies"
        else
            fail "rollback: expected pip install -r requirements.txt to be called"
        fi

        if grep -q "^restart ce-bot ce-scraper$" "$STUB_LOG"; then
            pass "rollback: restarted services"
        else
            fail "rollback: expected systemctl restart ce-bot ce-scraper to be called"
        fi
    )
    rm -rf "$tmp"
}

test_services_healthy_all_active
test_services_healthy_one_inactive
test_rollback_resets_and_restarts

echo ""
echo "---"
if [[ "$FAILURES" -eq 0 ]]; then
    echo "All tests passed."
    exit 0
else
    echo "$FAILURES test(s) failed."
    exit 1
fi
