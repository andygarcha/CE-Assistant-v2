from Classes.CE_User import CEAPIUser
from Modules.ProfileChart import tier_counts, category_counts

TOTAL_GENRE_ID = "00000000-0000-0000-0000-000000000000"
ACTION_GENRE_ID = "4d43349a-43a8-4755-9d52-41ece63ec5b1"
ARCADE_GENRE_ID = "ec499226-0913-4db1-890e-093b366bcb3c"
BULLET_HELL_GENRE_ID = "7f8676fe-4900-400b-9284-c073388d88f7"


def _make_api_user(tier_summary: list[dict]) -> CEAPIUser:
    return CEAPIUser(
        discord_id=1,
        ce_id="user-001-0000-0000-000000000000",
        owned_games=[],
        rolls=[],
        full_data={"userTierSummaries": tier_summary},
        display_name="TestUser",
        avatar="",
        last_updated=None,
    )


class TestTierCounts:
    def test_returns_fixed_tier_order(self):
        api_user = _make_api_user(
            [
                {
                    "genreId": TOTAL_GENRE_ID,
                    "tier1": 4,
                    "tier2": 9,
                    "tier3": 2,
                    "tier4": 0,
                    "tier5": 1,
                    "total": 16,
                }
            ]
        )
        assert tier_counts(api_user) == [
            ("Tier 1", 4),
            ("Tier 2", 9),
            ("Tier 3", 2),
            ("Tier 4", 0),
            ("Tier 5", 1),
        ]

    def test_all_zero_when_no_total_row(self):
        api_user = _make_api_user([])
        assert tier_counts(api_user) == [
            ("Tier 1", 0),
            ("Tier 2", 0),
            ("Tier 3", 0),
            ("Tier 4", 0),
            ("Tier 5", 0),
        ]


class TestCategoryCounts:
    def test_returns_fixed_alphabetical_order_regardless_of_input_order(self):
        api_user = _make_api_user(
            [
                {"genreId": TOTAL_GENRE_ID, "tier1": 0, "tier2": 0, "tier3": 0, "tier4": 0, "tier5": 0, "total": 0},
                {"genreId": BULLET_HELL_GENRE_ID, "total": 3},
                {"genreId": ACTION_GENRE_ID, "total": 7},
            ]
        )
        assert category_counts(api_user) == [
            ("Action", 7),
            ("Arcade", 0),
            ("Bullet Hell", 3),
            ("First-Person", 0),
            ("Platformer", 0),
            ("Strategy", 0),
        ]

    def test_all_zero_when_no_category_rows(self):
        api_user = _make_api_user([])
        assert category_counts(api_user) == [
            ("Action", 0),
            ("Arcade", 0),
            ("Bullet Hell", 0),
            ("First-Person", 0),
            ("Platformer", 0),
            ("Strategy", 0),
        ]
