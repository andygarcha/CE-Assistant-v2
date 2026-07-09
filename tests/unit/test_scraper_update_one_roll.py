import datetime
from typing import cast

import pytest

from Classes.CE_Game import CEGame
from Classes.CE_Roll import CERoll
from Classes.CE_User import MUTELIST_CEIDS
from tests.conftest import (
    make_game,
    make_objective,
    make_roll,
    make_user,
    make_user_game,
    make_user_objective,
)
from web_scraper.scraper import UpdateMessageForScraperProcess, update_one_roll

GAME_ID = "game-001-0000-0000-000000000000"
ROLL_NAME = "One Hell of a Day"
MUTED_CE_ID = MUTELIST_CEIDS[0]
OBJ_ID = "obj-0001-0000-0000-000000000000"


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _past(minutes: int = 10) -> datetime.datetime:
    return _now() - datetime.timedelta(minutes=minutes)


def _future(minutes: int = 10) -> datetime.datetime:
    return _now() + datetime.timedelta(minutes=minutes)


def _pending(due_time: datetime.datetime | None = None):
    return make_roll(
        roll_name=ROLL_NAME,
        status="pending",
        due_time=due_time if due_time is not None else _future(),
        games=[GAME_ID],
    )


def _roll(status: str):
    return make_roll(roll_name=ROLL_NAME, status=status, games=[GAME_ID])


def _expired_current():
    return make_roll(
        roll_name=ROLL_NAME, status="current", due_time=_past(), games=[GAME_ID]
    )


def _user():
    return make_user()


def _muted_user():
    return make_user(ce_id=MUTED_CE_ID)


def _games():
    return [make_game(ce_id=GAME_ID)]


# ── Return shape ──────────────────────────────────────────────────────────────


class TestUpdateOneRollReturnShape:
    def test_returns_tuple(self):
        result = update_one_roll(_pending(), _user(), None, _games())
        assert isinstance(result, tuple)

    def test_returns_three_elements(self):
        result = update_one_roll(_pending(), _user(), None, _games())
        assert len(result) == 3

    def test_first_element_is_update_or_none(self):
        update, _, __ = update_one_roll(_pending(), _user(), None, _games())
        assert update is None or isinstance(update, UpdateMessageForScraperProcess)

    def test_second_element_is_roll_or_none(self):
        _, roll_updated, __ = update_one_roll(_pending(), _user(), None, _games())
        assert roll_updated is None or isinstance(roll_updated, CERoll)

    def test_third_element_is_bool(self):
        _, __, delete_pending = update_one_roll(_pending(), _user(), None, _games())
        assert isinstance(delete_pending, bool)

    def test_shape_is_consistent_for_current_roll(self):
        result = update_one_roll(_roll("current"), _user(), None, _games())
        assert isinstance(result, tuple) and len(result) == 3


# ── delete_pending — pending rolls ────────────────────────────────────────────


class TestDeletePendingForPendingRolls:
    def test_unexpired_pending_is_false(self):
        _, __, delete_pending = update_one_roll(
            _pending(_future()), _user(), None, _games()
        )
        assert delete_pending is False

    def test_expired_pending_is_true(self):
        _, __, delete_pending = update_one_roll(
            _pending(_past()), _user(), None, _games()
        )
        assert delete_pending is True

    def test_just_expired_one_second_ago_is_true(self):
        just_expired = _now() - datetime.timedelta(seconds=1)
        _, __, delete_pending = update_one_roll(
            _pending(just_expired), _user(), None, _games()
        )
        assert delete_pending is True

    def test_expiring_far_future_is_false(self):
        far_future = _now() + datetime.timedelta(days=365)
        _, __, delete_pending = update_one_roll(
            _pending(far_future), _user(), None, _games()
        )
        assert delete_pending is False

    def test_expired_long_ago_is_true(self):
        long_past = _now() - datetime.timedelta(hours=24)
        _, __, delete_pending = update_one_roll(
            _pending(long_past), _user(), None, _games()
        )
        assert delete_pending is True

    def test_pending_no_due_time_is_false(self):
        # No due_time means it never expires
        roll = make_roll(
            roll_name="Never Lucky", status="pending", due_time=None, games=[GAME_ID]
        )
        _, __, delete_pending = update_one_roll(roll, _user(), None, _games())
        assert delete_pending is False


# ── delete_pending — non-pending statuses always False ────────────────────────


class TestDeletePendingAlwaysFalseForNonPending:
    @pytest.mark.parametrize(
        "status",
        ["current", "won", "failed", "between_stages", "removed", "won_legacy"],
    )
    def test_non_pending_status_never_sets_delete_pending(self, status):
        _, __, delete_pending = update_one_roll(_roll(status), _user(), None, _games())
        assert delete_pending is False


# ── roll_updated semantics for pending rolls ──────────────────────────────────


class TestRollUpdatedForPendingRolls:
    def test_unexpired_pending_has_no_roll_updated(self):
        _, roll_updated, __ = update_one_roll(
            _pending(_future()), _user(), None, _games()
        )
        assert roll_updated is None

    def test_expired_pending_has_no_roll_updated(self):
        # Expired pending is deleted, not modified — roll_updated should be None
        _, roll_updated, __ = update_one_roll(
            _pending(_past()), _user(), None, _games()
        )
        assert roll_updated is None


# ── Pending rolls with a partner (user2) ─────────────────────────────────────


class TestPendingRollWithUser2:
    def test_unexpired_pending_with_partner_delete_pending_false(self):
        user2 = make_user(ce_id="user-002-0000-0000-000000000000")
        _, __, delete_pending = update_one_roll(
            _pending(_future()), _user(), user2, _games()
        )
        assert delete_pending is False

    def test_expired_pending_with_partner_delete_pending_true(self):
        user2 = make_user(ce_id="user-002-0000-0000-000000000000")
        _, __, delete_pending = update_one_roll(
            _pending(_past()), _user(), user2, _games()
        )
        assert delete_pending is True

    def test_pending_with_partner_returns_three_tuple(self):
        user2 = make_user(ce_id="user-002-0000-0000-000000000000")
        result = update_one_roll(_pending(_future()), _user(), user2, _games())
        assert isinstance(result, tuple) and len(result) == 3


# ── user2=None is valid for solo rolls ───────────────────────────────────────


class TestSoloRollUser2None:
    def test_current_roll_solo_does_not_crash(self):
        result = update_one_roll(_roll("current"), _user(), None, _games())
        assert isinstance(result, tuple)

    def test_pending_roll_solo_does_not_crash(self):
        result = update_one_roll(_pending(_future()), _user(), None, _games())
        assert isinstance(result, tuple)


# ── Muted user1 ───────────────────────────────────────────────────────────────


class TestMutedUser:
    def test_muted_user_pending_expired_still_sets_delete_pending_true(self):
        _, __, delete_pending = update_one_roll(
            _pending(_past()), _muted_user(), None, _games()
        )
        assert delete_pending is True

    def test_muted_user_pending_unexpired_still_false(self):
        _, __, delete_pending = update_one_roll(
            _pending(_future()), _muted_user(), None, _games()
        )
        assert delete_pending is False

    def test_muted_user_expired_roll_goes_to_casino_not_privatelog(self):
        # update_one_roll routes casino messages to "casino"/"casinolog", never "privatelog"
        # (privatelog routing is for scraper notifications like check_rank, not roll outcomes)
        update, _, __ = update_one_roll(
            _expired_current(), _muted_user(), None, _games()
        )
        assert update is not None
        assert update.location != "privatelog"

    def test_non_muted_user_expired_roll_goes_to_casino_not_privatelog(self):
        update, _, __ = update_one_roll(_expired_current(), _user(), None, _games())
        assert update is not None
        assert update.location != "privatelog"


# ── Update message — basic guarantees ────────────────────────────────────────


class TestUpdateMessageGuarantees:
    def test_unexpired_pending_produces_no_update(self):
        update, _, __ = update_one_roll(_pending(_future()), _user(), None, _games())
        assert update is None

    def test_expired_roll_update_has_location_set(self):
        update, _, __ = update_one_roll(_expired_current(), _user(), None, _games())
        assert update is not None
        assert update.location is not None

    def test_expired_roll_update_is_embed_is_bool(self):
        update, _, __ = update_one_roll(_expired_current(), _user(), None, _games())
        assert update is not None
        assert isinstance(update.is_embed, bool)


# ── Removed game in roll ─────────────────────────────────────────────────────

# update_one_roll's signature declares `games: list[CEGame]`, but its body
# explicitly checks `if None in games` to handle a game being removed from
# the site out from under an in-progress roll. This helper documents that
# real, intentional gap rather than silencing it with a bare type: ignore
# at every call site.
_games_with_removed_slot: list[CEGame] = cast("list[CEGame]", [None])


class TestRemovedGameInRoll:
    def test_none_in_games_marks_roll_removed(self):
        roll = _roll("current")
        update, roll_updated, delete_pending = update_one_roll(
            roll, _user(), None, _games_with_removed_slot
        )
        assert update is not None
        assert roll_updated is not None
        assert roll_updated.status == "removed"
        assert delete_pending is False

    def test_none_in_games_update_goes_to_casino(self):
        update, _, __ = update_one_roll(
            _roll("current"), _user(), None, _games_with_removed_slot
        )
        assert update is not None
        assert update.location == "casino"

    def test_none_in_games_mentions_partner_when_present(self):
        update, _, __ = update_one_roll(
            _roll("current"), _user(), _user(), _games_with_removed_slot
        )
        assert update is not None
        assert "and" in update.text


# ── Won rolls ─────────────────────────────────────────────────────────────────


def _completed_user(game_id: str, points: int = 100):
    uobj = make_user_objective(ce_id=OBJ_ID, game_ce_id=game_id, user_points=points)
    ug = make_user_game(ce_id=game_id, user_objectives=[uobj])
    return make_user(owned_games=[ug])


def _db_game(game_id: str, points: int = 100):
    obj = make_objective(
        ce_id=OBJ_ID, point_value=points, obj_type="Primary", game_ce_id=game_id
    )
    return make_game(ce_id=game_id, objectives=[obj])


class TestWonSoloRoll:
    def test_won_roll_is_marked_won(self):
        roll = make_roll(roll_name="One Hell of a Day", games=[GAME_ID])
        user = _completed_user(GAME_ID)
        game = _db_game(GAME_ID)
        update, roll_updated, delete_pending = update_one_roll(roll, user, None, [game])
        assert update is not None
        assert roll_updated is not None
        assert roll_updated.status == "won"
        assert delete_pending is False

    def test_won_roll_sets_completed_time(self):
        roll = make_roll(roll_name="One Hell of a Day", games=[GAME_ID])
        user = _completed_user(GAME_ID)
        game = _db_game(GAME_ID)
        _, roll_updated, __ = update_one_roll(roll, user, None, [game])
        assert roll_updated is not None
        assert roll_updated.completed_time is not None

    def test_won_roll_update_goes_to_casinolog(self):
        roll = make_roll(roll_name="One Hell of a Day", games=[GAME_ID])
        user = _completed_user(GAME_ID)
        game = _db_game(GAME_ID)
        update, __, ___ = update_one_roll(roll, user, None, [game])
        assert update is not None
        assert update.location == "casinolog"


class TestWonMultiStageNotFinal:
    def test_non_final_stage_win_sets_between_stages(self):
        # "Fourward Thinking" is multi-stage; a single-game roll is not its
        # final stage (final stage requires 4 games).
        roll = make_roll(roll_name="Fourward Thinking", games=[GAME_ID])
        user = _completed_user(GAME_ID)
        game = _db_game(GAME_ID)
        update, roll_updated, delete_pending = update_one_roll(roll, user, None, [game])
        assert update is not None
        assert roll_updated is not None
        assert roll_updated.status == "between_stages"
        assert roll_updated.due_time is None
        assert delete_pending is False

    def test_non_final_stage_win_update_goes_to_casino(self):
        roll = make_roll(roll_name="Fourward Thinking", games=[GAME_ID])
        user = _completed_user(GAME_ID)
        game = _db_game(GAME_ID)
        update, __, ___ = update_one_roll(roll, user, None, [game])
        assert update is not None
        assert update.location == "casino"
