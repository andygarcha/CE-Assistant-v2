"""
Integration tests for SupabaseReader.delete_user (the function behind
/force-unlink's confirmation button).

These tests hit the real Supabase instance and perform write operations
against a throwaway fake user, cleaning up before and after every test so
they leave no residue and never touch any real registered user's data.

Assertions query Supabase directly via `SupabaseReader.supabase`, not
through `SupabaseReader.get_user`/`get_roll`/LocalCache -- those read from
the local SQLite mirror, which proves the cache was updated but says
nothing about whether the actual Supabase tables were touched. A bug where
Supabase silently failed but LocalCache still got updated would pass tests
that only look at LocalCache.

Run with:  pytest tests/integration/test_delete_user.py
"""

import datetime

import pytest

from Classes.CE_Roll import CERoll
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Modules import SupabaseReader

# Valid-shaped but obviously-fake UUIDs, fixed so leftover artifacts from a
# failed run are easy to spot and the `clean` fixture always targets the
# same rows.
_FAKE_CE_ID = "00000000-0000-4000-8000-000000000001"
_FAKE_DISCORD_ID = 999999999999999001

# Rolls where the fake user is user1 (the initiating/solo user).
_ROLL_IDS_AS_USER1 = [
    "00000000-0000-4000-8000-000000000010",
    "00000000-0000-4000-8000-000000000011",
    "00000000-0000-4000-8000-000000000012",
]
# Rolls where the fake user is user2 (the co-op partner).
_ROLL_IDS_AS_USER2 = [
    "00000000-0000-4000-8000-000000000020",
    "00000000-0000-4000-8000-000000000021",
]
_ALL_ROLL_IDS = _ROLL_IDS_AS_USER1 + _ROLL_IDS_AS_USER2


# ── raw Supabase helpers (deliberately bypass LocalCache) ──────────────────────


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
def real_game_and_objective() -> tuple[str, str]:
    """A real, existing game/objective pair to attach to the fake user, so
    the userGames/userObjectives foreign keys are satisfied. Read-only."""
    game_ids = SupabaseReader.get_list("name")
    assert game_ids, "Need at least 1 registered game to run this test."
    for game_id in game_ids:
        game = SupabaseReader.get_game(game_id)
        if game is not None and game.all_objectives:
            return game.ce_id, game.all_objectives[0].ce_id
    raise AssertionError("No registered game with at least one objective was found.")


@pytest.fixture(scope="module")
def real_user_id() -> str:
    """A real, existing, registered user id -- used as user1 for the co-op
    rolls where the fake user is the partner (user2). Read-only."""
    ids = SupabaseReader.get_list("user")
    real_ids = [uid for uid in ids if uid != _FAKE_CE_ID]
    assert real_ids, "Need at least 1 registered user to run this test."
    return real_ids[0]


def _make_fake_user(game_id: str, objective_id: str) -> CEUser:
    uobj = CEUserObjective(
        ce_id=objective_id,
        game_ce_id=game_id,
        user_points=1,
        type="Primary",
        name="__integration_test__",
    )
    ugame = CEUserGame(
        ce_id=game_id, user_objectives=[uobj], name="__integration_test__"
    )
    return CEUser(
        discord_id=_FAKE_DISCORD_ID,
        ce_id=_FAKE_CE_ID,
        owned_games=[ugame],
        rolls=[],
        display_name="__integration_test_force_unlink__",
        avatar="",
        last_updated=datetime.datetime.now(datetime.UTC),
    )


def _make_solo_rolls(game_id: str) -> list[CERoll]:
    """Rolls where the fake user is user1."""
    return [
        CERoll(
            roll_name="One Hell of a Day",
            user_ce_id=_FAKE_CE_ID,
            games=[game_id],
            status="current",
            _id=roll_id,
        )
        for roll_id in _ROLL_IDS_AS_USER1
    ]


def _make_partner_rolls(game_id: str, real_user1_id: str) -> list[CERoll]:
    """Rolls where the fake user is user2 (the co-op partner) and a real
    registered user is user1."""
    return [
        CERoll(
            roll_name="Destiny Alignment",
            user_ce_id=real_user1_id,
            partner_ce_id=_FAKE_CE_ID,
            games=[game_id, game_id],
            status="current",
            _id=roll_id,
        )
        for roll_id in _ROLL_IDS_AS_USER2
    ]


def _assert_no_fake_rows_in_supabase(when: str) -> None:
    """Raises if any fake id from this file currently exists as a row in
    Supabase. `when` is folded into the failure message so it's obvious
    whether this tripped before the suite ran or after it finished."""
    collisions = []

    if _supabase_row("users", "ce_id", _FAKE_CE_ID) is not None:
        collisions.append(f"users.ce_id = {_FAKE_CE_ID}")

    for roll_id in _ALL_ROLL_IDS:
        if _supabase_row("rolls", "id", roll_id) is not None:
            collisions.append(f"rolls.id = {roll_id}")

    assert not collisions, (
        f"{when}: these fake test ids exist as real rows in Supabase:\n"
        + "\n".join(collisions)
    )


@pytest.fixture(scope="module", autouse=True)
def _verify_clean_before_and_after():
    """Safety guard, runs once before anything else in this file and once
    after everything finishes.

    Pytest instantiates module-scoped fixtures before function-scoped ones
    and tears them down after, so the pre-check below runs before the very
    first `clean` invocation (before this file issues a single delete
    call) -- if any fake id is somehow already a real row, this fails
    loudly and nothing gets deleted, instead of `clean` silently wiping
    out real data.

    The post-check runs after the very last `clean` invocation, confirming
    the whole suite genuinely left no residue behind -- not just that each
    test looked clean individually along the way.
    """
    _assert_no_fake_rows_in_supabase("Before running this file")
    yield
    _assert_no_fake_rows_in_supabase("After running this file")


@pytest.fixture(autouse=True)
def clean():
    """Wipe the fake user and all fake rolls, in Supabase, before and after
    every test."""

    def _wipe():
        SupabaseReader.delete_user(_FAKE_CE_ID)
        for roll_id in _ALL_ROLL_IDS:
            SupabaseReader.delete_roll(roll_id)

    _wipe()
    yield
    _wipe()


# ── delete_user: the user itself ────────────────────────────────────────────


class TestDeleteUserInSupabase:
    def test_user_row_is_gone_from_supabase(
        self, real_game_and_objective: tuple[str, str]
    ):
        game_id, objective_id = real_game_and_objective
        SupabaseReader.dump_user(_make_fake_user(game_id, objective_id))

        SupabaseReader.delete_user(_FAKE_CE_ID)

        assert _supabase_row("users", "ce_id", _FAKE_CE_ID) is None

    def test_owned_games_are_gone_from_supabase(
        self, real_game_and_objective: tuple[str, str]
    ):
        game_id, objective_id = real_game_and_objective
        SupabaseReader.dump_user(_make_fake_user(game_id, objective_id))
        assert _supabase_rows("userGames", "user_ce_id", _FAKE_CE_ID)  # sanity check

        SupabaseReader.delete_user(_FAKE_CE_ID)

        assert _supabase_rows("userGames", "user_ce_id", _FAKE_CE_ID) == []

    def test_owned_objectives_are_gone_from_supabase(
        self, real_game_and_objective: tuple[str, str]
    ):
        game_id, objective_id = real_game_and_objective
        SupabaseReader.dump_user(_make_fake_user(game_id, objective_id))
        assert _supabase_rows(  # sanity check
            "userObjectives", "user_ce_id", _FAKE_CE_ID
        )

        SupabaseReader.delete_user(_FAKE_CE_ID)

        assert _supabase_rows("userObjectives", "user_ce_id", _FAKE_CE_ID) == []

    def test_noop_on_nonexistent_user(self):
        # Nothing was created for this id in this test -- must not raise.
        SupabaseReader.delete_user(_FAKE_CE_ID)


# ── delete_user: rolls where the fake user is user1 (solo) ────────────────────


class TestSoloRollsSurviveInSupabase:
    def test_all_solo_rolls_still_exist(self, real_game_and_objective: tuple[str, str]):
        game_id, objective_id = real_game_and_objective
        SupabaseReader.dump_user(_make_fake_user(game_id, objective_id))
        for roll in _make_solo_rolls(game_id):
            SupabaseReader.dump_roll(roll)

        SupabaseReader.delete_user(_FAKE_CE_ID)

        for roll_id in _ROLL_IDS_AS_USER1:
            row = _supabase_row("rolls", "id", roll_id)
            assert row is not None, f"roll {roll_id} was deleted, expected to survive"
            assert row["user1_ce_id"] == _FAKE_CE_ID

    def test_roll_games_for_solo_rolls_are_untouched(
        self, real_game_and_objective: tuple[str, str]
    ):
        game_id, objective_id = real_game_and_objective
        SupabaseReader.dump_user(_make_fake_user(game_id, objective_id))
        for roll in _make_solo_rolls(game_id):
            SupabaseReader.dump_roll(roll)

        SupabaseReader.delete_user(_FAKE_CE_ID)

        for roll_id in _ROLL_IDS_AS_USER1:
            assert _supabase_rows("rollGames", "roll_id", roll_id) != []


# ── delete_user: rolls where the fake user is user2 (co-op partner) ───────────


class TestPartnerRollsSurviveInSupabase:
    def test_all_partner_rolls_still_exist(
        self, real_game_and_objective: tuple[str, str], real_user_id: str
    ):
        game_id, objective_id = real_game_and_objective
        SupabaseReader.dump_user(_make_fake_user(game_id, objective_id))
        for roll in _make_partner_rolls(game_id, real_user_id):
            SupabaseReader.dump_roll(roll)

        SupabaseReader.delete_user(_FAKE_CE_ID)

        for roll_id in _ROLL_IDS_AS_USER2:
            row = _supabase_row("rolls", "id", roll_id)
            assert row is not None, f"roll {roll_id} was deleted, expected to survive"
            assert row["user2_ce_id"] == _FAKE_CE_ID

    def test_real_partners_user1_id_is_unaffected(
        self, real_game_and_objective: tuple[str, str], real_user_id: str
    ):
        """Deleting the fake user (user2) must not touch the real user's
        (user1) side of the roll."""
        game_id, objective_id = real_game_and_objective
        SupabaseReader.dump_user(_make_fake_user(game_id, objective_id))
        for roll in _make_partner_rolls(game_id, real_user_id):
            SupabaseReader.dump_roll(roll)

        SupabaseReader.delete_user(_FAKE_CE_ID)

        for roll_id in _ROLL_IDS_AS_USER2:
            row = _supabase_row("rolls", "id", roll_id)
            assert row is not None
            assert row["user1_ce_id"] == real_user_id

        # the real user1 is a pre-existing registered user; deleting the
        # fake partner must not have deleted or altered them.
        assert _supabase_row("users", "ce_id", real_user_id) is not None


# ── delete_user: mixed solo + partner rolls together ───────────────────────────


class TestMixedRollsSurviveInSupabase:
    def test_solo_and_partner_rolls_all_survive_a_single_delete(
        self, real_game_and_objective: tuple[str, str], real_user_id: str
    ):
        game_id, objective_id = real_game_and_objective
        SupabaseReader.dump_user(_make_fake_user(game_id, objective_id))
        for roll in _make_solo_rolls(game_id) + _make_partner_rolls(
            game_id, real_user_id
        ):
            SupabaseReader.dump_roll(roll)

        SupabaseReader.delete_user(_FAKE_CE_ID)  # must not raise

        for roll_id in _ALL_ROLL_IDS:
            assert _supabase_row("rolls", "id", roll_id) is not None

    def test_does_not_raise_with_multiple_rolls_referencing_the_user(
        self, real_game_and_objective: tuple[str, str], real_user_id: str
    ):
        """Regression guard: if Supabase ever gains a strict foreign key from
        rolls to users (without ON DELETE CASCADE/SET NULL), deleting a user
        who still has rolls referencing them -- as either user1 or user2,
        across multiple rows -- would start raising here."""
        game_id, objective_id = real_game_and_objective
        SupabaseReader.dump_user(_make_fake_user(game_id, objective_id))
        for roll in _make_solo_rolls(game_id) + _make_partner_rolls(
            game_id, real_user_id
        ):
            SupabaseReader.dump_roll(roll)

        SupabaseReader.delete_user(_FAKE_CE_ID)  # must not raise
