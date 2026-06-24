import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from Modules import LocalCache


def _setup() -> str:
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    LocalCache.init(db_path)
    return tmpdir


def _teardown(tmpdir: str) -> None:
    LocalCache.close()
    shutil.rmtree(tmpdir)


GAME_ROW = {
    "ce_id": "g1",
    "name": "Celeste",
    "platform": "steam",
    "platform_id": "504230",
    "category_primary": None,
    "image_header": "img.png",
    "image_icon": "",
    "updated_at_CE": "2026-01-01",
}

USER_ROW = {
    "ce_id": "u1",
    "discord_id": 123,
    "display_name": "Andy",
    "image_avatar": None,
    "steam_id": "s1",
    "created_at_CE": "",
    "updated_at_CE": "",
}

ROLL_ROW = {
    "id": "r1",
    "event_name": "Soul Mates",
    "user1_ce_id": "u1",
    "user2_ce_id": "u2",
    "time_created": None,
    "time_due": None,
    "time_completed": None,
    "is_lucky": 0,
    "chosen_tier": None,
    "chosen_tier_partner": None,
    "status": "current",
    "rerolls_remaining": None,
    "rerolls_used": 0,
    "winner": None,
}


class TestInit:
    def test_creates_db_and_tables(self):
        tmpdir = _setup()
        try:
            conn = LocalCache.get_connection()
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            for expected in [
                "games", "objectives", "objective_requirements", "categories",
                "users", "user_games", "user_objectives", "rolls", "roll_games", "tier",
            ]:
                assert expected in tables
        finally:
            _teardown(tmpdir)

    def test_wal_mode(self):
        tmpdir = _setup()
        try:
            mode = LocalCache.get_connection().execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"
        finally:
            _teardown(tmpdir)

    def test_idempotent(self):
        tmpdir = _setup()
        try:
            db_path = os.path.join(tmpdir, "test.db")
            LocalCache.close()
            LocalCache.init(db_path)
            assert LocalCache.get_game("nonexistent") is None
        finally:
            _teardown(tmpdir)


class TestGames:
    def test_upsert_and_get(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_game(GAME_ROW)
            result = LocalCache.get_game("g1")
            assert result is not None
            assert result["name"] == "Celeste"
            assert result["platform"] == "steam"
        finally:
            _teardown(tmpdir)

    def test_get_not_found(self):
        tmpdir = _setup()
        try:
            assert LocalCache.get_game("nonexistent") is None
        finally:
            _teardown(tmpdir)

    def test_upsert_overwrites(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_game(GAME_ROW)
            updated = {**GAME_ROW, "name": "Celeste 2"}
            LocalCache.upsert_game(updated)
            assert LocalCache.get_game("g1")["name"] == "Celeste 2"
        finally:
            _teardown(tmpdir)

    def test_bulk_upsert(self):
        tmpdir = _setup()
        try:
            rows = [{**GAME_ROW, "ce_id": f"g{i}", "name": f"Game {i}"} for i in range(5)]
            LocalCache.upsert_games_bulk(rows)
            assert len(LocalCache.get_games_all()) == 5
        finally:
            _teardown(tmpdir)

    def test_get_game_ids(self):
        tmpdir = _setup()
        try:
            for i in range(3):
                LocalCache.upsert_game({**GAME_ROW, "ce_id": f"g{i}"})
            assert set(LocalCache.get_game_ids()) == {"g0", "g1", "g2"}
        finally:
            _teardown(tmpdir)

    def test_get_games_by_ids(self):
        tmpdir = _setup()
        try:
            for i in range(5):
                LocalCache.upsert_game({**GAME_ROW, "ce_id": f"g{i}"})
            result = LocalCache.get_games_by_ids(["g1", "g3"])
            assert len(result) == 2
            assert {r["ce_id"] for r in result} == {"g1", "g3"}
        finally:
            _teardown(tmpdir)

    def test_delete_game(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_game(GAME_ROW)
            LocalCache.delete_game("g1")
            assert LocalCache.get_game("g1") is None
        finally:
            _teardown(tmpdir)


class TestObjectives:
    def test_upsert_and_get_by_game(self):
        tmpdir = _setup()
        try:
            rows = [
                {"ce_id": "o1", "game_ce_id": "g1", "type": "primary", "name": "Beat",
                 "description": "Beat the game", "points": 10, "points_partial": None,
                 "updated_at_CE": ""},
                {"ce_id": "o2", "game_ce_id": "g1", "type": "secondary", "name": "All",
                 "description": "Get all", "points": 50, "points_partial": None,
                 "updated_at_CE": ""},
                {"ce_id": "o3", "game_ce_id": "g2", "type": "primary", "name": "Other",
                 "description": "", "points": 5, "points_partial": None,
                 "updated_at_CE": ""},
            ]
            LocalCache.upsert_objectives_bulk(rows)
            result = LocalCache.get_objectives_by_game("g1")
            assert len(result) == 2
        finally:
            _teardown(tmpdir)

    def test_delete_by_ids(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_objectives_bulk([
                {"ce_id": "o1", "game_ce_id": "g1", "type": "primary", "name": "X",
                 "description": "", "points": 0, "points_partial": None, "updated_at_CE": ""},
            ])
            LocalCache.delete_objectives_by_ids(["o1"])
            assert LocalCache.get_objectives_by_game("g1") == []
        finally:
            _teardown(tmpdir)


class TestRequirements:
    def test_upsert_and_get(self):
        tmpdir = _setup()
        try:
            rows = [
                {"objective_ce_id": "o1", "requirement_type": "achievement",
                 "data": "ach-1", "updated_at_CE": ""},
                {"objective_ce_id": "o1", "requirement_type": "custom",
                 "data": "Do X", "updated_at_CE": ""},
            ]
            LocalCache.upsert_requirements_bulk(rows)
            result = LocalCache.get_requirements_by_objectives(["o1"])
            assert len(result) == 2
        finally:
            _teardown(tmpdir)

    def test_delete_by_objectives(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_requirements_bulk([
                {"objective_ce_id": "o1", "requirement_type": "achievement",
                 "data": "ach-1", "updated_at_CE": ""},
            ])
            LocalCache.delete_requirements_by_objectives(["o1"])
            assert LocalCache.get_requirements_by_objectives(["o1"]) == []
        finally:
            _teardown(tmpdir)


class TestCategories:
    def test_upsert_and_get(self):
        tmpdir = _setup()
        try:
            rows = [
                {"game_id": "g1", "category": "Action", "index": 0},
                {"game_id": "g1", "category": "Arcade", "index": 1},
            ]
            LocalCache.upsert_categories_bulk(rows)
            result = LocalCache.get_categories_by_game("g1")
            assert len(result) == 2
            assert result[0]["category"] == "Action"
            assert result[1]["category"] == "Arcade"
        finally:
            _teardown(tmpdir)

    def test_delete_by_game(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_categories_bulk([
                {"game_id": "g1", "category": "Action", "index": 0},
            ])
            LocalCache.delete_categories_by_game("g1")
            assert LocalCache.get_categories_by_game("g1") == []
        finally:
            _teardown(tmpdir)

    def test_delete_by_games_bulk(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_categories_bulk([
                {"game_id": "g1", "category": "A", "index": 0},
                {"game_id": "g2", "category": "B", "index": 0},
                {"game_id": "g3", "category": "C", "index": 0},
            ])
            LocalCache.delete_categories_by_games(["g1", "g2"])
            assert LocalCache.get_categories_by_game("g1") == []
            assert LocalCache.get_categories_by_game("g2") == []
            assert len(LocalCache.get_categories_by_game("g3")) == 1
        finally:
            _teardown(tmpdir)


class TestUsers:
    def test_upsert_and_get(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user(USER_ROW)
            result = LocalCache.get_user("u1")
            assert result is not None
            assert result["display_name"] == "Andy"
        finally:
            _teardown(tmpdir)

    def test_get_by_discord_id(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user(USER_ROW)
            result = LocalCache.get_user_by_discord_id(123)
            assert result is not None
            assert result["ce_id"] == "u1"
        finally:
            _teardown(tmpdir)

    def test_get_by_discord_id_not_found(self):
        tmpdir = _setup()
        try:
            assert LocalCache.get_user_by_discord_id(999) is None
        finally:
            _teardown(tmpdir)

    def test_delete_user(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user(USER_ROW)
            LocalCache.delete_user("u1")
            assert LocalCache.get_user("u1") is None
        finally:
            _teardown(tmpdir)


class TestUserGames:
    def test_upsert_and_get(self):
        tmpdir = _setup()
        try:
            rows = [
                {"user_ce_id": "u1", "game_ce_id": "g1", "updated_at_CE": ""},
                {"user_ce_id": "u1", "game_ce_id": "g2", "updated_at_CE": ""},
            ]
            LocalCache.upsert_user_games_bulk(rows)
            result = LocalCache.get_user_games("u1")
            assert len(result) == 2
        finally:
            _teardown(tmpdir)

    def test_delete(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user_games_bulk([
                {"user_ce_id": "u1", "game_ce_id": "g1", "updated_at_CE": ""},
            ])
            LocalCache.delete_user_games("u1")
            assert LocalCache.get_user_games("u1") == []
        finally:
            _teardown(tmpdir)


class TestRolls:
    def test_upsert_and_get(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll(ROLL_ROW)
            result = LocalCache.get_roll("r1")
            assert result is not None
            assert result["event_name"] == "Soul Mates"
        finally:
            _teardown(tmpdir)

    def test_get_by_user(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll(ROLL_ROW)
            LocalCache.upsert_roll({**ROLL_ROW, "id": "r2", "user1_ce_id": "u3", "user2_ce_id": None})
            assert len(LocalCache.get_rolls_by_user("u1")) == 1
            assert len(LocalCache.get_rolls_by_user("u2")) == 1
            assert len(LocalCache.get_rolls_by_user("u3")) == 1

        finally:
            _teardown(tmpdir)

    def test_get_checkable(self):
        tmpdir = _setup()
        try:
            for status in ["current", "pending", "won", "removed"]:
                LocalCache.upsert_roll({**ROLL_ROW, "id": f"r-{status}", "status": status})
            results = LocalCache.get_checkable_rolls()
            statuses = {r["status"] for r in results}
            assert statuses == {"current", "pending"}
        finally:
            _teardown(tmpdir)

    def test_delete_cascades_to_roll_games(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll(ROLL_ROW)
            LocalCache.upsert_roll_games_bulk([
                {"roll_id": "r1", "game_id": "g1", "index": 0, "rolled_at": ""},
            ])
            LocalCache.delete_roll("r1")
            assert LocalCache.get_roll("r1") is None
            assert LocalCache.get_roll_games("r1") == []
        finally:
            _teardown(tmpdir)

    def test_get_by_event_names(self):
        tmpdir = _setup()
        try:
            for name in ["Soul Mates", "Triple Threat", "One Hell of a Day"]:
                LocalCache.upsert_roll({**ROLL_ROW, "id": f"r-{name}", "event_name": name})
            result = LocalCache.get_rolls_by_event_names(["Soul Mates", "Triple Threat"])
            assert len(result) == 2
            assert {r["event_name"] for r in result} == {"Soul Mates", "Triple Threat"}
        finally:
            _teardown(tmpdir)

    def test_get_by_event_names_empty_list(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll(ROLL_ROW)
            assert LocalCache.get_rolls_by_event_names([]) == []
        finally:
            _teardown(tmpdir)


class TestRollGames:
    def test_upsert_and_get_ordered(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll_games_bulk([
                {"roll_id": "r1", "game_id": "g2", "index": 1, "rolled_at": ""},
                {"roll_id": "r1", "game_id": "g1", "index": 0, "rolled_at": ""},
            ])
            result = LocalCache.get_roll_games("r1")
            assert result[0]["game_id"] == "g1"
            assert result[1]["game_id"] == "g2"
        finally:
            _teardown(tmpdir)

    def test_get_by_ids(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll_games_bulk([
                {"roll_id": "r1", "game_id": "g1", "index": 0, "rolled_at": ""},
                {"roll_id": "r2", "game_id": "g2", "index": 0, "rolled_at": ""},
                {"roll_id": "r3", "game_id": "g3", "index": 0, "rolled_at": ""},
            ])
            result = LocalCache.get_roll_games_by_ids(["r1", "r3"])
            assert len(result) == 2
        finally:
            _teardown(tmpdir)


class TestTier:
    def test_upsert_and_get(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_tier_bulk([
                {"ce_id": "g1", "price": 9.99, "sh_hours": 5.0},
                {"ce_id": "g2", "price": 0.0, "sh_hours": 100.0},
            ])
            result = LocalCache.get_tier_all()
            assert len(result) == 2
        finally:
            _teardown(tmpdir)

    def test_upsert_overwrites_price(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_tier_bulk([{"ce_id": "g1", "price": 9.99, "sh_hours": 5.0}])
            LocalCache.upsert_tier_bulk([{"ce_id": "g1", "price": 4.99, "sh_hours": 5.0}])
            result = LocalCache.get_tier_all()
            assert len(result) == 1
            assert result[0]["price"] == 4.99
        finally:
            _teardown(tmpdir)


# === EMPTY LIST / EDGE CASE TESTS ===


class TestEmptyInputs:
    def test_bulk_upsert_games_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_games_bulk([])
            assert LocalCache.get_games_all() == []
        finally:
            _teardown(tmpdir)

    def test_bulk_upsert_objectives_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_objectives_bulk([])
            assert LocalCache.get_objective_ids() == []
        finally:
            _teardown(tmpdir)

    def test_bulk_upsert_users_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_users_bulk([])
            assert LocalCache.get_users_all() == []
        finally:
            _teardown(tmpdir)

    def test_bulk_upsert_rolls_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_rolls_bulk([])
            assert LocalCache.get_rolls_all() == []
        finally:
            _teardown(tmpdir)

    def test_bulk_upsert_roll_games_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll_games_bulk([])
            assert LocalCache.get_roll_games_by_ids([]) == []
        finally:
            _teardown(tmpdir)

    def test_bulk_upsert_requirements_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_requirements_bulk([])
            assert LocalCache.get_requirements_by_objectives([]) == []
        finally:
            _teardown(tmpdir)

    def test_bulk_upsert_categories_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_categories_bulk([])
        finally:
            _teardown(tmpdir)

    def test_bulk_upsert_user_games_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user_games_bulk([])
        finally:
            _teardown(tmpdir)

    def test_bulk_upsert_user_objectives_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user_objectives_bulk([])
        finally:
            _teardown(tmpdir)

    def test_bulk_upsert_tier_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_tier_bulk([])
            assert LocalCache.get_tier_all() == []
        finally:
            _teardown(tmpdir)

    def test_get_games_by_ids_empty(self):
        tmpdir = _setup()
        try:
            assert LocalCache.get_games_by_ids([]) == []
        finally:
            _teardown(tmpdir)

    def test_get_objectives_by_ids_empty(self):
        tmpdir = _setup()
        try:
            assert LocalCache.get_objectives_by_ids([]) == []
        finally:
            _teardown(tmpdir)

    def test_get_requirements_by_objectives_empty(self):
        tmpdir = _setup()
        try:
            assert LocalCache.get_requirements_by_objectives([]) == []
        finally:
            _teardown(tmpdir)

    def test_get_users_by_ids_empty(self):
        tmpdir = _setup()
        try:
            assert LocalCache.get_users_by_ids([]) == []
        finally:
            _teardown(tmpdir)

    def test_get_roll_games_by_ids_empty(self):
        tmpdir = _setup()
        try:
            assert LocalCache.get_roll_games_by_ids([]) == []
        finally:
            _teardown(tmpdir)

    def test_delete_objectives_by_ids_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.delete_objectives_by_ids([])
        finally:
            _teardown(tmpdir)

    def test_delete_requirements_by_objectives_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.delete_requirements_by_objectives([])
        finally:
            _teardown(tmpdir)

    def test_delete_categories_by_games_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.delete_categories_by_games([])
        finally:
            _teardown(tmpdir)

    def test_delete_rolls_by_ids_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.delete_rolls_by_ids([])
        finally:
            _teardown(tmpdir)

    def test_delete_roll_games_by_rolls_empty(self):
        tmpdir = _setup()
        try:
            LocalCache.delete_roll_games_by_rolls([])
        finally:
            _teardown(tmpdir)


# === UNTESTED GETTERS ===


class TestGettersNotPreviouslyCovered:
    def test_get_users_all(self):
        tmpdir = _setup()
        try:
            for i in range(3):
                LocalCache.upsert_user({**USER_ROW, "ce_id": f"u{i}", "discord_id": i})
            assert len(LocalCache.get_users_all()) == 3
        finally:
            _teardown(tmpdir)

    def test_get_user_ids(self):
        tmpdir = _setup()
        try:
            for i in range(3):
                LocalCache.upsert_user({**USER_ROW, "ce_id": f"u{i}", "discord_id": i})
            assert set(LocalCache.get_user_ids()) == {"u0", "u1", "u2"}
        finally:
            _teardown(tmpdir)

    def test_get_users_by_ids(self):
        tmpdir = _setup()
        try:
            for i in range(5):
                LocalCache.upsert_user({**USER_ROW, "ce_id": f"u{i}", "discord_id": i})
            result = LocalCache.get_users_by_ids(["u1", "u3"])
            assert len(result) == 2
            assert {r["ce_id"] for r in result} == {"u1", "u3"}
        finally:
            _teardown(tmpdir)

    def test_get_objectives_by_ids(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_objectives_bulk([
                {"ce_id": f"o{i}", "game_ce_id": "g1", "type": "primary",
                 "name": f"Obj {i}", "description": "", "points": i * 10,
                 "points_partial": None, "updated_at_CE": ""}
                for i in range(4)
            ])
            result = LocalCache.get_objectives_by_ids(["o0", "o2"])
            assert len(result) == 2
            assert {r["ce_id"] for r in result} == {"o0", "o2"}
        finally:
            _teardown(tmpdir)

    def test_get_objective_ids(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_objectives_bulk([
                {"ce_id": f"o{i}", "game_ce_id": "g1", "type": "primary",
                 "name": "", "description": "", "points": 0,
                 "points_partial": None, "updated_at_CE": ""}
                for i in range(3)
            ])
            assert set(LocalCache.get_objective_ids()) == {"o0", "o1", "o2"}
        finally:
            _teardown(tmpdir)

    def test_get_rolls_all(self):
        tmpdir = _setup()
        try:
            for i in range(3):
                LocalCache.upsert_roll({**ROLL_ROW, "id": f"r{i}"})
            assert len(LocalCache.get_rolls_all()) == 3
        finally:
            _teardown(tmpdir)

    def test_get_roll_ids(self):
        tmpdir = _setup()
        try:
            for i in range(3):
                LocalCache.upsert_roll({**ROLL_ROW, "id": f"r{i}"})
            assert set(LocalCache.get_roll_ids()) == {"r0", "r1", "r2"}
        finally:
            _teardown(tmpdir)

    def test_get_roll_not_found(self):
        tmpdir = _setup()
        try:
            assert LocalCache.get_roll("nonexistent") is None
        finally:
            _teardown(tmpdir)

    def test_get_user_not_found(self):
        tmpdir = _setup()
        try:
            assert LocalCache.get_user("nonexistent") is None
        finally:
            _teardown(tmpdir)


# === USER OBJECTIVES ===


class TestUserObjectives:
    def test_upsert_and_get(self):
        tmpdir = _setup()
        try:
            rows = [
                {"user_ce_id": "u1", "objective_ce_id": "o1", "user_points": 10, "updated_at_CE": ""},
                {"user_ce_id": "u1", "objective_ce_id": "o2", "user_points": 50, "updated_at_CE": ""},
            ]
            LocalCache.upsert_user_objectives_bulk(rows)
            result = LocalCache.get_user_objectives("u1")
            assert len(result) == 2
            points = {r["objective_ce_id"]: r["user_points"] for r in result}
            assert points["o1"] == 10
            assert points["o2"] == 50
        finally:
            _teardown(tmpdir)

    def test_upsert_overwrites_points(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user_objectives_bulk([
                {"user_ce_id": "u1", "objective_ce_id": "o1", "user_points": 10, "updated_at_CE": ""},
            ])
            LocalCache.upsert_user_objectives_bulk([
                {"user_ce_id": "u1", "objective_ce_id": "o1", "user_points": 25, "updated_at_CE": ""},
            ])
            result = LocalCache.get_user_objectives("u1")
            assert len(result) == 1
            assert result[0]["user_points"] == 25
        finally:
            _teardown(tmpdir)

    def test_delete(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user_objectives_bulk([
                {"user_ce_id": "u1", "objective_ce_id": "o1", "user_points": 10, "updated_at_CE": ""},
                {"user_ce_id": "u1", "objective_ce_id": "o2", "user_points": 20, "updated_at_CE": ""},
            ])
            LocalCache.delete_user_objectives("u1")
            assert LocalCache.get_user_objectives("u1") == []
        finally:
            _teardown(tmpdir)

    def test_different_users_isolated(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user_objectives_bulk([
                {"user_ce_id": "u1", "objective_ce_id": "o1", "user_points": 10, "updated_at_CE": ""},
                {"user_ce_id": "u2", "objective_ce_id": "o1", "user_points": 30, "updated_at_CE": ""},
            ])
            assert len(LocalCache.get_user_objectives("u1")) == 1
            assert len(LocalCache.get_user_objectives("u2")) == 1
            LocalCache.delete_user_objectives("u1")
            assert LocalCache.get_user_objectives("u1") == []
            assert len(LocalCache.get_user_objectives("u2")) == 1
        finally:
            _teardown(tmpdir)


# === BULK UPSERT EDGE CASES ===


class TestBulkUpsertEdgeCases:
    def test_bulk_games_with_duplicates_last_wins(self):
        tmpdir = _setup()
        try:
            rows = [
                {**GAME_ROW, "ce_id": "g1", "name": "First"},
                {**GAME_ROW, "ce_id": "g1", "name": "Second"},
            ]
            LocalCache.upsert_games_bulk(rows)
            result = LocalCache.get_game("g1")
            assert result is not None
            assert result["name"] == "Second"
        finally:
            _teardown(tmpdir)

    def test_bulk_users_with_duplicates_last_wins(self):
        tmpdir = _setup()
        try:
            rows = [
                {**USER_ROW, "ce_id": "u1", "display_name": "First"},
                {**USER_ROW, "ce_id": "u1", "display_name": "Second"},
            ]
            LocalCache.upsert_users_bulk(rows)
            result = LocalCache.get_user("u1")
            assert result is not None
            assert result["display_name"] == "Second"
        finally:
            _teardown(tmpdir)

    def test_bulk_rolls_with_duplicates_last_wins(self):
        tmpdir = _setup()
        try:
            rows = [
                {**ROLL_ROW, "id": "r1", "event_name": "First"},
                {**ROLL_ROW, "id": "r1", "event_name": "Second"},
            ]
            LocalCache.upsert_rolls_bulk(rows)
            result = LocalCache.get_roll("r1")
            assert result is not None
            assert result["event_name"] == "Second"
        finally:
            _teardown(tmpdir)

    def test_large_batch_games(self):
        tmpdir = _setup()
        try:
            rows = [
                {**GAME_ROW, "ce_id": f"g{i}", "name": f"Game {i}"}
                for i in range(200)
            ]
            LocalCache.upsert_games_bulk(rows)
            assert len(LocalCache.get_games_all()) == 200
            assert len(LocalCache.get_game_ids()) == 200
        finally:
            _teardown(tmpdir)

    def test_large_batch_get_by_ids(self):
        tmpdir = _setup()
        try:
            rows = [
                {**GAME_ROW, "ce_id": f"g{i}", "name": f"Game {i}"}
                for i in range(200)
            ]
            LocalCache.upsert_games_bulk(rows)
            ids = [f"g{i}" for i in range(0, 200, 2)]
            result = LocalCache.get_games_by_ids(ids)
            assert len(result) == 100
        finally:
            _teardown(tmpdir)


# === DELETE EDGE CASES ===


class TestDeleteEdgeCases:
    def test_delete_nonexistent_game_is_noop(self):
        tmpdir = _setup()
        try:
            LocalCache.delete_game("nonexistent")
        finally:
            _teardown(tmpdir)

    def test_delete_nonexistent_user_is_noop(self):
        tmpdir = _setup()
        try:
            LocalCache.delete_user("nonexistent")
        finally:
            _teardown(tmpdir)

    def test_delete_nonexistent_roll_is_noop(self):
        tmpdir = _setup()
        try:
            LocalCache.delete_roll("nonexistent")
        finally:
            _teardown(tmpdir)

    def test_delete_rolls_by_ids_partial_match(self):
        tmpdir = _setup()
        try:
            for i in range(3):
                LocalCache.upsert_roll({**ROLL_ROW, "id": f"r{i}"})
            LocalCache.delete_rolls_by_ids(["r0", "r2", "nonexistent"])
            assert LocalCache.get_roll("r0") is None
            assert LocalCache.get_roll("r1") is not None
            assert LocalCache.get_roll("r2") is None
        finally:
            _teardown(tmpdir)

    def test_delete_user_games_does_not_affect_other_users(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user_games_bulk([
                {"user_ce_id": "u1", "game_ce_id": "g1", "updated_at_CE": ""},
                {"user_ce_id": "u2", "game_ce_id": "g1", "updated_at_CE": ""},
            ])
            LocalCache.delete_user_games("u1")
            assert LocalCache.get_user_games("u1") == []
            assert len(LocalCache.get_user_games("u2")) == 1
        finally:
            _teardown(tmpdir)

    def test_delete_roll_games_by_roll(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll_games_bulk([
                {"roll_id": "r1", "game_id": "g1", "index": 0, "rolled_at": ""},
                {"roll_id": "r1", "game_id": "g2", "index": 1, "rolled_at": ""},
                {"roll_id": "r2", "game_id": "g3", "index": 0, "rolled_at": ""},
            ])
            LocalCache.delete_roll_games_by_roll("r1")
            assert LocalCache.get_roll_games("r1") == []
            assert len(LocalCache.get_roll_games("r2")) == 1
        finally:
            _teardown(tmpdir)

    def test_delete_roll_games_by_rolls_bulk(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll_games_bulk([
                {"roll_id": "r1", "game_id": "g1", "index": 0, "rolled_at": ""},
                {"roll_id": "r2", "game_id": "g2", "index": 0, "rolled_at": ""},
                {"roll_id": "r3", "game_id": "g3", "index": 0, "rolled_at": ""},
            ])
            LocalCache.delete_roll_games_by_rolls(["r1", "r2"])
            assert LocalCache.get_roll_games("r1") == []
            assert LocalCache.get_roll_games("r2") == []
            assert len(LocalCache.get_roll_games("r3")) == 1
        finally:
            _teardown(tmpdir)


# === DATA INTEGRITY ===


class TestDataIntegrity:
    def test_game_preserves_all_fields(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_game(GAME_ROW)
            result = LocalCache.get_game("g1")
            assert result is not None
            for key in GAME_ROW:
                assert result[key] == GAME_ROW[key], f"Mismatch on {key}"
        finally:
            _teardown(tmpdir)

    def test_user_preserves_all_fields(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user(USER_ROW)
            result = LocalCache.get_user("u1")
            assert result is not None
            for key in USER_ROW:
                assert result[key] == USER_ROW[key], f"Mismatch on {key}"
        finally:
            _teardown(tmpdir)

    def test_roll_preserves_all_fields(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll(ROLL_ROW)
            result = LocalCache.get_roll("r1")
            assert result is not None
            for key in ROLL_ROW:
                assert result[key] == ROLL_ROW[key], f"Mismatch on {key}"
        finally:
            _teardown(tmpdir)

    def test_objective_preserves_points_partial_none(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_objectives_bulk([
                {"ce_id": "o1", "game_ce_id": "g1", "type": "primary", "name": "X",
                 "description": "", "points": 10, "points_partial": None, "updated_at_CE": ""},
            ])
            result = LocalCache.get_objectives_by_game("g1")
            assert result[0]["points_partial"] is None
        finally:
            _teardown(tmpdir)

    def test_objective_preserves_points_partial_value(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_objectives_bulk([
                {"ce_id": "o1", "game_ce_id": "g1", "type": "primary", "name": "X",
                 "description": "", "points": 10, "points_partial": 5, "updated_at_CE": ""},
            ])
            result = LocalCache.get_objectives_by_game("g1")
            assert result[0]["points_partial"] == 5
        finally:
            _teardown(tmpdir)

    def test_requirement_data_with_special_characters(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_requirements_bulk([
                {"objective_ce_id": "o1", "requirement_type": "custom",
                 "data": "Beat the game 100% (including DLC's \"extra\" levels)",
                 "updated_at_CE": ""},
            ])
            result = LocalCache.get_requirements_by_objectives(["o1"])
            assert "DLC's" in result[0]["data"]
            assert '"extra"' in result[0]["data"]
        finally:
            _teardown(tmpdir)

    def test_categories_returned_in_index_order(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_categories_bulk([
                {"game_id": "g1", "category": "C", "index": 2},
                {"game_id": "g1", "category": "A", "index": 0},
                {"game_id": "g1", "category": "B", "index": 1},
            ])
            result = LocalCache.get_categories_by_game("g1")
            assert [r["category"] for r in result] == ["A", "B", "C"]
        finally:
            _teardown(tmpdir)

    def test_rolls_by_user_finds_as_user2(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll({**ROLL_ROW, "id": "r1", "user1_ce_id": "u1", "user2_ce_id": "u2"})
            result = LocalCache.get_rolls_by_user("u2")
            assert len(result) == 1
            assert result[0]["id"] == "r1"
        finally:
            _teardown(tmpdir)

    def test_rolls_by_user_no_duplicates_when_both_fields_match(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll({**ROLL_ROW, "id": "r1", "user1_ce_id": "u1", "user2_ce_id": "u1"})
            result = LocalCache.get_rolls_by_user("u1")
            assert len(result) == 1
        finally:
            _teardown(tmpdir)


# === INIT EDGE CASES ===


class TestInitEdgeCases:
    def test_get_connection_before_init_raises(self):
        LocalCache.close()
        with pytest.raises(RuntimeError, match="not initialized"):
            LocalCache.get_connection()

    def test_close_when_not_initialized_is_noop(self):
        LocalCache.close()
        LocalCache.close()


# === INTEGRITY CHECK ===


class TestRunIntegrityCheck:
    def _make_mock_supabase(self, data_by_table: dict[str, list[dict]]) -> MagicMock:
        mock_sb = MagicMock()

        def _table(name):
            mock_table = MagicMock()
            table_data = data_by_table.get(name, [])

            mock_table.select.return_value = mock_table
            mock_table.in_.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=table_data)
            return mock_table

        mock_sb.table.side_effect = _table
        return mock_sb

    def test_no_discrepancies(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_game(GAME_ROW)
            LocalCache.upsert_user(USER_ROW)

            mock_sb = self._make_mock_supabase({
                "games": [{"ce_id": "g1"}],
                "users": [{"ce_id": "u1"}],
                "objectives": [],
                "rolls": [],
            })

            with patch("Modules.SupabaseReader.supabase", mock_sb):
                from Modules.LocalCache import run_integrity_check
                report = run_integrity_check()

            assert report["synced"] == []
            assert report["removed"] == []
        finally:
            _teardown(tmpdir)

    def test_removes_stale_game_and_cascades(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_game(GAME_ROW)
            LocalCache.upsert_objectives_bulk([
                {"ce_id": "o1", "game_ce_id": "g1", "type": "primary", "name": "X",
                 "description": "", "points": 10, "points_partial": None, "updated_at_CE": ""},
            ])
            LocalCache.upsert_requirements_bulk([
                {"objective_ce_id": "o1", "requirement_type": "achievement",
                 "data": "ach-1", "updated_at_CE": ""},
            ])
            LocalCache.upsert_categories_bulk([
                {"game_id": "g1", "category": "Action", "index": 0},
            ])

            mock_sb = self._make_mock_supabase({
                "games": [],
                "users": [],
                "objectives": [],
                "rolls": [],
            })

            with patch("Modules.SupabaseReader.supabase", mock_sb):
                from Modules.LocalCache import run_integrity_check
                report = run_integrity_check()

            assert any("games" in s for s in report["removed"])
            assert LocalCache.get_game("g1") is None
            assert LocalCache.get_objectives_by_game("g1") == []
            assert LocalCache.get_requirements_by_objectives(["o1"]) == []
            assert LocalCache.get_categories_by_game("g1") == []
        finally:
            _teardown(tmpdir)

    def test_removes_stale_user_and_cascades(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_user(USER_ROW)
            LocalCache.upsert_user_games_bulk([
                {"user_ce_id": "u1", "game_ce_id": "g1", "updated_at_CE": ""},
            ])
            LocalCache.upsert_user_objectives_bulk([
                {"user_ce_id": "u1", "objective_ce_id": "o1",
                 "user_points": 10, "updated_at_CE": ""},
            ])

            mock_sb = self._make_mock_supabase({
                "games": [],
                "users": [],
                "objectives": [],
                "rolls": [],
            })

            with patch("Modules.SupabaseReader.supabase", mock_sb):
                from Modules.LocalCache import run_integrity_check
                report = run_integrity_check()

            assert LocalCache.get_user("u1") is None
            assert LocalCache.get_user_games("u1") == []
            assert LocalCache.get_user_objectives("u1") == []
        finally:
            _teardown(tmpdir)

    def test_removes_stale_roll_and_cascades(self):
        tmpdir = _setup()
        try:
            LocalCache.upsert_roll(ROLL_ROW)
            LocalCache.upsert_roll_games_bulk([
                {"roll_id": "r1", "game_id": "g1", "index": 0, "rolled_at": ""},
            ])

            mock_sb = self._make_mock_supabase({
                "games": [],
                "users": [],
                "objectives": [],
                "rolls": [],
            })

            with patch("Modules.SupabaseReader.supabase", mock_sb):
                from Modules.LocalCache import run_integrity_check
                report = run_integrity_check()

            assert LocalCache.get_roll("r1") is None
            assert LocalCache.get_roll_games("r1") == []
        finally:
            _teardown(tmpdir)

    def test_syncs_missing_game(self):
        tmpdir = _setup()
        try:
            mock_sb = self._make_mock_supabase({
                "games": [{"ce_id": "g-new"}],
                "users": [],
                "objectives": [],
                "rolls": [],
            })

            def _table_with_full_data(name):
                mock_table = MagicMock()
                if name == "games":
                    mock_table.select.return_value = mock_table
                    mock_table.in_.return_value = mock_table

                    def _execute_for_games():
                        return MagicMock(data=[{**GAME_ROW, "ce_id": "g-new"}])

                    mock_table.execute.side_effect = [
                        MagicMock(data=[{"ce_id": "g-new"}]),
                        MagicMock(data=[{**GAME_ROW, "ce_id": "g-new"}]),
                    ]
                else:
                    mock_table.select.return_value = mock_table
                    mock_table.in_.return_value = mock_table
                    mock_table.execute.return_value = MagicMock(data=[])
                return mock_table

            mock_sb.table.side_effect = _table_with_full_data

            with patch("Modules.SupabaseReader.supabase", mock_sb):
                from Modules.LocalCache import run_integrity_check
                report = run_integrity_check()

            assert any("games" in s for s in report["synced"])
            assert LocalCache.get_game("g-new") is not None
        finally:
            _teardown(tmpdir)
