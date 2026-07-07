import asyncio
import datetime
import io
from unittest.mock import AsyncMock, patch

import discord

from Classes.CE_User import CEAPIUser, CEUser
from Modules import Discord_Helper


def _make_registered_user() -> CEUser:
    return CEUser(
        discord_id=100000000000000000,
        ce_id="user-001-0000-0000-000000000000",
        owned_games=[],
        rolls=[],
        display_name="TestUser",
        avatar="",
        last_updated=datetime.datetime.now(datetime.timezone.utc),
    )


def _make_api_user() -> CEAPIUser:
    return CEAPIUser(
        discord_id=100000000000000000,
        ce_id="user-001-0000-0000-000000000000",
        owned_games=[],
        rolls=[],
        full_data={
            "userTierSummaries": [
                {
                    "genreId": "00000000-0000-0000-0000-000000000000",
                    "tier1": 1,
                    "tier2": 2,
                    "tier3": 3,
                    "tier4": 4,
                    "tier5": 5,
                    "total": 15,
                }
            ],
            "userObjectives": [],
        },
        display_name="TestUser",
        avatar="",
        last_updated=datetime.datetime.now(datetime.timezone.utc),
    )


class TestGetUserEmbeds:
    def test_returns_three_tuple_with_chart_file(self):
        user = _make_registered_user()
        api_user = _make_api_user()
        fake_chart = io.BytesIO(b"fake-png-bytes")

        with (
            patch.object(user, "get_api_user", new=AsyncMock(return_value=api_user)),
            patch(
                "Modules.Discord_Helper.ProfileChart.generate_completions_chart",
                new=AsyncMock(return_value=fake_chart),
            ),
        ):
            embed, view, chart_file = asyncio.run(
                Discord_Helper.get_user_embeds(user=user, database_name=[])
            )

        assert isinstance(embed, discord.Embed)
        assert isinstance(view, discord.ui.View)
        assert isinstance(chart_file, discord.File)

    def test_completions_field_removed_and_image_set(self):
        user = _make_registered_user()
        api_user = _make_api_user()
        fake_chart = io.BytesIO(b"fake-png-bytes")

        with (
            patch.object(user, "get_api_user", new=AsyncMock(return_value=api_user)),
            patch(
                "Modules.Discord_Helper.ProfileChart.generate_completions_chart",
                new=AsyncMock(return_value=fake_chart),
            ),
        ):
            embed, _, _ = asyncio.run(
                Discord_Helper.get_user_embeds(user=user, database_name=[])
            )

        field_names = [f.name for f in embed.fields]
        assert "Completions" not in field_names
        assert embed.image.url == "attachment://completions.png"

    def test_returns_none_file_when_api_user_missing(self):
        user = _make_registered_user()

        with patch.object(user, "get_api_user", new=AsyncMock(return_value=None)):
            embed, view, chart_file = asyncio.run(
                Discord_Helper.get_user_embeds(user=user, database_name=[])
            )

        assert chart_file is None
