from unittest.mock import MagicMock, patch

from Modules import SupabaseReader
from tests.conftest import make_game, make_objective


class TestUpsertPendingGameSnapshot:
    def test_writes_game_row_with_categories(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.upsert.return_value = mock_table
            mock_table.delete.return_value = mock_table
            mock_table.in_.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            game = make_game(
                ce_id="game-001-0000-0000-000000000000",
                game_name="Test Game",
                categories=["Action", "Arcade"],
                objectives=[],
            )
            SupabaseReader.upsert_pending_game_snapshot(game)

            game_call = next(
                c for c in mock_sb.table.call_args_list if c.args[0] == "pendingGame"
            )
            assert game_call.args[0] == "pendingGame"
            inserted = mock_table.upsert.call_args[0][0]
            assert inserted["ce_id"] == "game-001-0000-0000-000000000000"
            assert inserted["name"] == "Test Game"
            assert inserted["categories"] == ["Action", "Arcade"]

    def test_writes_objectives_and_requirements(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.upsert.return_value = mock_table
            mock_table.delete.return_value = mock_table
            mock_table.in_.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            objective = make_objective(
                ce_id="obj-aaaa-0000-0000-000000000000",
                point_value=10,
                achievement_ce_ids=["ach-1"],
                requirements="Beat the boss.",
            )
            game = make_game(objectives=[objective])
            SupabaseReader.upsert_pending_game_snapshot(game)

            tables_written = [c.args[0] for c in mock_sb.table.call_args_list]
            assert "pendingObjective" in tables_written
            assert "pendingObjectiveRequirement" in tables_written

    def test_deletes_old_requirements_before_reinserting(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.upsert.return_value = mock_table
            mock_table.delete.return_value = mock_table
            mock_table.in_.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            objective = make_objective(ce_id="obj-aaaa-0000-0000-000000000000")
            game = make_game(objectives=[objective])
            SupabaseReader.upsert_pending_game_snapshot(game)

            mock_table.delete.assert_any_call()
            mock_table.in_.assert_any_call(
                "objective_ce_id", ["obj-aaaa-0000-0000-000000000000"]
            )

    def test_no_objectives_skips_objective_and_requirement_writes(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.upsert.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            game = make_game(objectives=[])
            SupabaseReader.upsert_pending_game_snapshot(game)

            tables_written = [c.args[0] for c in mock_sb.table.call_args_list]
            assert "pendingObjective" not in tables_written
            assert "pendingObjectiveRequirement" not in tables_written
