import asyncio
from unittest.mock import AsyncMock, patch
from contextlib import contextmanager

import scraper_main


def _one_iteration_patches(**overrides):
    """Return a dict of patches for a single-iteration run.
    Override any patch by passing keyword args."""
    defaults = {
        "is_loop_running": patch.object(
            scraper_main.SupabaseReader, "is_loop_running", return_value=False
        ),
        "cleanup_updates": patch.object(
            scraper_main.SupabaseReader, "cleanup_delivered_updates"
        ),
        "cleanup_commands": patch.object(
            scraper_main.SupabaseReader, "cleanup_completed_commands"
        ),
        "get_commands": patch.object(
            scraper_main.SupabaseReader, "get_pending_commands", return_value=[]
        ),
        "ack_command": patch.object(scraper_main.SupabaseReader, "acknowledge_command"),
        "complete_command": patch.object(
            scraper_main.SupabaseReader, "complete_command"
        ),
        "start_run": patch.object(
            scraper_main.SupabaseReader, "start_loop_run", return_value="run-1"
        ),
        "finish_run": patch.object(scraper_main.SupabaseReader, "finish_loop_run"),
        "process_loop": patch.object(
            scraper_main,
            "process_loop",
            new_callable=AsyncMock,
            side_effect=lambda **kw: setattr(scraper_main, "_shutdown", True),
        ),
        "close_session": patch(
            "scraper_main.http_session.close_session", new_callable=AsyncMock
        ),
    }
    defaults.update(overrides)
    return defaults


def _run_main():
    scraper_main._shutdown = False
    asyncio.run(scraper_main.main())


class TestLoopLocking:
    def test_skips_everything_when_locked(self):
        """When loop is running, the entire iteration is skipped — no cleanup, no commands, no process_loop."""
        with (
            patch.object(
                scraper_main.SupabaseReader, "is_loop_running", return_value=True
            ),
            patch.object(
                scraper_main.SupabaseReader, "cleanup_delivered_updates"
            ) as mock_cleanup,
            patch.object(
                scraper_main.SupabaseReader, "get_pending_commands"
            ) as mock_cmds,
            patch.object(scraper_main.SupabaseReader, "start_loop_run") as mock_start,
            patch.object(
                scraper_main, "process_loop", new_callable=AsyncMock
            ) as mock_loop,
            patch("scraper_main.http_session.close_session", new_callable=AsyncMock),
            patch(
                "asyncio.sleep",
                new_callable=AsyncMock,
                side_effect=lambda _: setattr(scraper_main, "_shutdown", True),
            ),
        ):
            _run_main()

        mock_cleanup.assert_not_called()
        mock_cmds.assert_not_called()
        mock_start.assert_not_called()
        mock_loop.assert_not_called()

    def test_lock_acquired_before_process_loop(self):
        call_order = []

        def _track_start(*a):
            call_order.append("start_loop_run")
            return "run-1"

        async def _track_loop(**kw):
            call_order.append("process_loop")
            scraper_main._shutdown = True

        def _track_finish(*a):
            call_order.append("finish_loop_run")

        patches = _one_iteration_patches(
            start_run=patch.object(
                scraper_main.SupabaseReader, "start_loop_run", side_effect=_track_start
            ),
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_track_loop
            ),
            finish_run=patch.object(
                scraper_main.SupabaseReader,
                "finish_loop_run",
                side_effect=_track_finish,
            ),
        )
        with contextmanager_from_patches(patches):
            _run_main()

        assert call_order == ["start_loop_run", "process_loop", "finish_loop_run"]

    def test_lock_released_on_successful_iteration(self):
        patches = _one_iteration_patches()
        with contextmanager_from_patches(patches) as mocks:
            _run_main()

        mocks["finish_run"].assert_called_once_with("run-1")

    def test_lock_released_on_exception(self):
        def _raise_and_shutdown(**kw):
            scraper_main._shutdown = True
            raise RuntimeError("boom")

        patches = _one_iteration_patches(
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_raise_and_shutdown
            ),
        )
        with contextmanager_from_patches(patches) as mocks:
            _run_main()

        mocks["finish_run"].assert_called_once_with("run-1")

    def test_lock_check_reevaluated_each_iteration(self):
        """Lock check returns True on first call (skip), False on second (run), then shutdown."""
        iteration_count = 0

        async def _count_and_stop(**kw):
            nonlocal iteration_count
            iteration_count += 1
            scraper_main._shutdown = True

        with (
            patch.object(
                scraper_main.SupabaseReader,
                "is_loop_running",
                side_effect=[True, False],
            ),
            patch.object(scraper_main.SupabaseReader, "cleanup_delivered_updates"),
            patch.object(scraper_main.SupabaseReader, "cleanup_completed_commands"),
            patch.object(
                scraper_main.SupabaseReader, "get_pending_commands", return_value=[]
            ),
            patch.object(scraper_main.SupabaseReader, "acknowledge_command"),
            patch.object(scraper_main.SupabaseReader, "complete_command"),
            patch.object(
                scraper_main.SupabaseReader, "start_loop_run", return_value="run-1"
            ),
            patch.object(scraper_main.SupabaseReader, "finish_loop_run"),
            patch.object(scraper_main, "process_loop", side_effect=_count_and_stop),
            patch("scraper_main.http_session.close_session", new_callable=AsyncMock),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            _run_main()

        assert iteration_count == 1


class TestCommandProcessing:
    def test_full_scrape_command(self):
        received = {}

        async def _capture(**kw):
            received.update(kw)
            scraper_main._shutdown = True

        patches = _one_iteration_patches(
            get_commands=patch.object(
                scraper_main.SupabaseReader,
                "get_pending_commands",
                return_value=[{"id": "cmd-1", "command": "full_scrape"}],
            ),
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_capture
            ),
        )
        with contextmanager_from_patches(patches) as mocks:
            _run_main()

        assert received["full_scrape"] is True
        mocks["ack_command"].assert_called_once_with("cmd-1")
        mocks["complete_command"].assert_called_once_with("cmd-1")

    def test_initiate_loop_does_not_set_full_scrape(self):
        received = {}

        async def _capture(**kw):
            received.update(kw)
            scraper_main._shutdown = True

        patches = _one_iteration_patches(
            get_commands=patch.object(
                scraper_main.SupabaseReader,
                "get_pending_commands",
                return_value=[{"id": "cmd-1", "command": "initiate_loop"}],
            ),
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_capture
            ),
        )
        with contextmanager_from_patches(patches):
            _run_main()

        assert received["full_scrape"] is False

    def test_no_commands_means_no_full_scrape(self):
        received = {}

        async def _capture(**kw):
            received.update(kw)
            scraper_main._shutdown = True

        patches = _one_iteration_patches(
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_capture
            ),
        )
        with contextmanager_from_patches(patches) as mocks:
            _run_main()

        assert received["full_scrape"] is False
        mocks["ack_command"].assert_not_called()

    def test_multiple_commands_all_acknowledged_and_completed(self):
        async def _shutdown(**kw):
            scraper_main._shutdown = True

        commands = [
            {"id": "cmd-1", "command": "initiate_loop"},
            {"id": "cmd-2", "command": "full_scrape"},
            {"id": "cmd-3", "command": "initiate_loop"},
        ]

        patches = _one_iteration_patches(
            get_commands=patch.object(
                scraper_main.SupabaseReader,
                "get_pending_commands",
                return_value=commands,
            ),
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_shutdown
            ),
        )
        with contextmanager_from_patches(patches) as mocks:
            _run_main()

        assert mocks["ack_command"].call_count == 3
        assert mocks["complete_command"].call_count == 3
        mocks["ack_command"].assert_any_call("cmd-1")
        mocks["ack_command"].assert_any_call("cmd-2")
        mocks["ack_command"].assert_any_call("cmd-3")

    def test_full_scrape_wins_when_mixed_with_initiate_loop(self):
        received = {}

        async def _capture(**kw):
            received.update(kw)
            scraper_main._shutdown = True

        commands = [
            {"id": "cmd-1", "command": "initiate_loop"},
            {"id": "cmd-2", "command": "full_scrape"},
        ]

        patches = _one_iteration_patches(
            get_commands=patch.object(
                scraper_main.SupabaseReader,
                "get_pending_commands",
                return_value=commands,
            ),
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_capture
            ),
        )
        with contextmanager_from_patches(patches):
            _run_main()

        assert received["full_scrape"] is True

    def test_unknown_command_does_not_set_full_scrape(self):
        received = {}

        async def _capture(**kw):
            received.update(kw)
            scraper_main._shutdown = True

        patches = _one_iteration_patches(
            get_commands=patch.object(
                scraper_main.SupabaseReader,
                "get_pending_commands",
                return_value=[{"id": "cmd-1", "command": "something_weird"}],
            ),
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_capture
            ),
        )
        with contextmanager_from_patches(patches):
            _run_main()

        assert received["full_scrape"] is False

    def test_acknowledge_before_complete_per_command(self):
        call_log = []

        def _log_ack(cmd_id):
            call_log.append(("ack", cmd_id))

        def _log_complete(cmd_id):
            call_log.append(("complete", cmd_id))

        async def _shutdown(**kw):
            scraper_main._shutdown = True

        patches = _one_iteration_patches(
            get_commands=patch.object(
                scraper_main.SupabaseReader,
                "get_pending_commands",
                return_value=[
                    {"id": "cmd-1", "command": "full_scrape"},
                    {"id": "cmd-2", "command": "initiate_loop"},
                ],
            ),
            ack_command=patch.object(
                scraper_main.SupabaseReader, "acknowledge_command", side_effect=_log_ack
            ),
            complete_command=patch.object(
                scraper_main.SupabaseReader,
                "complete_command",
                side_effect=_log_complete,
            ),
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_shutdown
            ),
        )
        with contextmanager_from_patches(patches):
            _run_main()

        assert call_log == [
            ("ack", "cmd-1"),
            ("complete", "cmd-1"),
            ("ack", "cmd-2"),
            ("complete", "cmd-2"),
        ]


class TestCleanup:
    def test_both_cleanup_functions_called(self):
        patches = _one_iteration_patches()
        with contextmanager_from_patches(patches) as mocks:
            _run_main()

        mocks["cleanup_updates"].assert_called_once()
        mocks["cleanup_commands"].assert_called_once()

    def test_cleanup_not_called_when_locked(self):
        with (
            patch.object(
                scraper_main.SupabaseReader, "is_loop_running", return_value=True
            ),
            patch.object(
                scraper_main.SupabaseReader, "cleanup_delivered_updates"
            ) as mock_cu,
            patch.object(
                scraper_main.SupabaseReader, "cleanup_completed_commands"
            ) as mock_cc,
            patch.object(scraper_main, "process_loop", new_callable=AsyncMock),
            patch("scraper_main.http_session.close_session", new_callable=AsyncMock),
            patch(
                "asyncio.sleep",
                new_callable=AsyncMock,
                side_effect=lambda _: setattr(scraper_main, "_shutdown", True),
            ),
        ):
            _run_main()

        mock_cu.assert_not_called()
        mock_cc.assert_not_called()


class TestSessionCleanup:
    def test_http_session_closed_on_normal_exit(self):
        patches = _one_iteration_patches()
        with contextmanager_from_patches(patches) as mocks:
            _run_main()

        mocks["close_session"].assert_awaited_once()

    def test_http_session_closed_on_process_loop_exception(self):
        def _raise_and_shutdown(**kw):
            scraper_main._shutdown = True
            raise RuntimeError("boom")

        patches = _one_iteration_patches(
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_raise_and_shutdown
            ),
        )
        with contextmanager_from_patches(patches) as mocks:
            _run_main()

        mocks["close_session"].assert_awaited_once()


class TestSignalHandler:
    def test_signal_sets_shutdown_flag(self):
        scraper_main._shutdown = False
        scraper_main._handle_signal(2, None)
        assert scraper_main._shutdown is True

    def test_signal_handler_idempotent(self):
        scraper_main._shutdown = False
        scraper_main._handle_signal(2, None)
        scraper_main._handle_signal(15, None)
        assert scraper_main._shutdown is True


class TestLifecycleOrdering:
    def test_full_ordering_lock_check_cleanup_commands_lock_loop_unlock(self):
        call_order = []

        def _track(name):
            def _inner(*a, **kw):
                call_order.append(name)
                if name == "start_loop_run":
                    return "run-1"
                if name == "get_pending_commands":
                    return []

            return _inner

        async def _track_loop(**kw):
            call_order.append("process_loop")
            scraper_main._shutdown = True

        with (
            patch.object(
                scraper_main.SupabaseReader,
                "is_loop_running",
                side_effect=_track("is_loop_running"),
            ),
            patch.object(
                scraper_main.SupabaseReader,
                "cleanup_delivered_updates",
                side_effect=_track("cleanup_updates"),
            ),
            patch.object(
                scraper_main.SupabaseReader,
                "cleanup_completed_commands",
                side_effect=_track("cleanup_commands"),
            ),
            patch.object(
                scraper_main.SupabaseReader,
                "get_pending_commands",
                side_effect=_track("get_pending_commands"),
            ),
            patch.object(scraper_main.SupabaseReader, "acknowledge_command"),
            patch.object(scraper_main.SupabaseReader, "complete_command"),
            patch.object(
                scraper_main.SupabaseReader,
                "start_loop_run",
                side_effect=_track("start_loop_run"),
            ),
            patch.object(
                scraper_main.SupabaseReader,
                "finish_loop_run",
                side_effect=_track("finish_loop_run"),
            ),
            patch.object(scraper_main, "process_loop", side_effect=_track_loop),
            patch("scraper_main.http_session.close_session", new_callable=AsyncMock),
        ):
            _run_main()

        assert call_order == [
            "is_loop_running",
            "cleanup_updates",
            "cleanup_commands",
            "get_pending_commands",
            "start_loop_run",
            "process_loop",
            "finish_loop_run",
        ]


# ── helper ───────────────────────────────────────────────────────────────────


@contextmanager
def contextmanager_from_patches(patches: dict):
    """Enter all patches in a dict, yield a dict of the entered mocks, then exit all."""
    entered = {}
    contexts = {}
    try:
        for key, p in patches.items():
            ctx = p
            entered[key] = ctx.__enter__()
            contexts[key] = ctx
        yield entered
    finally:
        for ctx in reversed(list(contexts.values())):
            ctx.__exit__(None, None, None)
