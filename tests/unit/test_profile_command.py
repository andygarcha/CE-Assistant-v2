import asyncio
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from commands.user import profile


def _make_interaction(user_id=100000000000000000):
    return SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        user=SimpleNamespace(id=user_id, mention=f"<@{user_id}>"),
    )


class TestProfileCommand:
    def test_forwards_chart_file_to_followup_send(self):
        interaction = _make_interaction()
        fake_embed = discord.Embed(title="Profile")
        fake_view = MagicMock()
        fake_file = discord.File(
            io.BytesIO(b"fake-png-bytes"), filename="completions.png"
        )

        with (
            patch("commands.user.client", create=True, new=MagicMock()),
            patch("commands.user.hm.log_command", new_callable=AsyncMock),
            patch(
                "commands.user.SupabaseReader.get_database_name", return_value=[]
            ),
            patch(
                "commands.user.SupabaseReader.get_user",
                return_value=SimpleNamespace(),
            ),
            patch(
                "commands.user.Discord_Helper.get_user_embeds",
                new=AsyncMock(return_value=(fake_embed, fake_view, fake_file)),
            ),
        ):
            asyncio.run(profile(interaction, None))

        _, kwargs = interaction.followup.send.call_args
        assert kwargs["file"] is fake_file
        assert kwargs["embed"] is fake_embed
        assert kwargs["view"] is fake_view

    def test_sends_without_file_when_none(self):
        interaction = _make_interaction()
        fake_embed = discord.Embed(title="Profile")
        fake_view = MagicMock()

        with (
            patch("commands.user.client", create=True, new=MagicMock()),
            patch("commands.user.hm.log_command", new_callable=AsyncMock),
            patch(
                "commands.user.SupabaseReader.get_database_name", return_value=[]
            ),
            patch(
                "commands.user.SupabaseReader.get_user",
                return_value=SimpleNamespace(),
            ),
            patch(
                "commands.user.Discord_Helper.get_user_embeds",
                new=AsyncMock(return_value=(fake_embed, fake_view, None)),
            ),
        ):
            asyncio.run(profile(interaction, None))

        _, kwargs = interaction.followup.send.call_args
        assert "file" not in kwargs
        assert kwargs["embed"] is fake_embed
        assert kwargs["view"] is fake_view
