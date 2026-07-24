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

import pytest

from commands.user import set_color

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


def _run(interaction, rank_num: int = 8, bounty_colors: list[str] | None = None):
    import commands.user as user_mod

    user_ce = SimpleNamespace(ce_id="ce-1", rank_num=rank_num)

    with (
        patch.object(user_mod, "client", create=True, new=MagicMock()),
        patch("commands.user.hm.log_command", new_callable=AsyncMock),
        patch("commands.user.SupabaseReader.get_user", return_value=user_ce),
        patch(
            "commands.user.SupabaseReader.get_user_bounty_colors",
            return_value=bounty_colors or [],
        ),
    ):
        asyncio.run(set_color(interaction))


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


class TestMissingRoleRaises:
    """set_color intentionally fails loud (sends "error" + raises) rather
    than silently proceeding when a color it expects to find as a guild
    role isn't there -- this guards against COLORS/ROLES silently drifting
    out of alignment. Covers both the base colors (guild misconfiguration)
    and bounty colors (a color exists in BOUNTY_COLORS/was granted, but the
    Discord role for it was never created or was deleted)."""

    def test_missing_base_color_role_raises_and_notifies(self):
        interaction = _make_interaction()
        # Simulate "Black" (EX Rank) never having been created in the guild.
        interaction.guild.roles = [
            r for r in interaction.guild.roles if r.name != "Black"
        ]

        with pytest.raises(Exception, match="Black"):
            _run(interaction)

        interaction.followup.send.assert_called_with("error")

    def test_missing_bounty_color_role_raises_and_notifies(self):
        # "Cotton Candy" was granted (returned by get_user_bounty_colors)
        # but no matching role exists in the guild.
        interaction = _make_interaction(extra_roles=[])

        with pytest.raises(Exception, match="Cotton Candy"):
            _run(interaction, bounty_colors=["Cotton Candy"])

        interaction.followup.send.assert_called_with("error")

    def test_missing_role_does_not_send_the_color_picker_view(self):
        interaction = _make_interaction()
        interaction.guild.roles = [
            r for r in interaction.guild.roles if r.name != "Black"
        ]

        with pytest.raises(Exception, match="Black"):
            _run(interaction)

        # only the "error" call happened -- the view-with-buttons send never ran
        interaction.followup.send.assert_called_once_with("error")
