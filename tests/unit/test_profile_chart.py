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


import asyncio
import io
from unittest.mock import AsyncMock, patch

from PIL import Image

from Modules.ProfileChart import (
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    BACKGROUND_COLOR,
    generate_completions_chart,
)


class TestGenerateCompletionsChart:
    def _make_user_with_counts(self):
        return _make_api_user(
            [
                {
                    "genreId": TOTAL_GENRE_ID,
                    "tier1": 4,
                    "tier2": 9,
                    "tier3": 2,
                    "tier4": 0,
                    "tier5": 1,
                    "total": 16,
                },
                {"genreId": ACTION_GENRE_ID, "total": 7},
            ]
        )

    def test_returns_png_of_expected_size(self):
        api_user = self._make_user_with_counts()

        with patch(
            "Modules.ProfileChart.get_cached_emoji_path",
            new_callable=AsyncMock,
            return_value=None,
        ):
            buffer = asyncio.run(generate_completions_chart(api_user))

        assert isinstance(buffer, io.BytesIO)
        image = Image.open(buffer)
        assert image.format == "PNG"
        assert image.size == (IMAGE_WIDTH, IMAGE_HEIGHT)

    def test_background_color_is_near_black(self):
        api_user = self._make_user_with_counts()

        with patch(
            "Modules.ProfileChart.get_cached_emoji_path",
            new_callable=AsyncMock,
            return_value=None,
        ):
            buffer = asyncio.run(generate_completions_chart(api_user))

        image = Image.open(buffer).convert("RGB")
        # top-left corner should be untouched background
        assert image.getpixel((0, 0)) == BACKGROUND_COLOR

    def test_draws_a_tier_colored_bar_pixel(self):
        api_user = self._make_user_with_counts()

        with patch(
            "Modules.ProfileChart.get_cached_emoji_path",
            new_callable=AsyncMock,
            return_value=None,
        ):
            buffer = asyncio.run(generate_completions_chart(api_user))

        image = Image.open(buffer).convert("RGB")
        colors_present = {
            image.getpixel((x, y))
            for x in range(0, IMAGE_WIDTH, 4)
            for y in range(0, IMAGE_HEIGHT, 4)
        }
        from Modules.ProfileChart import TIER_COLORS

        assert TIER_COLORS["Tier 2"] in colors_present  # tallest tier bar (count 9)

    def test_handles_get_cached_emoji_path_exception(self):
        """Test that get_cached_emoji_path raising an exception doesn't crash chart generation."""
        api_user = self._make_user_with_counts()

        with patch(
            "Modules.ProfileChart.get_cached_emoji_path",
            new_callable=AsyncMock,
            side_effect=Exception("boom"),
        ):
            buffer = asyncio.run(generate_completions_chart(api_user))

        assert isinstance(buffer, io.BytesIO)
        image = Image.open(buffer)
        assert image.format == "PNG"
        assert image.size == (IMAGE_WIDTH, IMAGE_HEIGHT)

    def test_handles_corrupted_emoji_file(self, tmp_path):
        """Test that a corrupted emoji file doesn't crash chart generation."""
        api_user = self._make_user_with_counts()

        # Create a corrupted emoji file (garbage bytes, not a real PNG)
        bad_emoji_path = tmp_path / "bad.png"
        bad_emoji_path.write_bytes(b"not a real png")

        with patch(
            "Modules.ProfileChart.get_cached_emoji_path",
            new_callable=AsyncMock,
            return_value=bad_emoji_path,
        ):
            buffer = asyncio.run(generate_completions_chart(api_user))

        assert isinstance(buffer, io.BytesIO)
        image = Image.open(buffer)
        assert image.format == "PNG"
        assert image.size == (IMAGE_WIDTH, IMAGE_HEIGHT)
