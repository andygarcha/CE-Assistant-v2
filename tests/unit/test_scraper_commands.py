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
            mock_table.execute.return_value = MagicMock(data=[
                {"id": "cmd-1", "command": "full_scrape"},
            ])

            result = SupabaseReader.get_pending_commands()

            mock_table.eq.assert_called_once_with("status", "pending")
            mock_table.order.assert_called_once_with("created_at", desc=False)
            assert len(result) == 1


class TestIsLoopRunning:
    def test_returns_true_when_latest_is_started(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[
                {"start": True},
            ])

            assert SupabaseReader.is_loop_running() is True

    def test_returns_false_when_latest_is_finished(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[
                {"start": False},
            ])

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
