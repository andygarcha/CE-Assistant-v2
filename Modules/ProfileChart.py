"""Generates the /profile completions chart: two bar-chart panels (Tiers,
Categories) rendered as a single PNG, with cached Discord emoji images
pasted below each bar instead of text labels."""

from __future__ import annotations

from typing import TYPE_CHECKING

import Modules.hm as hm

if TYPE_CHECKING:
    from Classes.CE_User import CEAPIUser

TIER_ORDER = ["Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5"]
CATEGORY_ORDER = [
    "Action",
    "Arcade",
    "Bullet Hell",
    "First-Person",
    "Platformer",
    "Strategy",
]

_TIER_FIELD_NAMES = ["tier1", "tier2", "tier3", "tier4", "tier5"]


def tier_counts(api_user: "CEAPIUser") -> list[tuple[str, int]]:
    """Returns [("Tier 1", n), ..., ("Tier 5", n)] from the Total row of
    `api_user.api_tier_summary`. All tiers default to 0 if no Total row exists."""
    for row in api_user.api_tier_summary:
        if hm.genre_id_to_name(row["genreId"]) == "Total":
            return [
                (label, row[field])
                for label, field in zip(TIER_ORDER, _TIER_FIELD_NAMES)
            ]
    return [(label, 0) for label in TIER_ORDER]


def category_counts(api_user: "CEAPIUser") -> list[tuple[str, int]]:
    """Returns [("Action", n), ..., ("Strategy", n)] in fixed alphabetical
    order from `api_user.api_tier_summary`. Missing categories default to 0."""
    totals = {label: 0 for label in CATEGORY_ORDER}
    for row in api_user.api_tier_summary:
        genre_name = hm.genre_id_to_name(row["genreId"])
        if genre_name in totals:
            totals[genre_name] = row["total"]
    return [(label, totals[label]) for label in CATEGORY_ORDER]
