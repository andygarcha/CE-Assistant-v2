"""
Database health checks. These functions detect data-quality problems
(uncategorized games, miscounted roll games, orphaned objectives, and
LocalCache/Supabase drift) and return `:hospital:`-prefixed warning
strings for #privatelog. None of these functions mutate any data.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging

from Classes.CE_Game import CEGame
from Classes.CE_Roll import CERoll
from Modules import hm
from Modules import SupabaseReader

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RollGameCountExpectation:
    """
    Describes the expected `len(roll.games)` for a given roll type.

    fixed: `int | None`
        If set, every roll of this type must have exactly this many games.
    range: `tuple[int, int] | None`
        If set, every roll of this type must have a game count within
        this inclusive (lo, hi) range.
    won_fixed: `int | None`
        If set, every roll of this type with status "won" must have
        exactly this many games (checked in addition to `fixed`/`range`).
    """

    fixed: int | None = None
    range: tuple[int, int] | None = None
    won_fixed: int | None = None


ROLL_GAME_COUNT_EXPECTATIONS: dict[str, RollGameCountExpectation] = {
    "One Hell of a Day": RollGameCountExpectation(fixed=1),
    "One Hell of a Week": RollGameCountExpectation(fixed=5),
    "One Hell of a Month": RollGameCountExpectation(fixed=25),
    "Never Lucky": RollGameCountExpectation(fixed=1),
    "Triple Threat": RollGameCountExpectation(fixed=3),
    "Let Fate Decide": RollGameCountExpectation(fixed=1),
    "Two Week T2 Streak": RollGameCountExpectation(range=(1, 2), won_fixed=2),
    'Two "Two Week T2 Streak" Streak': RollGameCountExpectation(
        range=(1, 4), won_fixed=4
    ),
    "Fourward Thinking": RollGameCountExpectation(range=(1, 4), won_fixed=4),
    "Destiny Alignment": RollGameCountExpectation(fixed=2),
    "Soul Mates": RollGameCountExpectation(fixed=1),
    "Teamwork Makes the Dream Work": RollGameCountExpectation(fixed=4),
}


def check_roll_game_counts(rolls: list[CERoll]) -> list[str]:
    """
    Flags rolls whose `len(roll.games)` doesn't match the expectation
    for its `roll_name` in `ROLL_GAME_COUNT_EXPECTATIONS`.

    Parameters
    ---
    rolls: `list[CERoll]`
        The rolls to check.

    Returns
    ---
    warnings: `list[str]`
        One `:hospital:`-prefixed message per offending roll. Rolls with
        status "won_legacy" or a roll_name not present in
        `ROLL_GAME_COUNT_EXPECTATIONS` are skipped entirely.
    """
    warnings: list[str] = []

    by_name: dict[str, list[CERoll]] = {}
    for roll in rolls:
        if roll.status == "won_legacy":
            continue
        by_name.setdefault(roll.roll_name, []).append(roll)

    for roll_name, expectation in ROLL_GAME_COUNT_EXPECTATIONS.items():
        rolls_of_type = by_name.get(roll_name, [])

        if expectation.fixed is not None:
            for roll in rolls_of_type:
                if len(roll.games) != expectation.fixed:
                    warnings.append(
                        f":hospital: Roll {roll.id} ({roll.roll_name}) has "
                        f"{len(roll.games)} games, expected {expectation.fixed}."
                    )

        if expectation.range is not None:
            lo, hi = expectation.range
            for roll in rolls_of_type:
                if not (lo <= len(roll.games) <= hi):
                    warnings.append(
                        f":hospital: Roll {roll.id} ({roll.roll_name}) has "
                        f"{len(roll.games)} games, expected between {lo} and {hi}."
                    )

        if expectation.won_fixed is not None:
            for roll in rolls_of_type:
                if roll.status != "won":
                    continue
                if len(roll.games) != expectation.won_fixed:
                    warnings.append(
                        f":hospital: Won roll {roll.id} ({roll.roll_name}) has "
                        f"{len(roll.games)} games, expected {expectation.won_fixed}."
                    )

    return warnings


def check_uncategorized_games(games: list[CEGame]) -> list[str]:
    """
    Flags games with no categories, excluding the two games that are
    legitimately categoryless (Challenge Enthusiasts itself, and Clown Town).

    Parameters
    ---
    games: `list[CEGame]`
        The games to check.

    Returns
    ---
    warnings: `list[str]`
        One `:hospital:`-prefixed message per offending game.
    """
    warnings: list[str] = []

    excluded_ids = (hm.GAME_ID_CHALLENGE_ENTHUSIASTS, hm.GAME_ID_CLOWN_TOWN)

    for game in games:
        if game.categories:
            continue
        if game.ce_id in excluded_ids:
            continue
        warnings.append(f":hospital: Game {game.name_with_link} has no categories.")

    return warnings


def check_orphaned_objectives(games: list[CEGame]) -> list[str]:
    """
    Flags objectives with no requirements and no achievement IDs attached
    (i.e. objectives with zero rows in `objectiveRequirements`).

    Parameters
    ---
    games: `list[CEGame]`
        The games whose objectives should be checked.

    Returns
    ---
    warnings: `list[str]`
        One `:hospital:`-prefixed message per offending objective.
    """
    warnings: list[str] = []

    for game in games:
        for objective in game.all_objectives:
            if objective.requirements is not None:
                continue
            if objective.achievement_ce_ids:
                continue
            warnings.append(
                f":hospital: Objective {objective.name} ({objective.ce_id}) "
                "has no requirements."
            )

    return warnings


def format_integrity_report(report: dict) -> str:
    """
    Formats a `Modules.LocalCache.run_integrity_check()` report dict into
    a single `:hospital:`-prefixed summary string for #privatelog.

    Parameters
    ---
    report: `dict`
        The dict returned by `LocalCache.run_integrity_check()`, with
        keys "synced", "removed", "schema" (each `list[str]`).

    Returns
    ---
    summary: `str`
        A single summary line.
    """
    synced = ", ".join(report.get("synced", []))
    removed = ", ".join(report.get("removed", []))
    schema = ", ".join(report.get("schema", []))

    parts = []
    if synced:
        parts.append(f"synced [{synced}]")
    if removed:
        parts.append(f"removed [{removed}]")
    if schema:
        parts.append(f"schema [{schema}]")

    if parts:
        return ":hospital: Integrity check: " + ", ".join(parts)
    return ":hospital: Integrity check passed — local cache in sync with Supabase"


def run_cheap_checks() -> list[str]:
    """
    Runs every health check that doesn't cost extra Supabase egress
    (everything except the LocalCache/Supabase integrity check) and
    combines their warnings into one flat list.

    Each check runs independently — if one raises, it contributes a
    single `:hospital: {check} check failed: {error}` message instead
    of preventing the other checks from running. The games list is
    fetched once and shared between the uncategorized-games and
    orphaned-objectives checks to avoid fetching the games table from
    Supabase twice per invocation.

    Returns
    ---
    warnings: `list[str]`
        All `:hospital:`-prefixed warning messages from every check.
    """
    warnings: list[str] = []

    try:
        games = SupabaseReader.get_database_name()
    except Exception as e:
        logger.exception("Fetching games for health checks failed.")
        warnings.append(f":hospital: Uncategorized-games check failed: {e}")
        warnings.append(f":hospital: Orphaned-objectives check failed: {e}")
    else:
        try:
            warnings.extend(check_uncategorized_games(games))
        except Exception as e:
            logger.exception("Uncategorized-games check failed.")
            warnings.append(f":hospital: Uncategorized-games check failed: {e}")

        try:
            warnings.extend(check_orphaned_objectives(games))
        except Exception as e:
            logger.exception("Orphaned-objectives check failed.")
            warnings.append(f":hospital: Orphaned-objectives check failed: {e}")

    try:
        warnings.extend(check_roll_game_counts(SupabaseReader.get_all_rolls()))
    except Exception as e:
        logger.exception("Roll-game-count check failed.")
        warnings.append(f":hospital: Roll-game-count check failed: {e}")

    return warnings
