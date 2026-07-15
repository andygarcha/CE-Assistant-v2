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

    def test_objective_with_no_requirements_skips_requirement_write(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.upsert.return_value = mock_table
            mock_table.delete.return_value = mock_table
            mock_table.in_.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            objective = make_objective(
                ce_id="obj-aaaa-0000-0000-000000000000",
                achievement_ce_ids=None,
                requirements=None,
            )
            game = make_game(objectives=[objective])
            SupabaseReader.upsert_pending_game_snapshot(game)

            tables_written = [c.args[0] for c in mock_sb.table.call_args_list]
            assert "pendingObjective" in tables_written  # objective row still written
            # only the pre-write delete touches pendingObjectiveRequirement; no upsert
            assert tables_written.count("pendingObjectiveRequirement") == 1


class TestGetPendingGameSnapshotIds:
    def test_returns_set_of_ce_ids(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.execute.return_value = MagicMock(
                data=[{"ce_id": "game-001"}, {"ce_id": "game-002"}]
            )

            result = SupabaseReader.get_pending_game_snapshot_ids()

            mock_sb.table.assert_called_once_with("pendingGame")
            assert result == {"game-001", "game-002"}

    def test_empty_table_returns_empty_set(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            result = SupabaseReader.get_pending_game_snapshot_ids()

            assert result == set()


class TestGetPendingGameSnapshot:
    def test_returns_none_when_not_found(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            result = SupabaseReader.get_pending_game_snapshot("game-missing")

            assert result is None

    def test_reconstructs_game_with_objectives_and_categories(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table

            mock_table.in_.return_value = mock_table

            game_row = {
                "ce_id": "game-001",
                "name": "Test Game",
                "platform": "steam",
                "platform_id": "123456",
                "image_header": "",
                "categories": ["Action"],
                "updated_at_CE": "2026-01-01T00:00:00+00:00",
            }
            objective_row = {
                "ce_id": "obj-aaaa",
                "game_ce_id": "game-001",
                "type": "Primary",
                "name": "Test Objective",
                "description": "desc",
                "points": 10,
                "points_partial": 0,
            }

            def execute_side_effect():
                table_name = mock_sb.table.call_args[0][0]
                if table_name == "pendingGame":
                    return MagicMock(data=[game_row])
                if table_name == "pendingObjective":
                    return MagicMock(data=[objective_row])
                if table_name == "pendingObjectiveRequirement":
                    return MagicMock(data=[])
                raise AssertionError(f"unexpected table {table_name}")

            mock_table.execute.side_effect = execute_side_effect

            result = SupabaseReader.get_pending_game_snapshot("game-001")

            assert result is not None
            assert result.ce_id == "game-001"
            assert result.categories == ["Action"]
            assert len(result.all_objectives) == 1
            assert result.all_objectives[0].ce_id == "obj-aaaa"


class TestDeletePendingGameSnapshot:
    def test_deletes_in_fk_safe_order(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.delete.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[{"ce_id": "obj-aaaa"}])

            SupabaseReader.delete_pending_game_snapshot("game-001")

            tables_touched = [c.args[0] for c in mock_sb.table.call_args_list]
            assert tables_touched == [
                "pendingObjective",
                "pendingObjectiveRequirement",
                "pendingObjective",
                "pendingGame",
            ]

    def test_no_objectives_still_deletes_game_row(self):
        mock_table = MagicMock()
        with patch.object(SupabaseReader, "supabase") as mock_sb:
            mock_sb.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.delete.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            SupabaseReader.delete_pending_game_snapshot("game-001")

            tables_touched = [c.args[0] for c in mock_sb.table.call_args_list]
            assert "pendingGame" in tables_touched
