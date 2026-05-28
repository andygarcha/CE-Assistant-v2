from types import SimpleNamespace


from utils.general_utils import (
    format_ce_link,
    get_index_from_list,
    get_item_from_list,
    is_within_percentage,
    replace_item_in_list,
)

VALID_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def _item(ce_id: str):
    return SimpleNamespace(ce_id=ce_id)


# ── get_item_from_list ────────────────────────────────────────────────────────


class TestGetItemFromList:
    def test_returns_matching_item(self):
        items = [_item("aaa"), _item("bbb"), _item("ccc")]
        result = get_item_from_list("bbb", items)
        assert hasattr(result, "ce_id")
        assert result.ce_id == "bbb" # type: ignore

    def test_returns_none_when_not_found(self):
        assert get_item_from_list("zzz", [_item("aaa"), _item("bbb")]) is None

    def test_empty_list(self):
        assert get_item_from_list("aaa", []) is None

    def test_returns_first_on_duplicate_ids(self):
        a1, a2 = _item("aaa"), _item("aaa")
        assert get_item_from_list("aaa", [a1, a2]) is a1


# ── get_index_from_list ───────────────────────────────────────────────────────


class TestGetIndexFromList:
    def test_returns_correct_index(self):
        items = [_item("aaa"), _item("bbb"), _item("ccc")]
        assert get_index_from_list("ccc", items) == 2

    def test_returns_minus_one_when_not_found(self):
        assert get_index_from_list("zzz", [_item("aaa"), _item("bbb")]) == -1

    def test_empty_list(self):
        assert get_index_from_list("aaa", []) == -1

    def test_first_element(self):
        assert get_index_from_list("aaa", [_item("aaa"), _item("bbb")]) == 0


# ── replace_item_in_list ──────────────────────────────────────────────────────


class TestReplaceItemInList:
    def test_replaces_matching_item(self):
        items = [_item("aaa"), _item("bbb"), _item("ccc")]
        new = _item("bbb")
        result = replace_item_in_list("bbb", new, items)
        assert result[1] is new

    def test_returns_list(self):
        items = [_item("aaa")]
        assert isinstance(replace_item_in_list("aaa", _item("aaa"), items), list)

    def test_no_match_leaves_list_unchanged(self):
        original = _item("aaa")
        items = [original]
        result = replace_item_in_list("zzz", _item("zzz"), items)
        assert result[0] is original

    def test_does_not_affect_other_elements(self):
        a, b, c = _item("aaa"), _item("bbb"), _item("ccc")
        replace_item_in_list("bbb", _item("bbb"), [a, b, c])
        assert c.ce_id == "ccc"


# ── format_ce_link ────────────────────────────────────────────────────────────


class TestFormatCELink:
    def test_full_https_www_games_link(self):
        assert format_ce_link(f"https://www.cedb.me/games/{VALID_UUID}/") == VALID_UUID

    def test_no_www(self):
        assert format_ce_link(f"https://cedb.me/games/{VALID_UUID}/") == VALID_UUID

    def test_user_link(self):
        assert format_ce_link(f"https://www.cedb.me/user/{VALID_UUID}/") == VALID_UUID

    def test_bare_uuid_passthrough(self):
        assert format_ce_link(VALID_UUID) == VALID_UUID

    def test_invalid_string_returns_none(self):
        assert format_ce_link("thisisnotavaliduuid12345") is None

    def test_wrong_dash_positions_returns_none(self):
        # dashes at wrong positions
        assert format_ce_link("a1b2c3d4e5f67890abcdef1234567890") is None


# ── is_within_percentage ──────────────────────────────────────────────────────


class TestIsWithinPercentage:
    def test_exact_value(self):
        assert is_within_percentage(15, 50, 15) is True

    def test_within_bounds(self):
        # 50% of 15 = 7.5 → bounds [7.5, 22.5]
        assert is_within_percentage(10, 50, 15) is True

    def test_below_lower_bound(self):
        # 10% of 100 → bounds [90, 110]
        assert is_within_percentage(89, 10, 100) is False

    def test_above_upper_bound(self):
        assert is_within_percentage(111, 10, 100) is False

    def test_at_lower_bound_inclusive(self):
        assert is_within_percentage(90, 10, 100) is True

    def test_at_upper_bound_inclusive(self):
        assert is_within_percentage(110, 10, 100) is True

    def test_zero_percentage_exact_match(self):
        assert is_within_percentage(100, 0, 100) is True

    def test_zero_percentage_off_by_one(self):
        assert is_within_percentage(99, 0, 100) is False

    def test_float_input(self):
        assert is_within_percentage(10.5, 50, 15) is True

    def test_hundred_percent(self):
        # 100% of 50 → bounds [0, 100] — any non-negative value up to 100 qualifies
        assert is_within_percentage(0, 100, 50) is True
        assert is_within_percentage(100, 100, 50) is True
        assert is_within_percentage(101, 100, 50) is False
