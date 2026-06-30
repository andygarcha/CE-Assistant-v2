from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Callable, TypeVar

T = TypeVar("T")


def run_with_timeout(
    fn: Callable[[], T], timeout_seconds: float, cleanup: Callable[[], None]
) -> T:
    """
    Runs `fn` with a hard wall-clock timeout. `cleanup` always runs afterward,
    whether `fn` succeeds, raises, or times out.

    A timed-out `fn` keeps running in its own thread after this call returns,
    since Python can't forcibly kill a thread. `cleanup` exists for exactly this
    case: it should release whatever `fn` was blocked on (e.g. quitting a
    Selenium driver) so that abandoned call stops holding resources.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            raise TimeoutError(f"timed out after {timeout_seconds}s")
        finally:
            cleanup()
