#!/usr/bin/env bash
# Integration tests for scripts/deploy.sh main() orchestration.
# Run with: bash tests/deploy/test_deploy_main.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FAILURES=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAILURES=$((FAILURES + 1)); }

# Builds a fake "repo under deploy" with an origin remote, a requirements.txt,
# and stub bin/ scripts for systemctl, pip, python (smoke test), pytest.
# Args: $1 = scratch dir, $2 = smoke test exit code, $3 = pytest exit code,
#       $4 = space-separated list of services systemctl reports active
#       *after* restart (simulates start success/failure).
setup_fixture() {
    local tmp="$1" smoke_exit="$2" pytest_exit="$3" active_after_restart="$4"
    local origin="$tmp/origin" work="$tmp/work" bin="$tmp/bin"
    mkdir -p "$origin" "$bin"

    (
        cd "$origin"
        git init -q --bare
    )

    git clone -q "$origin" "$work"
    (
        cd "$work"
        git config user.email test@test.com
        git config user.name test
        echo "requests" > requirements.txt
        mkdir -p scripts
        echo '#!/usr/bin/env true' > scripts/smoke_test_imports.py
        git add requirements.txt scripts/smoke_test_imports.py
        git commit -q -m "v1 (good)"
        git push -q origin main 2>/dev/null || git push -q origin master
    )

    # setup_fixture runs inside a subshell (its output is captured via command
    # substitution by callers), so `export` here would not be visible to the
    # caller's shell. Pass PREV_SHA_FIXTURE back via a file instead.
    PREV_SHA_FIXTURE="$(cd "$work" && git rev-parse HEAD)"
    echo "$PREV_SHA_FIXTURE" > "$tmp/prev_sha"

    # Push v2 from a *separate* clone so "$work" (which stands in for the
    # VM's on-disk checkout) stays at v1 until deploy.sh's `git fetch` +
    # `git reset --hard origin/main` pulls it forward. If v2 were committed
    # directly in $work, main()'s `git rev-parse HEAD` (captured as prev_sha
    # before the fetch) would already equal v2, making rollback a no-op and
    # the "HEAD advanced" assertion trivially true regardless of correctness.
    local upstream="$tmp/upstream"
    git clone -q "$origin" "$upstream"
    (
        cd "$upstream"
        git config user.email test@test.com
        git config user.name test
        echo "requests==2" > requirements.txt
        git add requirements.txt
        git commit -q -m "v2 (new)"
        git push -q origin HEAD:main 2>/dev/null || git push -q origin HEAD:master
    )

    cat > "$bin/systemctl" <<EOF
#!/usr/bin/env bash
echo "\$*" >> "$tmp/log"
if [[ "\$1" == "restart" ]]; then
    exit 0
fi
if [[ "\$1" == "is-active" ]]; then
    svc="\$2"
    for active in $active_after_restart; do
        if [[ "\$active" == "\$svc" ]]; then
            echo "active"
            exit 0
        fi
    done
    echo "inactive"
    exit 3
fi
exit 0
EOF
    chmod +x "$bin/systemctl"

    cat > "$bin/pip" <<EOF
#!/usr/bin/env bash
echo "pip \$*" >> "$tmp/log"
exit 0
EOF
    chmod +x "$bin/pip"

    cat > "$bin/fake_smoke" <<EOF
#!/usr/bin/env bash
echo "smoke \$*" >> "$tmp/log"
exit $smoke_exit
EOF
    chmod +x "$bin/fake_smoke"

    cat > "$bin/fake_pytest" <<EOF
#!/usr/bin/env bash
echo "pytest \$*" >> "$tmp/log"
exit $pytest_exit
EOF
    chmod +x "$bin/fake_pytest"

    : > "$tmp/log"
    echo "$work"
}

run_deploy() {
    local tmp="$1" work="$2"
    (
        export REPO_DIR="$work"
        export PATH="$tmp/bin:$PATH"
        export PIP_BIN="pip"
        export PYTHON_BIN="fake_smoke"
        export PYTEST_BIN="fake_pytest"
        export HEALTH_CHECK_RETRIES=2
        export HEALTH_CHECK_INTERVAL=0
        cd "$work"
        bash "$REPO_ROOT/scripts/deploy.sh"
    )
}

test_success_path() {
    local tmp work
    tmp="$(mktemp -d)"
    work="$(setup_fixture "$tmp" 0 0 "ce-bot ce-scraper")"
    PREV_SHA_FIXTURE="$(cat "$tmp/prev_sha")"

    if run_deploy "$tmp" "$work"; then
        pass "success path: deploy.sh exits 0"
    else
        fail "success path: expected exit 0"
    fi

    new_sha="$(cd "$work" && git rev-parse HEAD)"
    if [[ "$new_sha" != "$PREV_SHA_FIXTURE" ]]; then
        pass "success path: HEAD advanced to new commit"
    else
        fail "success path: expected HEAD to advance"
    fi
    rm -rf "$tmp"
}

test_smoke_test_failure_rolls_back() {
    local tmp work
    tmp="$(mktemp -d)"
    work="$(setup_fixture "$tmp" 1 0 "ce-bot ce-scraper")"
    PREV_SHA_FIXTURE="$(cat "$tmp/prev_sha")"

    if run_deploy "$tmp" "$work"; then
        fail "smoke failure: expected deploy.sh to exit non-zero"
    else
        pass "smoke failure: deploy.sh exits non-zero"
    fi

    final_sha="$(cd "$work" && git rev-parse HEAD)"
    if [[ "$final_sha" == "$PREV_SHA_FIXTURE" ]]; then
        pass "smoke failure: HEAD rolled back to prev_sha"
    else
        fail "smoke failure: expected HEAD=$PREV_SHA_FIXTURE, got $final_sha"
    fi

    # rollback() (Task 1) always restarts services once with the reverted
    # (good) code to bring the VM back up, so exactly 1 restart is expected
    # here -- it's the rollback's restart, not a restart with broken v2 code.
    # main()'s own success-path restart never fires because it returns via
    # `rollback; exit 1` before reaching `systemctl restart` for the deploy.
    restart_count="$(grep -c "^restart ce-bot ce-scraper$" "$tmp/log" || true)"
    if [[ "$restart_count" -eq 1 ]]; then
        pass "smoke failure: services only restarted once, by rollback with reverted code"
    else
        fail "smoke failure: expected exactly 1 restart (from rollback), got $restart_count"
    fi
    rm -rf "$tmp"
}

test_unhealthy_after_restart_rolls_back() {
    local tmp work
    tmp="$(mktemp -d)"
    work="$(setup_fixture "$tmp" 0 0 "ce-bot")"  # ce-scraper never comes up
    PREV_SHA_FIXTURE="$(cat "$tmp/prev_sha")"

    if run_deploy "$tmp" "$work"; then
        fail "unhealthy: expected deploy.sh to exit non-zero"
    else
        pass "unhealthy: deploy.sh exits non-zero"
    fi

    final_sha="$(cd "$work" && git rev-parse HEAD)"
    if [[ "$final_sha" == "$PREV_SHA_FIXTURE" ]]; then
        pass "unhealthy: HEAD rolled back to prev_sha"
    else
        fail "unhealthy: expected HEAD=$PREV_SHA_FIXTURE, got $final_sha"
    fi
    rm -rf "$tmp"
}

test_success_path
test_smoke_test_failure_rolls_back
test_unhealthy_after_restart_rolls_back

echo ""
echo "---"
if [[ "$FAILURES" -eq 0 ]]; then
    echo "All tests passed."
    exit 0
else
    echo "$FAILURES test(s) failed."
    exit 1
fi
