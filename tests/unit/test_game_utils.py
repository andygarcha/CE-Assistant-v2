from unittest.mock import patch

import pytest

from Classes.CE_Game import CEGame
from Classes.CE_User import CEUser
from tests.conftest import (
    make_game,
    make_objective,
    make_user,
    make_user_game,
    make_user_objective,
)
from utils.game_utils import achievements_are_equal, genre_id_to_name, get_rollable_game

# ── achievements_are_equal ────────────────────────────────────────────────────


class TestAchievementsAreEqual:
    def test_both_none(self):
        assert achievements_are_equal(None, None) is True

    def test_old_none_new_populated(self):
        assert achievements_are_equal(None, ["ach1"]) is False

    def test_old_populated_new_none(self):
        assert achievements_are_equal(["ach1"], None) is False

    def test_identical_lists(self):
        assert achievements_are_equal(["ach1", "ach2"], ["ach1", "ach2"]) is True

    def test_same_elements_different_order(self):
        # order doesn't matter — comparison is set-based
        assert achievements_are_equal(["ach2", "ach1"], ["ach1", "ach2"]) is True

    def test_different_elements(self):
        assert achievements_are_equal(["ach1"], ["ach2"]) is False

    def test_subset(self):
        assert achievements_are_equal(["ach1"], ["ach1", "ach2"]) is False

    def test_empty_lists(self):
        assert achievements_are_equal([], []) is True

    def test_empty_vs_populated(self):
        assert achievements_are_equal([], ["ach1"]) is False

    def test_duplicates_treated_as_one(self):
        # sets collapse duplicates — both sides reduce to {"ach1"}, so equal
        assert achievements_are_equal(["ach1", "ach1"], ["ach1"]) is True


# ── genre_id_to_name ──────────────────────────────────────────────────────────


KNOWN_GENRES = [
    ("3c3fd562-525c-4e24-a1fa-5b5eda85ebbd", "Platformer"),
    ("4d43349a-43a8-4755-9d52-41ece63ec5b1", "Action"),
    ("7f8676fe-4900-400b-9284-c073388d88f7", "Bullet Hell"),
    ("a6d00cc0-9481-47cb-bb52-a7011041915a", "First-Person"),
    ("ec499226-0913-4db1-890e-093b366bcb3c", "Arcade"),
    ("ffb558c1-5a45-4b8c-856c-e9622ce54f00", "Strategy"),
    ("00000000-0000-0000-0000-000000000000", "Total"),
]


class TestGenreIdToName:
    @pytest.mark.parametrize("genre_id, expected", KNOWN_GENRES)
    def test_known_genres(self, genre_id, expected):
        assert genre_id_to_name(genre_id) == expected

    def test_unknown_id_returns_none(self):
        assert genre_id_to_name("ffffffff-ffff-ffff-ffff-ffffffffffff") is None

    def test_empty_string_returns_none(self):
        assert genre_id_to_name("") is None


# ── get_rollable_game ─────────────────────────────────────────────────────────
#
# Iteration model:
#   database_tier drives the candidate pool (indexed by tier + category).
#   database_name provides supplemental lookups used for the uncleared,
#   completion, points, and allow_multi_category checks.
#
# Units:
#   price in database_tier is in CENTS; price_limit is in dollars.
#   sh_hours in database_tier is in MINUTES; completion_limit is in hours.
#
# Boundary behaviour (from implementation):
#   price: game["price"] <= price_limit * 100  → at-limit is ALLOWED
#   hours: game["sh_hours"] > completion_limit * 60  → at-limit is ALLOWED

_ALL_CATS: list[str] = [
    "Action",
    "Arcade",
    "Bullet Hell",
    "First-Person",
    "Platformer",
    "Strategy",
]

GAME_A: str = "game-aaa-0000-0000-000000000000"
GAME_B: str = "game-bbb-0000-0000-000000000000"
OBJ_A: str = "obj-aaaa-0000-0000-000000000000"
OBJ_B: str = "obj-bbbb-0000-0000-000000000000"

TierEntry = dict[str, int | str]
DatabaseTier = dict[str, dict[str, list[TierEntry]]]


# safe defaults: $5.00 (500 cents), 60 minutes (1 hour)
def _tier_entry(ce_id: str, price: int = 500, sh_hours: int = 60) -> TierEntry:
    return {"ce_id": ce_id, "price": price, "sh_hours": sh_hours}


def _make_dt(
    slots: dict[tuple[int, str], list[TierEntry]] | None = None,
) -> DatabaseTier:
    """Build a full 7-tier database_tier dict with all categories initialised to [].

    `slots` maps (tier_int, category_str) → list[tier_entry].
    """
    dt: DatabaseTier = {str(t): {c: [] for c in _ALL_CATS} for t in range(1, 8)}
    if slots:
        for (tier, cat), entries in slots.items():
            dt[str(tier)][cat].extend(entries)
    return dt


def _completed_user(game_id: str, obj_id: str, points: int = 10) -> CEUser:
    """User who has fully completed `game_id` (all primary objectives done)."""
    uobj = make_user_objective(ce_id=obj_id, game_ce_id=game_id, user_points=points)
    ug = make_user_game(ce_id=game_id, user_objectives=[uobj])
    return make_user(owned_games=[ug])


def _db_game(
    ce_id: str,
    obj_id: str,
    points: int = 10,
    categories: list[str] | None = None,
) -> CEGame:
    """CEGame with one cleared primary objective worth `points`."""
    obj = make_objective(ce_id=obj_id, game_ce_id=ce_id, point_value=points)
    return make_game(ce_id=ce_id, categories=categories or ["Action"], objectives=[obj])


# Every test patches get_banned_games to avoid a real network call.
# Override the patch in specific tests that need a banned game.
@pytest.fixture(autouse=True)
def no_banned_games():
    with patch("utils.game_utils.get_banned_games", return_value=[]):
        yield


class TestGetRollableGame:
    # ── return type ───────────────────────────────────────────────────────────

    def test_returns_str_for_valid_game(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
        )
        assert result == GAME_A

    def test_returns_none_when_no_candidates(self):
        dt = _make_dt()  # all slots empty
        result = get_rollable_game(
            database_name=[],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
        )
        assert result is None

    # ── disallowed: banned games ──────────────────────────────────────────────

    def test_banned_game_excluded(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        with patch("utils.game_utils.get_banned_games", return_value=[GAME_A]):
            result = get_rollable_game(
                database_name=[game],
                database_tier=dt,
                completion_limit=None,
                price_limit=None,
                tier_number=1,
                user=make_user(),
                category="Action",
            )
        assert result is None

    def test_non_banned_game_allowed_when_other_game_is_banned(self):
        game_a = _db_game(GAME_A, OBJ_A)
        game_b = _db_game(GAME_B, OBJ_B)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A), _tier_entry(GAME_B)]})
        with patch("utils.game_utils.get_banned_games", return_value=[GAME_A]):
            result = get_rollable_game(
                database_name=[game_a, game_b],
                database_tier=dt,
                completion_limit=None,
                price_limit=None,
                tier_number=1,
                user=make_user(),
                category="Action",
            )
        assert result == GAME_B

    # ── disallowed: uncleared objective ──────────────────────────────────────
    # has_uncleared is a property that checks ALL objectives (primary and community).

    def test_game_with_uncleared_objective_excluded(self):
        uncleared = make_objective(ce_id=OBJ_A, game_ce_id=GAME_A, point_value=0)
        game = make_game(ce_id=GAME_A, categories=["Action"], objectives=[uncleared])
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
        )
        assert result is None

    def test_game_with_cleared_objectives_allowed(self):
        cleared = make_objective(ce_id=OBJ_A, game_ce_id=GAME_A, point_value=10)
        game = make_game(ce_id=GAME_A, categories=["Action"], objectives=[cleared])
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
        )
        assert result == GAME_A

    def test_game_not_in_database_name_excluded(self):
        """If database_name has no entry for a game_id, has_uncleared lookup returns
        None and the game is skipped."""
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[],  # GAME_A absent from database_name
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
        )
        assert result is None

    # ── disallowed: completed games ───────────────────────────────────────────

    def test_completed_game_excluded(self):
        game = _db_game(GAME_A, OBJ_A, points=10)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        user = _completed_user(GAME_A, OBJ_A, points=10)
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=user,
            category="Action",
        )
        assert result is None

    def test_uncompleted_game_allowed(self):
        game = _db_game(GAME_A, OBJ_A, points=10)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
        )
        assert result == GAME_A

    def test_completed_by_any_user_in_list_excluded(self):
        game = _db_game(GAME_A, OBJ_A, points=10)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        user1 = make_user(ce_id="user-001-0000-0000-000000000000")
        user2 = _completed_user(GAME_A, OBJ_A, points=10)
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=[user1, user2],
            category="Action",
        )
        assert result is None

    def test_single_user_object_accepted(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),  # single CEUser, not a list
            category="Action",
        )
        assert result == GAME_A

    def test_list_of_users_accepted(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=[make_user()],
            category="Action",
        )
        assert result == GAME_A

    # ── completion_limit / hours_restriction ──────────────────────────────────
    # sh_hours is in MINUTES; completion_limit is in HOURS.
    # Check: sh_hours > completion_limit * 60  → excluded.
    # At-limit (sh_hours == completion_limit * 60) is ALLOWED.

    def test_game_below_completion_limit_included(self):
        game = _db_game(GAME_A, OBJ_A)
        # 299 min < 5h (300 min) → allowed
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, sh_hours=299)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=5,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
            hours_restriction=True,
        )
        assert result == GAME_A

    def test_game_at_completion_limit_allowed(self):
        game = _db_game(GAME_A, OBJ_A)
        # 300 min == 5h (300 min) → NOT > 300, so allowed
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, sh_hours=300)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=5,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
            hours_restriction=True,
        )
        assert result == GAME_A

    def test_game_above_completion_limit_excluded(self):
        game = _db_game(GAME_A, OBJ_A)
        # 301 min > 5h (300 min) → excluded
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, sh_hours=301)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=5,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
            hours_restriction=True,
        )
        assert result is None

    def test_hours_restriction_false_ignores_completion_limit(self):
        game = _db_game(GAME_A, OBJ_A)
        # way above limit, but restriction is off
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, sh_hours=99999)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=5,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
            hours_restriction=False,
        )
        assert result == GAME_A

    def test_completion_limit_none_no_hours_cap(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, sh_hours=99999)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
            hours_restriction=True,
        )
        assert result == GAME_A

    # ── price_limit / price_restriction ───────────────────────────────────────
    # price in database_tier is in CENTS; price_limit is in dollars.
    # Check: game["price"] <= price_limit * 100  → allowed (NOT excluded).
    # Equivalently: game["price"] > price_limit * 100  → excluded (unless user owns game).
    # At-limit (price == price_limit * 100 cents) is ALLOWED.

    def test_game_below_price_limit_included(self):
        game = _db_game(GAME_A, OBJ_A)
        # $9.99 (999 cents) < $10 limit → allowed
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, price=999)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=10,
            tier_number=1,
            user=make_user(),
            category="Action",
            price_restriction=True,
        )
        assert result == GAME_A

    def test_game_at_price_limit_allowed(self):
        game = _db_game(GAME_A, OBJ_A)
        # $10.00 (1000 cents) == $10 limit → 1000 <= 1000, so allowed
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, price=1000)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=10,
            tier_number=1,
            user=make_user(),
            category="Action",
            price_restriction=True,
        )
        assert result == GAME_A

    def test_game_above_price_limit_excluded(self):
        game = _db_game(GAME_A, OBJ_A)
        # $10.01 (1001 cents) > $10 limit → excluded (user doesn't own it)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, price=1001)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=10,
            tier_number=1,
            user=make_user(),
            category="Action",
            price_restriction=True,
        )
        assert result is None

    def test_price_restriction_false_ignores_price_limit(self):
        game = _db_game(GAME_A, OBJ_A)
        # way over limit, but restriction is off
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, price=99999)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=10,
            tier_number=1,
            user=make_user(),
            category="Action",
            price_restriction=False,
        )
        assert result == GAME_A

    def test_price_limit_none_no_price_cap(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, price=99999)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
            price_restriction=True,
        )
        assert result == GAME_A

    def test_expensive_game_allowed_if_user_owns_it(self):
        """Price limit is bypassed when the user already owns the game."""
        game = _db_game(GAME_A, OBJ_A, points=10)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A, price=5999)]})
        uobj = make_user_objective(ce_id=OBJ_A, game_ce_id=GAME_A, user_points=5)
        ug = make_user_game(ce_id=GAME_A, user_objectives=[uobj])
        user = make_user(owned_games=[ug])
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=10,
            tier_number=1,
            user=user,
            category="Action",
            price_restriction=True,
        )
        assert result == GAME_A

    # ── tier_number ───────────────────────────────────────────────────────────

    def test_correct_tier_returned(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(3, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=3,
            user=make_user(),
            category="Action",
        )
        assert result == GAME_A

    def test_game_absent_from_searched_tier_not_returned(self):
        """database_tier is the candidate pool; a game only in tier 3 is invisible
        when tier_number=2 is requested."""
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(3, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=2,
            user=make_user(),
            category="Action",
        )
        assert result is None

    def test_tier_none_searches_all_tiers(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(4, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=None,
            user=make_user(),
            category="Action",
        )
        assert result == GAME_A

    @pytest.mark.parametrize("tier", [5, 6, 7])
    def test_tier_6_allows_t5_t6_t7(self, tier):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(tier, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=6,
            user=make_user(),
            category="Action",
        )
        assert result == GAME_A

    def test_tier_6_excludes_t4(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(4, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=6,
            user=make_user(),
            category="Action",
        )
        assert result is None

    # ── category ─────────────────────────────────────────────────────────────
    # Category filtering is purely structural: only entries in the requested
    # database_tier[tier][category] slot are considered.

    def test_category_string_filters_correctly(self):
        game = _db_game(GAME_A, OBJ_A, categories=["Strategy"])
        dt = _make_dt({(1, "Strategy"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Strategy",
        )
        assert result == GAME_A

    def test_category_list_filters_correctly(self):
        game = _db_game(GAME_A, OBJ_A, categories=["Platformer"])
        dt = _make_dt({(1, "Platformer"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category=["Platformer"],
        )
        assert result == GAME_A

    def test_category_none_searches_all_categories(self):
        game = _db_game(GAME_A, OBJ_A, categories=["Bullet Hell"])
        dt = _make_dt({(1, "Bullet Hell"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category=None,
        )
        assert result == GAME_A

    def test_game_absent_from_searched_category_not_returned(self):
        """A game only in the 'Action' slot is invisible when 'Arcade' is requested."""
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Arcade",
        )
        assert result is None

    # ── already_rolled_games ──────────────────────────────────────────────────

    def test_already_rolled_game_excluded(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
            already_rolled_games=[GAME_A],
        )
        assert result is None

    def test_already_rolled_excludes_only_listed_games(self):
        game_a = _db_game(GAME_A, OBJ_A)
        game_b = _db_game(GAME_B, OBJ_B)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A), _tier_entry(GAME_B)]})
        result = get_rollable_game(
            database_name=[game_a, game_b],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
            already_rolled_games=[GAME_A],
        )
        assert result == GAME_B

    # ── has_points_restriction ────────────────────────────────────────────────

    def test_has_points_restriction_excludes_game_with_user_points(self):
        game = _db_game(GAME_A, OBJ_A, points=10)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        uobj = make_user_objective(ce_id=OBJ_A, game_ce_id=GAME_A, user_points=5)
        ug = make_user_game(ce_id=GAME_A, user_objectives=[uobj])
        user = make_user(owned_games=[ug])
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=user,
            category="Action",
            has_points_restriction=True,
        )
        assert result is None

    def test_has_points_restriction_false_allows_game_with_points(self):
        game = _db_game(GAME_A, OBJ_A, points=10)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        uobj = make_user_objective(ce_id=OBJ_A, game_ce_id=GAME_A, user_points=5)
        ug = make_user_game(ce_id=GAME_A, user_objectives=[uobj])
        user = make_user(owned_games=[ug])
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=user,
            category="Action",
            has_points_restriction=False,
        )
        assert result == GAME_A

    def test_has_points_restriction_allows_game_with_no_points(self):
        game = _db_game(GAME_A, OBJ_A)
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
            has_points_restriction=True,
        )
        assert result == GAME_A

    # ── allow_multi_category ──────────────────────────────────────────────────

    def test_multi_category_game_excluded_when_flag_false(self):
        game = make_game(ce_id=GAME_A, categories=["Action", "Arcade"])
        dt = _make_dt(
            {
                (1, "Action"): [_tier_entry(GAME_A)],
                (1, "Arcade"): [_tier_entry(GAME_A)],
            }
        )
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category=None,
            allow_multi_category=False,
        )
        assert result is None

    def test_multi_category_game_allowed_when_flag_true(self):
        game = make_game(ce_id=GAME_A, categories=["Action", "Arcade"])
        dt = _make_dt(
            {
                (1, "Action"): [_tier_entry(GAME_A)],
                (1, "Arcade"): [_tier_entry(GAME_A)],
            }
        )
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category=None,
            allow_multi_category=True,
        )
        assert result == GAME_A

    def test_single_category_game_unaffected_by_multi_category_flag(self):
        game = _db_game(GAME_A, OBJ_A, categories=["Action"])
        dt = _make_dt({(1, "Action"): [_tier_entry(GAME_A)]})
        result = get_rollable_game(
            database_name=[game],
            database_tier=dt,
            completion_limit=None,
            price_limit=None,
            tier_number=1,
            user=make_user(),
            category="Action",
            allow_multi_category=False,
        )
        assert result == GAME_A

    # ── combined filter interactions ──────────────────────────────────────────

    def test_only_valid_game_returned_when_other_filtered_by_price(self):
        game_a = _db_game(GAME_A, OBJ_A)
        game_b = _db_game(GAME_B, OBJ_B)
        dt = _make_dt(
            {
                # GAME_A: $50.00 (5000 cents) > $10 limit → excluded
                # GAME_B: $5.00 (500 cents) < $10 limit → allowed
                (1, "Action"): [
                    _tier_entry(GAME_A, price=5000),
                    _tier_entry(GAME_B, price=500),
                ],
            }
        )
        result = get_rollable_game(
            database_name=[game_a, game_b],
            database_tier=dt,
            completion_limit=None,
            price_limit=10,
            tier_number=1,
            user=make_user(),
            category="Action",
            price_restriction=True,
        )
        assert result == GAME_B

    def test_all_filters_combined_returns_only_match(self):
        game_a = _db_game(GAME_A, OBJ_A, categories=["Arcade"])
        game_b = _db_game(GAME_B, OBJ_B, categories=["Action"])
        dt = _make_dt(
            {
                # GAME_A: $5.00 (500 cents), 3h (180 min) → passes both limits
                (2, "Arcade"): [_tier_entry(GAME_A, price=500, sh_hours=180)],
                # GAME_B: $30.00 (3000 cents) → fails $10 price limit
                (2, "Action"): [_tier_entry(GAME_B, price=3000, sh_hours=180)],
            }
        )
        result = get_rollable_game(
            database_name=[game_a, game_b],
            database_tier=dt,
            completion_limit=10,
            price_limit=10,
            tier_number=2,
            user=make_user(),
            category=None,
            price_restriction=True,
            hours_restriction=True,
        )
        assert result == GAME_A
