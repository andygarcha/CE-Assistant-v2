import datetime

from Classes.CE_Game import CEGame
from Classes.CE_User import CEAPIUser
from Classes.CE_User_Game import CEUserGame
from tests.conftest import (
    make_game,
    make_objective,
    make_user,
    make_user_game,
    make_user_objective,
)
from web_scraper.scraper import update_one_user

GAME_ID = "game-001-0000-0000-000000000000"


def _game_with_points(ce_id: str, user_points: int) -> tuple[CEUserGame, CEGame]:
    """A single-PO game where the user's points exactly match the PO value,
    so it's simultaneously "completed" and worth exactly `user_points`."""
    obj = make_objective(
        ce_id=f"obj-{ce_id}",
        obj_type="Primary",
        point_value=user_points,
        name="PO",
        game_ce_id=ce_id,
    )
    db_game = make_game(ce_id=ce_id, objectives=[obj])
    uobj = make_user_objective(
        ce_id=f"obj-{ce_id}", game_ce_id=ce_id, user_points=user_points
    )
    owned = make_user_game(ce_id=ce_id, user_objectives=[uobj])
    return owned, db_game


def _api_user(owned_games: list[CEUserGame]) -> CEAPIUser:
    return CEAPIUser(
        discord_id=100000000000000000,
        ce_id="user-001-0000-0000-000000000000",
        owned_games=owned_games,
        rolls=[],
        full_data={},
        display_name="TestUser",
        avatar="",
        last_updated=datetime.datetime.now(datetime.UTC),
    )


# ── no changes ────────────────────────────────────────────────────────────────


class TestNoChanges:
    def test_identical_state_produces_no_updates(self):
        owned, db_game = _game_with_points(GAME_ID, 10)
        user = make_user(owned_games=[owned])
        site_data = _api_user([owned])
        updates = update_one_user(user, site_data, [db_game], [db_game])
        assert updates == []

    def test_empty_owned_games_produces_no_updates(self):
        user = make_user(owned_games=[])
        site_data = _api_user([])
        updates = update_one_user(user, site_data, [], [])
        assert updates == []


# ── state mutation ───────────────────────────────────────────────────────────


class TestStateMutation:
    def test_owned_games_replaced_with_site_data(self):
        old_owned, old_db = _game_with_points(GAME_ID, 10)
        new_owned, new_db = _game_with_points(GAME_ID, 20)
        user = make_user(owned_games=[old_owned])
        site_data = _api_user([new_owned])
        update_one_user(user, site_data, [old_db], [new_db])
        assert user.owned_games == [new_owned]

    def test_last_updated_is_refreshed(self):
        stale_time = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
        owned, db_game = _game_with_points(GAME_ID, 10)
        user = make_user(owned_games=[owned])
        user.set_last_updated(stale_time)
        site_data = _api_user([owned])
        update_one_user(user, site_data, [db_game], [db_game])
        assert user.last_updated > stale_time


# ── aggregation from each sub-check ──────────────────────────────────────────


class TestAggregatesRankUpdate:
    def test_rank_up_produces_an_update(self):
        # E->D rank threshold is 50 points (see RANK_THRESHOLDS).
        old_owned, old_db = _game_with_points(GAME_ID, 0)
        new_owned, new_db = _game_with_points(GAME_ID, 50)
        user = make_user(owned_games=[old_owned])
        site_data = _api_user([new_owned])
        updates = update_one_user(user, site_data, [old_db], [new_db])
        assert any("Rank" in u.text for u in updates)


class TestAggregatesCompletionCount:
    def test_crossing_25_completions_produces_an_update(self):
        old_owned = []
        old_db = []
        new_owned = []
        new_db = []
        for i in range(25):
            ce_id = f"game-{i:03d}"
            o, g = _game_with_points(ce_id, 10)
            new_owned.append(o)
            new_db.append(g)
        user = make_user(owned_games=old_owned)
        site_data = _api_user(new_owned)
        updates = update_one_user(user, site_data, old_db, new_db)
        assert any("25" in u.text for u in updates)


class TestAggregatesNewlyCompletedGames:
    def test_newly_completed_high_tier_game_produces_an_update(self):
        # 80 PO points is exactly T4, the completion-message floor.
        old_owned, old_db = [], []
        new_owned, new_db = _game_with_points(GAME_ID, 80)
        user = make_user(owned_games=old_owned)
        site_data = _api_user([new_owned])
        updates = update_one_user(user, site_data, old_db, [new_db])
        assert any("completed" in u.text.lower() for u in updates)


class TestAggregatesRoles:
    def test_crossing_category_threshold_produces_an_update(self):
        old_owned, old_db = _game_with_points(GAME_ID, 499)
        new_owned, new_db = _game_with_points(GAME_ID, 500)
        user = make_user(owned_games=[old_owned])
        site_data = _api_user([new_owned])
        updates = update_one_user(user, site_data, [old_db], [new_db])
        assert any("Expert" in u.text for u in updates)


class TestMultipleSimultaneousUpdates:
    def test_combines_updates_from_multiple_checks(self):
        # A single game jump that crosses both the D-rank threshold (50 points)
        # and completes a T4 game (80 points) should produce updates from both
        # check_rank and check_newly_completed_games in one call.
        old_owned, old_db = [], []
        new_owned, new_db = _game_with_points(GAME_ID, 80)
        user = make_user(owned_games=old_owned)
        site_data = _api_user([new_owned])
        updates = update_one_user(user, site_data, old_db, [new_db])
        assert any("Rank" in u.text for u in updates)
        assert any("completed" in u.text.lower() for u in updates)
        assert len(updates) >= 2
