"""
Integration tests that verify our CR calculation matches the cedb.me leaderboard.

For each sampled user:
  1. The expected total CR is fetched live from /api/leaderboards
  2. The user's game data is fetched live from /api/user/<id>
  3. We compute total CR locally and assert it matches.

Run with:  pytest tests/integration/test_cr_leaderboard.py
"""

import asyncio
import random

import pytest

from Modules import CEAPIReader, SupabaseReader, http_session

_OVERALL_GENRE_ID = "00000000-0000-0000-0000-000000000000"
_LEADERBOARD_URL = "https://cedb.me/api/leaderboards"
_SAMPLE_SIZE = 5
_RANDOM_SEED = 42


async def _fetch_leaderboard() -> list[dict]:
    session = await http_session.get_session()
    async with session.get(_LEADERBOARD_URL) as response:
        data = await response.json()
    entries = []
    for entry in data["entries"]:
        lb = entry["user"]["userLeaderboardEntries"]
        overall = next((x for x in lb if x["genreId"] == _OVERALL_GENRE_ID), None)
        if overall and not overall.get("invalid", False):
            entries.append(
                {
                    "user_id": entry["userId"],
                    "display_name": entry["user"]["displayName"],
                    "expected_skill": overall["skill"],
                }
            )
    rng = random.Random(_RANDOM_SEED)
    return rng.sample(entries, min(_SAMPLE_SIZE, len(entries)))


@pytest.fixture(scope="module")
def db_name():
    return SupabaseReader.get_database_name()


@pytest.fixture(scope="module")
def fetched_users():
    async def _fetch_all():
        sampled = await _fetch_leaderboard()
        users = await asyncio.gather(
            *[CEAPIReader.get_user(e["user_id"]) for e in sampled]
        )
        return list(zip(sampled, users))

    return asyncio.run(_fetch_all())


def test_total_cr_matches_leaderboard(fetched_users, db_name):
    failures = []
    for entry, user in fetched_users:
        assert user is not None, f"API returned None for {entry['display_name']}"
        actual = user.get_cr(db_name).total_cr
        expected = entry["expected_skill"]
        if actual != expected:
            failures.append(
                f"{entry['display_name']}: expected {expected}, got {actual}"
            )
    assert not failures, "CR mismatches:\n" + "\n".join(failures)
