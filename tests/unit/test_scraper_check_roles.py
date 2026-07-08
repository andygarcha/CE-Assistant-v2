import pytest

from Classes.CE_Game import CEGame
from Classes.CE_User_Game import CEUserGame
from tests.conftest import (
    make_game,
    make_objective,
    make_user,
    make_user_game,
    make_user_objective,
)
from web_scraper.scraper import check_roles

GAME_ID = "game-001-0000-0000-000000000000"


def _user(display_name: str = "TestUser"):
    return make_user(ce_id="user-001-0000-0000-000000000000", display_name=display_name)


def _game_with_points(
    ce_id: str, user_points: int, categories: list | None = None
) -> tuple[CEUserGame, CEGame]:
    """A single-PO game where the user's points exactly match the PO value
    (so it's simultaneously "completed" and contributes `user_points` to
    that category, regardless of tier)."""
    obj = make_objective(
        ce_id=f"obj-{ce_id}",
        obj_type="Primary",
        point_value=user_points,
        name="PO",
        game_ce_id=ce_id,
    )
    db_game = make_game(
        ce_id=ce_id, objectives=[obj], categories=categories or ["Action"]
    )
    uobj = make_user_objective(
        ce_id=f"obj-{ce_id}", game_ce_id=ce_id, user_points=user_points
    )
    owned = make_user_game(ce_id=ce_id, user_objectives=[uobj])
    return owned, db_game


def _n_completed_games(
    n: int, po_points: int, prefix: str
) -> tuple[list[CEUserGame], list[CEGame]]:
    """`n` distinct, fully-completed games each worth `po_points`, so their
    combined contribution to a tier bucket is `n * po_points`."""
    owned: list[CEUserGame] = []
    db: list[CEGame] = []
    for i in range(n):
        ce_id = f"{prefix}-{i:04d}"
        o, g = _game_with_points(ce_id, po_points)
        owned.append(o)
        db.append(g)
    return owned, db


# ── category threshold crossings (Expert/Master/Grandmaster) ────────────────


class TestCategoryThresholdCrossing:
    @pytest.mark.parametrize(
        ("threshold", "role_name"),
        [(500, "Expert"), (1000, "Master"), (2000, "Grandmaster")],
    )
    def test_crossing_threshold_sends_message(self, threshold, role_name):
        old_owned, old_db = _game_with_points(GAME_ID, threshold - 1)
        new_owned, new_db = _game_with_points(GAME_ID, threshold)
        updates = check_roles([old_owned], [new_owned], [old_db], [new_db], _user())
        assert any(
            "Action" in u.text and role_name in u.text and str(threshold) in u.text
            for u in updates
        )

    @pytest.mark.parametrize("threshold", [500, 1000, 2000])
    def test_staying_under_threshold_sends_no_message(self, threshold):
        owned, db = _game_with_points(GAME_ID, threshold - 1)
        updates = check_roles([owned], [owned], [db], [db], _user())
        assert updates == []

    @pytest.mark.parametrize("threshold", [500, 1000, 2000])
    def test_already_past_threshold_sends_no_duplicate_message(self, threshold):
        old_owned, old_db = _game_with_points(GAME_ID, threshold)
        new_owned, new_db = _game_with_points(GAME_ID, threshold + 100)
        updates = check_roles([old_owned], [new_owned], [old_db], [new_db], _user())
        assert updates == []

    def test_category_role_message_mentions_user(self):
        user = _user("CategoryChamp")
        old_owned, old_db = _game_with_points(GAME_ID, 499)
        new_owned, new_db = _game_with_points(GAME_ID, 500)
        updates = check_roles([old_owned], [new_owned], [old_db], [new_db], user)
        assert len(updates) == 1
        assert user.mention() in updates[0].text
        assert user.display_name_with_link() in updates[0].text

    def test_category_role_message_is_not_embed(self):
        old_owned, old_db = _game_with_points(GAME_ID, 499)
        new_owned, new_db = _game_with_points(GAME_ID, 500)
        updates = check_roles([old_owned], [new_owned], [old_db], [new_db], _user())
        assert updates[0].is_embed is False

    def test_category_role_message_goes_to_userlog(self):
        old_owned, old_db = _game_with_points(GAME_ID, 499)
        new_owned, new_db = _game_with_points(GAME_ID, 500)
        updates = check_roles([old_owned], [new_owned], [old_db], [new_db], _user())
        assert updates[0].location == "userlog"

    def test_different_category_tracked_independently(self):
        old_owned, old_db = _game_with_points(GAME_ID, 499, categories=["Arcade"])
        new_owned, new_db = _game_with_points(GAME_ID, 500, categories=["Arcade"])
        updates = check_roles([old_owned], [new_owned], [old_db], [new_db], _user())
        assert any("Arcade" in u.text for u in updates)


# ── tier threshold crossings (Tier N Enthusiast) ─────────────────────────────

# PO point values chosen to stay inside each tier's own range (see
# Classes/CE_Game.py TIER_THRESHOLDS) so a completed game of that value
# actually counts as that tier.
_TIER_PO_POINTS = {1: 19, 2: 39, 3: 79, 4: 199}


class TestTierThresholdCrossing:
    @pytest.mark.parametrize("tier", [1, 2, 3, 4])
    def test_crossing_tier_threshold_sends_message(self, tier):
        po = _TIER_PO_POINTS[tier]
        threshold = tier * 500
        old_count = threshold // po
        new_count = old_count + 1
        old_owned, old_db = _n_completed_games(old_count, po, f"t{tier}old")
        new_owned, new_db = _n_completed_games(new_count, po, f"t{tier}new")
        updates = check_roles(old_owned, new_owned, old_db, new_db, _user())
        assert any(f"Tier {tier} Enthusiast" in u.text for u in updates)

    @pytest.mark.parametrize("tier", [1, 2, 3, 4])
    def test_staying_under_tier_threshold_sends_no_message(self, tier):
        po = _TIER_PO_POINTS[tier]
        threshold = tier * 500
        count = threshold // po
        owned, db = _n_completed_games(count, po, f"t{tier}stay")
        updates = check_roles(owned, owned, db, db, _user())
        assert not any(f"Tier {tier} Enthusiast" in u.text for u in updates)

    def test_incomplete_game_does_not_contribute_to_tier(self):
        # Same PO value as the completed case, but the user hasn't finished it
        # (0 user points) -- should not count toward the tier bucket at all.
        obj = make_objective(
            ce_id="obj-incomplete",
            obj_type="Primary",
            point_value=500,
            name="PO",
            game_ce_id=GAME_ID,
        )
        db_game = make_game(ce_id=GAME_ID, objectives=[obj], categories=["Action"])
        uobj = make_user_objective(
            ce_id="obj-incomplete", game_ce_id=GAME_ID, user_points=0
        )
        owned = make_user_game(ce_id=GAME_ID, user_objectives=[uobj])
        updates = check_roles([], [owned], [], [db_game], _user())
        assert not any("Tier" in u.text and "Enthusiast" in u.text for u in updates)

    def test_t0_game_does_not_crash_or_grant_tier_role(self):
        # A T0 game (0 PO points) means tier_num - 1 == -1, which indexes the
        # *last* slot of the internal tiers array instead of raising or being
        # ignored. That internal array isn't exposed here, so this test can
        # only confirm the externally-visible behavior (no crash, no spurious
        # role message) -- it does not prove the -1 indexing is harmless in
        # general, only that it's harmless today because only indices 0-3 are
        # ever read back out by the TIERS loop below.
        obj = make_objective(
            ce_id="obj-t0",
            obj_type="Primary",
            point_value=0,
            name="PO",
            game_ce_id=GAME_ID,
        )
        db_game = make_game(ce_id=GAME_ID, objectives=[obj], categories=["Action"])
        uobj = make_user_objective(ce_id="obj-t0", game_ce_id=GAME_ID, user_points=0)
        owned = make_user_game(ce_id=GAME_ID, user_objectives=[uobj])
        updates = check_roles([], [owned], [], [db_game], _user())
        assert not any("Enthusiast" in u.text for u in updates)


# ── games missing from the database ──────────────────────────────────────────


class TestGameNotInDatabase:
    def test_owned_game_with_no_matching_new_database_entry_is_skipped(self):
        uobj = make_user_objective(
            ce_id="obj-orphan", game_ce_id=GAME_ID, user_points=500
        )
        owned = make_user_game(ce_id=GAME_ID, user_objectives=[uobj])
        # database_name_new has no entry for GAME_ID at all.
        updates = check_roles([], [owned], [], [], _user())
        assert updates == []

    def test_owned_game_with_no_matching_old_database_entry_is_skipped(self):
        uobj = make_user_objective(
            ce_id="obj-orphan", game_ce_id=GAME_ID, user_points=500
        )
        owned = make_user_game(ce_id=GAME_ID, user_objectives=[uobj])
        # database_name_old has no entry for GAME_ID at all; games_new is
        # empty too, so this only exercises the games_old skip branch.
        updates = check_roles([owned], [], [], [], _user())
        assert updates == []


# ── conglomerate roles ───────────────────────────────────────────────────────


class TestMasterOfAll:
    def test_crossing_500_in_every_category_sends_message(self):
        categories = [
            "Action",
            "Arcade",
            "Bullet Hell",
            "First-Person",
            "Platformer",
            "Strategy",
        ]
        old_owned, old_db, new_owned, new_db = [], [], [], []
        for i, cat in enumerate(categories):
            ce_id = f"moa-{i}"
            o_old, g_old = _game_with_points(ce_id, 499, categories=[cat])
            o_new, g_new = _game_with_points(ce_id, 500, categories=[cat])
            old_owned.append(o_old)
            old_db.append(g_old)
            new_owned.append(o_new)
            new_db.append(g_new)
        updates = check_roles(old_owned, new_owned, old_db, new_db, _user())
        assert any(
            "Master of All" in u.text and "Grandm" not in u.text for u in updates
        )

    def test_all_but_one_category_at_500_sends_no_message(self):
        categories = ["Action", "Arcade", "Bullet Hell", "First-Person", "Platformer"]
        old_owned, old_db, new_owned, new_db = [], [], [], []
        for i, cat in enumerate(categories):
            ce_id = f"moa-partial-{i}"
            o_old, g_old = _game_with_points(ce_id, 499, categories=[cat])
            o_new, g_new = _game_with_points(ce_id, 500, categories=[cat])
            old_owned.append(o_old)
            old_db.append(g_old)
            new_owned.append(o_new)
            new_db.append(g_new)
        # "Strategy" (the 6th category) is never touched, so min(new_categories) stays 0.
        updates = check_roles(old_owned, new_owned, old_db, new_db, _user())
        assert not any("Master of All" in u.text for u in updates)


class TestOverpowered:
    def test_crossing_3000_in_a_single_category_sends_message(self):
        old_owned, old_db = _game_with_points(GAME_ID, 2999)
        new_owned, new_db = _game_with_points(GAME_ID, 3000)
        updates = check_roles([old_owned], [new_owned], [old_db], [new_db], _user())
        assert any("Overpowered" in u.text for u in updates)

    def test_staying_under_3000_sends_no_message(self):
        owned, db = _game_with_points(GAME_ID, 2999)
        updates = check_roles([owned], [owned], [db], [db], _user())
        assert not any("Overpowered" in u.text for u in updates)


class TestNoChangesProducesNoUpdates:
    def test_empty_input_produces_no_updates(self):
        assert check_roles([], [], [], [], _user()) == []
