"""
Unit tests for SupabaseReader.get_database_tier().

Contract (from docstring + scraper reference implementation):
  database_tier[str(tier_num)][category] = list of entries
  Each entry: {"ce_id": str, "price": int, "sh_hours": int}
  - Only Steam games are included.
  - T0 games (0 PO points) are excluded.
  - Games with no entry in the tier table are excluded.
  - Multi-category games appear in every category they belong to.
"""

import os
import shutil
import tempfile
from typing import get_args

import pytest

from Classes.CE_Game import CEGame
from Modules import LocalCache, hm
from Modules.SupabaseReader import get_database_tier
from tests.conftest import make_game, make_objective

# ── constants ─────────────────────────────────────────────────────────────────

ALL_CATS: list[str] = list(get_args(hm.CATEGORIES))
ALL_TIERS: list[str] = [str(t) for t in range(1, 8)]

GAME_A: str = "game-aaa-0000-0000-000000000000"
GAME_B: str = "game-bbb-0000-0000-000000000000"

# ── game builders ─────────────────────────────────────────────────────────────


def _steam_game(
    ce_id: str,
    po_points: int,
    categories: list[str] | None = None,
) -> CEGame:
    obj = make_objective(ce_id="obj-001", game_ce_id=ce_id, point_value=po_points)
    return make_game(
        ce_id=ce_id,
        categories=categories or ["Action"],
        objectives=[obj],
        platform="steam",
    )


def _tier_row(ce_id: str, price: int = 500, sh_hours: int = 60) -> dict[str, int | str]:
    return {"ce_id": ce_id, "price": price, "sh_hours": sh_hours}


# ── cache fixture ─────────────────────────────────────────────────────────────

_tmpdir: str | None = None


def _setup_cache(tier_rows: list[dict] | None = None) -> None:
    global _tmpdir
    if _tmpdir is not None:
        LocalCache.close()
        shutil.rmtree(_tmpdir)
    _tmpdir = tempfile.mkdtemp()
    LocalCache.init(os.path.join(_tmpdir, "test.db"))
    if tier_rows:
        LocalCache.upsert_tier_bulk(tier_rows)


def _teardown_cache() -> None:
    global _tmpdir
    if _tmpdir is not None:
        LocalCache.close()
        shutil.rmtree(_tmpdir)
        _tmpdir = None


def _run(tier_rows: list[dict], games: list[CEGame]) -> dict:
    _setup_cache(tier_rows)
    try:
        return get_database_tier(games)
    finally:
        _teardown_cache()


# ── output structure ──────────────────────────────────────────────────────────


class TestOutputStructure:
    def test_returns_dict(self) -> None:
        assert isinstance(_run([], []), dict)

    def test_has_all_seven_tiers(self) -> None:
        result = _run([], [])
        assert set(result.keys()) == set(ALL_TIERS)

    def test_each_tier_has_all_categories(self) -> None:
        result = _run([], [])
        for tier in ALL_TIERS:
            assert set(result[tier].keys()) == set(ALL_CATS)

    def test_each_category_is_a_list(self) -> None:
        result = _run([], [])
        for tier in ALL_TIERS:
            for cat in ALL_CATS:
                assert isinstance(result[tier][cat], list)

    def test_empty_database_name_has_no_entries(self) -> None:
        result = _run([], [])
        for tier in ALL_TIERS:
            for cat in ALL_CATS:
                assert result[tier][cat] == []


# ── entry shape ──────────────────────────────────────────────────────────────


class TestEntryShape:
    def test_entry_has_ce_id(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])
        result = _run([_tier_row(GAME_A)], [game])
        entry = result["1"]["Action"][0]
        assert "ce_id" in entry

    def test_entry_has_price(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])
        result = _run([_tier_row(GAME_A)], [game])
        entry = result["1"]["Action"][0]
        assert "price" in entry

    def test_entry_has_sh_hours(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])
        result = _run([_tier_row(GAME_A)], [game])
        entry = result["1"]["Action"][0]
        assert "sh_hours" in entry

    def test_entry_values_match_tier_table(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])
        row = _tier_row(GAME_A, price=1499, sh_hours=180)
        result = _run([row], [game])
        entry = result["1"]["Action"][0]
        assert entry["ce_id"] == GAME_A
        assert entry["price"] == 1499
        assert entry["sh_hours"] == 180


# ── tier placement ───────────────────────────────────────────────────────────


class TestTierPlacement:
    @pytest.mark.parametrize(
        "po_points, expected_tier",
        [(10, "1"), (25, "2"), (50, "3"), (100, "4"), (200, "5"), (400, "6"), (800, "7")],
    )
    def test_game_placed_in_correct_tier(self, po_points: int, expected_tier: str) -> None:
        game = _steam_game(GAME_A, po_points=po_points, categories=["Action"])
        result = _run([_tier_row(GAME_A)], [game])
        assert len(result[expected_tier]["Action"]) == 1

    @pytest.mark.parametrize(
        "po_points, expected_tier",
        [(10, "1"), (25, "2"), (50, "3"), (100, "4"), (200, "5"), (400, "6"), (800, "7")],
    )
    def test_game_absent_from_other_tiers(self, po_points: int, expected_tier: str) -> None:
        game = _steam_game(GAME_A, po_points=po_points, categories=["Action"])
        result = _run([_tier_row(GAME_A)], [game])
        for tier in ALL_TIERS:
            if tier != expected_tier:
                assert result[tier]["Action"] == []


# ── category placement ──────────────────────────────────────────────────────


class TestCategoryPlacement:
    def test_single_category(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Arcade"])
        result = _run([_tier_row(GAME_A)], [game])
        assert len(result["1"]["Arcade"]) == 1
        assert result["1"]["Action"] == []

    def test_multi_category_appears_in_all(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action", "Arcade"])
        result = _run([_tier_row(GAME_A)], [game])
        assert len(result["1"]["Action"]) == 1
        assert len(result["1"]["Arcade"]) == 1


# ── exclusions ───────────────────────────────────────────────────────────────


class TestExclusions:
    def test_t0_game_excluded(self) -> None:
        game = _steam_game(GAME_A, po_points=0, categories=["Action"])
        result = _run([_tier_row(GAME_A)], [game])
        for tier in ALL_TIERS:
            assert result[tier]["Action"] == []

    def test_non_steam_game_excluded(self) -> None:
        obj = make_objective(ce_id="obj-001", game_ce_id=GAME_A, point_value=10)
        game = make_game(ce_id=GAME_A, categories=["Action"], objectives=[obj], platform="other")
        result = _run([_tier_row(GAME_A)], [game])
        for tier in ALL_TIERS:
            assert result[tier]["Action"] == []

    def test_game_without_tier_table_entry_excluded(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])
        result = _run([], [game])
        assert result["1"]["Action"] == []

    def test_only_game_with_tier_entry_is_included(self) -> None:
        game_a = _steam_game(GAME_A, po_points=10, categories=["Action"])
        game_b = _steam_game(GAME_B, po_points=10, categories=["Action"])
        result = _run([_tier_row(GAME_A)], [game_a, game_b])
        assert len(result["1"]["Action"]) == 1
        assert result["1"]["Action"][0]["ce_id"] == GAME_A


# ── multiple games ───────────────────────────────────────────────────────────


class TestMultipleGames:
    def test_two_games_same_tier_and_category_both_present(self) -> None:
        game_a = _steam_game(GAME_A, po_points=10, categories=["Action"])
        game_b = _steam_game(GAME_B, po_points=10, categories=["Action"])
        rows = [_tier_row(GAME_A), _tier_row(GAME_B)]
        result = _run(rows, [game_a, game_b])
        ids = {e["ce_id"] for e in result["1"]["Action"]}
        assert ids == {GAME_A, GAME_B}

    def test_games_in_different_tiers_placed_correctly(self) -> None:
        game_a = _steam_game(GAME_A, po_points=10, categories=["Action"])
        game_b = _steam_game(GAME_B, po_points=50, categories=["Action"])
        rows = [_tier_row(GAME_A), _tier_row(GAME_B)]
        result = _run(rows, [game_a, game_b])
        assert len(result["1"]["Action"]) == 1
        assert result["1"]["Action"][0]["ce_id"] == GAME_A
        assert len(result["3"]["Action"]) == 1
        assert result["3"]["Action"][0]["ce_id"] == GAME_B
