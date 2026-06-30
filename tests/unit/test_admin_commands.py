import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

from commands.admin import fail_roll, loop


class TestAdminLoopCommand:
    def _make_interaction(self) -> SimpleNamespace:
        return SimpleNamespace(
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

    def _run(self, interaction, full_scrape=False, send_updates=True):
        import commands.admin as admin_mod

        with (
            patch.object(admin_mod, "client", create=True, new=MagicMock()),
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
        ):
            asyncio.run(
                loop(interaction, full_scrape=full_scrape, send_updates=send_updates)
            )

    def test_full_scrape_writes_full_scrape_command(self):
        interaction = self._make_interaction()

        with (
            patch("commands.admin.SupabaseReader.write_scraper_command") as mock_write,
            patch("commands.admin.SupabaseReader.is_loop_running", return_value=False),
        ):
            self._run(interaction, full_scrape=True)

        mock_write.assert_called_once_with("full_scrape")

    def test_initiate_loop_writes_initiate_loop_command(self):
        interaction = self._make_interaction()

        with (
            patch("commands.admin.SupabaseReader.write_scraper_command") as mock_write,
            patch("commands.admin.SupabaseReader.is_loop_running", return_value=False),
        ):
            self._run(interaction, full_scrape=False)

        mock_write.assert_called_once_with("initiate_loop")

    def test_response_mentions_full_scrape(self):
        interaction = self._make_interaction()

        with (
            patch("commands.admin.SupabaseReader.write_scraper_command"),
            patch("commands.admin.SupabaseReader.is_loop_running", return_value=False),
        ):
            self._run(interaction, full_scrape=True)

        msg = interaction.followup.send.call_args[0][0]
        assert "full scrape" in msg.lower()

    def test_response_mentions_loop(self):
        interaction = self._make_interaction()

        with (
            patch("commands.admin.SupabaseReader.write_scraper_command"),
            patch("commands.admin.SupabaseReader.is_loop_running", return_value=False),
        ):
            self._run(interaction, full_scrape=False)

        msg = interaction.followup.send.call_args[0][0]
        assert "loop" in msg.lower()

    def test_already_running_note_included_when_locked(self):
        interaction = self._make_interaction()

        with (
            patch("commands.admin.SupabaseReader.write_scraper_command"),
            patch("commands.admin.SupabaseReader.is_loop_running", return_value=True),
        ):
            self._run(interaction, full_scrape=True)

        msg = interaction.followup.send.call_args[0][0]
        assert "already in progress" in msg.lower()

    def test_no_already_running_note_when_not_locked(self):
        interaction = self._make_interaction()

        with (
            patch("commands.admin.SupabaseReader.write_scraper_command"),
            patch("commands.admin.SupabaseReader.is_loop_running", return_value=False),
        ):
            self._run(interaction, full_scrape=True)

        msg = interaction.followup.send.call_args[0][0]
        assert "already in progress" not in msg.lower()

    def test_command_still_queued_when_loop_running(self):
        """Even when the loop is running, the command should still be written."""
        interaction = self._make_interaction()

        with (
            patch("commands.admin.SupabaseReader.write_scraper_command") as mock_write,
            patch("commands.admin.SupabaseReader.is_loop_running", return_value=True),
        ):
            self._run(interaction, full_scrape=True)

        mock_write.assert_called_once_with("full_scrape")

    def test_sends_exactly_one_message(self):
        interaction = self._make_interaction()

        with (
            patch("commands.admin.SupabaseReader.write_scraper_command"),
            patch("commands.admin.SupabaseReader.is_loop_running", return_value=True),
        ):
            self._run(interaction, full_scrape=True)

        assert interaction.followup.send.await_count == 1


# ── fail_roll ─────────────────────────────────────────────────────────────────


class TestFailRoll:
    def _make_interaction(self) -> SimpleNamespace:
        return SimpleNamespace(
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

    def _make_roll(self, status: str = "current", partner_ce_id: str | None = None):
        roll = MagicMock()
        roll.status = status
        roll.user_ce_id = "user-001-0000-0000-000000000000"
        roll.partner_ce_id = partner_ce_id
        roll.get_fail_message = MagicMock(return_value="the fail message")
        return roll

    def _run(
        self,
        interaction,
        roll_id: str = "roll-001",
        is_not_current: bool = False,
        get_roll_return=None,
        get_user_side_effect=None,
    ):
        import commands.admin as admin_mod

        mock_user = MagicMock()
        get_user_return = get_user_side_effect or (lambda _: mock_user)

        with (
            patch.object(admin_mod, "client", create=True, new=MagicMock()),
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch("commands.admin.hm.send_message", new_callable=AsyncMock) as mock_send,
            patch("commands.admin.SupabaseReader.get_roll", return_value=get_roll_return),
            patch("commands.admin.SupabaseReader.dump_roll"),
            patch("commands.admin.SupabaseReader.get_database_name", return_value=[]),
            patch("commands.admin.SupabaseReader.get_user", side_effect=get_user_return),
        ):
            asyncio.run(fail_roll(interaction, roll_id, is_not_current))
            return mock_send

    # ── roll not found ────────────────────────────────────────────────────────

    def test_roll_not_found_sends_error(self):
        interaction = self._make_interaction()
        self._run(interaction, roll_id="bad-id", get_roll_return=None)
        msg = interaction.followup.send.call_args[0][0]
        assert "bad-id" in msg

    def test_roll_not_found_does_not_persist(self):
        interaction = self._make_interaction()
        with (
            patch("commands.admin.SupabaseReader.get_roll", return_value=None),
            patch("commands.admin.SupabaseReader.dump_roll") as mock_dump,
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch("commands.admin.hm.send_message", new_callable=AsyncMock),
            patch("commands.admin.SupabaseReader.get_database_name", return_value=[]),
            patch("commands.admin.SupabaseReader.get_user", return_value=MagicMock()),
        ):
            import commands.admin as admin_mod
            with patch.object(admin_mod, "client", create=True, new=MagicMock()):
                asyncio.run(fail_roll(interaction, "bad-id", False))
        mock_dump.assert_not_called()

    # ── non-current roll, flag not set ────────────────────────────────────────

    def test_non_current_roll_blocked_without_flag(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="won")
        self._run(interaction, get_roll_return=roll, is_not_current=False)
        msg = interaction.followup.send.call_args[0][0]
        assert "won" in msg

    def test_non_current_roll_blocked_hints_at_flag(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="removed")
        self._run(interaction, get_roll_return=roll, is_not_current=False)
        msg = interaction.followup.send.call_args[0][0]
        assert "is_not_current" in msg

    def test_non_current_roll_blocked_does_not_persist(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="won")
        with (
            patch("commands.admin.SupabaseReader.get_roll", return_value=roll),
            patch("commands.admin.SupabaseReader.dump_roll") as mock_dump,
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch("commands.admin.hm.send_message", new_callable=AsyncMock),
            patch("commands.admin.SupabaseReader.get_database_name", return_value=[]),
            patch("commands.admin.SupabaseReader.get_user", return_value=MagicMock()),
        ):
            import commands.admin as admin_mod
            with patch.object(admin_mod, "client", create=True, new=MagicMock()):
                asyncio.run(fail_roll(interaction, "roll-001", False))
        mock_dump.assert_not_called()

    # ── current roll succeeds ─────────────────────────────────────────────────

    def test_current_roll_sets_status_to_failed(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="current")
        self._run(interaction, get_roll_return=roll)
        roll.set_status.assert_called_once_with("failed")

    def test_current_roll_persists(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="current")
        with (
            patch("commands.admin.SupabaseReader.get_roll", return_value=roll),
            patch("commands.admin.SupabaseReader.dump_roll") as mock_dump,
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch("commands.admin.hm.send_message", new_callable=AsyncMock),
            patch("commands.admin.SupabaseReader.get_database_name", return_value=[]),
            patch("commands.admin.SupabaseReader.get_user", return_value=MagicMock()),
        ):
            import commands.admin as admin_mod
            with patch.object(admin_mod, "client", create=True, new=MagicMock()):
                asyncio.run(fail_roll(interaction, "roll-001", False))
        mock_dump.assert_called_once_with(roll)

    def test_current_roll_sends_success_message(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="current")
        self._run(interaction, get_roll_return=roll)
        # first followup is the success message to the admin
        msg = interaction.followup.send.call_args_list[0][0][0]
        assert "failed" in msg.lower()

    def test_current_roll_posts_to_casino_channel(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="current")
        mock_send = self._run(interaction, get_roll_return=roll)
        mock_send.assert_awaited_once()
        _, channel, _ = mock_send.call_args[0]
        assert channel == "casino"

    # ── is_not_current override ───────────────────────────────────────────────

    def test_is_not_current_overrides_non_current_status(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="won")
        self._run(interaction, get_roll_return=roll, is_not_current=True)
        roll.set_status.assert_called_once_with("failed")

    def test_is_not_current_still_posts_casino_message(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="removed")
        mock_send = self._run(interaction, get_roll_return=roll, is_not_current=True)
        mock_send.assert_awaited_once()

    # ── casino message routing ────────────────────────────────────────────────

    def test_solo_roll_looks_up_only_main_user(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="current", partner_ce_id=None)
        with (
            patch("commands.admin.SupabaseReader.get_roll", return_value=roll),
            patch("commands.admin.SupabaseReader.dump_roll"),
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch("commands.admin.hm.send_message", new_callable=AsyncMock),
            patch("commands.admin.SupabaseReader.get_database_name", return_value=[]),
            patch("commands.admin.SupabaseReader.get_user", return_value=MagicMock()) as mock_get_user,
        ):
            import commands.admin as admin_mod
            with patch.object(admin_mod, "client", create=True, new=MagicMock()):
                asyncio.run(fail_roll(interaction, "roll-001", False))
        mock_get_user.assert_called_once_with(roll.user_ce_id)

    def test_co_op_roll_looks_up_both_users(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="current", partner_ce_id="partner-001")
        with (
            patch("commands.admin.SupabaseReader.get_roll", return_value=roll),
            patch("commands.admin.SupabaseReader.dump_roll"),
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch("commands.admin.hm.send_message", new_callable=AsyncMock),
            patch("commands.admin.SupabaseReader.get_database_name", return_value=[]),
            patch("commands.admin.SupabaseReader.get_user", return_value=MagicMock()) as mock_get_user,
        ):
            import commands.admin as admin_mod
            with patch.object(admin_mod, "client", create=True, new=MagicMock()):
                asyncio.run(fail_roll(interaction, "roll-001", False))
        called_ids = {c[0][0] for c in mock_get_user.call_args_list}
        assert roll.user_ce_id in called_ids
        assert "partner-001" in called_ids

    def test_user_not_found_sends_fallback_casino_message(self):
        interaction = self._make_interaction()
        roll = self._make_roll(status="current")
        with (
            patch("commands.admin.SupabaseReader.get_roll", return_value=roll),
            patch("commands.admin.SupabaseReader.dump_roll"),
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch("commands.admin.hm.send_message", new_callable=AsyncMock) as mock_send,
            patch("commands.admin.SupabaseReader.get_database_name", return_value=[]),
            patch("commands.admin.SupabaseReader.get_user", return_value=None),
        ):
            import commands.admin as admin_mod
            with patch.object(admin_mod, "client", create=True, new=MagicMock()):
                asyncio.run(fail_roll(interaction, "roll-001", False))
        _, channel, msg = mock_send.call_args[0]
        assert channel == "casino"
        assert "not found" in msg.lower()
