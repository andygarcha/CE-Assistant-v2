import pytest

from Classes.CE_Game import CEGame
from Classes.CE_User_Game import CEUserGame
from tests.conftest import (
    make_game,
    make_objective,
    make_user_game,
    make_user_objective,
)
from utils.game_utils import (
    CATEGORY_COUNT,
    TIER_COUNT,
    compute_role_points,
    t5_plus_points,
)

# PO point values that land inside each tier's own band, per the
# TIER_THRESHOLDS table in Classes/CE_Game.py.
TIER_PO_POINTS = {1: 10, 2: 25, 3: 50, 4: 100, 5: 250, 6: 500, 7: 900}


def _completed_game(
    ce_id: str, po_points: int, categories: list | None = None
) -> tuple[CEUserGame, CEGame]:
    """A single-PO game the user has fully completed, so it contributes
    `po_points` to the tier that `po_points` puts it in."""
    obj = make_objective(
        ce_id=f"obj-{ce_id}",
        obj_type="Primary",
        point_value=po_points,
        name="PO",
        game_ce_id=ce_id,
    )
    db_game = make_game(
        ce_id=ce_id, objectives=[obj], categories=categories or ["Action"]
    )
    uobj = make_user_objective(
        ce_id=f"obj-{ce_id}", game_ce_id=ce_id, user_points=po_points
    )
    return make_user_game(ce_id=ce_id, user_objectives=[uobj]), db_game


def _overcompleted_game(
    ce_id: str, po_points: int, so_points: int
) -> tuple[CEUserGame, CEGame]:
    """A game with one PO and one SO, both fully completed by the user."""
    po = make_objective(
        ce_id=f"po-{ce_id}",
        obj_type="Primary",
        point_value=po_points,
        name="PO",
        game_ce_id=ce_id,
    )
    so = make_objective(
        ce_id=f"so-{ce_id}",
        obj_type="Secondary",
        point_value=so_points,
        name="SO",
        game_ce_id=ce_id,
    )
    db_game = make_game(ce_id=ce_id, objectives=[po, so], categories=["Action"])
    user_po = make_user_objective(
        ce_id=f"po-{ce_id}",
        game_ce_id=ce_id,
        obj_type="Primary",
        user_points=po_points,
    )
    user_so = make_user_objective(
        ce_id=f"so-{ce_id}",
        game_ce_id=ce_id,
        obj_type="Secondary",
        user_points=so_points,
    )
    owned = make_user_game(ce_id=ce_id, user_objectives=[user_po, user_so])
    return owned, db_game


class TestShape:
    def test_empty_input_returns_zeroed_lists(self):
        points = compute_role_points([], [])
        assert points.tiers == [0] * TIER_COUNT
        assert points.categories == [0] * CATEGORY_COUNT

    def test_is_unpackable_as_tiers_then_categories(self):
        # check_roles unpacks the result positionally, so order matters.
        tiers, categories = compute_role_points([], [])
        assert tiers == [0] * TIER_COUNT
        assert categories == [0] * CATEGORY_COUNT


class TestTierPoints:
    @pytest.mark.parametrize("tier", [1, 2, 3, 4, 5, 6, 7])
    def test_completed_game_adds_primary_points_to_its_tier(self, tier):
        po_points = TIER_PO_POINTS[tier]
        owned, db_game = _completed_game("g1", po_points)

        tiers = compute_role_points([owned], [db_game]).tiers

        assert tiers[tier - 1] == po_points
        # and nothing landed anywhere else
        assert sum(tiers) == po_points

    def test_incomplete_game_contributes_nothing_to_tiers(self):
        obj = make_objective(
            ce_id="obj-incomplete",
            obj_type="Primary",
            point_value=100,
            name="PO",
            game_ce_id="g1",
        )
        db_game = make_game(ce_id="g1", objectives=[obj], categories=["Action"])
        uobj = make_user_objective(
            ce_id="obj-incomplete", game_ce_id="g1", user_points=0
        )
        owned = make_user_game(ce_id="g1", user_objectives=[uobj])

        assert compute_role_points([owned], [db_game]).tiers == [0] * TIER_COUNT

    def test_overcompleted_game_uses_tier_including_secondaries(self):
        # 100 PO points alone is a T4; adding a 150-point SO pushes the
        # game to T5, and all 250 points should land in the T5 bucket.
        owned, db_game = _overcompleted_game("g1", po_points=100, so_points=150)

        tiers = compute_role_points([owned], [db_game]).tiers

        assert tiers[4] == 250
        assert tiers[3] == 0

    def test_game_missing_from_database_is_skipped(self):
        owned, _ = _completed_game("g1", 100)

        points = compute_role_points([owned], [])

        assert points.tiers == [0] * TIER_COUNT
        assert points.categories == [0] * CATEGORY_COUNT

    def test_points_accumulate_across_games_in_the_same_tier(self):
        owned_a, db_a = _completed_game("g1", TIER_PO_POINTS[2])
        owned_b, db_b = _completed_game("g2", TIER_PO_POINTS[2])

        tiers = compute_role_points([owned_a, owned_b], [db_a, db_b]).tiers

        assert tiers[1] == TIER_PO_POINTS[2] * 2


def _game_with_secondaries(
    ce_id: str,
    po_points: int,
    so_points: list[int],
    completed_sos: list[int] | None = None,
    user_completes_pos: bool = True,
) -> tuple[CEUserGame, CEGame]:
    """A game with one PO and several SOs. `completed_sos` picks which SO
    indices the user has also finished."""
    completed = completed_sos if completed_sos is not None else []

    objectives = [
        make_objective(
            ce_id=f"po-{ce_id}",
            obj_type="Primary",
            point_value=po_points,
            name="PO",
            game_ce_id=ce_id,
        )
    ]
    for i, points in enumerate(so_points):
        objectives.append(
            make_objective(
                ce_id=f"so-{ce_id}-{i}",
                obj_type="Secondary",
                point_value=points,
                name=f"SO{i}",
                game_ce_id=ce_id,
            )
        )
    db_game = make_game(ce_id=ce_id, objectives=objectives, categories=["Action"])

    user_objectives = [
        make_user_objective(
            ce_id=f"po-{ce_id}",
            game_ce_id=ce_id,
            obj_type="Primary",
            user_points=po_points if user_completes_pos else 0,
        )
    ]
    for i in completed:
        user_objectives.append(
            make_user_objective(
                ce_id=f"so-{ce_id}-{i}",
                game_ce_id=ce_id,
                obj_type="Secondary",
                user_points=so_points[i],
            )
        )
    owned = make_user_game(ce_id=ce_id, user_objectives=user_objectives)
    return owned, db_game


class TestSecondariesRaiseTier:
    """A game's tier, for role purposes, follows what the user earned: their
    POs plus any SOs they also finished. Clearing an SO can therefore lift a
    game above the tier its POs alone would put it in."""

    def test_completed_secondary_lifts_game_into_a_higher_tier(self):
        # 75 PO points is a T3. Clearing the 10 point SO makes 85, a T4.
        owned, db_game = _game_with_secondaries(
            "g1", po_points=75, so_points=[10, 200], completed_sos=[0]
        )

        tiers = compute_role_points([owned], [db_game]).tiers

        assert tiers[3] == 85
        assert tiers[2] == 0

    def test_primaries_alone_stay_in_the_lower_tier(self):
        # Same game, but the user cleared no SOs: 75 points, still a T3.
        owned, db_game = _game_with_secondaries(
            "g1", po_points=75, so_points=[10, 200], completed_sos=[]
        )

        tiers = compute_role_points([owned], [db_game]).tiers

        assert tiers[2] == 75
        assert tiers[3] == 0

    def test_clearing_every_secondary_uses_the_full_total(self):
        # 75 + 10 + 200 = 285, which is a T5.
        owned, db_game = _game_with_secondaries(
            "g1", po_points=75, so_points=[10, 200], completed_sos=[0, 1]
        )

        tiers = compute_role_points([owned], [db_game]).tiers

        assert tiers[4] == 285

    def test_secondary_that_does_not_cross_a_threshold_keeps_the_tier(self):
        # 75 + 2 = 77, still short of the 80 point T4 threshold.
        owned, db_game = _game_with_secondaries(
            "g1", po_points=75, so_points=[2, 200], completed_sos=[0]
        )

        tiers = compute_role_points([owned], [db_game]).tiers

        assert tiers[2] == 77
        assert tiers[3] == 0

    def test_unfinished_primaries_contribute_nothing_even_with_secondaries(self):
        # The user cleared a big SO but hasn't finished the POs, so the game
        # contributes no tier points at all.
        owned, db_game = _game_with_secondaries(
            "g1",
            po_points=75,
            so_points=[200],
            completed_sos=[0],
            user_completes_pos=False,
        )

        tiers = compute_role_points([owned], [db_game]).tiers

        assert tiers == [0] * TIER_COUNT

    def test_game_with_no_primaries_counts_when_all_secondaries_are_done(self):
        # A game with zero POs is "finished" by clearing every SO. This is the
        # one case is_completed() rejects and is_overcompleted() catches.
        so = make_objective(
            ce_id="so-only",
            obj_type="Secondary",
            point_value=100,
            name="SO",
            game_ce_id="g1",
        )
        db_game = make_game(ce_id="g1", objectives=[so], categories=["Action"])
        user_so = make_user_objective(
            ce_id="so-only", game_ce_id="g1", obj_type="Secondary", user_points=100
        )
        owned = make_user_game(ce_id="g1", user_objectives=[user_so])

        tiers = compute_role_points([owned], [db_game]).tiers

        assert tiers[3] == 100


class TestSubTierOneGames:
    """A game worth fewer than 5 PO points has tier_num == 0. Indexing
    tiers[tier_num - 1] would wrap to tiers[-1] -- the Tier 7 slot -- and
    silently inflate the Tier 5+ total that Tier 5 Enthusiast reads."""

    @pytest.mark.parametrize("po_points", [1, 2, 3, 4])
    def test_sub_t1_completed_game_does_not_land_in_tier_7(self, po_points):
        owned, db_game = _completed_game("g1", po_points)

        tiers = compute_role_points([owned], [db_game]).tiers

        assert tiers[6] == 0
        assert tiers == [0] * TIER_COUNT

    def test_sub_t1_game_does_not_inflate_t5_plus_total(self):
        owned, db_game = _completed_game("g1", 4)

        tiers = compute_role_points([owned], [db_game]).tiers

        assert t5_plus_points(tiers) == 0

    def test_sub_t1_game_still_counts_toward_categories(self):
        # Category roles don't care about completion or tier at all.
        owned, db_game = _completed_game("g1", 4)

        categories = compute_role_points([owned], [db_game]).categories

        assert categories[0] == 4


class TestCategoryPoints:
    def test_completed_game_adds_points_to_its_category(self):
        owned, db_game = _completed_game("g1", 100, categories=["Arcade"])

        categories = compute_role_points([owned], [db_game]).categories

        assert categories[1] == 100

    def test_incomplete_game_still_counts_toward_categories(self):
        obj = make_objective(
            ce_id="obj-partial",
            obj_type="Primary",
            point_value=100,
            name="PO",
            game_ce_id="g1",
        )
        db_game = make_game(ce_id="g1", objectives=[obj], categories=["Action"])
        uobj = make_user_objective(ce_id="obj-partial", game_ce_id="g1", user_points=30)
        owned = make_user_game(ce_id="g1", user_objectives=[uobj])

        points = compute_role_points([owned], [db_game])

        assert points.categories[0] == 30
        assert points.tiers == [0] * TIER_COUNT

    def test_multi_category_game_counts_in_every_category(self):
        owned, db_game = _completed_game("g1", 100, categories=["Action", "Strategy"])

        categories = compute_role_points([owned], [db_game]).categories

        assert categories[0] == 100
        assert categories[5] == 100


class TestT5PlusPoints:
    def test_sums_tiers_five_six_and_seven(self):
        # index 0 is Tier 1, so Tiers 5-7 are indices 4, 5 and 6.
        tiers = [1, 2, 4, 8, 100, 200, 400]

        assert t5_plus_points(tiers) == 700

    def test_ignores_tiers_one_through_four(self):
        tiers = [1000, 1000, 1000, 1000, 0, 0, 0]

        assert t5_plus_points(tiers) == 0

    def test_zeroed_tiers_are_zero(self):
        assert t5_plus_points([0] * TIER_COUNT) == 0
