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
