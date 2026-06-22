from unittest.mock import MagicMock, patch
from Modules import SupabaseReader


class TestWriteScraperUpdate:
    def test_inserts_single_row(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            SupabaseReader.write_scraper_update(
                {
                    "is_embed": False,
                    "channel": "casino",
                    "text": "You won!",
                    "status": "stable",
                }
            )

            mock_sb.table.assert_called_once_with("scraper_updates")
            inserted = mock_table.insert.call_args[0][0]
            assert inserted["channel"] == "casino"
            assert inserted["text"] == "You won!"
            assert inserted["status"] == "stable"

    def test_bulk_inserts_multiple_rows(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            updates = [
                {
                    "is_embed": False,
                    "channel": "casino",
                    "text": "msg1",
                    "status": "stable",
                },
                {
                    "is_embed": True,
                    "channel": "gameadditions",
                    "title": "New!",
                    "status": "stable",
                },
            ]
            SupabaseReader.write_scraper_updates_bulk(updates)

            mock_sb.table.assert_called_once_with("scraper_updates")
            inserted = mock_table.insert.call_args[0][0]
            assert len(inserted) == 2

    def test_bulk_insert_empty_list_is_noop(self):
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            SupabaseReader.write_scraper_updates_bulk([])
            mock_sb.table.assert_not_called()


class TestGetStableUpdates:
    def test_queries_stable_status_ordered_by_created_at(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.execute.return_value = MagicMock(
                data=[
                    {"id": "abc", "channel": "casino", "text": "hello"},
                ]
            )

            result = SupabaseReader.get_stable_updates()

            mock_table.eq.assert_called_once_with("status", "stable")
            mock_table.order.assert_called_once_with("created_at", desc=False)
            assert len(result) == 1
            assert result[0]["id"] == "abc"


class TestMarkUpdatesDelivered:
    def test_updates_status_for_given_ids(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.update.return_value = mock_table
            mock_table.in_.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            SupabaseReader.mark_updates_delivered(["id1", "id2"])

            mock_table.update.assert_called_once_with({"status": "delivered"})
            mock_table.in_.assert_called_once_with("id", ["id1", "id2"])

    def test_empty_ids_is_noop(self):
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            SupabaseReader.mark_updates_delivered([])
            mock_sb.table.assert_not_called()


class TestCleanupDeliveredUpdates:
    def test_deletes_delivered_rows_older_than_threshold(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.delete.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.lt.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[{}, {}])

            count = SupabaseReader.cleanup_delivered_updates(older_than_hours=24)

            mock_table.eq.assert_called_once_with("status", "delivered")
            assert count == 2
