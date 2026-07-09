import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from commands.user import register

ADMIN_ID = 111
TARGET_ID = 222
CE_ID = "user-target-0000-0000-000000000000"


def _make_registered_user(discord_id: int, ce_id: str = "some-other-ce-id"):
    return SimpleNamespace(discord_id=discord_id, ce_id=ce_id)


def _make_interaction(user_id: int = ADMIN_ID) -> SimpleNamespace:
    guild = SimpleNamespace(id=999, roles=[SimpleNamespace(name="CEA Registered")])
    return SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        user=SimpleNamespace(id=user_id, add_roles=AsyncMock()),
        guild=guild,
    )


def _make_discord_user(user_id: int = TARGET_ID) -> SimpleNamespace:
    return SimpleNamespace(id=user_id, mention=f"<@{user_id}>", add_roles=AsyncMock())


def _run(interaction, ce_link=CE_ID, discord_user=None, existing_users=None):
    import commands.user as user_mod

    fake_ce_user = MagicMock()
    fake_ce_user.discord_id = None

    with (
        patch.object(user_mod, "client", create=True, new=MagicMock()),
        patch("commands.user.hm.log_command", new_callable=AsyncMock),
        patch("commands.user.hm.format_ce_link", return_value=CE_ID),
        patch(
            "commands.user.SupabaseReader.get_database_user",
            return_value=existing_users or [],
        ),
        patch(
            "commands.user.CEAPIReader.get_user",
            new=AsyncMock(return_value=fake_ce_user),
        ),
        patch("commands.user.SupabaseReader.bulk_dump_users") as mock_dump,
        patch(
            "commands.user.discord.utils.get",
            return_value=SimpleNamespace(name="CEA Registered"),
        ),
        patch("commands.user.hm.send_message", new_callable=AsyncMock),
    ):
        asyncio.run(register(interaction, ce_link, discord_user))
    return mock_dump


# ── the bug: force-register checked the caller, not the target ────────────────


class TestForceRegisterChecksTarget:
    def test_admin_already_registered_does_not_block_a_new_target(self):
        """The admin running /force-register is already registered under
        their own account; the target is not. This must succeed."""
        interaction = _make_interaction(user_id=ADMIN_ID)
        discord_user = _make_discord_user(user_id=TARGET_ID)
        existing = [_make_registered_user(discord_id=ADMIN_ID)]

        mock_dump = _run(
            interaction, discord_user=discord_user, existing_users=existing
        )

        mock_dump.assert_called_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "already registered" not in msg.lower()

    def test_target_already_registered_still_blocks(self):
        """The actual target is already registered under a different
        account than the admin's -- this must still be blocked."""
        interaction = _make_interaction(user_id=ADMIN_ID)
        discord_user = _make_discord_user(user_id=TARGET_ID)
        existing = [_make_registered_user(discord_id=TARGET_ID)]

        mock_dump = _run(
            interaction, discord_user=discord_user, existing_users=existing
        )

        mock_dump.assert_not_called()
        msg = interaction.followup.send.call_args[0][0]
        assert "already registered" in msg.lower()

    def test_self_register_still_checks_the_caller(self):
        """Normal /register (no discord_user) must still check the caller,
        not silently allow anyone through."""
        interaction = _make_interaction(user_id=ADMIN_ID)
        existing = [_make_registered_user(discord_id=ADMIN_ID)]

        mock_dump = _run(interaction, discord_user=None, existing_users=existing)

        mock_dump.assert_not_called()
        msg = interaction.followup.send.call_args[0][0]
        assert "already registered" in msg.lower()

    def test_ce_id_already_connected_blocks_regardless_of_caller(self):
        interaction = _make_interaction(user_id=ADMIN_ID)
        discord_user = _make_discord_user(user_id=TARGET_ID)
        existing = [_make_registered_user(discord_id=999999, ce_id=CE_ID)]

        mock_dump = _run(
            interaction, discord_user=discord_user, existing_users=existing
        )

        mock_dump.assert_not_called()
        msg = interaction.followup.send.call_args[0][0]
        assert "already connected" in msg.lower()
