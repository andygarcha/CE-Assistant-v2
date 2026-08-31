import pytest

from Classes.CE_Game import CEGame
from Classes.CE_User_Game import CEUserGame
from Modules.Discord_Helper import (
    ENTHUSIAST_BAR_EMPTY,
    ENTHUSIAST_BAR_FILLED,
    ENTHUSIAST_BAR_SEGMENTS,
    get_enthusiast_embed,
    get_enthusiast_row,
    get_progress_bar,
)
from tests.conftest import (
    make_game,
    make_objective,
    make_user,
    make_user_game,
    make_user_objective,
)

# PO values inside each tier's band, per TIER_THRESHOLDS in Classes/CE_Game.py.
TIER_PO_POINTS = {1: 10, 2: 25, 3: 50, 4: 100, 5: 250, 6: 500, 7: 900}


def _completed_games(
    n: int, po_points: int, prefix: str
) -> tuple[list[CEUserGame], list[CEGame]]:
    """`n` fully-completed single-PO games, together worth `n * po_points`
    in the tier that `po_points` falls into."""
    owned: list[CEUserGame] = []
    db: list[CEGame] = []
    for i in range(n):
        ce_id = f"{prefix}-{i:04d}"
        obj = make_objective(
            ce_id=f"obj-{ce_id}",
            obj_type="Primary",
            point_value=po_points,
            name="PO",
            game_ce_id=ce_id,
        )
        db.append(make_game(ce_id=ce_id, objectives=[obj], categories=["Action"]))
        uobj = make_user_objective(
            ce_id=f"obj-{ce_id}", game_ce_id=ce_id, user_points=po_points
        )
        owned.append(make_user_game(ce_id=ce_id, user_objectives=[uobj]))
    return owned, db


def _embed_for(owned, db):
    return get_enthusiast_embed(make_user(owned_games=owned), db)


def _field(embed, label: str):
    "Returns the embed field whose name contains `label`."
    return next(f for f in embed.fields if label in (f.name or ""))


class TestProgressBar:
    def test_empty_at_zero(self):
        bar = get_progress_bar(0, 1000)
        assert bar == ENTHUSIAST_BAR_EMPTY * ENTHUSIAST_BAR_SEGMENTS

    def test_full_at_threshold(self):
        bar = get_progress_bar(1000, 1000)
        assert bar == ENTHUSIAST_BAR_FILLED * ENTHUSIAST_BAR_SEGMENTS

    def test_half_at_midpoint(self):
        bar = get_progress_bar(500, 1000)
        assert bar.count(ENTHUSIAST_BAR_FILLED) == 5
        assert bar.count(ENTHUSIAST_BAR_EMPTY) == 5

    @pytest.mark.parametrize("current", [0, 1, 250, 999, 1000, 5000])
    def test_length_is_always_constant(self, current):
        assert len(get_progress_bar(current, 1000)) == ENTHUSIAST_BAR_SEGMENTS

    def test_does_not_overflow_past_threshold(self):
        bar = get_progress_bar(9999, 1000)
        assert bar == ENTHUSIAST_BAR_FILLED * ENTHUSIAST_BAR_SEGMENTS

    def test_negative_threshold_does_not_crash(self):
        assert len(get_progress_bar(0, 0)) == ENTHUSIAST_BAR_SEGMENTS


class TestEnthusiastRow:
    def test_unlocked_row_marks_completion(self):
        row = get_enthusiast_row(640, 500)
        assert "Completed" in row
        assert "640" in row

    def test_locked_row_shows_progress_and_remainder(self):
        row = get_enthusiast_row(780, 1000)
        assert "780 / 1,000" in row
        assert "(78%)" in row
        assert "220 to go" in row

    def test_row_at_exactly_the_threshold_is_unlocked(self):
        assert "Completed" in get_enthusiast_row(1000, 1000)

    def test_zero_progress_row(self):
        row = get_enthusiast_row(0, 2500)
        assert "0 / 2,500" in row
        assert "(0%)" in row

    def test_thousands_are_comma_separated(self):
        row = get_enthusiast_row(1234, 2500)
        assert "1,234 / 2,500" in row
        assert "1234" not in row
        assert "2500" not in row

    def test_remainder_is_comma_separated(self):
        # 2500 - 250 = 2250 left to go.
        row = get_enthusiast_row(250, 2500)
        assert "2,250 to go" in row

    def test_completed_row_is_comma_separated(self):
        row = get_enthusiast_row(3300, 2500)
        assert "3,300 / 2,500" in row

    def test_values_under_a_thousand_are_left_alone(self):
        row = get_enthusiast_row(300, 500)
        assert "300 / 500" in row
        assert "," not in row


class TestEnthusiastEmbed:
    def test_has_five_rows(self):
        embed = _embed_for([], [])
        assert len(embed.fields) == 5

    def test_rows_are_labelled_tier_one_through_five(self):
        embed = _embed_for([], [])
        names = [f.name or "" for f in embed.fields]
        for tier in range(1, 6):
            assert any(f"Tier {tier} Enthusiast" in name for name in names)

    def test_tier_five_row_is_marked_as_covering_t5_plus(self):
        embed = _embed_for([], [])
        tier5 = _field(embed, "Tier 5 Enthusiast")
        assert "T5+" in (tier5.name or "")

    def test_zeroed_user_renders_all_empty_bars(self):
        embed = _embed_for([], [])
        for field in embed.fields:
            assert ENTHUSIAST_BAR_FILLED not in (field.value or "")

    def test_tier_two_progress_is_reflected(self):
        # 10 x 25 = 250 points of Tier 2, against a 1000 threshold.
        owned, db = _completed_games(10, TIER_PO_POINTS[2], "t2")
        embed = _embed_for(owned, db)
        tier2 = _field(embed, "Tier 2 Enthusiast")
        assert "250 / 1,000" in (tier2.value or "")

    def test_unlocked_tier_renders_checkmark_form(self):
        # 50 x 10 = 500 points of Tier 1, exactly the threshold.
        owned, db = _completed_games(50, TIER_PO_POINTS[1], "t1")
        embed = _embed_for(owned, db)
        tier1 = _field(embed, "Tier 1 Enthusiast")
        assert "Completed" in (tier1.value or "")

    def test_tier_five_row_sums_tiers_five_six_and_seven(self):
        # 1 x 250 (T5) + 1 x 500 (T6) + 1 x 900 (T7) = 1650, not just the 250.
        owned_5, db_5 = _completed_games(1, TIER_PO_POINTS[5], "mix5")
        owned_6, db_6 = _completed_games(1, TIER_PO_POINTS[6], "mix6")
        owned_7, db_7 = _completed_games(1, TIER_PO_POINTS[7], "mix7")

        embed = _embed_for(owned_5 + owned_6 + owned_7, db_5 + db_6 + db_7)

        tier5 = _field(embed, "Tier 5 Enthusiast")
        assert "1,650 / 2,500" in (tier5.value or "")

    def test_tier_five_row_unlocks_at_2500(self):
        # 3 x 900 = 2700 of Tier 7.
        owned, db = _completed_games(3, TIER_PO_POINTS[7], "t7")
        embed = _embed_for(owned, db)
        tier5 = _field(embed, "Tier 5 Enthusiast")
        assert "Completed" in (tier5.value or "")

    def test_over_threshold_tier_does_not_overflow_its_bar(self):
        owned, db = _completed_games(200, TIER_PO_POINTS[1], "over")
        embed = _embed_for(owned, db)
        tier1 = _field(embed, "Tier 1 Enthusiast")
        value = tier1.value or ""
        assert value.count(ENTHUSIAST_BAR_FILLED) == ENTHUSIAST_BAR_SEGMENTS

    def test_incomplete_games_do_not_show_progress(self):
        obj = make_objective(
            ce_id="obj-x",
            obj_type="Primary",
            point_value=100,
            name="PO",
            game_ce_id="g1",
        )
        db_game = make_game(ce_id="g1", objectives=[obj], categories=["Action"])
        uobj = make_user_objective(ce_id="obj-x", game_ce_id="g1", user_points=30)
        owned = make_user_game(ce_id="g1", user_objectives=[uobj])

        embed = _embed_for([owned], [db_game])

        for field in embed.fields:
            assert ENTHUSIAST_BAR_FILLED not in (field.value or "")
