import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

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
        "recent_full_scrape": patch.object(
            scraper_main.SupabaseReader, "recent_full_scrape", return_value=True
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
    def test_recovery_pass_when_locked(self):
        """When previous loop crashed (lock stuck), a recovery pass runs with send_updates=False."""
        received = {}

        async def _capture(**kw):
            received.update(kw)
            scraper_main._shutdown = True
            return {
                "games_updated": 5,
                "users_updated": 3,
                "rolls_updated": 1,
                "updates_generated": 4,
            }

        with (
            patch.object(
                scraper_main.SupabaseReader, "is_loop_running", return_value=True
            ),
            patch.object(scraper_main.SupabaseReader, "cleanup_delivered_updates"),
            patch.object(scraper_main.SupabaseReader, "cleanup_completed_commands"),
            patch.object(
                scraper_main.SupabaseReader, "get_pending_commands"
            ) as mock_cmds,
            patch.object(
                scraper_main.SupabaseReader, "start_loop_run", return_value="run-r"
            ),
            patch.object(scraper_main.SupabaseReader, "finish_loop_run"),
            patch.object(scraper_main.SupabaseReader, "write_scraper_update"),
            patch.object(scraper_main, "process_loop", side_effect=_capture),
            patch("scraper_main.http_session.close_session", new_callable=AsyncMock),
        ):
            _run_main()

        assert received["send_updates"] is False
        mock_cmds.assert_not_called()

    def test_recovery_sends_summary_to_privatelog(self):
        async def _return_counts(**kw):
            scraper_main._shutdown = True
            return {
                "games_updated": 10,
                "users_updated": 5,
                "rolls_updated": 2,
                "updates_generated": 7,
            }

        with (
            patch.object(
                scraper_main.SupabaseReader, "is_loop_running", return_value=True
            ),
            patch.object(scraper_main.SupabaseReader, "cleanup_delivered_updates"),
            patch.object(scraper_main.SupabaseReader, "cleanup_completed_commands"),
            patch.object(
                scraper_main.SupabaseReader, "start_loop_run", return_value="run-r"
            ),
            patch.object(scraper_main.SupabaseReader, "finish_loop_run"),
            patch.object(
                scraper_main.SupabaseReader, "write_scraper_update"
            ) as mock_write,
            patch.object(scraper_main, "process_loop", side_effect=_return_counts),
            patch("scraper_main.http_session.close_session", new_callable=AsyncMock),
        ):
            _run_main()

        mock_write.assert_called_once()
        row = mock_write.call_args[0][0]
        assert row["channel"] == "privatelog"
        assert row["status"] == "stable"
        assert "10 games" in row["text"]
        assert "5 users" in row["text"]
        assert "2 rolls" in row["text"]
        assert "7 notifications suppressed" in row["text"]

    def test_recovery_no_summary_when_process_loop_fails(self):
        def _raise(**kw):
            scraper_main._shutdown = True
            raise RuntimeError("crash during recovery")

        with (
            patch.object(
                scraper_main.SupabaseReader, "is_loop_running", return_value=True
            ),
            patch.object(scraper_main.SupabaseReader, "cleanup_delivered_updates"),
            patch.object(scraper_main.SupabaseReader, "cleanup_completed_commands"),
            patch.object(
                scraper_main.SupabaseReader, "start_loop_run", return_value="run-r"
            ),
            patch.object(scraper_main.SupabaseReader, "finish_loop_run"),
            patch.object(
                scraper_main.SupabaseReader, "write_scraper_update"
            ) as mock_write,
            patch.object(scraper_main, "process_loop", side_effect=_raise),
            patch("scraper_main.http_session.close_session", new_callable=AsyncMock),
        ):
            _run_main()

        mock_write.assert_not_called()

    def test_lock_acquired_before_process_loop(self):
        call_order = []

        def _track_start(*a, **kw):
            call_order.append("start_loop_run")
            return "run-1"

        async def _track_loop(**kw):
            call_order.append("process_loop")
            scraper_main._shutdown = True

        def _track_finish(*a, **kw):
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

    def test_auto_triggers_full_scrape_when_none_recent(self):
        """No command requested a full scrape, but none has run in the last
        24 hours -- process_loop should still get full_scrape=True."""
        received = {}

        async def _capture(**kw):
            received.update(kw)
            scraper_main._shutdown = True

        patches = _one_iteration_patches(
            recent_full_scrape=patch.object(
                scraper_main.SupabaseReader, "recent_full_scrape", return_value=False
            ),
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_capture
            ),
        )
        with contextmanager_from_patches(patches):
            _run_main()

        assert received["full_scrape"] is True

    def test_no_auto_trigger_when_full_scrape_ran_recently(self):
        received = {}

        async def _capture(**kw):
            received.update(kw)
            scraper_main._shutdown = True

        patches = _one_iteration_patches(
            recent_full_scrape=patch.object(
                scraper_main.SupabaseReader, "recent_full_scrape", return_value=True
            ),
            process_loop=patch.object(
                scraper_main, "process_loop", side_effect=_capture
            ),
        )
        with contextmanager_from_patches(patches):
            _run_main()

        assert received["full_scrape"] is False

    def test_command_full_scrape_skips_recent_full_scrape_lookup(self):
        """If a command already forced full_scrape=True, there's no need to
        query recent_full_scrape at all."""
        patches = _one_iteration_patches(
            get_commands=patch.object(
                scraper_main.SupabaseReader,
                "get_pending_commands",
                return_value=[{"id": "cmd-1", "command": "full_scrape"}],
            ),
        )
        with contextmanager_from_patches(patches) as mocks:
            _run_main()

        mocks["recent_full_scrape"].assert_not_called()

    def test_start_loop_run_receives_full_scrape_decision(self):
        patches = _one_iteration_patches(
            recent_full_scrape=patch.object(
                scraper_main.SupabaseReader, "recent_full_scrape", return_value=False
            ),
        )
        with contextmanager_from_patches(patches) as mocks:
            _run_main()

        mocks["start_run"].assert_called_once_with(full_scrape=True)

    def test_recovery_pass_does_not_check_recent_full_scrape(self):
        async def _return_counts(**kw):
            scraper_main._shutdown = True
            return {
                "games_updated": 0,
                "users_updated": 0,
                "rolls_updated": 0,
                "updates_generated": 0,
            }

        with (
            patch.object(
                scraper_main.SupabaseReader, "is_loop_running", return_value=True
            ),
            patch.object(scraper_main.SupabaseReader, "cleanup_delivered_updates"),
            patch.object(scraper_main.SupabaseReader, "cleanup_completed_commands"),
            patch.object(
                scraper_main.SupabaseReader, "recent_full_scrape"
            ) as mock_recent,
            patch.object(
                scraper_main.SupabaseReader, "start_loop_run", return_value="run-r"
            ),
            patch.object(scraper_main.SupabaseReader, "finish_loop_run"),
            patch.object(scraper_main.SupabaseReader, "write_scraper_update"),
            patch.object(scraper_main, "process_loop", side_effect=_return_counts),
            patch("scraper_main.http_session.close_session", new_callable=AsyncMock),
        ):
            _run_main()

        mock_recent.assert_not_called()

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

    def test_cleanup_still_called_during_recovery(self):
        """Cleanup runs even during a recovery pass — old delivered updates
        and completed commands should still be pruned."""

        async def _shutdown(**kw):
            scraper_main._shutdown = True
            return {
                "games_updated": 0,
                "users_updated": 0,
                "rolls_updated": 0,
                "updates_generated": 0,
            }

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
            patch.object(
                scraper_main.SupabaseReader, "start_loop_run", return_value="run-r"
            ),
            patch.object(scraper_main.SupabaseReader, "finish_loop_run"),
            patch.object(scraper_main.SupabaseReader, "write_scraper_update"),
            patch.object(scraper_main, "process_loop", side_effect=_shutdown),
            patch("scraper_main.http_session.close_session", new_callable=AsyncMock),
        ):
            _run_main()

        mock_cu.assert_called_once()
        mock_cc.assert_called_once()


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

    def test_second_signal_forces_exit(self):
        scraper_main._shutdown = False
        scraper_main._handle_signal(2, None)
        assert scraper_main._shutdown is True
        with pytest.raises(SystemExit):
            scraper_main._handle_signal(2, None)


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
                return None

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
                scraper_main.SupabaseReader, "recent_full_scrape", return_value=True
            ),
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
