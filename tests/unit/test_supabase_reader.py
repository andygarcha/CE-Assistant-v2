"""
Unit tests for SupabaseReader.get_database_tier().

The function is unimplemented; these tests define the expected contract.
All Supabase I/O is mocked — no real network calls are made.

Contract (from docstring + scraper reference implementation):
  database_tier[str(tier_num)][category] = list of entries
  Each entry: {"ce_id": str, "price": int, "sh_hours": int}
  - Only Steam games are included.
  - T0 games (0 PO points) are excluded.
  - Games with no entry in the tier table are excluded.
  - Multi-category games appear in every category they belong to.
"""

from typing import get_args
from unittest.mock import MagicMock, patch

import pytest

from Classes.CE_Game import CEGame
from Modules import hm
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
    """Steam game whose tier is derived from `po_points`."""
    obj = make_objective(ce_id="obj-001", game_ce_id=ce_id, point_value=po_points)
    return make_game(
        ce_id=ce_id,
        categories=categories or ["Action"],
        objectives=[obj],
        platform="steam",
    )


def _tier_row(ce_id: str, price: int = 500, sh_hours: int = 60) -> dict[str, int | str]:
    """A single row as returned by the `tier` Supabase table."""
    return {"ce_id": ce_id, "price": price, "sh_hours": sh_hours}


# ── fixtures ──────────────────────────────────────────────────────────────────


def _mock_supabase(tier_rows: list[dict]) -> MagicMock:
    """Return a mock supabase client whose tier table select returns `tier_rows`."""
    mock: MagicMock = MagicMock()
    mock.table.return_value.select.return_value.execute.return_value.data = tier_rows
    return mock


# ── output structure ──────────────────────────────────────────────────────────


class TestOutputStructure:
    def test_returns_dict(self) -> None:
        with patch("Modules.SupabaseReader.supabase", _mock_supabase([])):
            result = get_database_tier([])
        assert isinstance(result, dict)

    def test_has_all_seven_tiers(self) -> None:
        with patch("Modules.SupabaseReader.supabase", _mock_supabase([])):
            result = get_database_tier([])
        assert set(result.keys()) == set(ALL_TIERS)

    def test_each_tier_has_all_categories(self) -> None:
        with patch("Modules.SupabaseReader.supabase", _mock_supabase([])):
            result = get_database_tier([])
        for tier in ALL_TIERS:
            assert set(result[tier].keys()) == set(ALL_CATS), (
                f"Tier {tier!r} is missing some category keys."
            )

    def test_each_category_is_a_list(self) -> None:
        with patch("Modules.SupabaseReader.supabase", _mock_supabase([])):
            result = get_database_tier([])
        for tier in ALL_TIERS:
            for cat in ALL_CATS:
                assert isinstance(result[tier][cat], list), (
                    f"result[{tier!r}][{cat!r}] should be a list."
                )

    def test_empty_database_name_has_no_entries(self) -> None:
        with patch("Modules.SupabaseReader.supabase", _mock_supabase([])):
            result = get_database_tier([])
        for tier in ALL_TIERS:
            for cat in ALL_CATS:
                assert result[tier][cat] == []


# ── entry shape ───────────────────────────────────────────────────────────────


class TestEntryShape:
    def test_entry_has_ce_id(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        entry = result["1"]["Action"][0]
        assert "ce_id" in entry

    def test_entry_has_price(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        entry = result["1"]["Action"][0]
        assert "price" in entry

    def test_entry_has_sh_hours(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        entry = result["1"]["Action"][0]
        assert "sh_hours" in entry

    def test_entry_values_match_tier_table(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])
        row = _tier_row(GAME_A, price=1499, sh_hours=180)
        with patch("Modules.SupabaseReader.supabase", _mock_supabase([row])):
            result = get_database_tier([game])
        entry = result["1"]["Action"][0]
        assert entry["ce_id"] == GAME_A
        assert entry["price"] == 1499
        assert entry["sh_hours"] == 180


# ── tier placement ────────────────────────────────────────────────────────────


class TestTierPlacement:
    @pytest.mark.parametrize(
        "po_points, expected_tier",
        [
            (10, "1"),  # T1: 5–19
            (25, "2"),  # T2: 20–39
            (50, "3"),  # T3: 40–79
            (100, "4"),  # T4: 80–199
            (250, "5"),  # T5: 200–399
            (500, "6"),  # T6: 400–799
            (1000, "7"),  # T7: 800+
        ],
    )
    def test_game_placed_in_correct_tier(
        self, po_points: int, expected_tier: str
    ) -> None:
        game = _steam_game(GAME_A, po_points=po_points, categories=["Action"])
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        ids_in_expected = [e["ce_id"] for e in result[expected_tier]["Action"]]
        assert GAME_A in ids_in_expected

    def test_game_not_in_other_tiers(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])  # T1
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        for tier in ALL_TIERS:
            if tier == "1":
                continue
            ids = [e["ce_id"] for e in result[tier]["Action"]]
            assert GAME_A not in ids, f"T1 game found in tier {tier!r}."


# ── category placement ────────────────────────────────────────────────────────


class TestCategoryPlacement:
    def test_single_category_game_in_correct_slot(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Strategy"])
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        assert any(e["ce_id"] == GAME_A for e in result["1"]["Strategy"])

    def test_single_category_game_absent_from_other_categories(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Strategy"])
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        for cat in ALL_CATS:
            if cat == "Strategy":
                continue
            ids = [e["ce_id"] for e in result["1"][cat]]
            assert GAME_A not in ids, f"Single-category game found in {cat!r}."

    def test_multi_category_game_appears_in_all_its_categories(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action", "Arcade"])
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        assert any(e["ce_id"] == GAME_A for e in result["1"]["Action"])
        assert any(e["ce_id"] == GAME_A for e in result["1"]["Arcade"])

    def test_multi_category_game_absent_from_unrelated_categories(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action", "Arcade"])
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        for cat in ALL_CATS:
            if cat in ("Action", "Arcade"):
                continue
            ids = [e["ce_id"] for e in result["1"][cat]]
            assert GAME_A not in ids


# ── exclusion rules ───────────────────────────────────────────────────────────


class TestExclusions:
    def test_non_steam_game_excluded(self) -> None:
        game = make_game(
            ce_id=GAME_A,
            categories=["Action"],
            objectives=[make_objective(point_value=10)],
            platform="gog",
        )
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        for tier in ALL_TIERS:
            for cat in ALL_CATS:
                assert not any(e["ce_id"] == GAME_A for e in result[tier][cat])

    def test_t0_game_excluded(self) -> None:
        game = _steam_game(GAME_A, po_points=0, categories=["Action"])
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game])
        for tier in ALL_TIERS:
            for cat in ALL_CATS:
                assert not any(e["ce_id"] == GAME_A for e in result[tier][cat])

    def test_game_without_tier_table_entry_excluded(self) -> None:
        game = _steam_game(GAME_A, po_points=10, categories=["Action"])
        # tier table is empty — no entry for GAME_A
        with patch("Modules.SupabaseReader.supabase", _mock_supabase([])):
            result = get_database_tier([game])
        for tier in ALL_TIERS:
            for cat in ALL_CATS:
                assert not any(e["ce_id"] == GAME_A for e in result[tier][cat])

    def test_only_game_with_tier_entry_is_included(self) -> None:
        """GAME_A has a tier entry; GAME_B does not. Only GAME_A should appear."""
        game_a = _steam_game(GAME_A, po_points=10, categories=["Action"])
        game_b = _steam_game(GAME_B, po_points=10, categories=["Action"])
        with patch(
            "Modules.SupabaseReader.supabase", _mock_supabase([_tier_row(GAME_A)])
        ):
            result = get_database_tier([game_a, game_b])
        ids = [e["ce_id"] for e in result["1"]["Action"]]
        assert GAME_A in ids
        assert GAME_B not in ids


# ── multiple games ────────────────────────────────────────────────────────────


class TestMultipleGames:
    def test_two_games_same_tier_and_category_both_present(self) -> None:
        game_a = _steam_game(GAME_A, po_points=10, categories=["Action"])
        game_b = _steam_game(GAME_B, po_points=15, categories=["Action"])
        rows = [_tier_row(GAME_A), _tier_row(GAME_B)]
        with patch("Modules.SupabaseReader.supabase", _mock_supabase(rows)):
            result = get_database_tier([game_a, game_b])
        ids = [e["ce_id"] for e in result["1"]["Action"]]
        assert GAME_A in ids
        assert GAME_B in ids

    def test_games_in_different_tiers_placed_correctly(self) -> None:
        game_a = _steam_game(GAME_A, po_points=10, categories=["Action"])  # T1
        game_b = _steam_game(GAME_B, po_points=25, categories=["Action"])  # T2
        rows = [_tier_row(GAME_A), _tier_row(GAME_B)]
        with patch("Modules.SupabaseReader.supabase", _mock_supabase(rows)):
            result = get_database_tier([game_a, game_b])
        t1_ids = [e["ce_id"] for e in result["1"]["Action"]]
        t2_ids = [e["ce_id"] for e in result["2"]["Action"]]
        assert GAME_A in t1_ids and GAME_B not in t1_ids
        assert GAME_B in t2_ids and GAME_A not in t2_ids
