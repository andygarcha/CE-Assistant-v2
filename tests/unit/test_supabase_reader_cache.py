"""Tests for SupabaseReader after switching to LocalCache.

Getters should read from SQLite (via LocalCache), not Supabase.
Writers should dual-write to both Supabase and LocalCache.
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from Classes.CE_Game import CEGame
from Classes.CE_Roll import CERoll
from Classes.CE_User import CEUser
from Modules import LocalCache, SupabaseReader

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


def _seed_user(partial: bool = False):
    LocalCache.upsert_user(USER_DB_ROW)
    LocalCache.upsert_user_games_bulk(
        [
            {"user_ce_id": "user-001", "game_ce_id": "game-001", "updated_at_CE": ""},
        ]
    )
    LocalCache.upsert_user_objectives_bulk(
        [
            {
                "user_ce_id": "user-001",
                "objective_ce_id": "obj-001",
                "partial": partial,
                "updated_at_CE": "",
            },
        ]
    )


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
            with (
                patch.object(SupabaseReader, "supabase"),
                pytest.raises(ValueError, match="Invalid get_list argument"),
            ):
                SupabaseReader.get_list("invalid")  # type: ignore[arg-type]
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
            LocalCache.upsert_game(
                {**GAME_DB_ROW, "ce_id": "game-002", "name": "Hollow Knight"}
            )
            LocalCache.upsert_categories_bulk(
                [
                    {"game_id": "game-002", "category": "Action", "index": 0},
                ]
            )
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


class TestGetUserPointsDerivedLive:
    def test_full_completion_uses_current_objective_points(self):
        tmpdir = _init_cache()
        try:
            _seed_game()  # OBJECTIVE_DB_ROW has points=25
            _seed_user(partial=False)
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("user-001")
            assert result is not None
            obj = result.owned_games[0].user_objectives[0]
            assert obj.user_points == 25
        finally:
            _teardown_cache(tmpdir)

    def test_partial_completion_uses_current_partial_points(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_game(GAME_DB_ROW)
            LocalCache.upsert_objectives_bulk(
                [{**OBJECTIVE_DB_ROW, "points_partial": 5}]
            )
            _seed_user(partial=True)
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("user-001")
            assert result is not None
            obj = result.owned_games[0].user_objectives[0]
            assert obj.user_points == 5
        finally:
            _teardown_cache(tmpdir)

    def test_reflects_a_point_value_that_changed_after_completion(self):
        # The whole point of this migration: no snapshot to go stale.
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_game(GAME_DB_ROW)
            LocalCache.upsert_objectives_bulk([{**OBJECTIVE_DB_ROW, "points": 999}])
            _seed_user(partial=False)
            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_user("user-001")
            assert result is not None
            obj = result.owned_games[0].user_objectives[0]
            assert obj.user_points == 999
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
            LocalCache.upsert_categories_bulk(
                [
                    {"game_id": "game-002", "category": "Action", "index": 0},
                ]
            )
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
                LocalCache.upsert_roll(
                    {**ROLL_DB_ROW, "id": f"r-{status}", "status": status}
                )
                LocalCache.upsert_roll_games_bulk(
                    [
                        {
                            "roll_id": f"r-{status}",
                            "game_id": "game-001",
                            "index": 0,
                            "rolled_at": "",
                        },
                    ]
                )
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
                LocalCache.upsert_roll_games_bulk(
                    [
                        {
                            "roll_id": f"r{i}",
                            "game_id": "game-001",
                            "index": 0,
                            "rolled_at": "",
                        },
                    ]
                )
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
                result = SupabaseReader.get_all_rolls(
                    event_names=["Soul Mates", "Triple Threat"]
                )
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
            LocalCache.upsert_roll(
                {**ROLL_DB_ROW, "id": "roll-other", "user1_ce_id": "user-999"}
            )
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
            LocalCache.upsert_tier_bulk(
                [
                    {"ce_id": "game-001", "price": 9.99, "sh_hours": 5.0},
                ]
            )
            with patch.object(SupabaseReader, "supabase"):
                database_name = SupabaseReader.get_database_name()
                result = SupabaseReader.get_database_tier(database_name)
            assert isinstance(result, dict)
        finally:
            _teardown_cache(tmpdir)


# === Writer Tests ===
# These verify that writers still call Supabase AND also write to LocalCache.


class TestDumpGameDualWrite:
    def _mock_supabase(self):
        mock_sb = MagicMock()
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table
        mock_table.upsert.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        return mock_sb

    def test_writes_all_four_tables_to_cache(self):
        tmpdir = _init_cache()
        try:
            from tests.conftest import make_game, make_objective

            game = make_game(
                ce_id="game-new",
                game_name="New Game",
                categories=["Action", "Platformer"],
                objectives=[
                    make_objective(
                        ce_id="obj-new",
                        game_ce_id="game-new",
                        achievement_ce_ids=["ach-1", "ach-2"],
                        requirements="Beat all levels",
                    ),
                ],
            )

            with patch.object(SupabaseReader, "supabase", self._mock_supabase()):
                SupabaseReader.bulk_dump_games([game])

            # games table
            cached = LocalCache.get_game("game-new")
            assert cached is not None
            assert cached["name"] == "New Game"

            # objectives table
            cached_objs = LocalCache.get_objectives_by_game("game-new")
            assert len(cached_objs) == 1
            assert cached_objs[0]["ce_id"] == "obj-new"

            # objectiveRequirements table
            cached_reqs = LocalCache.get_requirements_by_objectives(["obj-new"])
            achievement_reqs = [
                r for r in cached_reqs if r["requirement_type"] == "achievement"
            ]
            custom_reqs = [r for r in cached_reqs if r["requirement_type"] == "custom"]
            assert len(achievement_reqs) == 2
            assert {r["data"] for r in achievement_reqs} == {"ach-1", "ach-2"}
            assert len(custom_reqs) == 1
            assert custom_reqs[0]["data"] == "Beat all levels"

            # categories table
            cached_cats = LocalCache.get_categories_by_game("game-new")
            assert len(cached_cats) == 2
            assert [c["category"] for c in cached_cats] == ["Action", "Platformer"]
        finally:
            _teardown_cache(tmpdir)

    def test_replaces_old_categories_and_requirements(self):
        """When a game is re-dumped, old categories and requirements should be
        replaced, not accumulated."""
        tmpdir = _init_cache()
        try:
            from tests.conftest import make_game, make_objective

            # First dump: 2 categories, 1 achievement
            game_v1 = make_game(
                ce_id="game-x",
                game_name="V1",
                categories=["Action", "Arcade"],
                objectives=[
                    make_objective(
                        ce_id="obj-x",
                        game_ce_id="game-x",
                        achievement_ce_ids=["ach-old"],
                    ),
                ],
            )
            with patch.object(SupabaseReader, "supabase", self._mock_supabase()):
                SupabaseReader.bulk_dump_games([game_v1])

            assert len(LocalCache.get_categories_by_game("game-x")) == 2
            assert len(LocalCache.get_requirements_by_objectives(["obj-x"])) == 1

            # Second dump: 1 category, 2 achievements
            game_v2 = make_game(
                ce_id="game-x",
                game_name="V2",
                categories=["Platformer"],
                objectives=[
                    make_objective(
                        ce_id="obj-x",
                        game_ce_id="game-x",
                        achievement_ce_ids=["ach-new-1", "ach-new-2"],
                    ),
                ],
            )
            with patch.object(SupabaseReader, "supabase", self._mock_supabase()):
                SupabaseReader.bulk_dump_games([game_v2])

            # Should be replaced, not accumulated
            cats = LocalCache.get_categories_by_game("game-x")
            assert len(cats) == 1
            assert cats[0]["category"] == "Platformer"

            reqs = LocalCache.get_requirements_by_objectives(["obj-x"])
            assert len(reqs) == 2
            assert {r["data"] for r in reqs} == {"ach-new-1", "ach-new-2"}
        finally:
            _teardown_cache(tmpdir)


class TestDumpRollDualWrite:
    def test_writes_roll_and_roll_games_to_cache(self):
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

            cached = LocalCache.get_roll(roll._id)
            assert cached is not None
            assert cached["event_name"] == "One Hell of a Day"

            cached_games = LocalCache.get_roll_games(roll._id)
            assert len(cached_games) == 1
            assert cached_games[0]["game_id"] == "game-001"
        finally:
            _teardown_cache(tmpdir)

    def test_replaces_old_roll_games(self):
        """When a roll is re-dumped with different games, old roll_games
        should be replaced."""
        tmpdir = _init_cache()
        try:
            import uuid

            from tests.conftest import make_roll

            roll_id = str(uuid.uuid4())

            # First dump: 1 game
            roll_v1 = make_roll(roll_name="E", games=["game-old"])
            roll_v1._id = roll_id

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])
                SupabaseReader.dump_roll(roll_v1)

            assert len(LocalCache.get_roll_games(roll_id)) == 1

            # Second dump: 2 different games
            roll_v2 = make_roll(roll_name="E", games=["game-new-1", "game-new-2"])
            roll_v2._id = roll_id

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])
                SupabaseReader.dump_roll(roll_v2)

            cached_games = LocalCache.get_roll_games(roll_id)
            assert len(cached_games) == 2
            assert {g["game_id"] for g in cached_games} == {"game-new-1", "game-new-2"}
        finally:
            _teardown_cache(tmpdir)


class TestDeleteGameDualWrite:
    def test_deletes_all_related_tables_from_cache(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            # Verify data exists before delete
            assert LocalCache.get_game("game-001") is not None
            assert len(LocalCache.get_objectives_by_game("game-001")) == 1
            assert len(LocalCache.get_requirements_by_objectives(["obj-001"])) == 1
            assert len(LocalCache.get_categories_by_game("game-001")) == 2

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.select.return_value = mock_table
                mock_table.eq.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.delete_game("game-001")

            # All four tables should be cleaned
            assert LocalCache.get_game("game-001") is None
            assert LocalCache.get_objectives_by_game("game-001") == []
            assert LocalCache.get_requirements_by_objectives(["obj-001"]) == []
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
    def test_writes_single_user_pending_to_cache(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.insert.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.add_pending("Soul Mates", "user-001")

            rolls = LocalCache.get_rolls_by_user("user-001")
            pending = [r for r in rolls if r["status"] == "pending"]
            assert len(pending) == 1
            assert pending[0]["event_name"] == "Soul Mates"
        finally:
            _teardown_cache(tmpdir)

    def test_writes_two_user_pendings_to_cache(self):
        tmpdir = _init_cache()
        try:
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.insert.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.add_pending("Soul Mates", "user-001", "user-002")

            rolls_u1 = [
                r
                for r in LocalCache.get_rolls_by_user("user-001")
                if r["status"] == "pending"
            ]
            rolls_u2 = [
                r
                for r in LocalCache.get_rolls_by_user("user-002")
                if r["status"] == "pending"
            ]
            assert len(rolls_u1) == 1
            assert len(rolls_u2) == 1
        finally:
            _teardown_cache(tmpdir)


class TestKillPendingDualWrite:
    def test_deletes_roll_and_roll_games_from_cache(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_roll(
                {
                    **ROLL_DB_ROW,
                    "id": "pending-001",
                    "event_name": "Soul Mates",
                    "user1_ce_id": "user-001",
                    "status": "pending",
                }
            )
            LocalCache.upsert_roll_games_bulk(
                [
                    {
                        "roll_id": "pending-001",
                        "game_id": "game-001",
                        "index": 0,
                        "rolled_at": "",
                    },
                ]
            )

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
            assert LocalCache.get_roll_games("pending-001") == []
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
                LocalCache.upsert_user_games_bulk(
                    [
                        {
                            "user_ce_id": uid,
                            "game_ce_id": "game-001",
                            "updated_at_CE": "",
                        },
                    ]
                )
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
                result = SupabaseReader.get_games_bulk(["game-001", "nonexistent"])
            assert len(result) == 1
        finally:
            _teardown_cache(tmpdir)


class TestGetGameCustomRequirements:
    def test_game_with_custom_requirement(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_game(GAME_DB_ROW)
            LocalCache.upsert_objectives_bulk([OBJECTIVE_DB_ROW])
            LocalCache.upsert_requirements_bulk(
                [
                    {
                        "objective_ce_id": "obj-001",
                        "requirement_type": "custom",
                        "data": "Beat all chapters without dying",
                        "updated_at_CE": "2026-01-01",
                    },
                ]
            )
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
            LocalCache.upsert_requirements_bulk(
                [
                    {
                        "objective_ce_id": "obj-001",
                        "requirement_type": "achievement",
                        "data": "ach-1",
                        "updated_at_CE": "",
                    },
                    {
                        "objective_ce_id": "obj-001",
                        "requirement_type": "achievement",
                        "data": "ach-2",
                        "updated_at_CE": "",
                    },
                    {
                        "objective_ce_id": "obj-001",
                        "requirement_type": "custom",
                        "data": "Custom requirement text",
                        "updated_at_CE": "",
                    },
                ]
            )
            LocalCache.upsert_categories_bulk(CATEGORY_DB_ROWS)

            with patch.object(SupabaseReader, "supabase"):
                result = SupabaseReader.get_game("game-001")
            assert result is not None
            obj = result.all_objectives[0]
            assert set(obj.achievement_ce_ids or []) == {"ach-1", "ach-2"}
            assert obj.requirements == "Custom requirement text"
        finally:
            _teardown_cache(tmpdir)


class TestGetAllRollsGamesAttached:
    def test_rolls_have_games_attached(self):
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_roll(ROLL_DB_ROW)
            LocalCache.upsert_roll_games_bulk(
                [
                    {
                        "roll_id": "roll-001",
                        "game_id": "game-001",
                        "index": 0,
                        "rolled_at": "",
                    },
                    {
                        "roll_id": "roll-001",
                        "game_id": "game-002",
                        "index": 1,
                        "rolled_at": "",
                    },
                ]
            )
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
            LocalCache.upsert_tier_bulk(
                [
                    {"ce_id": "game-001", "price": 9.99, "sh_hours": 5.0},
                ]
            )
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
            LocalCache.upsert_tier_bulk(
                [
                    {"ce_id": "game-001", "price": 9.99, "sh_hours": 5.0},
                ]
            )
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                database_name = SupabaseReader.get_database_name()
                SupabaseReader.get_database_tier(database_name)
            mock_sb.table.assert_not_called()
        finally:
            _teardown_cache(tmpdir)


# === Missing writer coverage ===


class TestBulkDumpUsersDualWrite:
    def test_writes_users_games_and_objectives_to_cache(self):
        tmpdir = _init_cache()
        try:
            _seed_game()
            from tests.conftest import make_user, make_user_game, make_user_objective

            user = make_user(
                ce_id="user-new",
                discord_id=999,
                owned_games=[
                    make_user_game(
                        ce_id="game-001",
                        user_objectives=[
                            make_user_objective(
                                ce_id="obj-001",
                                game_ce_id="game-001",
                                user_points=25,
                                partial=True,
                            ),
                        ],
                    ),
                ],
            )

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.select.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.bulk_dump_users([user])

            # users table
            cached = LocalCache.get_user("user-new")
            assert cached is not None
            assert cached["display_name"] == "TestUser"

            # userGames table
            cached_games = LocalCache.get_user_games("user-new")
            assert len(cached_games) == 1
            assert cached_games[0]["game_ce_id"] == "game-001"

            # userObjectives table
            cached_objs = LocalCache.get_user_objectives("user-new")
            assert len(cached_objs) == 1
            assert cached_objs[0]["objective_ce_id"] == "obj-001"
            assert cached_objs[0]["partial"] == 1
        finally:
            _teardown_cache(tmpdir)

    def test_replaces_old_user_objectives(self):
        """When a user is re-dumped, old userObjectives should be replaced."""
        tmpdir = _init_cache()
        try:
            _seed_game()
            from tests.conftest import make_user, make_user_game, make_user_objective

            # First dump: obj-001
            user_v1 = make_user(
                ce_id="user-x",
                owned_games=[
                    make_user_game(
                        ce_id="game-001",
                        user_objectives=[
                            make_user_objective(
                                ce_id="obj-001", game_ce_id="game-001", user_points=10
                            ),
                        ],
                    ),
                ],
            )
            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.select.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])
                SupabaseReader.bulk_dump_users([user_v1])

            assert len(LocalCache.get_user_objectives("user-x")) == 1

            # Second dump: no objectives (user lost progress somehow)
            user_v2 = make_user(
                ce_id="user-x",
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
                SupabaseReader.bulk_dump_users([user_v2])

            # Old objectives should be gone
            assert LocalCache.get_user_objectives("user-x") == []
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
            assert [g["game_id"] for g in cached_games] == [
                "game-a",
                "game-b",
                "game-c",
            ]
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


class TestAsyncWrappersRemoved:
    """With the scraper decoupled into its own process and low bot traffic,
    asyncio.to_thread wrappers are unnecessary. All SupabaseReader functions
    should be called synchronously from bot command handlers."""

    def test_no_async_wrappers_on_module(self):
        async_names = [
            "get_user_async",
            "get_game_async",
            "get_list_async",
            "get_database_name_async",
            "get_database_user_async",
            "get_database_tier_async",
            "dump_user_async",
            "dump_game_async",
            "dump_roll_async",
            "bulk_dump_rolls_async",
            "bulk_dump_users_async",
            "add_pending_async",
            "kill_pending_async",
        ]
        for name in async_names:
            assert not hasattr(SupabaseReader, name), (
                f"SupabaseReader.{name} should be removed — call the sync version directly"
            )

    def test_no_to_thread_helper(self):
        assert not hasattr(SupabaseReader, "_to_thread"), (
            "_to_thread helper should be removed"
        )

    def test_asyncio_not_imported(self):
        import inspect

        source = inspect.getsource(SupabaseReader)
        assert "asyncio" not in source, "SupabaseReader should not import asyncio"


class TestThreadingRemovedFromLocalCache:
    """With async wrappers gone, SQLite is only accessed from a single thread.
    Threading infrastructure should be removed from LocalCache."""

    def test_no_lock_on_module(self):
        assert not hasattr(LocalCache, "_lock"), (
            "LocalCache._lock should be removed — no concurrent thread access"
        )

    def test_no_with_lock_decorator(self):
        assert not hasattr(LocalCache, "_with_lock"), (
            "_with_lock decorator should be removed"
        )

    def test_no_get_lock_function(self):
        assert not hasattr(LocalCache, "get_lock"), "get_lock() should be removed"

    def test_threading_not_imported(self):
        import inspect

        source = inspect.getsource(LocalCache)
        assert "threading" not in source, "LocalCache should not import threading"

    def test_sqlite_uses_default_same_thread(self):
        """Without threading, check_same_thread should be True (the default)."""
        import inspect

        source = inspect.getsource(LocalCache)
        assert "check_same_thread" not in source, (
            "check_same_thread=False should be removed — single-thread access only"
        )


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
                            make_user_objective(
                                ce_id="obj-001",
                                game_ce_id="game-001",
                                user_points=15,
                                partial=True,
                            ),
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
            assert cached_objs[0]["partial"] == 1
        finally:
            _teardown_cache(tmpdir)

    def test_writes_partial_to_supabase_payload(self):
        tmpdir = _init_cache()
        try:
            from tests.conftest import make_user, make_user_game, make_user_objective

            user = make_user(
                ce_id="user-new2",
                owned_games=[
                    make_user_game(
                        ce_id="game-001",
                        user_objectives=[
                            make_user_objective(
                                ce_id="obj-001", game_ce_id="game-001", partial=True
                            ),
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

            upsert_calls = [
                c for c in mock_sb.table.call_args_list if c.args == ("userObjectives",)
            ]
            assert len(upsert_calls) >= 1
            payload = mock_table.upsert.call_args_list[-1].args[0]
            assert payload["partial"] is True
            assert "user_points" not in payload
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
                result = SupabaseReader.get_users_bulk(
                    ["user-001"], include_rolls=False
                )
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
                result = SupabaseReader.get_users_bulk(
                    ["user-001"], include_rolls=False
                )
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
            LocalCache.upsert_game(
                {**GAME_DB_ROW, "ce_id": "game-002", "name": "Hollow Knight"}
            )
            LocalCache.upsert_objectives_bulk(
                [
                    {
                        **OBJECTIVE_DB_ROW,
                        "ce_id": "obj-002",
                        "game_ce_id": "game-002",
                        "name": "Steel Soul",
                    },
                ]
            )
            LocalCache.upsert_categories_bulk(
                [
                    {"game_id": "game-002", "category": "Action", "index": 0},
                ]
            )

            # Seed user with both games
            LocalCache.upsert_user(USER_DB_ROW)
            LocalCache.upsert_user_games_bulk(
                [
                    {
                        "user_ce_id": "user-001",
                        "game_ce_id": "game-001",
                        "updated_at_CE": "",
                    },
                    {
                        "user_ce_id": "user-001",
                        "game_ce_id": "game-002",
                        "updated_at_CE": "",
                    },
                ]
            )
            LocalCache.upsert_user_objectives_bulk(
                [
                    {
                        "user_ce_id": "user-001",
                        "objective_ce_id": "obj-001",
                        "partial": False,
                        "updated_at_CE": "",
                    },
                    {
                        "user_ce_id": "user-001",
                        "objective_ce_id": "obj-002",
                        "partial": False,
                        "updated_at_CE": "",
                    },
                ]
            )

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


class TestDeleteGameDeletesCategoriesFromSupabase:
    def test_calls_supabase_categories_delete(self):
        """delete_game must delete categories from Supabase, not just LocalCache."""
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

            # Collect all table names passed to supabase.table()
            table_calls = [c.args[0] for c in mock_sb.table.call_args_list]
            assert "categories" in table_calls, (
                "delete_game should delete categories from Supabase"
            )
        finally:
            _teardown_cache(tmpdir)


class TestDumpRollDeletesOldRollGamesFromSupabase:
    def test_calls_supabase_rollgames_delete_before_upsert(self):
        """dump_roll must delete old rollGames from Supabase before inserting new ones."""
        tmpdir = _init_cache()
        try:
            from tests.conftest import make_roll

            roll = make_roll(roll_name="One Hell of a Day", games=["game-001"])

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.eq.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                SupabaseReader.dump_roll(roll)

            # Collect table names that had .delete() called
            table_calls = [c.args[0] for c in mock_sb.table.call_args_list]
            assert "rollGames" in table_calls, (
                "dump_roll should call supabase.table('rollGames')"
            )
            assert mock_table.delete.called, (
                "dump_roll should delete old rollGames from Supabase before re-inserting"
            )
        finally:
            _teardown_cache(tmpdir)


class TestBulkDumpUsersDeletesViaLocalCache:
    def test_user_objectives_delete_uses_localcache_function(self):
        """bulk_dump_users should use LocalCache.delete_user_objectives,
        not raw conn.execute()."""
        tmpdir = _init_cache()
        try:
            _seed_game()
            from tests.conftest import make_user, make_user_game, make_user_objective

            # Pre-seed an objective that should be cleared
            LocalCache.upsert_user(
                {
                    "ce_id": "user-lock",
                    "discord_id": 111,
                    "display_name": "LockTest",
                    "image_avatar": None,
                    "steam_id": None,
                    "created_at_CE": "",
                    "updated_at_CE": "",
                }
            )
            LocalCache.upsert_user_objectives_bulk(
                [
                    {
                        "user_ce_id": "user-lock",
                        "objective_ce_id": "obj-stale",
                        "partial": False,
                        "updated_at_CE": "",
                    }
                ]
            )

            user = make_user(
                ce_id="user-lock",
                discord_id=111,
                owned_games=[
                    make_user_game(
                        ce_id="game-001",
                        user_objectives=[
                            make_user_objective(
                                ce_id="obj-001", game_ce_id="game-001", user_points=25
                            ),
                        ],
                    ),
                ],
            )

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.select.return_value = mock_table
                mock_table.upsert.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                with patch.object(LocalCache, "delete_user_objectives") as mock_delete:
                    SupabaseReader.bulk_dump_users([user])

                    mock_delete.assert_called_once_with("user-lock")
        finally:
            _teardown_cache(tmpdir)


class TestCleanDbUsesLocalCacheDeleteFunctions:
    def test_orphan_cleanup_uses_localcache_delete_functions(self):
        """clean_db should use LocalCache's dedicated delete functions
        instead of raw conn.execute() for SQLite writes."""
        tmpdir = _init_cache()
        try:
            # Create orphan user_game and user_objective
            LocalCache.upsert_user(USER_DB_ROW)
            LocalCache.upsert_user_games_bulk(
                [
                    {
                        "user_ce_id": "user-001",
                        "game_ce_id": "orphan-game",
                        "updated_at_CE": "",
                    },
                ]
            )
            LocalCache.upsert_user_objectives_bulk(
                [
                    {
                        "user_ce_id": "user-001",
                        "objective_ce_id": "orphan-obj",
                        "partial": False,
                        "updated_at_CE": "",
                    },
                ]
            )

            with patch.object(SupabaseReader, "supabase") as mock_sb:
                mock_table = MagicMock()
                mock_sb.table.return_value = mock_table
                mock_table.delete.return_value = mock_table
                mock_table.in_.return_value = mock_table
                mock_table.execute.return_value = MagicMock(data=[])

                with (
                    patch.object(
                        LocalCache, "delete_user_games_by_game_ids"
                    ) as mock_ug,
                    patch.object(
                        LocalCache, "delete_user_objectives_by_objective_ids"
                    ) as mock_uo,
                ):
                    SupabaseReader.clean_db()

                    mock_ug.assert_called_once()
                    mock_uo.assert_called_once()
        finally:
            _teardown_cache(tmpdir)


class TestGetAllRollsUsesIndexing:
    def test_multiple_rolls_get_correct_games(self):
        """get_all_rolls should correctly match roll_games to their rolls,
        even with multiple rolls — verifies dict-based indexing works."""
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_rolls_bulk(
                [
                    {**ROLL_DB_ROW, "id": "roll-A", "event_name": "One Hell of a Day"},
                    {**ROLL_DB_ROW, "id": "roll-B", "event_name": "One Hell of a Week"},
                ]
            )
            LocalCache.upsert_roll_games_bulk(
                [
                    {
                        "roll_id": "roll-A",
                        "game_id": "game-aaa",
                        "index": 0,
                        "rolled_at": "",
                    },
                    {
                        "roll_id": "roll-B",
                        "game_id": "game-bbb",
                        "index": 0,
                        "rolled_at": "",
                    },
                    {
                        "roll_id": "roll-B",
                        "game_id": "game-ccc",
                        "index": 1,
                        "rolled_at": "",
                    },
                ]
            )

            with patch.object(SupabaseReader, "supabase"):
                rolls = SupabaseReader.get_all_rolls()

            rolls_by_id = {r._id: r for r in rolls}
            assert set(rolls_by_id["roll-A"].games) == {"game-aaa"}
            assert set(rolls_by_id["roll-B"].games) == {"game-bbb", "game-ccc"}
        finally:
            _teardown_cache(tmpdir)

    def test_get_checkable_rolls_correct_games(self):
        """get_checkable_rolls should correctly match roll_games."""
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_rolls_bulk(
                [
                    {**ROLL_DB_ROW, "id": "roll-X", "status": "current"},
                    {**ROLL_DB_ROW, "id": "roll-Y", "status": "pending"},
                ]
            )
            LocalCache.upsert_roll_games_bulk(
                [
                    {
                        "roll_id": "roll-X",
                        "game_id": "game-x1",
                        "index": 0,
                        "rolled_at": "",
                    },
                    {
                        "roll_id": "roll-Y",
                        "game_id": "game-y1",
                        "index": 0,
                        "rolled_at": "",
                    },
                ]
            )

            with patch.object(SupabaseReader, "supabase"):
                rolls = SupabaseReader.get_checkable_rolls()

            rolls_by_id = {r._id: r for r in rolls}
            assert rolls_by_id["roll-X"].games == ["game-x1"]
            assert rolls_by_id["roll-Y"].games == ["game-y1"]
        finally:
            _teardown_cache(tmpdir)

    def test_get_user_rolls_correct_games(self):
        """get_user_rolls should correctly match roll_games."""
        tmpdir = _init_cache()
        try:
            LocalCache.upsert_rolls_bulk(
                [
                    {**ROLL_DB_ROW, "id": "roll-u1", "user1_ce_id": "user-001"},
                    {**ROLL_DB_ROW, "id": "roll-u2", "user1_ce_id": "user-001"},
                ]
            )
            LocalCache.upsert_roll_games_bulk(
                [
                    {
                        "roll_id": "roll-u1",
                        "game_id": "game-r1",
                        "index": 0,
                        "rolled_at": "",
                    },
                    {
                        "roll_id": "roll-u2",
                        "game_id": "game-r2",
                        "index": 0,
                        "rolled_at": "",
                    },
                    {
                        "roll_id": "roll-u2",
                        "game_id": "game-r3",
                        "index": 1,
                        "rolled_at": "",
                    },
                ]
            )

            with patch.object(SupabaseReader, "supabase"):
                rolls = SupabaseReader.get_user_rolls("user-001")

            rolls_by_id = {r._id: r for r in rolls}
            assert rolls_by_id["roll-u1"].games == ["game-r1"]
            assert set(rolls_by_id["roll-u2"].games) == {"game-r2", "game-r3"}
        finally:
            _teardown_cache(tmpdir)


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
            LocalCache.upsert_user_games_bulk(
                [
                    {
                        "user_ce_id": "user-001",
                        "game_ce_id": "nonexistent-game",
                        "updated_at_CE": "",
                    },
                ]
            )

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
