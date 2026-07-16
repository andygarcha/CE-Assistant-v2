import datetime
from unittest.mock import MagicMock, patch

from Modules import SupabaseReader


class TestWriteScraperCommand:
    def test_inserts_pending_command(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[{"id": "cmd-1"}])

            result = SupabaseReader.write_scraper_command("full_scrape")

            inserted = mock_table.insert.call_args[0][0]
            assert inserted["command"] == "full_scrape"
            assert inserted["status"] == "pending"
            assert result == "cmd-1"


class TestGetPendingCommands:
    def test_queries_pending_ordered_by_created_at(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.execute.return_value = MagicMock(
                data=[
                    {"id": "cmd-1", "command": "full_scrape"},
                ]
            )

            result = SupabaseReader.get_pending_commands()

            mock_table.eq.assert_called_once_with("status", "pending")
            mock_table.order.assert_called_once_with("created_at", desc=False)
            assert len(result) == 1


class TestStartLoopRun:
    def test_records_fullscrape_flag(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[{"id": "run-1"}])

            result = SupabaseReader.start_loop_run(full_scrape=True)

            inserted = mock_table.insert.call_args[0][0]
            assert inserted["fullscrape"] is True
            assert inserted["start"] is True
            assert result == "run-1"

    def test_defaults_fullscrape_to_false(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[{"id": "run-1"}])

            SupabaseReader.start_loop_run()

            inserted = mock_table.insert.call_args[0][0]
            assert inserted["fullscrape"] is False


class TestRecentFullScrape:
    def test_true_when_a_recent_fullscrape_row_exists(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.gte.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[{"id": "run-1"}])

            assert SupabaseReader.recent_full_scrape(hours=24) is True
            mock_table.eq.assert_called_once_with("fullscrape", True)

    def test_false_when_no_recent_fullscrape_row(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.gte.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            assert SupabaseReader.recent_full_scrape(hours=24) is False

    def test_cutoff_is_hours_param_in_the_past(self):
        """The `hours` argument should control how far back the cutoff is,
        not a hardcoded 24. Regression test for the cutoff-math bug this
        would catch, e.g. a stray `hours * 60` or an unused `hours` param."""
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.gte.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            before_call = datetime.datetime.now(datetime.UTC)
            SupabaseReader.recent_full_scrape(hours=5)
            after_call = datetime.datetime.now(datetime.UTC)

            cutoff_arg = mock_table.gte.call_args[0][1]
            cutoff = datetime.datetime.fromisoformat(cutoff_arg)

            assert (before_call - datetime.timedelta(hours=5)) <= cutoff
            assert cutoff <= (after_call - datetime.timedelta(hours=5))
            mock_table.gte.assert_called_once_with("ran_at", cutoff_arg)


class TestIsLoopRunning:
    def test_returns_true_when_latest_is_started(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = MagicMock(
                data=[
                    {"start": True},
                ]
            )

            assert SupabaseReader.is_loop_running() is True

    def test_returns_false_when_latest_is_finished(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = MagicMock(
                data=[
                    {"start": False},
                ]
            )

            assert SupabaseReader.is_loop_running() is False

    def test_returns_false_when_no_rows(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            assert SupabaseReader.is_loop_running() is False
