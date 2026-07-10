"""Tests for SupabaseReader's banned-games functions and their in-process
cache (get_banned_game, get_banned_games, ban_game).

get_rollable_game() calls get_banned_games() on every candidate game --
up to 25 times in a single /solo-roll One Hell of a Month -- so the result
is cached in-process instead of hitting Supabase live every call. These
tests verify the cache actually avoids repeat calls, and that ban_game()
correctly invalidates it.
"""

from unittest.mock import MagicMock, patch

import pytest

from Modules import SupabaseReader


@pytest.fixture(autouse=True)
def reset_cache():
    """The cache is a module-level global; make sure no test leaks state
    into another one."""
    SupabaseReader._banned_games_cache = None
    yield
    SupabaseReader._banned_games_cache = None


def _mock_supabase(rows: list[dict]) -> MagicMock:
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.upsert.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=rows)
    mock_sb.table.return_value = mock_table
    return mock_sb


class TestGetBannedGamesCache:
    def test_first_call_hits_supabase(self):
        mock_sb = _mock_supabase([{"game_id": "g1", "reason": "r", "banned_by": "u1"}])
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            SupabaseReader.get_banned_games()
        mock_sb.table.assert_called_once_with("bannedGames")

    def test_second_call_does_not_hit_supabase_again(self):
        mock_sb = _mock_supabase([{"game_id": "g1", "reason": "r", "banned_by": "u1"}])
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            SupabaseReader.get_banned_games()
            SupabaseReader.get_banned_games()
        mock_sb.table.assert_called_once_with("bannedGames")

    def test_returns_rows_from_supabase(self):
        rows = [{"game_id": "g1", "reason": "r", "banned_by": "u1"}]
        mock_sb = _mock_supabase(rows)
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            result = SupabaseReader.get_banned_games()
        assert result == rows

    def test_many_calls_in_a_loop_only_hit_supabase_once(self):
        """Regression: this is the exact shape of get_rollable_game()'s
        loop over up to 25 candidate games in One Hell of a Month."""
        mock_sb = _mock_supabase([])
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            for _ in range(25):
                SupabaseReader.get_banned_games()
        mock_sb.table.assert_called_once_with("bannedGames")


class TestGetBannedGame:
    def test_returns_matching_row(self):
        rows = [
            {"game_id": "g1", "reason": "r1", "banned_by": "u1"},
            {"game_id": "g2", "reason": "r2", "banned_by": "u2"},
        ]
        mock_sb = _mock_supabase(rows)
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            result = SupabaseReader.get_banned_game("g2")
        assert result == rows[1]

    def test_returns_none_when_not_banned(self):
        mock_sb = _mock_supabase([{"game_id": "g1", "reason": "r", "banned_by": "u1"}])
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            result = SupabaseReader.get_banned_game("does-not-exist")
        assert result is None

    def test_reuses_the_cache_from_get_banned_games(self):
        mock_sb = _mock_supabase([{"game_id": "g1", "reason": "r", "banned_by": "u1"}])
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            SupabaseReader.get_banned_games()
            SupabaseReader.get_banned_game("g1")
        mock_sb.table.assert_called_once_with("bannedGames")


class TestBanGameInvalidatesCache:
    def test_ban_game_clears_the_cache(self):
        mock_sb = _mock_supabase([])
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            SupabaseReader.get_banned_games()  # populate the cache
            SupabaseReader.ban_game("g1", "reason", "banner-ce-id")
        assert SupabaseReader._banned_games_cache is None

    def test_next_read_after_a_ban_hits_supabase_again(self):
        mock_sb = _mock_supabase([])
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            SupabaseReader.get_banned_games()
            SupabaseReader.ban_game("g1", "reason", "banner-ce-id")
            SupabaseReader.get_banned_games()
        # once for the initial populate, once for the upsert's internal
        # get_banned_game() lookup, once for the re-populate after ban
        assert mock_sb.table.call_count == 3

    def test_appends_to_existing_reason(self):
        mock_sb = _mock_supabase(
            [{"game_id": "g1", "reason": "too easy", "banned_by": "u1"}]
        )
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            SupabaseReader.ban_game("g1", "also buggy", "u2", append=True)

        upsert_call = mock_sb.table.return_value.upsert.call_args[0][0]
        assert upsert_call["reason"] == "too easy\nalso buggy"

    def test_append_false_overwrites_reason(self):
        mock_sb = _mock_supabase(
            [{"game_id": "g1", "reason": "too easy", "banned_by": "u1"}]
        )
        with patch("Modules.SupabaseReader.supabase", mock_sb):
            SupabaseReader.ban_game("g1", "fresh reason", "u2", append=False)

        upsert_call = mock_sb.table.return_value.upsert.call_args[0][0]
        assert upsert_call["reason"] == "fresh reason"
