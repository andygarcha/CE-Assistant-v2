import os
import shutil
import tempfile

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
