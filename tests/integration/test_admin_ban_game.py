"""
Integration tests for the /ban-game command (commands.admin.ban_game).

These tests hit the real Supabase instance and perform write operations against
the `banned_games` table (columns: game_id, reason, banned_by), cleaning up
before and after each test so they leave no residue.

Spec under test (from commands.admin.ban_game's docstring):
- Adds a row to `banned_games` for the given game, with `reason` and `banned_by`
  (the CE ID of the admin who ran the command) set.
- If the game is already banned, appends the given `reason` onto the existing
  `reason` column instead of creating a duplicate row.
- If the invoking user is not registered with CE Assistant, the command exits
  early and does not touch `banned_games`.

Run with:  pytest tests/integration/test_admin_ban_game.py
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import commands.admin as admin_mod
from commands.admin import ban_game
from Modules import SupabaseReader

# A discord id that (almost certainly) does not belong to any registered user.
_UNREGISTERED_DISCORD_ID = 1


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def game_id() -> str:
    """A real game CE ID fetched from the database."""
    ids = SupabaseReader.get_list("name")
    assert len(ids) >= 1, "Need at least 1 game to run ban-game tests."
    return ids[0]


@pytest.fixture(scope="module")
def admin(game_id: str) -> tuple[str, int]:
    """A real, registered (ce_id, discord_id) pair to act as the banning admin."""
    user_ids = SupabaseReader.get_list("user")
    assert len(user_ids) >= 1, "Need at least 1 registered user to run ban-game tests."
    for ce_id in user_ids:
        user = SupabaseReader.get_user(ce_id)
        if user is not None:
            return user.ce_id, user.discord_id
    pytest.fail("Could not resolve a registered user with a discord_id.")


def _banned_rows(game_id: str) -> list[dict]:
    resp = (
        SupabaseReader.supabase.table("bannedGames")
        .select("*")
        .eq("game_id", game_id)
        .execute()
    )
    return resp.data or []


def _make_interaction(discord_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        user=SimpleNamespace(id=discord_id, mention=f"<@{discord_id}>"),
    )


def _run_ban_game(interaction, game: str, reason: str):
    with (
        patch.object(admin_mod, "client", create=True, new=MagicMock()),
        patch("commands.admin.hm.log_command", new_callable=AsyncMock),
    ):
        asyncio.run(ban_game(interaction, game, reason))


def _wipe_banned_row(game_id: str) -> None:
    # Deletes directly via Supabase (not SupabaseReader.ban_game/delete
    # helpers), so get_banned_games()'s in-process cache must be reset by
    # hand -- otherwise a later ban_game() call in this file would read a
    # stale cached row and incorrectly "append" instead of creating fresh.
    SupabaseReader.supabase.table("bannedGames").delete().eq(
        "game_id", game_id
    ).execute()
    SupabaseReader._banned_games_cache = None


@pytest.fixture(autouse=True)
def clean(game_id: str):
    """Wipe any leftover banned_games rows for our test game before and after every test."""
    _wipe_banned_row(game_id)
    yield
    _wipe_banned_row(game_id)


# ── banning a game ───────────────────────────────────────────────────────────


class TestBanGameCreatesRow:
    def test_creates_one_row(self, game_id: str, admin: tuple[str, int]):
        _, admin_discord_id = admin
        interaction = _make_interaction(admin_discord_id)

        _run_ban_game(interaction, game_id, "Too easy to farm.")

        rows = _banned_rows(game_id)
        assert len(rows) == 1

    def test_row_has_correct_reason(self, game_id: str, admin: tuple[str, int]):
        _, admin_discord_id = admin
        interaction = _make_interaction(admin_discord_id)

        _run_ban_game(interaction, game_id, "Too easy to farm.")

        rows = _banned_rows(game_id)
        assert rows[0]["reason"] == "Too easy to farm."

    def test_row_has_correct_banned_by(self, game_id: str, admin: tuple[str, int]):
        admin_ce_id, admin_discord_id = admin
        interaction = _make_interaction(admin_discord_id)

        _run_ban_game(interaction, game_id, "Too easy to farm.")

        rows = _banned_rows(game_id)
        assert rows[0]["banned_by"] == admin_ce_id

    def test_response_is_deferred(self, game_id: str, admin: tuple[str, int]):
        _, admin_discord_id = admin
        interaction = _make_interaction(admin_discord_id)

        _run_ban_game(interaction, game_id, "Too easy to farm.")

        interaction.response.defer.assert_awaited_once()

    def test_sends_confirmation_message(self, game_id: str, admin: tuple[str, int]):
        _, admin_discord_id = admin
        interaction = _make_interaction(admin_discord_id)

        _run_ban_game(interaction, game_id, "Too easy to farm.")

        interaction.followup.send.assert_awaited()
        msg = interaction.followup.send.call_args[0][0]
        assert "banned" in msg.lower()


# ── banning an already-banned game ──────────────────────────────────────────


class TestBanGameAlreadyBanned:
    def test_does_not_create_a_second_row(self, game_id: str, admin: tuple[str, int]):
        _, admin_discord_id = admin
        interaction = _make_interaction(admin_discord_id)

        _run_ban_game(interaction, game_id, "Too easy to farm.")
        _run_ban_game(interaction, game_id, "Also, it's buggy.")

        rows = _banned_rows(game_id)
        assert len(rows) == 1

    def test_appends_new_reason_to_existing_reason(
        self, game_id: str, admin: tuple[str, int]
    ):
        _, admin_discord_id = admin
        interaction = _make_interaction(admin_discord_id)

        _run_ban_game(interaction, game_id, "Too easy to farm.")
        _run_ban_game(interaction, game_id, "Also, it's buggy.")

        rows = _banned_rows(game_id)
        reason = rows[0]["reason"]
        assert "Too easy to farm." in reason
        assert "Also, it's buggy." in reason


# ── unregistered banning user ───────────────────────────────────────────────


class TestBanGameUnregisteredUser:
    def test_does_not_create_a_row(self, game_id: str):
        interaction = _make_interaction(_UNREGISTERED_DISCORD_ID)

        _run_ban_game(interaction, game_id, "Too easy to farm.")

        rows = _banned_rows(game_id)
        assert rows == []

    def test_sends_not_registered_message(self, game_id: str):
        interaction = _make_interaction(_UNREGISTERED_DISCORD_ID)

        _run_ban_game(interaction, game_id, "Too easy to farm.")

        interaction.followup.send.assert_awaited()
        msg = interaction.followup.send.call_args[0][0]
        assert "registered" in msg.lower()

    def test_exits_early_without_raising(self, game_id: str):
        interaction = _make_interaction(_UNREGISTERED_DISCORD_ID)

        # Should not raise, even though the user has no CE ID to record as banned_by.
        _run_ban_game(interaction, game_id, "Too easy to farm.")
