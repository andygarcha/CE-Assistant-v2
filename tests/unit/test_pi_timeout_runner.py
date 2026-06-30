import time

import pytest

from pi_screenshot_service.timeout_runner import run_with_timeout


def test_run_with_timeout_returns_result_when_fn_completes_in_time():
    result = run_with_timeout(lambda: "done", timeout_seconds=1, cleanup=lambda: None)

    assert result == "done"


def test_run_with_timeout_raises_timeout_error_when_fn_is_too_slow():
    def slow_fn():
        time.sleep(1)
        return "too late"

    with pytest.raises(TimeoutError):
        run_with_timeout(slow_fn, timeout_seconds=0.05, cleanup=lambda: None)


def test_run_with_timeout_calls_cleanup_on_success():
    calls = []

    run_with_timeout(lambda: "done", timeout_seconds=1, cleanup=lambda: calls.append(1))

    assert calls == [1]


def test_run_with_timeout_calls_cleanup_on_timeout():
    calls = []

    def slow_fn():
        time.sleep(1)

    with pytest.raises(TimeoutError):
        run_with_timeout(slow_fn, timeout_seconds=0.05, cleanup=lambda: calls.append(1))

    assert calls == [1]


def test_run_with_timeout_calls_cleanup_when_fn_raises():
    calls = []

    def failing_fn():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        run_with_timeout(failing_fn, timeout_seconds=1, cleanup=lambda: calls.append(1))

    assert calls == [1]
