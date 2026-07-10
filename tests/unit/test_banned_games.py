"""Tests for SupabaseReader's banned-games functions
(get_banned_game, get_banned_games, ban_game).

Like every other table in SupabaseReader.py, reads go through the
LocalCache SQLite mirror rather than hitting Supabase live, and ban_game()
dual-writes to both Supabase and LocalCache. get_rollable_game() calls
get_banned_games() on every candidate game it considers -- up to 25 times
in a single /solo-roll One Hell of a Month -- so these tests also confirm
that reading never touches Supabase at all.
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

from Modules import LocalCache, SupabaseReader


def _init_cache() -> str:
    tmpdir = tempfile.mkdtemp()
    LocalCache.init(os.path.join(tmpdir, "test.db"))
    return tmpdir


def _teardown_cache(tmpdir: str) -> None:
    LocalCache.close()
    shutil.rmtree(tmpdir)


def _mock_supabase() -> MagicMock:
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_table.upsert.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[])
    mock_sb.table.return_value = mock_table
    return mock_sb


class TestGetBannedGamesReadsFromCache:
    def test_returns_empty_when_nothing_banned(self):
        tmpdir = _init_cache()
        try:
            assert SupabaseReader.get_banned_games() == []
        finally:
            _teardown_cache(tmpdir)

    def test_returns_seeded_rows_without_touching_supabase(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_banned_games_bulk(
                [{"game_id": "g1", "reason": "r1", "banned_by": "u1"}]
            )
            mock_sb = MagicMock()
            with patch("Modules.SupabaseReader.supabase", mock_sb):
                result = SupabaseReader.get_banned_games()
            assert result == [{"game_id": "g1", "reason": "r1", "banned_by": "u1"}]
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)

    def test_many_calls_in_a_loop_never_touch_supabase(self):
        """Regression: this is the exact shape of get_rollable_game()'s
        loop over up to 25 candidate games in One Hell of a Month."""
        tmpdir = _init_cache()
        try:
            mock_sb = MagicMock()
            with patch("Modules.SupabaseReader.supabase", mock_sb):
                for _ in range(25):
                    SupabaseReader.get_banned_games()
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)


class TestGetBannedGame:
    def test_returns_matching_row(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_banned_games_bulk(
                [
                    {"game_id": "g1", "reason": "r1", "banned_by": "u1"},
                    {"game_id": "g2", "reason": "r2", "banned_by": "u2"},
                ]
            )
            result = SupabaseReader.get_banned_game("g2")
            assert result == {"game_id": "g2", "reason": "r2", "banned_by": "u2"}
        finally:
            _teardown_cache(tmpdir)

    def test_returns_none_when_not_banned(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_banned_games_bulk(
                [{"game_id": "g1", "reason": "r", "banned_by": "u1"}]
            )
            assert SupabaseReader.get_banned_game("does-not-exist") is None
        finally:
            _teardown_cache(tmpdir)


class TestBanGameDualWrite:
    def test_writes_to_local_cache(self):
        tmpdir = _init_cache()
        try:
            with patch("Modules.SupabaseReader.supabase", _mock_supabase()):
                SupabaseReader.ban_game("g1", "Too easy.", "u1")
            assert LocalCache.get_banned_game("g1") == {
                "game_id": "g1",
                "reason": "Too easy.",
                "banned_by": "u1",
            }
        finally:
            _teardown_cache(tmpdir)

    def test_writes_to_supabase(self):
        tmpdir = _init_cache()
        try:
            mock_sb = _mock_supabase()
            with patch("Modules.SupabaseReader.supabase", mock_sb):
                SupabaseReader.ban_game("g1", "Too easy.", "u1")
            mock_sb.table.assert_called_with("bannedGames")
            mock_sb.table.return_value.upsert.assert_called_once_with(
                {"game_id": "g1", "reason": "Too easy.", "banned_by": "u1"}
            )
        finally:
            _teardown_cache(tmpdir)

    def test_a_read_immediately_after_a_ban_sees_it_via_cache_only(self):
        """Regression: the old in-process cache was only invalidated inside
        ban_game() itself, so a ban made anywhere else (another process, a
        manual Supabase edit) was invisible until process restart. Routing
        through LocalCache -- refreshed the same way every other table is,
        via rebuild_from_supabase()/run_integrity_check() -- removes that
        as a second, inconsistent caching mechanism."""
        tmpdir = _init_cache()
        try:
            with patch("Modules.SupabaseReader.supabase", _mock_supabase()):
                SupabaseReader.ban_game("g1", "Too easy.", "u1")
                # no supabase mock needed for the read -- proves it never
                # goes back out to Supabase after a write
                result = SupabaseReader.get_banned_games()
            assert result == [
                {"game_id": "g1", "reason": "Too easy.", "banned_by": "u1"}
            ]
        finally:
            _teardown_cache(tmpdir)

    def test_appends_to_existing_reason(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_banned_games_bulk(
                [{"game_id": "g1", "reason": "too easy", "banned_by": "u1"}]
            )
            mock_sb = _mock_supabase()
            with patch("Modules.SupabaseReader.supabase", mock_sb):
                SupabaseReader.ban_game("g1", "also buggy", "u2", append=True)

            cached = LocalCache.get_banned_game("g1")
            assert cached is not None
            assert cached["reason"] == "too easy\nalso buggy"
            upsert_call = mock_sb.table.return_value.upsert.call_args[0][0]
            assert upsert_call["reason"] == "too easy\nalso buggy"
        finally:
            _teardown_cache(tmpdir)

    def test_append_false_overwrites_reason(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_banned_games_bulk(
                [{"game_id": "g1", "reason": "too easy", "banned_by": "u1"}]
            )
            with patch("Modules.SupabaseReader.supabase", _mock_supabase()):
                SupabaseReader.ban_game("g1", "fresh reason", "u2", append=False)

            cached = LocalCache.get_banned_game("g1")
            assert cached is not None
            assert cached["reason"] == "fresh reason"
        finally:
            _teardown_cache(tmpdir)

    def test_rebanning_after_re_seeding_cache_does_not_lose_the_existing_reason(self):
        """Regression for the stale-cache data-loss bug: simulates a ban
        that landed in LocalCache via rebuild/integrity-check (i.e. made
        out-of-band, not through this process's ban_game()), then confirms
        a normal re-ban through ban_game() still finds and appends to it --
        the old in-process cache would have missed this row entirely."""
        tmpdir = _init_cache()
        try:
            # simulates a row that arrived via rebuild_from_supabase() /
            # run_integrity_check(), not via this process's ban_game()
            LocalCache.upsert_banned_games_bulk(
                [{"game_id": "g1", "reason": "banned elsewhere", "banned_by": "u1"}]
            )
            with patch("Modules.SupabaseReader.supabase", _mock_supabase()):
                SupabaseReader.ban_game("g1", "also buggy", "u2", append=True)

            cached = LocalCache.get_banned_game("g1")
            assert cached is not None
            assert cached["reason"] == "banned elsewhere\nalso buggy"
        finally:
            _teardown_cache(tmpdir)


class TestBannedGamesUpsertBulk:
    """LocalCache.rebuild_from_supabase() and run_integrity_check() both
    sync banned_games through LocalCache.upsert_banned_games_bulk() (see
    _UPSERT_BULK_FUNCS in LocalCache.py) -- rebuild_from_supabase() itself
    is globally patched to a no-op for this whole test session (see
    tests/conftest.py, to avoid real network calls at import time), so this
    tests the bulk-upsert entry point those two callers actually use."""

    def test_populates_banned_games_from_supabase_shaped_rows(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_banned_games_bulk(
                [{"game_id": "g1", "reason": "r1", "banned_by": "u1"}]
            )
            assert LocalCache.get_banned_game("g1") == {
                "game_id": "g1",
                "reason": "r1",
                "banned_by": "u1",
            }
        finally:
            _teardown_cache(tmpdir)

    def test_is_registered_in_the_rebuild_dispatch_table(self):
        assert "banned_games" in LocalCache._UPSERT_BULK_FUNCS
        assert (
            LocalCache._UPSERT_BULK_FUNCS["banned_games"]
            is LocalCache.upsert_banned_games_bulk
        )
