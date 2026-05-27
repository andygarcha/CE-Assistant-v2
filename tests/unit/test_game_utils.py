import pytest

from utils.game_utils import achievements_are_equal, genre_id_to_name


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
