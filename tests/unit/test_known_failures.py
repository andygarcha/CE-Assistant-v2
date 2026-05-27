"""
Tests for known broken or unimplemented behaviour.
Every test in this file is EXPECTED TO FAIL until the underlying issue is fixed.
Each test documents:
  - the function / property that is broken
  - what the correct behaviour should be
  - why it currently fails
"""

from Classes.OtherClasses import CEInput
from utils.general_utils import get_grammar_str
from tests.conftest import make_game, make_roll, make_user, make_user_game, make_user_objective


# ── get_grammar_str (utils/general_utils.py:25-31) ───────────────────────────
# Bug: function body is `return NotImplemented` (a bare sentinel, not a string).
# The docstring shows the intended behaviour:
#   ["a"]         → "a"
#   ["a", "b", "c"] → "a, b, and c"


def test_grammar_str_empty_list():
    # An empty list should return an empty string (or some defined value).
    assert get_grammar_str([]) == ""


def test_grammar_str_single_item():
    assert get_grammar_str(["a"]) == "a"


def test_grammar_str_two_items():
    # No Oxford comma for two items: "a and b"
    assert get_grammar_str(["a", "b"]) == "a and b"


def test_grammar_str_three_items():
    # Oxford comma per the docstring example
    assert get_grammar_str(["a", "b", "c"]) == "a, b, and c"


def test_grammar_str_returns_str_not_not_implemented():
    # At minimum it must not return the NotImplemented sentinel.
    result = get_grammar_str(["x"])
    assert result is not NotImplemented
    assert isinstance(result, str)


# ── CEUser.casino_score (CE_User.py:97-99) ───────────────────────────────────
# Bug: property body is `return NotImplemented`.
# Expected: returns an int (or at least not the NotImplemented sentinel).


def test_casino_score_is_not_sentinel():
    user = make_user()
    assert user.casino_score is not NotImplemented


def test_casino_score_is_numeric():
    user = make_user()
    assert isinstance(user.casino_score, (int, float))


# ── CEUser.to_dict_supabase_objectives (CE_User.py:569-572) ──────────────────
# Bug: method builds `_objectives` list but has no `return` statement —
#      implicitly returns None.
# Expected: returns list[dict].


def test_to_dict_supabase_objectives_returns_list():
    uobj = make_user_objective()
    ug = make_user_game(user_objectives=[uobj])
    user = make_user(owned_games=[ug])
    result = user.to_dict_supabase_objectives()
    assert isinstance(result, list)


def test_to_dict_supabase_objectives_not_none():
    user = make_user(owned_games=[])
    assert user.to_dict_supabase_objectives() is not None


# ── CEInput.is_curatable (OtherClasses.py:839-844) ───────────────────────────
# Bug: `self.average_curate()` returns a str like "80.0%".
#      The method then compares that str to int 75 with `>=`,
#      which raises TypeError in Python 3 when curator_count() >= 10.
# Expected: returns True when ≥10 votes AND average yes-percentage ≥ 75.


def _ce_input_with_curates(votes: list[int]) -> CEInput:
    ci = CEInput(game_ce_id="game-001", value_inputs=[], curate_inputs=[], tag_inputs=[])
    for i, v in enumerate(votes):
        ci.add_new_curate_input(user_id=f"user-{i:03}", curate=v)
    return ci


def test_is_curatable_all_yes_ten_votes():
    # 10 votes, all yes (100%) → should be True; currently raises TypeError.
    ci = _ce_input_with_curates([1] * 10)
    assert ci.is_curatable() is True


def test_is_curatable_insufficient_votes():
    # 9 votes (below threshold) → should be False regardless of percentage.
    ci = _ce_input_with_curates([1] * 9)
    assert ci.is_curatable() is False


def test_is_curatable_low_percentage_ten_votes():
    # 10 votes but only 50% yes → should be False; currently raises TypeError.
    ci = _ce_input_with_curates([1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
    assert ci.is_curatable() is False


# ── CERoll.rolled_categories (CE_Roll.py:527-535) ────────────────────────────
# Bug: raises NotImplementedError unconditionally (TODO casino fix).
# Expected: returns a list[str] of category names for the rolled games.


def test_rolled_categories_returns_list():
    game = make_game(ce_id="game-001-0000-0000-000000000000", categories=["Action"])
    roll = make_roll(games=["game-001-0000-0000-000000000000"])
    result = roll.rolled_categories([game])
    assert isinstance(result, list)


def test_rolled_categories_contains_correct_category():
    game = make_game(ce_id="game-001-0000-0000-000000000000", categories=["Action"])
    roll = make_roll(games=["game-001-0000-0000-000000000000"])
    assert "Action" in roll.rolled_categories([game])


# ── CEUserGame.get_category_v2 (CE_User_Game.py:136-143) ─────────────────────
# Bug: raises NotImplementedError unconditionally (TODO casino fix).
# Expected: returns the category string for the game.


def test_get_category_v2_returns_category():
    game = make_game(ce_id="game-001-0000-0000-000000000000", categories=["Action"])
    ug = make_user_game(ce_id="game-001-0000-0000-000000000000")
    result = ug.get_category_v2([game])
    assert result is not None


def test_get_category_v2_returns_correct_category():
    game = make_game(ce_id="game-001-0000-0000-000000000000", categories=["Strategy"])
    ug = make_user_game(ce_id="game-001-0000-0000-000000000000")
    assert ug.get_category_v2([game]) == "Strategy"
