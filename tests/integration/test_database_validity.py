"""
Database validity tests for the MongoDB → Supabase roll migration.

These tests hit the real Supabase instance and are read-only.
Run them with:  pytest tests/integration/
"""

from collections import defaultdict

import pytest

from Classes.CE_Roll import CERoll
from Modules import SupabaseReader
from utils.game_utils import ALL_ROLL_EVENT_NAMES_TUPLE


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def all_rolls() -> list[CERoll]:
    return SupabaseReader.get_all_rolls()


@pytest.fixture(scope="module")
def by_name(all_rolls: list[CERoll]) -> dict[str, list[CERoll]]:
    result: dict[str, list[CERoll]] = defaultdict(list)
    for roll in all_rolls:
        if roll.status == "won_legacy":
            continue
        result[roll.roll_name].append(roll)
    return dict(result)


# ── helpers ───────────────────────────────────────────────────────────────────


def _wrong_count(rolls: list[CERoll], expected: int) -> list[CERoll]:
    return [r for r in rolls if len(r.games) != expected]


def _out_of_range(rolls: list[CERoll], lo: int, hi: int) -> list[CERoll]:
    return [r for r in rolls if not (lo <= len(r.games) <= hi)]


def _ids(rolls: list[CERoll]) -> list[str]:
    """Return roll IDs for use in assertion messages."""
    return [r._id for r in rolls]


def _rolls_won(rolls: list[CERoll]) -> list[CERoll]:
    return [r for r in rolls if r.status == "won"]


def _rolls_active(rolls: list[CERoll]) -> list[CERoll]:
    return [r for r in rolls if r.status in ("current", "between_stages", "pending")]


# ── structural checks ─────────────────────────────────────────────────────────


class TestStructural:
    def test_database_has_rolls(self, all_rolls: list[CERoll]):
        assert len(all_rolls) > 0, "No rolls found in the database."

    def test_no_roll_has_empty_id(self, all_rolls: list[CERoll]):
        bad = [r for r in all_rolls if not r._id]
        assert not bad, f"{len(bad)} rolls have an empty/None ID."

    def test_no_roll_has_empty_name(self, all_rolls: list[CERoll]):
        bad = [r for r in all_rolls if not r.roll_name]
        assert not bad, f"{len(bad)} rolls have an empty/None roll_name."

    def test_all_roll_names_are_known(self, all_rolls: list[CERoll]):
        unknown = {r.roll_name for r in all_rolls} - set(ALL_ROLL_EVENT_NAMES_TUPLE)
        assert not unknown, f"Unknown roll names found in database: {unknown}"

    def test_no_roll_has_zero_games(self, all_rolls: list[CERoll]):
        bad = [r for r in all_rolls if len(r.games) == 0]
        assert not bad, (
            f"{len(bad)} rolls have 0 games — likely orphaned rows from migration:\n"
            f"{_ids(bad)}"
        )

    def test_no_roll_has_duplicate_games(self, all_rolls: list[CERoll]):
        bad = [r for r in all_rolls if len(r.games) != len(set(r.games))]
        assert not bad, f"{len(bad)} rolls contain duplicate game IDs:\n{_ids(bad)}"

    def test_all_game_ids_are_non_empty(self, all_rolls: list[CERoll]):
        bad = [r for r in all_rolls if any(not g for g in r.games)]
        assert not bad, f"{len(bad)} rolls contain empty/None game IDs:\n{_ids(bad)}"

    def test_no_duplicate_roll_ids(self, all_rolls: list[CERoll]):
        ids = [r._id for r in all_rolls]
        seen, dupes = set(), set()
        for i in ids:
            (dupes if i in seen else seen).add(i)
        assert not dupes, f"Duplicate roll IDs found: {dupes}"

    def test_roll_status_values_are_valid(self, all_rolls: list[CERoll]):
        valid = {
            "current",
            "won",
            "failed",
            "pending",
            "between_stages",
            "removed",
            "won_legacy",
        }
        bad = [r for r in all_rolls if r.status not in valid]
        assert not bad, (
            f"{len(bad)} rolls have an unrecognised status value:\n"
            + "\n".join(f"  {r._id}: {r.status!r}" for r in bad)
        )


# ── solo roll game counts ─────────────────────────────────────────────────────


class TestSoloRollGameCounts:
    def test_one_hell_of_a_day_has_one_game(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("One Hell of a Day", [])
        bad = _wrong_count(rolls, 1)
        assert not bad, (
            f"{len(bad)} 'One Hell of a Day' rolls have the wrong game count:\n{_ids(bad)}"
        )

    def test_one_hell_of_a_week_has_five_games(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("One Hell of a Week", [])
        bad = _wrong_count(rolls, 5)
        assert not bad, (
            f"{len(bad)} 'One Hell of a Week' rolls have the wrong game count:\n{_ids(bad)}"
        )

    def test_one_hell_of_a_month_has_25_games(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("One Hell of a Month", [])
        bad = _wrong_count(rolls, 25)
        assert not bad, (
            f"{len(bad)} 'One Hell of a Month' rolls have the wrong game count:\n{_ids(bad)}"
        )

    def test_never_lucky_has_one_game(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("Never Lucky", [])
        bad = _wrong_count(rolls, 1)
        assert not bad, (
            f"{len(bad)} 'Never Lucky' rolls have the wrong game count:\n{_ids(bad)}"
        )

    def test_triple_threat_has_three_games(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("Triple Threat", [])
        bad = _wrong_count(rolls, 3)
        assert not bad, (
            f"{len(bad)} 'Triple Threat' rolls have the wrong game count:\n{_ids(bad)}"
        )

    def test_let_fate_decide_has_one_game(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("Let Fate Decide", [])
        bad = _wrong_count(rolls, 1)
        assert not bad, (
            f"{len(bad)} 'Let Fate Decide' rolls have the wrong game count:\n{_ids(bad)}"
        )

    # ── multi-stage solo rolls ────────────────────────────────────────────────

    def test_two_week_t2_streak_game_count_in_range(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("Two Week T2 Streak", [])
        bad = _out_of_range(rolls, 1, 2)
        assert not bad, (
            f"{len(bad)} 'Two Week T2 Streak' rolls have a game count outside [1, 2]:\n"
            + "\n".join(f"  {r._id}: {len(r.games)} games" for r in bad)
        )

    def test_two_week_t2_streak_won_has_two_games(self, by_name: dict[str, list[CERoll]]):
        won = _rolls_won(by_name.get("Two Week T2 Streak", []))
        bad = _wrong_count(won, 2)
        assert not bad, (
            f"{len(bad)} won 'Two Week T2 Streak' rolls have the wrong game count "
            f"(expected 2):\n{_ids(bad)}"
        )

    def test_two_two_week_t2_streak_streak_game_count_in_range(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get('Two "Two Week T2 Streak" Streak', [])
        bad = _out_of_range(rolls, 1, 4)
        assert not bad, (
            f"{len(bad)} 'Two \"Two Week T2 Streak\" Streak' rolls have a game count "
            f"outside [1, 4]:\n"
            + "\n".join(f"  {r._id}: {len(r.games)} games" for r in bad)
        )

    def test_two_two_week_t2_streak_streak_won_has_four_games(self, by_name: dict[str, list[CERoll]]):
        won = _rolls_won(by_name.get('Two "Two Week T2 Streak" Streak', []))
        bad = _wrong_count(won, 4)
        assert not bad, (
            f"{len(bad)} won 'Two \"Two Week T2 Streak\" Streak' rolls have wrong "
            f"game count (expected 4):\n{_ids(bad)}"
        )

    def test_fourward_thinking_game_count_in_range(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("Fourward Thinking", [])
        bad = _out_of_range(rolls, 1, 4)
        assert not bad, (
            f"{len(bad)} 'Fourward Thinking' rolls have a game count outside [1, 4]:\n"
            + "\n".join(f"  {r._id}: {len(r.games)} games" for r in bad)
        )

    def test_fourward_thinking_won_has_four_games(self, by_name: dict[str, list[CERoll]]):
        won = _rolls_won(by_name.get("Fourward Thinking", []))
        bad = _wrong_count(won, 4)
        assert not bad, (
            f"{len(bad)} won 'Fourward Thinking' rolls have wrong game count "
            f"(expected 4):\n{_ids(bad)}"
        )


# ── co-op roll game counts ────────────────────────────────────────────────────


class TestCoopRollGameCounts:
    def test_destiny_alignment_has_two_games(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("Destiny Alignment", [])
        bad = _wrong_count(rolls, 2)
        assert not bad, (
            f"{len(bad)} 'Destiny Alignment' rolls have the wrong game count "
            f"(expected 2 — one game per player):\n{_ids(bad)}"
        )

    def test_soul_mates_has_one_game(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("Soul Mates", [])
        bad = _wrong_count(rolls, 1)
        assert not bad, (
            f"{len(bad)} 'Soul Mates' rolls have the wrong game count:\n{_ids(bad)}"
        )

    def test_teamwork_makes_the_dream_work_has_four_games(self, by_name: dict[str, list[CERoll]]):
        rolls = by_name.get("Teamwork Makes the Dream Work", [])
        bad = _wrong_count(rolls, 4)
        assert not bad, (
            f"{len(bad)} 'Teamwork Makes the Dream Work' rolls have the wrong game "
            f"count (expected 4):\n{_ids(bad)}"
        )


# ── cross-roll consistency ────────────────────────────────────────────────────


class TestCrossRollConsistency:
    def test_co_op_rolls_have_partner_id(self, by_name: dict[str, list[CERoll]]):
        co_op_names = (
            "Destiny Alignment",
            "Soul Mates",
            "Teamwork Makes the Dream Work",
        )
        for name in co_op_names:
            bad = [r for r in by_name.get(name, []) if not r.partner_ce_id]
            assert not bad, (
                f"{len(bad)} '{name}' rolls are missing a partner_ce_id:\n{_ids(bad)}"
            )

    def test_solo_rolls_have_no_partner_id(self, by_name: dict[str, list[CERoll]]):
        from utils.game_utils import SOLO_ROLL_EVENT_NAMES_TUPLE

        for name in SOLO_ROLL_EVENT_NAMES_TUPLE:
            bad = [r for r in by_name.get(name, []) if r.partner_ce_id]
            assert not bad, (
                f"{len(bad)} '{name}' solo rolls unexpectedly have a partner_ce_id:\n"
                f"{_ids(bad)}"
            )

    def test_active_multi_stage_rolls_have_valid_stage_count(self, by_name: dict[str, list[CERoll]]):
        """Active multi-stage rolls should have at least 1 game and not exceed max."""
        checks = {
            "Two Week T2 Streak": 2,
            'Two "Two Week T2 Streak" Streak': 4,
            "Fourward Thinking": 4,
        }
        for name, max_games in checks.items():
            active = _rolls_active(by_name.get(name, []))
            bad = _out_of_range(active, 1, max_games)
            assert not bad, (
                f"{len(bad)} active '{name}' rolls have a game count outside "
                f"[1, {max_games}]:\n"
                + "\n".join(f"  {r._id}: {len(r.games)} games" for r in bad)
            )
