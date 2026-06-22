import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from commands.admin import loop


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
