"""
Integration test for /clear-roll-portion (commands.admin.clear_roll_portion).

This is a regression test for a bug where the command mutated a roll in
memory but persisted via SupabaseReader.dump_user(user), which never
touches user.rolls -- so the mutation was silently discarded. The fix
persists via SupabaseReader.dump_roll(roll) instead.

These tests run the real command against a real (throwaway, fake) user and
roll in Supabase -- only the Discord-facing bits (interaction, member) are
mocked. Assertions check Supabase directly (bypassing LocalCache) *and*
LocalCache directly (bypassing Supabase), so a bug where only one of the two
got updated would be caught.

Run with:  pytest tests/integration/test_clear_roll_portion.py
"""

import asyncio
import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from Classes.CE_Roll import CERoll
from Classes.CE_User import CEUser
from commands.admin import clear_roll_portion
from Modules import LocalCache, SupabaseReader

_FAKE_CE_ID = "00000000-0000-4000-8000-000000000002"
_FAKE_DISCORD_ID = 999999999999999002
_FAKE_ROLL_ID = "00000000-0000-4000-8000-000000000030"
_ROLL_NAME = "Two Week T2 Streak"


# ── raw Supabase helper (deliberately bypasses LocalCache) ─────────────────────


def _supabase_row(table: str, id_column: str, id_value: str) -> dict | None:
    resp = (
        SupabaseReader.supabase.table(table)
        .select("*")
        .eq(id_column, id_value)
        .execute()
    )
    return resp.data[0] if resp.data else None


def _supabase_rows(table: str, column: str, value: str) -> list[dict]:
    resp = SupabaseReader.supabase.table(table).select("*").eq(column, value).execute()
    return resp.data or []


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def real_two_game_ids() -> tuple[str, str]:
    """Two distinct, real, existing game ids -- used to satisfy rollGames'
    foreign key to games. Read-only."""
    game_ids = SupabaseReader.get_list("name")
    assert len(game_ids) >= 2, "Need at least 2 registered games to run this test."
    return game_ids[0], game_ids[1]


def _assert_no_fake_rows_in_supabase(when: str) -> None:
    collisions = []
    if _supabase_row("users", "ce_id", _FAKE_CE_ID) is not None:
        collisions.append(f"users.ce_id = {_FAKE_CE_ID}")
    if _supabase_row("rolls", "id", _FAKE_ROLL_ID) is not None:
        collisions.append(f"rolls.id = {_FAKE_ROLL_ID}")
    assert not collisions, (
        f"{when}: these fake test ids exist as real rows in Supabase:\n"
        + "\n".join(collisions)
    )


@pytest.fixture(scope="module", autouse=True)
def _verify_clean_before_and_after():
    _assert_no_fake_rows_in_supabase("Before running this file")
    yield
    _assert_no_fake_rows_in_supabase("After running this file")


@pytest.fixture(autouse=True)
def clean():
    """Wipe the fake user and roll, in both Supabase and LocalCache, before
    and after every test."""

    def _wipe():
        SupabaseReader.delete_user(_FAKE_CE_ID)
        SupabaseReader.delete_roll(_FAKE_ROLL_ID)

    _wipe()
    yield
    _wipe()


def _make_fake_user() -> CEUser:
    return CEUser(
        discord_id=_FAKE_DISCORD_ID,
        ce_id=_FAKE_CE_ID,
        owned_games=[],
        rolls=[],
        display_name="__integration_test_clear_roll_portion__",
        avatar="",
        last_updated=datetime.datetime.now(datetime.UTC),
    )


def _make_fake_roll(game_ids: tuple[str, str]) -> CERoll:
    return CERoll(
        roll_name=_ROLL_NAME,  # type: ignore[arg-type]
        user_ce_id=_FAKE_CE_ID,
        games=list(game_ids),
        status="current",  # type: ignore[arg-type]
        due_time=datetime.datetime(2030, 1, 1, tzinfo=datetime.UTC),
        _id=_FAKE_ROLL_ID,
    )


def _run_command():
    interaction = SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )
    member = SimpleNamespace(id=_FAKE_DISCORD_ID, mention=f"<@{_FAKE_DISCORD_ID}>")

    import commands.admin as admin_mod

    with (
        patch.object(admin_mod, "client", create=True, new=MagicMock()),
        # log_command is a Discord-side effect (privatelog post), unrelated
        # to the persistence behavior under test -- mocked out so this test
        # doesn't need a real admin caller registered in Supabase.
        patch("commands.admin.hm.log_command", new_callable=AsyncMock),
    ):
        asyncio.run(
            clear_roll_portion(interaction, member, _ROLL_NAME)  # type: ignore[arg-type]
        )
    return interaction


class TestClearRollPortionPersistsToSupabase:
    def test_status_is_between_stages_in_supabase(
        self, real_two_game_ids: tuple[str, str]
    ):
        SupabaseReader.dump_user(_make_fake_user())
        SupabaseReader.dump_roll(_make_fake_roll(real_two_game_ids))

        _run_command()

        row = _supabase_row("rolls", "id", _FAKE_ROLL_ID)
        assert row is not None
        assert row["status"] == "between_stages"

    def test_due_time_is_cleared_in_supabase(self, real_two_game_ids: tuple[str, str]):
        SupabaseReader.dump_user(_make_fake_user())
        SupabaseReader.dump_roll(_make_fake_roll(real_two_game_ids))

        _run_command()

        row = _supabase_row("rolls", "id", _FAKE_ROLL_ID)
        assert row is not None
        assert row["time_due"] is None

    def test_last_game_is_removed_in_supabase(self, real_two_game_ids: tuple[str, str]):
        SupabaseReader.dump_user(_make_fake_user())
        SupabaseReader.dump_roll(_make_fake_roll(real_two_game_ids))
        assert len(_supabase_rows("rollGames", "roll_id", _FAKE_ROLL_ID)) == 2  # sanity

        _run_command()

        remaining = _supabase_rows("rollGames", "roll_id", _FAKE_ROLL_ID)
        assert len(remaining) == 1
        assert remaining[0]["game_id"] == real_two_game_ids[0]


class TestClearRollPortionPersistsToLocalCache:
    def test_status_is_between_stages_in_local_cache(
        self, real_two_game_ids: tuple[str, str]
    ):
        SupabaseReader.dump_user(_make_fake_user())
        SupabaseReader.dump_roll(_make_fake_roll(real_two_game_ids))

        _run_command()

        row = LocalCache.get_roll(_FAKE_ROLL_ID)
        assert row is not None
        assert row["status"] == "between_stages"

    def test_due_time_is_cleared_in_local_cache(
        self, real_two_game_ids: tuple[str, str]
    ):
        SupabaseReader.dump_user(_make_fake_user())
        SupabaseReader.dump_roll(_make_fake_roll(real_two_game_ids))

        _run_command()

        row = LocalCache.get_roll(_FAKE_ROLL_ID)
        assert row is not None
        assert row["time_due"] is None

    def test_last_game_is_removed_in_local_cache(
        self, real_two_game_ids: tuple[str, str]
    ):
        SupabaseReader.dump_user(_make_fake_user())
        SupabaseReader.dump_roll(_make_fake_roll(real_two_game_ids))
        assert len(LocalCache.get_roll_games(_FAKE_ROLL_ID)) == 2  # sanity check

        _run_command()

        remaining = LocalCache.get_roll_games(_FAKE_ROLL_ID)
        assert len(remaining) == 1
        assert remaining[0]["game_id"] == real_two_game_ids[0]


class TestClearRollPortionResponse:
    def test_success_message_sent(self, real_two_game_ids: tuple[str, str]):
        SupabaseReader.dump_user(_make_fake_user())
        SupabaseReader.dump_roll(_make_fake_roll(real_two_game_ids))

        interaction = _run_command()

        msg = interaction.followup.send.call_args[0][0]
        assert "between_stages" in msg
