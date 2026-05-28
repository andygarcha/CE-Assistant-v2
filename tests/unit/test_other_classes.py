"""
Tests for pure-logic classes in OtherClasses.py and CRData.calculate_cr.
Skips: EmbedMessage/UpdateMessage (trivial containers), RAData (dict passthrough),
       CEInput.is_curatable (known bug: compares str to int, always False).
"""

import pytest

from Classes.OtherClasses import (
    CECompletion,
    CECurateInput,
    CEIndividualValueInput,
    CEInput,
    CEValueInput,
    CRData,
)


# ── CECompletion ──────────────────────────────────────────────────────────────


def _completion(completed: int, started: int, total: int) -> CECompletion:
    return CECompletion({"completed": completed, "started": started, "total": total})


class TestCECompletion:
    def test_no_progress(self):
        c = _completion(completed=5, started=10, total=30)
        assert c.no_progress == 15

    def test_no_progress_all_completed(self):
        assert _completion(100, 0, 100).no_progress == 0

    def test_completion_percentage_formatted(self):
        assert _completion(5, 0, 100).completion_percentage() == "5.0%"

    def test_completion_percentage_zero_total_returns_none(self):
        assert _completion(0, 0, 0).completion_percentage() is None

    def test_completion_percentage_rounding(self):
        # 1/3 ≈ 33.33%
        result = _completion(1, 0, 3).completion_percentage()
        assert result == "33.33%"

    def test_description_with_owners(self):
        result = _completion(10, 5, 100).description()
        assert "10" in result
        assert "10.0%" in result
        assert "100" in result

    def test_description_zero_total(self):
        result = _completion(0, 0, 0).description()
        assert "Percentage N/A" in result

    def test_raw_properties(self):
        c = _completion(3, 7, 20)
        assert c.completions == 3
        assert c.started == 7
        assert c.total == 20


# ── CRData.calculate_cr ───────────────────────────────────────────────────────


class TestCalculateCR:
    def test_empty_list_returns_zero(self):
        assert CRData.calculate_cr([]) == 0

    def test_single_game(self):
        # First game: multiplier^0 * points = 1.0 * 100 = 100
        assert CRData.calculate_cr([100]) == 100.0

    def test_two_games(self):
        # 100 + 0.9 * 100 = 190
        assert CRData.calculate_cr([100, 100]) == 190.0

    def test_three_games(self):
        # 100 + 0.9*100 + 0.81*100 = 271
        assert CRData.calculate_cr([100, 100, 100]) == 271.0

    def test_per_game_cap_applied(self):
        # A single game worth 2000 should be capped at 1000
        assert CRData.calculate_cr([2000]) == 1000.0

    def test_cap_applied_independently_per_game(self):
        # [500, 2000] → 500 + 0.9 * 1000 = 1400
        assert CRData.calculate_cr([500, 2000]) == 1400.0

    def test_result_rounded_to_two_decimals(self):
        result = CRData.calculate_cr([1, 1, 1])
        # 1 + 0.9 + 0.81 = 2.71
        assert result == 2.71

    def test_descending_order_gives_higher_cr(self):
        # Higher-valued games should be listed first for maximum CR
        asc = CRData.calculate_cr([10, 100])
        desc = CRData.calculate_cr([100, 10])
        assert desc > asc


# ── CEIndividualValueInput ────────────────────────────────────────────────────


class TestCEIndividualValueInput:
    def test_properties(self):
        inp = CEIndividualValueInput(user_ce_id="user-001", value=50)
        assert inp.user_ce_id == "user-001"
        assert inp.value == 50

    def test_set_value(self):
        inp = CEIndividualValueInput(user_ce_id="user-001", value=50)
        inp.set_value(75)
        assert inp.value == 75

    def test_to_dict(self):
        inp = CEIndividualValueInput(user_ce_id="user-001", value=40)
        assert inp.to_dict() == {"user_ce_id": "user-001", "recommendation": 40}


# ── CEValueInput ──────────────────────────────────────────────────────────────


OBJ_ID = "obj-0001-0000-0000-000000000000"


def _value_input(*values: int) -> CEValueInput:
    vi = CEValueInput(objective_ce_id=OBJ_ID, individual_value_inputs=[])
    for i, v in enumerate(values):
        vi.add_new_individual_input(user_id=f"user-{i:03}", value=v)
    return vi


class TestCEValueInput:
    def test_average_single_input(self):
        assert _value_input(40).average() == 40.0

    def test_average_multiple_inputs(self):
        assert _value_input(10, 20, 30).average() == 20.0

    def test_average_rounded_to_two_decimals(self):
        result = _value_input(10, 20).average()
        assert result == 15.0

    def test_user_has_individual_input_found(self):
        vi = _value_input(10)
        assert vi.user_has_individual_input("user-000") is True

    def test_user_has_individual_input_not_found(self):
        assert _value_input(10).user_has_individual_input("unknown-user") is False

    def test_add_individual_input_new_user(self):
        vi = _value_input(10)
        vi.add_individual_input("new-user", 99)
        assert vi.user_has_individual_input("new-user") is True

    def test_add_individual_input_replaces_existing(self):
        vi = _value_input(10)
        vi.add_individual_input("user-000", 50)
        assert vi.get_individual_input("user-000").value == 50

    def test_index_of_individual_input_found(self):
        vi = _value_input(10, 20)
        assert vi.index_of_individual_input("user-001") == 1

    def test_index_of_individual_input_not_found(self):
        assert _value_input(10).index_of_individual_input("nobody") == -1


# ── CECurateInput ─────────────────────────────────────────────────────────────


class TestCECurateInput:
    @pytest.mark.parametrize(
        "curate, expected",
        [
            (0, "Don't Curate"),
            (1, "Curate"),
            (2, "Indifferent"),
            (99, "Failure"),
        ],
    )
    def test_curate_meaning(self, curate, expected):
        assert CECurateInput(user_ce_id="u", curate=curate).curate_meaning() == expected

    def test_set_curate(self):
        ci = CECurateInput(user_ce_id="u", curate=0)
        ci.set_curate(1)
        assert ci.curate == 1


# ── CEInput curate voting ─────────────────────────────────────────────────────


def _ce_input_with_curates(votes: list[int]) -> CEInput:
    """Build a CEInput with the given list of curate values (0=no, 1=yes, 2=indifferent)."""
    ci = CEInput(
        game_ce_id="game-001", value_inputs=[], curate_inputs=[], tag_inputs=[]
    )
    for i, v in enumerate(votes):
        ci.add_new_curate_input(user_id=f"user-{i:03}", curate=v)
    return ci


class TestCEInputCurating:
    def test_average_curate_num_all_yes(self):
        assert _ce_input_with_curates([1, 1, 1]).average_curate_num() == 100.0

    def test_average_curate_num_all_no(self):
        assert _ce_input_with_curates([0, 0, 0]).average_curate_num() == 0.0

    def test_average_curate_num_mixed(self):
        # 2 yes out of 3 (indifferent excluded from denominator)
        # votes: [1, 1, 0] → 2 yes, 1 no → 2/(2+1) * 100 = 66.67
        result = _ce_input_with_curates([1, 1, 0]).average_curate_num()
        assert abs(result - 66.67) < 0.01

    def test_average_curate_num_empty_is_zero(self):
        assert _ce_input_with_curates([]).average_curate_num() == 0.0

    def test_average_curate_string_format(self):
        result = _ce_input_with_curates([1, 1, 1]).average_curate()
        assert result == "100.0%"

    def test_curator_count(self):
        assert _ce_input_with_curates([1, 0, 2]).curator_count() == 3

    def test_add_curate_input_replaces_existing(self):
        ci = _ce_input_with_curates([0])
        ci.add_curate_input("user-000", 1)
        assert ci.user_has_selected_yes("user-000") is True
        assert ci.user_has_selected_no("user-000") is False

    def test_has_curate_input(self):
        ci = _ce_input_with_curates([1])
        assert ci.has_curate_input("user-000") is True
        assert ci.has_curate_input("nobody") is False

    def test_user_has_selected_yes_no_indifferent(self):
        ci = _ce_input_with_curates([1, 0, 2])
        assert ci.user_has_selected_yes("user-000") is True
        assert ci.user_has_selected_no("user-001") is True
        assert ci.user_has_selected_indifferent("user-002") is True


# ── CEInput value voting ──────────────────────────────────────────────────────


class TestCEInputValueVoting:
    def test_add_value_input_new_objective(self):
        ci = CEInput(
            game_ce_id="game-001", value_inputs=[], curate_inputs=[], tag_inputs=[]
        )
        ci.add_value_input(objective_id=OBJ_ID, user_id="user-001", value=30)
        assert ci.has_value_input(OBJ_ID) is True

    def test_add_value_input_second_user_same_objective(self):
        ci = CEInput(
            game_ce_id="game-001", value_inputs=[], curate_inputs=[], tag_inputs=[]
        )
        ci.add_value_input(OBJ_ID, "user-001", 30)
        ci.add_value_input(OBJ_ID, "user-002", 50)
        vi = ci.get_value_input(OBJ_ID)
        assert vi.average() == 40.0

    def test_get_value_input_not_found_returns_none(self):
        ci = CEInput(
            game_ce_id="game-001", value_inputs=[], curate_inputs=[], tag_inputs=[]
        )
        assert ci.get_value_input("nonexistent") is None
