"""Tests for commands.user.set_color, focused on the two bounty-color bugs
that shipped without coverage:

- a bounty color granted while it was in utils.channels.BOUNTY_COLORS, then
  later renamed/removed, used to raise an unhandled KeyError and crash the
  whole command instead of just dropping the stale option.
- bounty-color buttons used to inherit the rank-based `disabled` check meant
  for the base rank colors, so they were always disabled since no rank_num
  reaches the index a bounty color lands at in the combined list.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from commands.user import set_color
from utils.channels import BOUNTY_COLORS

REAL_BOUNTY_EMOJI_BY_NAME = dict(BOUNTY_COLORS)


def _bounty_emoji_id(color_name: str) -> int:
    parsed = discord.PartialEmoji.from_str(REAL_BOUNTY_EMOJI_BY_NAME[color_name])
    assert parsed.id is not None
    return parsed.id


BASE_COLORS = [
    "Gray",
    "Brown",
    "Green",
    "Blue",
    "Purple",
    "Orange",
    "Yellow",
    "Red",
    "Black",
]


def _make_role(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name)


def _make_interaction(extra_roles: list[str] | None = None) -> SimpleNamespace:
    roles = [_make_role(c) for c in BASE_COLORS]
    roles += [_make_role(c) for c in (extra_roles or [])]
    guild = SimpleNamespace(id=1, roles=roles)
    return SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        user=SimpleNamespace(id=42),
        guild=guild,
    )


def _run(
    interaction,
    rank_num: int = 8,
    bounty_colors: list[str] | None = None,
    owned_emoji_ids: set[int] | None = None,
    fetch_application_emojis_side_effect: BaseException | None = None,
):
    import commands.user as user_mod

    user_ce = SimpleNamespace(ce_id="ce-1", rank_num=rank_num)

    # _bounty_emoji_ids is a process-lifetime cache in commands.user -- reset
    # it so each test gets its own fetch_application_emojis() call rather
    # than reusing whatever a previous test cached.
    user_mod._bounty_emoji_ids = None
    fake_emojis = [SimpleNamespace(id=eid) for eid in (owned_emoji_ids or set())]

    with (
        patch.object(user_mod, "client", create=True, new=MagicMock()) as mock_client,
        patch("commands.user.hm.log_command", new_callable=AsyncMock),
        patch("commands.user.SupabaseReader.get_user", return_value=user_ce),
        patch(
            "commands.user.SupabaseReader.get_user_bounty_colors",
            return_value=bounty_colors or [],
        ),
    ):
        mock_client.fetch_application_emojis = AsyncMock(
            return_value=fake_emojis, side_effect=fetch_application_emojis_side_effect
        )
        asyncio.run(set_color(interaction))
    return mock_client


class TestStaleBountyColorIsSkippedNotCrashed:
    def test_does_not_raise(self):
        interaction = _make_interaction()
        # "Extinct Color" simulates a grant that predates a BOUNTY_COLORS
        # rename/removal -- it is not present in utils.channels.BOUNTY_COLORS.
        _run(interaction, bounty_colors=["Extinct Color"])
        interaction.followup.send.assert_called_once()

    def test_still_shows_the_base_colors(self):
        interaction = _make_interaction()
        _run(interaction, bounty_colors=["Extinct Color"])
        view = interaction.followup.send.call_args.kwargs["view"]
        # 9 base color buttons + 1 clear button; the stale bounty color
        # contributes nothing since it never resolved to a role.
        assert len(view.children) == 10

    def test_valid_and_stale_bounty_colors_together(self):
        interaction = _make_interaction(extra_roles=["Cotton Candy"])
        _run(interaction, bounty_colors=["Cotton Candy", "Extinct Color"])
        view = interaction.followup.send.call_args.kwargs["view"]
        # 9 base + 1 valid bounty + 1 clear button.
        assert len(view.children) == 11


class TestBountyColorButtonsAreNeverRankDisabled:
    def test_bounty_button_enabled_at_lowest_rank(self):
        interaction = _make_interaction(extra_roles=["Cotton Candy"])
        _run(interaction, rank_num=0, bounty_colors=["Cotton Candy"])
        view = interaction.followup.send.call_args.kwargs["view"]
        # Bounty button is appended right after the 9 base-color buttons.
        bounty_button = view.children[9]
        assert bounty_button.disabled is False

    def test_base_color_buttons_still_respect_rank(self):
        interaction = _make_interaction(extra_roles=["Cotton Candy"])
        _run(interaction, rank_num=0, bounty_colors=["Cotton Candy"])
        view = interaction.followup.send.call_args.kwargs["view"]
        # rank_num=0 (E Rank) should only leave the first base button (Gray)
        # enabled; every other base color is above the user's rank.
        assert view.children[0].disabled is False
        assert all(button.disabled for button in view.children[1:9])


class TestBountyEmojiFallsBackToLabelWhenNotOwned:
    """Bounty color emojis are Application Emojis (uploaded to this bot's
    own Developer Portal), not guild emojis. A bot that doesn't have a
    given emoji uploaded (e.g. a test bot) can't send a button referencing
    it, so set_color checks ownership via fetch_application_emojis() and
    falls back to a plain text label instead."""

    def test_falls_back_to_label_when_bot_does_not_own_the_emoji(self):
        interaction = _make_interaction(extra_roles=["Cotton Candy"])
        _run(
            interaction,
            bounty_colors=["Cotton Candy"],
            owned_emoji_ids=set(),  # bot owns none of its application emojis
        )
        view = interaction.followup.send.call_args.kwargs["view"]
        bounty_button = view.children[9]
        assert bounty_button.emoji is None
        assert bounty_button.label == "Cotton Candy"

    def test_uses_the_real_emoji_when_the_bot_owns_it(self):
        interaction = _make_interaction(extra_roles=["Cotton Candy"])
        _run(
            interaction,
            bounty_colors=["Cotton Candy"],
            owned_emoji_ids={_bounty_emoji_id("Cotton Candy")},
        )
        view = interaction.followup.send.call_args.kwargs["view"]
        bounty_button = view.children[9]
        assert bounty_button.emoji is not None
        assert bounty_button.label is None

    def test_base_color_buttons_are_unaffected(self):
        interaction = _make_interaction(extra_roles=["Cotton Candy"])
        _run(interaction, bounty_colors=["Cotton Candy"], owned_emoji_ids=set())
        view = interaction.followup.send.call_args.kwargs["view"]
        assert all(button.label is None for button in view.children[:9])
        assert all(button.emoji is not None for button in view.children[:9])

    def test_does_not_fetch_application_emojis_when_no_bounty_colors_granted(self):
        interaction = _make_interaction()
        mock_client = _run(interaction, bounty_colors=[])
        mock_client.fetch_application_emojis.assert_not_called()

    def test_fetch_failure_falls_back_to_labels_instead_of_crashing(self):
        interaction = _make_interaction(extra_roles=["Cotton Candy"])
        _run(
            interaction,
            bounty_colors=["Cotton Candy"],
            fetch_application_emojis_side_effect=discord.DiscordException("boom"),
        )
        view = interaction.followup.send.call_args.kwargs["view"]
        bounty_button = view.children[9]
        assert bounty_button.label == "Cotton Candy"


class TestMissingRoleRaises:
    """set_color intentionally fails loud (sends an error naming the
    missing color(s), then raises) rather than silently proceeding when a
    color it expects to find as a guild role isn't there -- this guards
    against COLORS/ROLES silently drifting out of alignment. Covers both
    the base colors (guild misconfiguration) and bounty colors (a color
    exists in BOUNTY_COLORS/was granted, but the Discord role for it was
    never created or was deleted)."""

    def test_missing_base_color_role_raises_and_notifies(self):
        interaction = _make_interaction()
        # Simulate "Black" (EX Rank) never having been created in the guild.
        interaction.guild.roles = [
            r for r in interaction.guild.roles if r.name != "Black"
        ]

        with pytest.raises(Exception, match="Black"):
            _run(interaction)

        msg = interaction.followup.send.call_args[0][0]
        assert "Black" in msg

    def test_missing_bounty_color_role_raises_and_notifies(self):
        # "Cotton Candy" was granted (returned by get_user_bounty_colors)
        # but no matching role exists in the guild.
        interaction = _make_interaction(extra_roles=[])

        with pytest.raises(Exception, match="Cotton Candy"):
            _run(interaction, bounty_colors=["Cotton Candy"])

        msg = interaction.followup.send.call_args[0][0]
        assert "Cotton Candy" in msg

    def test_missing_role_does_not_send_the_color_picker_view(self):
        interaction = _make_interaction()
        interaction.guild.roles = [
            r for r in interaction.guild.roles if r.name != "Black"
        ]

        with pytest.raises(Exception, match="Black"):
            _run(interaction)

        # only the error-notification call happened -- the view-with-buttons
        # send never ran
        interaction.followup.send.assert_called_once()
        assert "view" not in interaction.followup.send.call_args.kwargs
