import asyncio
import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from commands.admin import (
    UnlinkView,
    ban_game,
    clear_roll_portion,
    fail_roll,
    force_unlink,
    loop,
)
from tests.conftest import make_game, make_roll, make_user


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
            patch(
                "commands.admin.hm.send_message", new_callable=AsyncMock
            ) as mock_send,
            patch(
                "commands.admin.SupabaseReader.get_roll", return_value=get_roll_return
            ),
            patch("commands.admin.SupabaseReader.dump_roll"),
            patch("commands.admin.SupabaseReader.get_database_name", return_value=[]),
            patch(
                "commands.admin.SupabaseReader.get_user", side_effect=get_user_return
            ),
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
                asyncio.run(fail_roll(interaction, "bad-id", False))  # type: ignore[arg-type]
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
                asyncio.run(fail_roll(interaction, "roll-001", False))  # type: ignore[arg-type]
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
                asyncio.run(fail_roll(interaction, "roll-001", False))  # type: ignore[arg-type]
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
            patch(
                "commands.admin.SupabaseReader.get_user", return_value=MagicMock()
            ) as mock_get_user,
        ):
            import commands.admin as admin_mod

            with patch.object(admin_mod, "client", create=True, new=MagicMock()):
                asyncio.run(fail_roll(interaction, "roll-001", False))  # type: ignore[arg-type]
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
            patch(
                "commands.admin.SupabaseReader.get_user", return_value=MagicMock()
            ) as mock_get_user,
        ):
            import commands.admin as admin_mod

            with patch.object(admin_mod, "client", create=True, new=MagicMock()):
                asyncio.run(fail_roll(interaction, "roll-001", False))  # type: ignore[arg-type]
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
            patch(
                "commands.admin.hm.send_message", new_callable=AsyncMock
            ) as mock_send,
            patch("commands.admin.SupabaseReader.get_database_name", return_value=[]),
            patch("commands.admin.SupabaseReader.get_user", return_value=None),
        ):
            import commands.admin as admin_mod

            with patch.object(admin_mod, "client", create=True, new=MagicMock()):
                asyncio.run(fail_roll(interaction, "roll-001", False))  # type: ignore[arg-type]
        _, channel, msg = mock_send.call_args[0]
        assert channel == "casino"
        assert "not found" in msg.lower()


# ── clear_roll_portion ───────────────────────────────────────────────────────


class TestClearRollPortion:
    def _make_interaction(self) -> SimpleNamespace:
        return SimpleNamespace(
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

    def _make_member(self, member_id: int = 123) -> SimpleNamespace:
        return SimpleNamespace(id=member_id, mention=f"<@{member_id}>")

    def _run(self, interaction, member, user=None, roll_name="Two Week T2 Streak"):
        import commands.admin as admin_mod

        with (
            patch.object(admin_mod, "client", create=True, new=MagicMock()),
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch("commands.admin.SupabaseReader.get_user", return_value=user),
            patch("commands.admin.SupabaseReader.get_game", return_value=make_game()),
            patch("commands.admin.SupabaseReader.dump_roll") as mock_dump,
        ):
            asyncio.run(
                clear_roll_portion(interaction, member, roll_name)  # type: ignore[arg-type]
            )
        return mock_dump

    def test_unregistered_user_raises_and_notifies(self):
        interaction = self._make_interaction()
        with pytest.raises(Exception, match="Could not find user"):
            self._run(interaction, self._make_member(), user=None)
        msg = interaction.followup.send.call_args[0][0]
        assert "could not find" in msg.lower()

    def test_no_matching_current_roll_sends_message_and_does_not_persist(self):
        interaction = self._make_interaction()
        user = make_user(rolls=[])
        mock_dump = self._run(interaction, self._make_member(), user=user)
        mock_dump.assert_not_called()
        msg = interaction.followup.send.call_args[0][0]
        assert "does not have roll" in msg.lower()

    def test_matching_roll_persists_via_dump_roll(self):
        """Regression: this used to call SupabaseReader.dump_user(user), which
        never touches user.rolls, so the mutation was silently discarded."""
        interaction = self._make_interaction()
        roll = make_roll(
            roll_name="Two Week T2 Streak",
            status="current",
            games=[
                "game-001-0000-0000-000000000000",
                "game-002-0000-0000-000000000000",
            ],
        )
        user = make_user(rolls=[roll])
        mock_dump = self._run(
            interaction, self._make_member(), user=user, roll_name="Two Week T2 Streak"
        )
        mock_dump.assert_called_once_with(roll)

    def test_matching_roll_sets_status_between_stages_and_clears_due_time(self):
        interaction = self._make_interaction()
        roll = make_roll(
            roll_name="Two Week T2 Streak",
            status="current",
            games=[
                "game-001-0000-0000-000000000000",
                "game-002-0000-0000-000000000000",
            ],
            due_time=datetime.datetime(2030, 1, 1, tzinfo=datetime.UTC),
        )
        user = make_user(rolls=[roll])
        self._run(
            interaction, self._make_member(), user=user, roll_name="Two Week T2 Streak"
        )
        assert roll.status == "between_stages"
        assert roll.due_time is None

    def test_matching_roll_removes_last_game(self):
        interaction = self._make_interaction()
        roll = make_roll(
            roll_name="Two Week T2 Streak",
            status="current",
            games=[
                "game-001-0000-0000-000000000000",
                "game-002-0000-0000-000000000000",
            ],
        )
        user = make_user(rolls=[roll])
        self._run(
            interaction, self._make_member(), user=user, roll_name="Two Week T2 Streak"
        )
        assert roll.games == ["game-001-0000-0000-000000000000"]

    def test_success_message_names_removed_game_and_user(self):
        interaction = self._make_interaction()
        roll = make_roll(
            roll_name="Two Week T2 Streak",
            status="current",
            games=[
                "game-001-0000-0000-000000000000",
                "game-002-0000-0000-000000000000",
            ],
        )
        user = make_user(rolls=[roll], display_name="TestUser")
        self._run(
            interaction, self._make_member(), user=user, roll_name="Two Week T2 Streak"
        )
        msg = interaction.followup.send.call_args[0][0]
        assert "TestUser" in msg
        assert "between_stages" in msg


# ── ban_game ──────────────────────────────────────────────────────────────────


class TestBanGame:
    def _make_interaction(self, discord_id: int = 111) -> SimpleNamespace:
        return SimpleNamespace(
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
            user=SimpleNamespace(id=discord_id),
        )

    def _run(
        self,
        interaction,
        game="game-001",
        reason="Too easy.",
        author=None,
        game_exists=True,
    ):
        import commands.admin as admin_mod

        with (
            patch.object(admin_mod, "client", create=True, new=MagicMock()),
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch("commands.admin.SupabaseReader.get_user", return_value=author),
            patch(
                "commands.admin.SupabaseReader.get_game",
                return_value=(make_game() if game_exists else None),
            ),
            patch("commands.admin.SupabaseReader.ban_game") as mock_ban,
        ):
            asyncio.run(ban_game(interaction, game, reason))
        return mock_ban

    def test_unregistered_user_does_not_ban(self):
        interaction = self._make_interaction()
        mock_ban = self._run(interaction, author=None)
        mock_ban.assert_not_called()

    def test_unregistered_user_sends_registration_message(self):
        interaction = self._make_interaction()
        self._run(interaction, author=None)
        msg = interaction.followup.send.call_args[0][0]
        assert "registered" in msg.lower()

    def test_nonexistent_game_does_not_ban(self):
        interaction = self._make_interaction()
        mock_ban = self._run(interaction, author=make_user(), game_exists=False)
        mock_ban.assert_not_called()

    def test_nonexistent_game_sends_error_message(self):
        interaction = self._make_interaction()
        self._run(interaction, author=make_user(), game_exists=False)
        msg = interaction.followup.send.call_args[0][0]
        assert "not a real game" in msg.lower()

    def test_registered_user_and_real_game_bans_with_ce_id(self):
        interaction = self._make_interaction()
        author = make_user(ce_id="banner-ce-id")
        mock_ban = self._run(
            interaction, game="game-001", reason="Too easy.", author=author
        )
        mock_ban.assert_called_once_with("game-001", "Too easy.", "banner-ce-id")

    def test_success_message_names_game_and_reason(self):
        interaction = self._make_interaction()
        author = make_user(display_name="TestAdmin")
        self._run(interaction, game="game-001", reason="Too easy.", author=author)
        msg = interaction.followup.send.call_args[0][0]
        assert "game-001" in msg
        assert "Too easy." in msg


# ── health_check ──────────────────────────────────────────────────────────────


class TestHealthCheck:
    def _make_interaction(self) -> SimpleNamespace:
        return SimpleNamespace(
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

    def _run(
        self,
        interaction,
        include_integrity: bool = False,
        cheap_warnings=None,
        integrity_report=None,
    ):
        import commands.admin as admin_mod
        from commands.admin import health_check

        with (
            patch.object(admin_mod, "client", create=True, new=MagicMock()),
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch(
                "commands.admin.HealthCheck.run_cheap_checks",
                return_value=cheap_warnings or [],
            ),
            patch(
                "commands.admin.LocalCache.run_integrity_check",
                return_value=integrity_report or {},
            ) as mock_integrity,
            patch(
                "commands.admin.hm.send_message", new_callable=AsyncMock
            ) as mock_send,
        ):
            asyncio.run(health_check(interaction, include_integrity))
            return mock_send, mock_integrity

    def test_default_skips_integrity_check(self):
        interaction = self._make_interaction()
        _, mock_integrity = self._run(interaction, include_integrity=False)
        mock_integrity.assert_not_called()

    def test_include_integrity_runs_it(self):
        interaction = self._make_interaction()
        _, mock_integrity = self._run(
            interaction,
            include_integrity=True,
            integrity_report={"synced": [], "removed": [], "schema": []},
        )
        mock_integrity.assert_called_once()

    def test_sends_each_warning_to_privatelog(self):
        interaction = self._make_interaction()
        mock_send, _ = self._run(
            interaction, cheap_warnings=[":hospital: a", ":hospital: b"]
        )
        assert mock_send.await_count == 2
        for call in mock_send.call_args_list:
            _, channel, msg = call[0]
            assert channel == "privatelog"
            assert msg in (":hospital: a", ":hospital: b")

    def test_followup_reports_warning_count(self):
        interaction = self._make_interaction()
        self._run(interaction, cheap_warnings=[":hospital: a", ":hospital: b"])
        msg = interaction.followup.send.call_args[0][0]
        assert "2" in msg

    def test_followup_reports_no_issues_when_clean(self):
        interaction = self._make_interaction()
        self._run(interaction, cheap_warnings=[])
        msg = interaction.followup.send.call_args[0][0]
        assert "no issues" in msg.lower()


# ── force_unlink ──────────────────────────────────────────────────────────────


class TestForceUnlink:
    def _make_interaction(self) -> SimpleNamespace:
        return SimpleNamespace(
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

    def _make_member(self, member_id: int = 123) -> SimpleNamespace:
        return SimpleNamespace(id=member_id, mention=f"<@{member_id}>")

    def _run(self, interaction, member, user=None):
        import commands.admin as admin_mod

        with (
            patch.object(admin_mod, "client", create=True, new=MagicMock()),
            patch("commands.admin.hm.log_command", new_callable=AsyncMock),
            patch("commands.admin.SupabaseReader.get_user", return_value=user),
        ):
            asyncio.run(force_unlink(interaction, member))

    def test_unknown_user_sends_not_found_message(self):
        interaction = self._make_interaction()
        self._run(interaction, self._make_member(), user=None)
        msg = interaction.followup.send.call_args[0][0]
        assert "could not find" in msg.lower()

    def test_unknown_user_does_not_attach_a_view(self):
        interaction = self._make_interaction()
        self._run(interaction, self._make_member(), user=None)
        assert "view" not in interaction.followup.send.call_args.kwargs

    def test_known_user_sends_confirmation_with_view(self):
        interaction = self._make_interaction()
        user = make_user(display_name="TestUser")
        self._run(interaction, self._make_member(456), user=user)
        args, kwargs = interaction.followup.send.call_args
        assert "TestUser" in args[0]
        assert isinstance(kwargs["view"], UnlinkView)

    def test_confirmation_does_not_delete_yet(self):
        interaction = self._make_interaction()
        user = make_user()
        with patch("commands.admin.SupabaseReader.delete_user") as mock_delete:
            self._run(interaction, self._make_member(), user=user)
        mock_delete.assert_not_called()


class TestUnlinkViewYesButton:
    async def _invoke(self, member_id: int, user):
        interaction = SimpleNamespace(
            response=SimpleNamespace(edit_message=AsyncMock())
        )
        view = UnlinkView(member_id)
        with (
            patch("commands.admin.SupabaseReader.get_user", return_value=user),
            patch("commands.admin.SupabaseReader.delete_user") as mock_delete,
        ):
            await UnlinkView.yes_button(view, interaction, MagicMock())  # type: ignore[reportCallIssue] -- class-level access is the undecorated function at runtime
        return interaction, mock_delete

    def _run(self, member_id: int, user):
        return asyncio.run(self._invoke(member_id, user))

    def test_deletes_the_user_by_ce_id(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        _, mock_delete = self._run(123, user)
        mock_delete.assert_called_once_with("user-001-0000-0000-000000000000")

    async def _invoke_no_rolls_check(self, member_id: int, user):
        interaction = SimpleNamespace(
            response=SimpleNamespace(edit_message=AsyncMock())
        )
        view = UnlinkView(member_id)
        with (
            patch("commands.admin.SupabaseReader.get_user", return_value=user),
            patch("commands.admin.SupabaseReader.delete_user"),
            patch("commands.admin.SupabaseReader.delete_roll") as mock_delete_roll,
        ):
            await UnlinkView.yes_button(view, interaction, MagicMock())  # type: ignore[reportCallIssue] -- class-level access is the undecorated function at runtime
        return mock_delete_roll

    def test_does_not_touch_rolls(self):
        user = make_user()
        mock_delete_roll = asyncio.run(self._invoke_no_rolls_check(123, user))
        mock_delete_roll.assert_not_called()

    def test_edits_message_confirming_unlink(self):
        user = make_user(display_name="GoneUser")
        interaction, _ = self._run(123, user)
        msg = interaction.response.edit_message.call_args.kwargs["content"]
        assert "GoneUser" in msg
        assert "unlink" in msg.lower()

    async def _invoke_missing_user(self):
        interaction = SimpleNamespace(
            response=SimpleNamespace(edit_message=AsyncMock())
        )
        view = UnlinkView(999)
        with (
            patch("commands.admin.SupabaseReader.get_user", return_value=None),
            pytest.raises(Exception, match="Could not find user"),
        ):
            await UnlinkView.yes_button(view, interaction, MagicMock())  # type: ignore[reportCallIssue] -- class-level access is the undecorated function at runtime

    def test_missing_user_raises(self):
        asyncio.run(self._invoke_missing_user())
