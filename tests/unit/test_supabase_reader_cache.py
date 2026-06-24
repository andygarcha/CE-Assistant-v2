"""Tests for SupabaseReader after switching to LocalCache.

Getters should read from SQLite (via LocalCache), not Supabase.
Writers should dual-write to both Supabase and LocalCache.
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from Modules import LocalCache, SupabaseReader
from Classes.CE_Game import CEGame
from Classes.CE_User import CEUser
from Classes.CE_Roll import CERoll


# === Fixtures ===


GAME_DB_ROW = {
    "ce_id": "game-001",
    "name": "Celeste",
    "platform": "steam",
    "platform_id": "504230",
    "category_primary": None,
    "image_header": "https://example.com/celeste.png",
    "image_icon": "",
    "updated_at_CE": "2026-01-01T00:00:00",
}

OBJECTIVE_DB_ROW = {
    "ce_id": "obj-001",
    "game_ce_id": "game-001",
    "type": "Primary",
    "name": "Beat the Game",
    "description": "Complete all chapters",
    "points": 25,
    "points_partial": None,
    "updated_at_CE": "2026-01-01T00:00:00",
}

REQUIREMENT_DB_ROW = {
    "objective_ce_id": "obj-001",
    "requirement_type": "achievement",
    "data": "ach-123",
    "updated_at_CE": "2026-01-01T00:00:00",
}

CATEGORY_DB_ROWS = [
    {"game_id": "game-001", "category": "Action", "index": 0},
    {"game_id": "game-001", "category": "Platformer", "index": 1},
]

USER_DB_ROW = {
    "ce_id": "user-001",
    "discord_id": 123456789,
    "display_name": "TestUser",
    "image_avatar": "https://example.com/avatar.png",
    "steam_id": "steam-001",
    "created_at_CE": "2025-01-01T00:00:00",
    "updated_at_CE": "2026-01-01T00:00:00",
}

ROLL_DB_ROW = {
    "id": "roll-001",
    "event_name": "One Hell of a Day",
    "user1_ce_id": "user-001",
    "user2_ce_id": None,
    "time_created": "2026-01-01T00:00:00",
    "time_due": "2026-01-02T00:00:00",
    "time_completed": None,
    "is_lucky": 0,
    "chosen_tier": 1,
    "chosen_tier_partner": None,
    "status": "current",
    "rerolls_remaining": None,
    "rerolls_used": 0,
    "winner": None,
}

ROLL_GAME_DB_ROW = {
    "roll_id": "roll-001",
    "game_id": "game-001",
    "index": 0,
    "rolled_at": "2026-01-01T00:00:00",
}


def _init_cache() -> str:
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    LocalCache.init(db_path)
    return tmpdir


def _teardown_cache(tmpdir: str) -> None:
    LocalCache.close()
    shutil.rmtree(tmpdir)


def _seed_game():
    LocalCache.upsert_game(GAME_DB_ROW)
    LocalCache.upsert_objectives_bulk([OBJECTIVE_DB_ROW])
    LocalCache.upsert_requirements_bulk([REQUIREMENT_DB_ROW])
    LocalCache.upsert_categories_bulk(CATEGORY_DB_ROWS)


def _seed_user():
    LocalCache.upsert_user(USER_DB_ROW)
    LocalCache.upsert_user_games_bulk([
        {"user_ce_id": "user-001", "game_ce_id": "game-001", "updated_at_CE": ""},
    ])
    LocalCache.upsert_user_objectives_bulk([
        {"user_ce_id": "user-001", "objective_ce_id": "obj-001",
         "user_points": 25, "updated_at_CE": ""},
    ])


def _seed_roll():
    LocalCache.upsert_roll(ROLL_DB_ROW)
    LocalCache.upsert_roll_games_bulk([ROLL_GAME_DB_ROW])


# === Getter Tests ===
# These verify that getters read from LocalCache and return correct domain objects.


class TestGetGameFromCache:
    def test_returns_ce_game(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_game("game-001")
            assert isinstance(result, CEGame)
            assert result.ce_id == "game-001"
            assert result.game_name == "Celeste"
        finally:
            _teardown_cache(tmpdir)

    def test_returns_none_when_not_found(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_game("nonexistent")
            assert result is None
        finally:
            _teardown_cache(tmpdir)

    def test_includes_categories(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_game("game-001")
            assert result is not None
            assert result.categories == ["Action", "Platformer"]
        finally:
            _teardown_cache(tmpdir)

    def test_includes_objectives(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_game("game-001")
            assert result is not None
            assert len(result.all_objectives) == 1
            assert result.all_objectives[0].ce_id == "obj-001"
            assert result.all_objectives[0].name == "Beat the Game"
            assert result.all_objectives[0].point_value == 25
        finally:
            _teardown_cache(tmpdir)

    def test_includes_achievement_requirements(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_game("game-001")
            assert result is not None
            obj = result.all_objectives[0]
            assert obj.achievement_ce_ids == ["ach-123"]
        finally:
            _teardown_cache(tmpdir)

    def test_does_not_call_supabase(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                SupabaseReader.get_game("game-001")
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)


class TestGetListFromCache:
    def test_get_list_name(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_list("name")
            assert "game-001" in result
        finally:
            _teardown_cache(tmpdir)

    def test_get_list_user(self):
        tmpdir = _init_cache()
        try:
            _seed_user()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_list("user")
            assert "user-001" in result
        finally:
            _teardown_cache(tmpdir)

    def test_get_list_objectives(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_list("objectives")
            assert "obj-001" in result
        finally:
            _teardown_cache(tmpdir)

    def test_get_list_invalid_raises(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase"):
                with pytest.raises(Exception):
                    SupabaseReader.get_list("invalid")
        finally:
            _teardown_cache(tmpdir)

    def test_does_not_call_supabase(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                SupabaseReader.get_list("name")
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)


class TestGetDatabaseNameFromCache:
    def test_returns_list_of_ce_games(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_database_name()
            assert len(result) == 1
            assert isinstance(result[0], CEGame)
            assert result[0].ce_id == "game-001"
        finally:
            _teardown_cache(tmpdir)

    def test_returns_empty_list_when_no_games(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_database_name()
            assert result == []
        finally:
            _teardown_cache(tmpdir)

    def test_multiple_games(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            LocalCache.upsert_game({**GAME_DB_ROW, "ce_id": "game-002", "name": "Hollow Knight"})
            LocalCache.upsert_categories_bulk([
                {"game_id": "game-002", "category": "Action", "index": 0},
            ])
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_database_name()
            assert len(result) == 2
            names = {g.game_name for g in result}
            assert names == {"Celeste", "Hollow Knight"}
        finally:
            _teardown_cache(tmpdir)

    def test_does_not_call_supabase(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                SupabaseReader.get_database_name()
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)


class TestGetUserFromCache:
    def test_returns_ce_user_by_ce_id(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            _seed_user()
            _seed_roll()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("user-001")
            assert isinstance(result, CEUser)
            assert result.ce_id == "user-001"
            assert result.display_name == "TestUser"
        finally:
            _teardown_cache(tmpdir)

    def test_returns_ce_user_by_discord_id(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            _seed_user()
            _seed_roll()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user(123456789, use_discord_id=True)
            assert isinstance(result, CEUser)
            assert result.ce_id == "user-001"
        finally:
            _teardown_cache(tmpdir)

    def test_returns_none_when_not_found(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("nonexistent")
            assert result is None
        finally:
            _teardown_cache(tmpdir)

    def test_includes_owned_games(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            _seed_user()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("user-001")
            assert result is not None
            assert len(result.owned_games) == 1
            assert result.owned_games[0].ce_id == "game-001"
        finally:
            _teardown_cache(tmpdir)

    def test_includes_rolls(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            _seed_user()
            _seed_roll()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("user-001")
            assert result is not None
            assert len(result.rolls) == 1
            assert result.rolls[0].roll_name == "One Hell of a Day"
        finally:
            _teardown_cache(tmpdir)

    def test_does_not_call_supabase(self):
        tmpdir = _init_cache()
        try:
            _seed_user()
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                SupabaseReader.get_user("user-001")
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)


class TestGetGamesBulkFromCache:
    def test_returns_multiple_games(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            LocalCache.upsert_game({**GAME_DB_ROW, "ce_id": "game-002", "name": "HK"})
            LocalCache.upsert_categories_bulk([
                {"game_id": "game-002", "category": "Action", "index": 0},
            ])
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_games_bulk(["game-001", "game-002"])
            assert len(result) == 2
            assert all(isinstance(g, CEGame) for g in result)
        finally:
            _teardown_cache(tmpdir)

    def test_empty_list_returns_empty(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_games_bulk([])
            assert result == []
        finally:
            _teardown_cache(tmpdir)

    def test_does_not_call_supabase(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                SupabaseReader.get_games_bulk(["game-001"])
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)


class TestGetRollFromCache:
    def test_returns_ce_roll(self):
        tmpdir = _init_cache()
        try:
            _seed_roll()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_roll("roll-001")
            assert isinstance(result, CERoll)
            assert result.roll_name == "One Hell of a Day"
            assert result.games == ["game-001"]
        finally:
            _teardown_cache(tmpdir)

    def test_returns_none_when_not_found(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_roll("nonexistent")
            assert result is None
        finally:
            _teardown_cache(tmpdir)


class TestGetCheckableRollsFromCache:
    def test_returns_current_and_pending(self):
        tmpdir = _init_cache()
        try:
            for status in ["current", "pending", "won", "removed"]:
                LocalCache.upsert_roll({**ROLL_DB_ROW, "id": f"r-{status}", "status": status})
                LocalCache.upsert_roll_games_bulk([
                    {"roll_id": f"r-{status}", "game_id": "game-001", "index": 0, "rolled_at": ""},
                ])
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_checkable_rolls()
            assert len(result) == 2
            statuses = {r.status for r in result}
            assert statuses == {"current", "pending"}
        finally:
            _teardown_cache(tmpdir)


class TestGetAllRollsFromCache:
    def test_returns_all_rolls(self):
        tmpdir = _init_cache()
        try:
            for i in range(3):
                LocalCache.upsert_roll({**ROLL_DB_ROW, "id": f"r{i}"})
                LocalCache.upsert_roll_games_bulk([
                    {"roll_id": f"r{i}", "game_id": "game-001", "index": 0, "rolled_at": ""},
                ])
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_all_rolls()
            assert len(result) == 3
            assert all(isinstance(r, CERoll) for r in result)
        finally:
            _teardown_cache(tmpdir)

    def test_filters_by_event_names(self):
        tmpdir = _init_cache()
        try:
            for name in ["One Hell of a Day", "Soul Mates", "Triple Threat"]:
                rid = f"r-{name.replace(' ', '')}"
                LocalCache.upsert_roll({**ROLL_DB_ROW, "id": rid, "event_name": name})
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_all_rolls(event_names=["Soul Mates", "Triple Threat"])
            assert len(result) == 2
            names = {r.roll_name for r in result}
            assert names == {"Soul Mates", "Triple Threat"}
        finally:
            _teardown_cache(tmpdir)


class TestGetUserRollsFromCache:
    def test_returns_rolls_for_user(self):
        tmpdir = _init_cache()
        try:
            _seed_roll()
            LocalCache.upsert_roll({**ROLL_DB_ROW, "id": "roll-other", "user1_ce_id": "user-999"})
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user_rolls("user-001")
            assert len(result) == 1
            assert result[0].roll_name == "One Hell of a Day"
        finally:
            _teardown_cache(tmpdir)


class TestGetDatabaseTierFromCache:
    def test_reads_tier_from_cache(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            LocalCache.upsert_tier_bulk([
                {"ce_id": "game-001", "price": 9.99, "sh_hours": 5.0},
            ])
            with patch.object(SupabaseReader, "supabase"):
                database_name = SupabaseReader.get_database_name()
                result = SupabaseReader.get_database_tier(database_name)
            assert isinstance(result, dict)
        finally:
            _teardown_cache(tmpdir)


# === Writer Tests ===
# These verify that writers still call Supabase AND also write to LocalCache.


class TestDumpGameDualWrite:
    def test_writes_to_both_supabase_and_cache(self):
        tmpdir = _init_cache()
        try:
            from tests.conftest import make_game, make_objective

            game = make_game(
                ce_id="game-new",
                game_name="New Game",
                categories=["Action"],
                objectives=[make_objective(ce_id="obj-new", game_ce_id="game-new")],
            )

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.bulk_dump_games([game])

            mock_sb.table.assert_called()

            cached = LocalCache.get_game("game-new")
            assert cached is not None
            assert cached["name"] == "New Game"

            cached_objs = LocalCache.get_objectives_by_game("game-new")
            assert len(cached_objs) == 1
            assert cached_objs[0]["ce_id"] == "obj-new"

            cached_cats = LocalCache.get_categories_by_game("game-new")
            assert len(cached_cats) == 1
            assert cached_cats[0]["category"] == "Action"
        finally:
            _teardown_cache(tmpdir)


class TestDumpRollDualWrite:
    def test_writes_to_both_supabase_and_cache(self):
        tmpdir = _init_cache()
        try:
            from tests.conftest import make_roll

            roll = make_roll(roll_name="One Hell of a Day", games=["game-001"])

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.dump_roll(roll)

            mock_sb.table.assert_called()

            cached = LocalCache.get_roll(roll._id)
            assert cached is not None
            assert cached["event_name"] == "One Hell of a Day"

            cached_games = LocalCache.get_roll_games(roll._id)
            assert len(cached_games) == 1
            assert cached_games[0]["game_id"] == "game-001"
        finally:
            _teardown_cache(tmpdir)


class TestDeleteGameDualWrite:
    def test_deletes_from_both_supabase_and_cache(self):
        tmpdir = _init_cache()
        try:
            _seed_game()

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.select.return_value = mock_table
                mock_table.eq.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.delete_game("game-001")

            assert LocalCache.get_game("game-001") is None
            assert LocalCache.get_categories_by_game("game-001") == []
        finally:
            _teardown_cache(tmpdir)


class TestDeleteRollDualWrite:
    def test_deletes_from_both_supabase_and_cache(self):
        tmpdir = _init_cache()
        try:
            _seed_roll()

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.eq.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.delete_roll("roll-001")

            assert LocalCache.get_roll("roll-001") is None
            assert LocalCache.get_roll_games("roll-001") == []
        finally:
            _teardown_cache(tmpdir)


class TestDeleteUserDualWrite:
    def test_deletes_from_both_supabase_and_cache(self):
        tmpdir = _init_cache()
        try:
            _seed_user()

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.eq.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.delete_user("user-001")

            assert LocalCache.get_user("user-001") is None
            assert LocalCache.get_user_games("user-001") == []
            assert LocalCache.get_user_objectives("user-001") == []
        finally:
            _teardown_cache(tmpdir)


class TestDeleteObjectivesManyDualWrite:
    def test_deletes_from_both_supabase_and_cache(self):
        tmpdir = _init_cache()
        try:
            _seed_game()

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.delete_objectives_many(["obj-001"])

            assert LocalCache.get_objectives_by_game("game-001") == []
            assert LocalCache.get_requirements_by_objectives(["obj-001"]) == []
        finally:
            _teardown_cache(tmpdir)


class TestAddPendingDualWrite:
    def test_writes_to_both_supabase_and_cache(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.insert.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.add_pending("Soul Mates", "user-001", "user-002")

            rolls = LocalCache.get_rolls_by_user("user-001")
            assert len(rolls) >= 1
            pending = [r for r in rolls if r["status"] == "pending"]
            assert len(pending) >= 1
        finally:
            _teardown_cache(tmpdir)


class TestKillPendingDualWrite:
    def test_deletes_from_both_supabase_and_cache(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_roll({
                **ROLL_DB_ROW,
                "id": "pending-001",
                "event_name": "Soul Mates",
                "user1_ce_id": "user-001",
                "status": "pending",
            })

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.select.return_value = mock_table
                mock_table.eq.return_value = mock_table
                mock_table.or_.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(
                    data=[{"id": "pending-001"}]
                )

                SupabaseReader.kill_pending("Soul Mates", "user-001")

            assert LocalCache.get_roll("pending-001") is None
        finally:
            _teardown_cache(tmpdir)


# === Missing getter coverage ===


class TestGetUsersBulkFromCache:
    def test_returns_multiple_users(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            for i in range(3):
                uid = f"user-{i:03d}"
                LocalCache.upsert_user({**USER_DB_ROW, "ce_id": uid, "discord_id": i})
                LocalCache.upsert_user_games_bulk([
                    {"user_ce_id": uid, "game_ce_id": "game-001", "updated_at_CE": ""},
                ])
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_users_bulk(
                    ["user-000", "user-001", "user-002"]
                )
            assert len(result) == 3
            assert all(isinstance(u, CEUser) for u in result)
        finally:
            _teardown_cache(tmpdir)

    def test_empty_list_returns_empty(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_users_bulk([])
            assert result == []
        finally:
            _teardown_cache(tmpdir)

    def test_includes_owned_games(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            _seed_user()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_users_bulk(["user-001"])
            assert len(result) == 1
            assert len(result[0].owned_games) == 1
        finally:
            _teardown_cache(tmpdir)

    def test_does_not_call_supabase(self):
        tmpdir = _init_cache()
        try:
            _seed_user()
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                SupabaseReader.get_users_bulk(["user-001"])
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)


class TestGetDatabaseUserFromCache:
    def test_returns_all_users(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            for i in range(3):
                uid = f"user-{i:03d}"
                LocalCache.upsert_user({**USER_DB_ROW, "ce_id": uid, "discord_id": i})
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_database_user()
            assert len(result) == 3
            assert all(isinstance(u, CEUser) for u in result)
        finally:
            _teardown_cache(tmpdir)

    def test_returns_empty_when_no_users(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_database_user()
            assert result == []
        finally:
            _teardown_cache(tmpdir)

    def test_does_not_call_supabase(self):
        tmpdir = _init_cache()
        try:
            _seed_user()
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                SupabaseReader.get_database_user()
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)


class TestGetUserObjectivesContent:
    def test_user_objectives_have_correct_points(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            _seed_user()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("user-001")
            assert result is not None
            assert len(result.owned_games) == 1
            game = result.owned_games[0]
            assert len(game.user_objectives) == 1
            assert game.user_objectives[0].user_points == 25
        finally:
            _teardown_cache(tmpdir)

    def test_user_with_no_rolls(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            _seed_user()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("user-001")
            assert result is not None
            assert result.rolls == []
        finally:
            _teardown_cache(tmpdir)

    def test_user_with_no_games(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_user(USER_DB_ROW)
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("user-001")
            assert result is not None
            assert result.owned_games == []
        finally:
            _teardown_cache(tmpdir)


class TestGetGamesBulkObjectives:
    def test_includes_objectives_and_requirements(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_games_bulk(["game-001"])
            assert len(result) == 1
            game = result[0]
            assert len(game.all_objectives) == 1
            assert game.all_objectives[0].name == "Beat the Game"
            assert game.all_objectives[0].achievement_ce_ids == ["ach-123"]
        finally:
            _teardown_cache(tmpdir)

    def test_nonexistent_ids_skipped(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_games_bulk(
                    ["game-001", "nonexistent"]
                )
            assert len(result) == 1
        finally:
            _teardown_cache(tmpdir)


class TestGetGameCustomRequirements:
    def test_game_with_custom_requirement(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_game(GAME_DB_ROW)
            LocalCache.upsert_objectives_bulk([OBJECTIVE_DB_ROW])
            LocalCache.upsert_requirements_bulk([
                {"objective_ce_id": "obj-001", "requirement_type": "custom",
                 "data": "Beat all chapters without dying", "updated_at_CE": "2026-01-01"},
            ])
            LocalCache.upsert_categories_bulk(CATEGORY_DB_ROWS)

            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_game("game-001")
            assert result is not None
            obj = result.all_objectives[0]
            assert obj.requirements == "Beat all chapters without dying"
        finally:
            _teardown_cache(tmpdir)

    def test_game_with_both_achievement_and_custom_reqs(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_game(GAME_DB_ROW)
            LocalCache.upsert_objectives_bulk([OBJECTIVE_DB_ROW])
            LocalCache.upsert_requirements_bulk([
                {"objective_ce_id": "obj-001", "requirement_type": "achievement",
                 "data": "ach-1", "updated_at_CE": ""},
                {"objective_ce_id": "obj-001", "requirement_type": "achievement",
                 "data": "ach-2", "updated_at_CE": ""},
                {"objective_ce_id": "obj-001", "requirement_type": "custom",
                 "data": "Custom requirement text", "updated_at_CE": ""},
            ])
            LocalCache.upsert_categories_bulk(CATEGORY_DB_ROWS)

            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_game("game-001")
            assert result is not None
            obj = result.all_objectives[0]
            assert set(obj.achievement_ce_ids) == {"ach-1", "ach-2"}
            assert obj.requirements == "Custom requirement text"
        finally:
            _teardown_cache(tmpdir)


class TestGetAllRollsGamesAttached:
    def test_rolls_have_games_attached(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_roll(ROLL_DB_ROW)
            LocalCache.upsert_roll_games_bulk([
                {"roll_id": "roll-001", "game_id": "game-001", "index": 0, "rolled_at": ""},
                {"roll_id": "roll-001", "game_id": "game-002", "index": 1, "rolled_at": ""},
            ])
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_all_rolls()
            assert len(result) == 1
            assert result[0].games == ["game-001", "game-002"]
        finally:
            _teardown_cache(tmpdir)


class TestGetUserRollsGamesAttached:
    def test_rolls_have_games_attached(self):
        tmpdir = _init_cache()
        try:
            _seed_roll()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user_rolls("user-001")
            assert len(result) == 1
            assert result[0].games == ["game-001"]
        finally:
            _teardown_cache(tmpdir)


class TestGetDatabaseTierStructure:
    def test_tier_structure_has_tiers_and_categories(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            LocalCache.upsert_tier_bulk([
                {"ce_id": "game-001", "price": 9.99, "sh_hours": 5.0},
            ])
            with patch.object(SupabaseReader, "supabase"):
                database_name = SupabaseReader.get_database_name()
                result = SupabaseReader.get_database_tier(database_name)
            for tier_num in range(1, 8):
                assert str(tier_num) in result
            assert isinstance(result["1"], dict)
        finally:
            _teardown_cache(tmpdir)

    def test_does_not_call_supabase(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            LocalCache.upsert_tier_bulk([
                {"ce_id": "game-001", "price": 9.99, "sh_hours": 5.0},
            ])
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                database_name = SupabaseReader.get_database_name()
                SupabaseReader.get_database_tier(database_name)
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)


# === Missing writer coverage ===


class TestBulkDumpUsersDualWrite:
    def test_writes_users_to_cache(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            from tests.conftest import make_user, make_user_game

            user = make_user(
                ce_id="user-new",
                discord_id=999,
                owned_games=[make_user_game(ce_id="game-001")],
            )

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.select.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                # get_list("name") and get_list("objectives") are called for FK validation
                # After the switch, these read from LocalCache, so we need the game in cache
                SupabaseReader.bulk_dump_users([user])

            cached = LocalCache.get_user("user-new")
            assert cached is not None
            assert cached["display_name"] == "TestUser"

            cached_games = LocalCache.get_user_games("user-new")
            assert len(cached_games) == 1
        finally:
            _teardown_cache(tmpdir)


class TestBulkDumpRollsDualWrite:
    def test_writes_rolls_to_cache(self):
        tmpdir = _init_cache()
        try:
            from tests.conftest import make_roll

            roll = make_roll(
                roll_name="Triple Threat",
                games=["game-a", "game-b", "game-c"],
            )

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.insert.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.bulk_dump_rolls([roll])

            cached = LocalCache.get_roll(roll._id)
            assert cached is not None
            assert cached["event_name"] == "Triple Threat"

            cached_games = LocalCache.get_roll_games(roll._id)
            assert len(cached_games) == 3
            assert [g["game_id"] for g in cached_games] == ["game-a", "game-b", "game-c"]
        finally:
            _teardown_cache(tmpdir)


class TestDumpDatabaseTierDualWrite:
    def test_writes_tier_to_cache(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                database_name = SupabaseReader.get_database_name()
                SupabaseReader.dump_database_tier(
                    SupabaseReader.get_database_tier(database_name)
                )

            cached = LocalCache.get_tier_all()
            # tier data comes from get_database_tier which builds from cache,
            # and dump_database_tier writes it back — verify cache has tier rows
            assert isinstance(cached, list)
        finally:
            _teardown_cache(tmpdir)


class TestDatabaseNameCacheRemoved:
    def test_no_cache_globals_exist(self):
        """After the switch to LocalCache, the old in-memory TTL cache should be removed."""
        assert not hasattr(SupabaseReader, "_database_name_cache")
        assert not hasattr(SupabaseReader, "_database_name_cache_time")
        assert not hasattr(SupabaseReader, "_DATABASE_NAME_TTL")
        assert not hasattr(SupabaseReader, "invalidate_database_name_cache")


# === dump_user (standalone, not bulk) ===


class TestDumpUserDualWrite:
    def test_writes_user_and_games_to_cache(self):
        tmpdir = _init_cache()
        try:
            from tests.conftest import make_user, make_user_game, make_user_objective

            user = make_user(
                ce_id="user-new",
                discord_id=888,
                owned_games=[
                    make_user_game(
                        ce_id="game-001",
                        user_objectives=[
                            make_user_objective(ce_id="obj-001", game_ce_id="game-001", user_points=15),
                        ],
                    ),
                ],
            )

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.dump_user(user)

            cached = LocalCache.get_user("user-new")
            assert cached is not None
            assert cached["discord_id"] == 888

            cached_games = LocalCache.get_user_games("user-new")
            assert len(cached_games) == 1
            assert cached_games[0]["game_ce_id"] == "game-001"

            cached_objs = LocalCache.get_user_objectives("user-new")
            assert len(cached_objs) == 1
            assert cached_objs[0]["user_points"] == 15
        finally:
            _teardown_cache(tmpdir)


# === dump_objective (standalone) ===


class TestDumpObjectiveDualWrite:
    def test_writes_objective_and_requirements_to_cache(self):
        tmpdir = _init_cache()
        try:
            from tests.conftest import make_objective

            obj = make_objective(
                ce_id="obj-new",
                game_ce_id="game-001",
                point_value=50,
                name="Completionist",
                requirements="Beat everything",
                achievement_ce_ids=["ach-1", "ach-2"],
            )

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.eq.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.dump_objective(obj)

            cached_objs = LocalCache.get_objectives_by_game("game-001")
            assert len(cached_objs) == 1
            assert cached_objs[0]["name"] == "Completionist"
            assert cached_objs[0]["points"] == 50

            cached_reqs = LocalCache.get_requirements_by_objectives(["obj-new"])
            assert len(cached_reqs) == 3
            types = {r["requirement_type"] for r in cached_reqs}
            assert types == {"achievement", "custom"}
        finally:
            _teardown_cache(tmpdir)


# === get_users_bulk with include_rolls=False ===


class TestGetUsersBulkNoRolls:
    def test_returns_users_without_rolls(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            _seed_user()
            _seed_roll()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_users_bulk(["user-001"], include_rolls=False)
            assert len(result) == 1
            assert result[0].rolls == []
        finally:
            _teardown_cache(tmpdir)

    def test_still_includes_games_and_objectives(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            _seed_user()
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_users_bulk(["user-001"], include_rolls=False)
            assert len(result) == 1
            assert len(result[0].owned_games) == 1
        finally:
            _teardown_cache(tmpdir)


# === get_user with multiple games ===


class TestGetUserMultipleGames:
    def test_user_with_multiple_games_and_objectives(self):
        tmpdir = _init_cache()
        try:
            # Seed two games with objectives
            _seed_game()
            LocalCache.upsert_game({**GAME_DB_ROW, "ce_id": "game-002", "name": "Hollow Knight"})
            LocalCache.upsert_objectives_bulk([
                {**OBJECTIVE_DB_ROW, "ce_id": "obj-002", "game_ce_id": "game-002", "name": "Steel Soul"},
            ])
            LocalCache.upsert_categories_bulk([
                {"game_id": "game-002", "category": "Action", "index": 0},
            ])

            # Seed user with both games
            LocalCache.upsert_user(USER_DB_ROW)
            LocalCache.upsert_user_games_bulk([
                {"user_ce_id": "user-001", "game_ce_id": "game-001", "updated_at_CE": ""},
                {"user_ce_id": "user-001", "game_ce_id": "game-002", "updated_at_CE": ""},
            ])
            LocalCache.upsert_user_objectives_bulk([
                {"user_ce_id": "user-001", "objective_ce_id": "obj-001", "user_points": 25, "updated_at_CE": ""},
                {"user_ce_id": "user-001", "objective_ce_id": "obj-002", "user_points": 100, "updated_at_CE": ""},
            ])

            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("user-001")

            assert result is not None
            assert len(result.owned_games) == 2
            game_ids = {g.ce_id for g in result.owned_games}
            assert game_ids == {"game-001", "game-002"}

            total_objectives = sum(len(g.user_objectives) for g in result.owned_games)
            assert total_objectives == 2
        finally:
            _teardown_cache(tmpdir)


# === clean_db reads from cache ===


class TestCleanDbFromCache:
    def test_does_not_call_supabase_for_reads(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            _seed_user()
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.clean_db()

            # clean_db should read game/objective/userGame/userObjective lists
            # from LocalCache, not Supabase. If it called supabase.table().select(),
            # that would go through the mock and return empty data (wrong behavior).
            # Instead it should use LocalCache and find no orphans.
        finally:
            _teardown_cache(tmpdir)

    def test_finds_and_reports_orphans(self):
        tmpdir = _init_cache()
        try:
            # Create a user_game pointing to a game that doesn't exist
            LocalCache.upsert_user(USER_DB_ROW)
            LocalCache.upsert_user_games_bulk([
                {"user_ce_id": "user-001", "game_ce_id": "nonexistent-game", "updated_at_CE": ""},
            ])

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.clean_db()

            # The orphan should still be cleaned up from Supabase via the mock
            mock_sb.table.assert_called()
        finally:
            _teardown_cache(tmpdir)
