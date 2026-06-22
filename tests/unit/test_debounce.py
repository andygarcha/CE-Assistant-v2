from unittest.mock import MagicMock, patch
from Modules import SupabaseReader


class TestGetPendingGameUpdates:
    def test_queries_pending_status(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.not_.is_.return_value = mock_table
            mock_table.execute.return_value = MagicMock(
                data=[
                    {"id": "p1", "game_ce_id": "game-001", "status": "pending"},
                ]
            )

            result = SupabaseReader.get_pending_game_updates()
            assert len(result) == 1
            assert result[0]["game_ce_id"] == "game-001"


class TestPromotePendingToStable:
    def test_updates_status(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.update.return_value = mock_table
            mock_table.in_.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            SupabaseReader.promote_pending_to_stable(["p1", "p2"])

            mock_table.update.assert_called_once_with({"status": "stable"})
            mock_table.in_.assert_called_once_with("id", ["p1", "p2"])

    def test_empty_ids_is_noop(self):
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            SupabaseReader.promote_pending_to_stable([])
            mock_sb.table.assert_not_called()


class TestUpsertPendingUpdate:
    def test_inserts_when_no_existing(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])
            mock_table.insert.return_value = mock_table

            update = {"game_ce_id": "game-001", "title": "New!", "status": "pending"}
            SupabaseReader.upsert_pending_update(update)

            mock_table.insert.assert_called_once_with(update)

    def test_updates_when_existing(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[{"id": "existing-1"}])
            mock_table.update.return_value = mock_table

            update = {
                "game_ce_id": "game-001",
                "title": "Updated!",
                "status": "pending",
            }
            SupabaseReader.upsert_pending_update(update)

            mock_table.update.assert_called_once_with(update)
