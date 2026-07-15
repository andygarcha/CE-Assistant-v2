"""
THIS FILE SHOULD BE RUN IN A DIFFERENT PROCESS
"""

import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass

# Add parent directory to path for direct script execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime
import json
import logging
import typing

import requests

from Classes.CE_Game import CEAPIGame, CEGame
from Classes.CE_Roll import CERoll
from Classes.CE_User import CEAPIUser, CEUser
from Classes.CE_User_Game import CEUserGame
from Modules import (
    CEAPIReader,
    HealthCheck,
    LocalCache,
    SupabaseReader,
    hm,
    http_session,
)

logger = logging.getLogger(__name__)

SAVEDATA = True
DEBUG = True
SKIPUPDATES = False  # doesn't skip roll updates

""" SCRAPER CLASSES """


@dataclass
class UpdateMessageForScraperProcess:
    is_embed: bool = False
    location: str | None = None

    text: str = ""

    title: str = ""
    description: str = ""
    image: str = ""
    url: str = ""
    color: int = 0x000000

    game_ce_id: str | None = None

    def print(self, full=False, info=False):
        string: str = ""
        string += f"update ({'embed' if self.is_embed else 'text'}): "
        if self.is_embed:
            string += f"{self.title!r} ----- {self.description!r}\n"
        else:
            string += f"{self.text!r}\n"

        print(string)  # noqa: T201 -- intentional console output for dry-run/silent scrapes, in addition to logging below

        if full and info:
            logger.info(string)
        elif full:
            logger.debug(string)
        elif info:
            logger.info(string[0:100])
        else:
            logger.debug(string[0:100])


def flush_updates(updates: list[UpdateMessageForScraperProcess]) -> None:
    immediate_rows = []
    for update in updates:
        if update.location is None:
            logger.warning(
                "Update with location=None skipped: %s", update.text or update.title
            )
            continue

        row = {
            "is_embed": update.is_embed,
            "channel": update.location,
            "text": update.text,
            "title": update.title,
            "description": update.description,
            "image": update.image,
            "url": update.url,
            "color": update.color,
            "game_ce_id": update.game_ce_id,
        }

        if row["game_ce_id"] is not None:
            row["status"] = "pending"
            SupabaseReader.upsert_pending_update(row)
        else:
            row["status"] = "stable"
            immediate_rows.append(row)

    if immediate_rows:
        SupabaseReader.write_scraper_updates_bulk(immediate_rows)
        logger.info("Flushed %d immediate updates.", len(immediate_rows))


def compute_changed_game_ids(
    updates: list[UpdateMessageForScraperProcess], removed_games: set[str]
) -> set[str]:
    """Games that actually produced an UpdateMessageForScraperProcess this loop,
    plus removed games. A game whose updatedAt ticked without producing a real
    diff (a "ghost update") is not included."""
    return {u.game_ce_id for u in updates if u.game_ce_id is not None} | removed_games


def stabilize_pending_updates(changed_game_ids: set[str]) -> None:
    pending = SupabaseReader.get_pending_game_updates()
    if not pending:
        return

    to_promote = [
        row["id"] for row in pending if row["game_ce_id"] not in changed_game_ids
    ]

    if to_promote:
        SupabaseReader.promote_pending_to_stable(to_promote)
        logger.info("Promoted %d pending updates to stable.", len(to_promote))


""" TOP LEVEL FUNCTION """


async def process_loop(
    full_scrape: bool = False,
    send_updates: bool = True,
):
    logger.info("process_loop() invoked with full_scrape=%s (initially).", full_scrape)

    full_scrape = (
        (  # Noon/1PM EST (based on daylight savings)
            datetime.datetime.now(datetime.UTC).hour == 17
        )
        and (datetime.datetime.now(datetime.UTC).minute == 0)
    ) or full_scrape

    logger.info("full_scrape=%s (second try)", full_scrape)

    logger.info(
        "Scraper loop started at %s%s",
        hm.get_datetime("now"),
        ", FULL SCRAPE" if full_scrape else "",
    )

    logger.debug(
        "FLAGS: SAVEDATA=%s, DEBUG=%s, SKIPUPDATES=%s", SAVEDATA, DEBUG, SKIPUPDATES
    )
    time_current: datetime.datetime = datetime.datetime.now(datetime.UTC)

    updates: list[UpdateMessageForScraperProcess] = []

    # Step 1: Update Games
    logger.info("UPDATE GAMES: begin")
    (
        _updates,
        games_new,
        removed_games,
        removed_objectives,
        notIsFinished,
    ) = await update_games(full_scrape)
    logger.debug("UPDATE GAMES: done!")
    updates.extend(_updates)

    # Promote pending game updates that had no further changes since last loop
    changed_game_ids = compute_changed_game_ids(_updates, removed_games)
    stabilize_pending_updates(changed_game_ids)

    logger.info("len(updates)=%d (games only!)", len(updates))
    for update in updates:
        update.print(full=True)

    # Step 2: Update Users
    #  -- now to do this we have to generate databasename_old and databasename_new
    #  -- generating old is easy, that's just what's in the supabase.
    #  -- but the new has updates and removals and additions.
    # TODO
    # fix this is mad inefficient

    # step 2a) generate name_old and name_new
    database_name_old = SupabaseReader.get_games_bulk(SupabaseReader.get_list("name"))

    _games_by_id: dict[str, CEGame | CEAPIGame] = {
        g.ce_id: g for g in database_name_old
    }
    for _game_id in removed_games:
        _games_by_id.pop(_game_id, None)
    for _game_new in games_new:
        _games_by_id[_game_new.ce_id] = _game_new
    database_name_new: list[CEGame | CEAPIGame] = list(_games_by_id.values())
    del _games_by_id

    logger.debug("len(database_name_old)=%d", len(database_name_old))
    logger.debug("len(database_name_new)=%d", len(database_name_new))

    logger.info("UPDATE USERS: begin")
    _updates, users_new, removed_users = await update_users(
        database_name_old, database_name_new, full_scrape, notIsFinished
    )
    del database_name_old
    updates.extend(_updates)
    logger.info("UPDATE USERS: complete")
    logger.debug("len(_user_updates)=%d", len(_updates))

    # Step 3: Check curator
    check_curator_steam()

    # Step 3.5: Check rolls
    # TODO: send back all users
    _updates, rolls_updated, rolls_deleted = update_rolls(
        database_name=database_name_new,
        database_user=users_new,
    )
    updates.extend(_updates)

    # Step 4: write all of our stuff
    if SAVEDATA:

        def _save_all():
            logger.info("saving data")

            logger.debug("len(games_new)=%d", len(games_new))
            SupabaseReader.bulk_dump_games(games_new)

            logger.debug("len(removed_games)=%d", len(removed_games))
            for _game_id in removed_games:
                SupabaseReader.delete_game(_game_id)

            logger.debug("len(removed_objectives)=%d", len(removed_objectives))
            SupabaseReader.delete_objectives_many(removed_objectives)

            logger.debug("len(users_new)=%d", len(users_new))
            SupabaseReader.bulk_dump_users(users_new)

            logger.debug("len(removed_users)=%d", len(removed_users))
            for _user_id in removed_users:
                SupabaseReader.delete_user(_user_id)

            logger.debug("len(rolls_updated)=%d", len(rolls_updated))
            SupabaseReader.bulk_dump_rolls(rolls_updated)

            logger.debug("len(rolls_deleted)=%d", len(rolls_deleted))
            for r in rolls_deleted:
                r.set_status("removed")
            SupabaseReader.bulk_dump_rolls(rolls_deleted)

        _save_all()

    # Flush updates to Supabase for the bot to deliver
    logger.info("Flushing %d updates.", len(updates))
    if send_updates:
        flush_updates(updates)
    else:
        for update in updates:
            update.print(full=True)

    logger.info("process_loop() complete at time=%s", hm.get_datetime("now"))

    try:
        health_warnings = HealthCheck.run_cheap_checks()
        if health_warnings:
            SupabaseReader.write_scraper_updates_bulk(
                [
                    {
                        "is_embed": False,
                        "channel": "privatelog",
                        "text": warning,
                        "title": "",
                        "description": "",
                        "image": "",
                        "url": "",
                        "color": 0,
                        "status": "stable",
                        "game_ce_id": None,
                    }
                    for warning in health_warnings
                ]
            )
    except Exception:
        logger.exception("Health check failed.")

    if full_scrape:
        try:
            integrity_report = LocalCache.run_integrity_check()
            summary = HealthCheck.format_integrity_report(integrity_report)
            logger.info(summary)
            SupabaseReader.write_scraper_update(
                {
                    "is_embed": False,
                    "channel": "privatelog",
                    "text": summary,
                    "title": "",
                    "description": "",
                    "image": "",
                    "url": "",
                    "color": 0,
                    "status": "stable",
                    "game_ce_id": None,
                }
            )
        except Exception:
            logger.exception("Integrity check failed.")

    if SAVEDATA and not full_scrape:
        try:
            SupabaseReader.dump_loop(time_current)
        except Exception as e:
            logger.error("dump_loop failed to save last run time: %s", e)

    return {
        "games_updated": len(games_new),
        "users_updated": len(users_new),
        "rolls_updated": len(rolls_updated) + len(rolls_deleted),
        "updates_generated": len(updates),
    }


""" MEDIUM LEVEL FUNCTIONS """


async def update_games(
    full_scrape=False,
) -> tuple[
    list[UpdateMessageForScraperProcess],  # updates
    list[CEAPIGame],  # games_new
    set[str],  # removed_games
    list[str],  # removed_objectives
    set[str],  # notIsFinished
]:
    """
    Updates all games. This version began April 9, 2026 for Supabase.
    Returns
    ---
    - updates: a list of updates to be sent
    - games_new: the games that have been updated
    - removed_games: a list of ceids of games that have been removed.
    - removed_objectives: a list of ceids of objectives that have been removed
    - notIsFinished: a list of ceids of games that have had the 'isFinished' flag turned off.
        These games are to be *ignored* until isFinished is turned back on.
    """

    updates: list[UpdateMessageForScraperProcess] = []
    objectives_removed: list[str] = []
    last_run: datetime.datetime = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    _updated_game_ids: set = set()

    # Step 0: Determine the last time the loop ran
    if not full_scrape:
        last_run = SupabaseReader.get_last_loop()
        logger.info("GAMES: last_run at %s, full_scrape=%s", last_run, full_scrape)

    # Step 1: Go through /api/games and /api/objectives and find the list of all games that have been updated.
    # 1a) get the ids of all games that have been updated from /api/games
    if not full_scrape:
        session = await http_session.get_session()
        params = {"sortBy": "updatedAt", "sortOrder": "DESC"}
        async with session.get("https://cedb.me/api/games") as _r:
            if _r.status != 200:
                raise RuntimeError(f"/api/games returned HTTP {_r.status}")
            response = await _r.json()

        logger.debug("/api/games responded with %d games.", len(response))
        _updated_game_ids = set()
        for game in response:
            timestamp_game = datetime.datetime.fromisoformat(game["updatedAt"])

            if timestamp_game < last_run:
                continue
            _updated_game_ids.add(game["id"])

        logger.debug("Updated IDs from /api/games: %d", len(_updated_game_ids))
        __count = len(_updated_game_ids)

        # 1b) get the ids of all games that have been updated from /api/objectives
        params = {"sortBy": "updatedAt", "sortOrder": "DESC", "limit": 100, "offset": 0}
        while 1:
            async with session.get(
                "https://cedb.me/api/objectives", params=params
            ) as _r:
                if _r.status != 200:
                    raise RuntimeError(f"/api/objectives returned HTTP {_r.status}")
                _response_local = await _r.json()
                # all objectives are new
                if (
                    datetime.datetime.fromisoformat(_response_local[-1]["updatedAt"])
                    >= last_run
                ):
                    _updated_game_ids.update(r["gameId"] for r in _response_local)
                    params["offset"] += 100
                    continue

                # we found something wrong. go thru one by one.
                for objective in _response_local:
                    if (
                        datetime.datetime.fromisoformat(objective["updatedAt"])
                        < last_run
                    ):
                        # TODO: can we confirm sorting works?
                        break

                    _updated_game_ids.add(objective["gameId"])

                break

        logger.debug(
            "Updated IDs from /api/objectives: %d", len(_updated_game_ids) - __count
        )
        logger.debug(
            "Total Updated IDs (from /api/games + /api/objectives): %d",
            len(_updated_game_ids),
        )

    # 1c) get the ids of all games that have removed objectives
    #  -- solved! folkius changed the schema so now any removed objective updates the game's updatedAt entry.

    # 1d) get the actual data for all those games
    games: list[CEAPIGame] = []
    notIsFinished: set[str] = set()

    if full_scrape:
        logger.info("Full scraping: pulling from /api/games/full.")
        games = await CEAPIReader.get_api_games_full()
        notIsFinished = {g.ce_id for g in games if not g.is_finished}
        games = [g for g in games if g.is_finished]
    else:
        logger.info(
            "Pulling %d games one at a time using /api/game/[id].",
            len(_updated_game_ids),
        )
        for gameId in _updated_game_ids.copy():
            _game = await CEAPIReader.get_game(gameId)
            if _game is None:
                logger.warning("Game with ID %s was not found in CEAPIReader.", gameId)
                _updated_game_ids.remove(gameId)
                continue
            # isFinished games should *not* have updates made for them,
            # nor should their data be persisted to local backend.
            if _game.is_finished:
                games.append(_game)
            else:
                notIsFinished.add(_game.ce_id)
    hidden_ids = await CEAPIReader.get_api_hidden_game_ids()
    notIsFinished.update(hidden_ids)
    logger.info("Pulling from CEDB complete.")

    # Step 2: Generate updates for those by comparing with Supabase games.
    if SKIPUPDATES:
        logger.info("Skipping updates.")
    else:
        _ids = [g.ce_id for g in games]
        games_old = SupabaseReader.get_games_bulk(_ids)

        logger.info("Generating updates for games.")
        for i, game_new in enumerate(games):
            if i % 10 == 0:
                logger.debug("Updating game %d.", i)

            game_old = hm.get_item_from_list(game_new.ce_id, games_old)
            _update, _or = update_one_game(game_old, game_new)
            if _update is not None:
                updates.append(_update)
            if _or is not None:
                objectives_removed.extend(_or)

        logger.info("Game updates completed.")

    # Step 3: Find all removed games.
    logger.debug("Pulling list of Game IDs from Supabase.")
    game_list_old = set(SupabaseReader.get_list("name"))
    logger.debug("Pulling /api/games.")
    game_list_new = set(await CEAPIReader.get_api_games())
    logger.debug("Requests complete.")

    game_list_removed = game_list_old.difference(game_list_new)

    for _game in game_list_removed.copy():
        _game_cedb = await CEAPIReader.get_game(_game)
        if _game_cedb is not None:
            # TODO inefficient. see above for previous notIsFinished logic.
            game_list_removed.remove(_game)
            notIsFinished.add(_game)

    # Step 4: Generate updates for those removed games.
    if SKIPUPDATES:
        logger.warning("Skipping updates (again...)")
    elif len(game_list_removed) != 0:
        logger.debug("Generating updates for %d removed games.", len(game_list_removed))
        for game_removed in game_list_removed:
            _game = SupabaseReader.get_game(game_removed)
            if _game is None:
                logger.warning(
                    "Could not find soon-to-be removed game with ID %s in Supabase.",
                    game_removed,
                )
                continue
            _update, _or = update_one_game(_game, None)
            if _update is not None:
                updates.append(_update)
            if _or is not None:
                objectives_removed.extend(_or)

    return updates, games, game_list_removed, objectives_removed, notIsFinished


async def update_users(
    games_old: list[CEGame],
    games_new: list[CEGame],
    full_scrape=False,
    notIsFinished: set | None = None,
) -> tuple[list[UpdateMessageForScraperProcess], list[CEAPIUser], list[str]]:
    """
    Updates all users. This version began April 9, 2026 for Supabase.

    Parameters
    ---
    games_old: `list[CEGame]`
        The previous version of database_name.
    games_new: `list[CEGame]`
        The current version of database_name.
    full_scrape: `bool`
        Whether or not to do a full scrape.
        A full scrape entails pulling *everybody's* data,
        and then running updates on it. This is in
        the event the bot goes down or misses information.
    notIsFinished: `set[str]`
        A list of ce_ids relating to games that have the
        'isFinished' flag turned to False. We need these
        so that we don't run updates on userGames corresponding
        to these 'unfinished' games.
    """

    if notIsFinished is None:
        notIsFinished = set()

    # Step 0: Determine the last time the loop ran.
    last_run = SupabaseReader.get_last_loop()
    updates: list[UpdateMessageForScraperProcess] = []

    # Step 1: Go through /api/userObjectives and find the list of all users that have been updated.
    #   -- or: if folkius makes /api/userGames, that should work too? plus it comes with the added benefit
    #          of marking that a user owns a game, which is important for rolls.
    _updated_user_ids: set[str] = set()

    _users_registered = SupabaseReader.get_list("user")

    # TODO once folkius makes the new endpoint with MAX(updatedAt)
    # 1a) Go through api/userGames/updatedAt (or whatever it's called) and find the last updated
    # 1b) Do the same but with userObjectives
    # NOTE maybe folkius could make a combined one....
    if full_scrape:
        logger.debug("Pulling list of User IDs from Supabase.")
        _updated_user_ids.update(SupabaseReader.get_list("user"))
    else:
        logger.debug("Pulling /api/userGames/lastUpdatedAt")
        session = await http_session.get_session()
        async with session.get("http://cedb.me/api/userGames/lastUpdatedAt") as _r:
            if _r.status != 200:
                raise RuntimeError(
                    f"/api/userGames/lastUpdatedAt returned HTTP {_r.status}"
                )
            response = await _r.json()

        for user in response:
            timestamp_user = datetime.datetime.fromisoformat(user["lastUpdatedAt"])

            if timestamp_user < last_run:
                break
            if user["userId"] not in _users_registered:
                continue

            _updated_user_ids.add(user["userId"])

        logger.info(
            "Updated IDs from /api/userGames/lastUpdatedAt: %d", len(_updated_user_ids)
        )

    # Step 2: Pull all of those users
    users: list[CEAPIUser] = []
    # TODO
    # re-implement this once /api/users/query is up
    # i will step through the indexes (not the items!) in the list
    # 100 at a time,
    # for i in range(0, len(_updated_user_ids), 10):
    #     if DEBUG: print(f"posting /api/users/query for users {i} through {i+9} (of {len(_updated_user_ids)})")
    #     users.extend(await CEAPIReader.post_users_query(users[i:i+10]))
    if full_scrape:
        logger.info("Pulling users from /api/users/all")
        users = await CEAPIReader.get_api_users_all(list(_updated_user_ids))
    else:
        logger.info(
            "Pulling %d users one-by-one from /api/user/[id]", len(_updated_user_ids)
        )
        for i, _user_id in enumerate(_updated_user_ids):
            if i % 10 == 0:
                logger.debug("Pulling user %d", i)
            _user = await CEAPIReader.get_user(_user_id)
            if _user is not None:
                users.append(_user)
    logger.info("Pulling users complete.")

    # Step 3: Generate updates for these changed users by comparing with Supabase users.
    if SKIPUPDATES:
        logger.warning("Skipping updates for users.")
    else:
        logger.info("Fetching %d users from Supabase", len(users))

        # Bulk-fetch the existing users from Supabase to avoid blocking the event loop
        ce_ids = [u.ce_id for u in users]
        users_old: list[CEUser] = []
        batch_size = 100
        for bstart in range(0, len(ce_ids), batch_size):
            batch_ids = ce_ids[bstart : bstart + batch_size]
            logger.debug(
                "Fetching users %d through %d from Supabase.",
                bstart,
                bstart + batch_size,
            )
            batch_users = SupabaseReader.get_users_bulk(
                batch_ids,
                False,  # DONT PULL ROLLS!
            )
            users_old.extend(batch_users)

        users_old_map = {u.ce_id: u for u in users_old}

        logger.info("Generating updates for %d users.", len(users_old))
        for i, user_new in enumerate(users):
            if i % 5 == 0:
                logger.debug("Updating user %d", i)

            user_old = users_old_map.get(user_new.ce_id)
            if user_old is None:
                logger.error("Could not find user_old with ID %s.", user_new.ce_id)
                continue

            # Handle notIsFinished games.
            # Any game with the isFinished flag turned off should report NO CHANGES.
            # To do this, we can just take the old game (if it exists) and copy it to user_new.
            # We *must* also delete the old version of the game.
            for _game_new in user_new.owned_games.copy():
                if _game_new.ce_id in notIsFinished:
                    _game_old = user_old.get_owned_game(_game_new.ce_id)
                    if _game_old is None:
                        user_new.remove_owned_game(_game_new.ce_id)
                    else:
                        user_new.replace_owned_game(_game_old)

            _updates = update_one_user(user_old, user_new, games_old, games_new)
            if _updates is not None:
                updates.extend(_updates)

            if user_old is not None:
                users[i]._discord_id = user_old.discord_id

        logger.info("Done updating users.")

    # Step 4: Find any removed users
    # TODO future update
    user_list_removed: list[str] = []

    # TODO future update
    # only return users who *actually* had something changed.
    return updates, users, user_list_removed


def update_rolls(
    database_name: Sequence[CEGame], database_user: Sequence[CEUser]
) -> tuple[list[UpdateMessageForScraperProcess], list[CERoll], list[CERoll]]:
    """
    Update all rolls in the database.
    Pulls the rolls within this function.

    Parameters
    ---
    database_name: `list[CEGame]`
        The list of all games in the site.
        This is the up-to-date version generated
        by `.update_games()`.
    database_user: `list[CEUser]`
        The list of all users in the site.
        This is the up-to-date version generated
        by `.update_users()`.

    Returns
    ---
    updates: `list[UpdateMessageForScraperProcess]`
        A list of updates related to these rolls.
    rolls_updated: `list[CERoll]
        A list of rolls to replace in the database.
        Maybe a game was added, maybe a status was changed.
        Who knows!
    rolls_to_delete: `list[CERoll]`
        A list of rolls that need to be deleted.
        As of right now, the only case this would happen
        is in the event of a 'pending' roll.
    """

    # TODO future update
    # only pull the second user **after** you've confirmed it would potentially pass the current player's game

    rolls_updated: list[CERoll] = []
    updates: list[UpdateMessageForScraperProcess] = []
    rolls_deleted: list[CERoll] = []

    logger.info("Updating rolls.")
    logger.info("Pulling rolls from Supabase...")
    rolls = SupabaseReader.get_checkable_rolls()
    logger.info("Pulling complete. len(rolls)=%d. Beginning updates...", len(rolls))

    # Build O(1) lookup dicts from what the caller already fetched.
    users_by_id: dict[str, CEUser] = {u.ce_id: u for u in database_user}
    games_by_id: dict[str, CEGame] = {g.ce_id: g for g in database_name}

    # Pre-pass: collect every user/game ID referenced by checkable rolls,
    # then bulk-fetch any misses in two Supabase calls instead of one per roll.
    needed_user_ids: set[str] = set()
    needed_game_ids: set[str] = set()
    for _roll in rolls:
        if _roll.status not in ("current", "pending"):
            continue
        needed_user_ids.add(_roll.user_ce_id)
        if _roll.partner_ce_id is not None:
            needed_user_ids.add(_roll.partner_ce_id)
        for game_id in _roll.games:
            if game_id:
                needed_game_ids.add(game_id)

    missing_user_ids = [uid for uid in needed_user_ids if uid not in users_by_id]
    missing_game_ids = [gid for gid in needed_game_ids if gid not in games_by_id]

    if missing_user_ids:
        logger.info(
            "Bulk-fetching %d users not in database_user.", len(missing_user_ids)
        )
        for u in SupabaseReader.get_users_bulk(missing_user_ids, include_rolls=False):
            users_by_id[u.ce_id] = u

    if missing_game_ids:
        logger.info(
            "Bulk-fetching %d games not in database_name.", len(missing_game_ids)
        )
        for g in SupabaseReader.get_games_bulk(missing_game_ids):
            games_by_id[g.ce_id] = g

    # Main loop — all lookups are now O(1) dict reads, no per-roll Supabase calls.
    for i, _roll in enumerate(rolls):
        if i % 15 == 0:
            logger.debug("Updating roll %d of %d.", i, len(rolls))

        if _roll.status != "current" and _roll.status != "pending":
            continue

        user1 = users_by_id.get(_roll.user_ce_id)
        if user1 is None:
            logger.error(
                "Could not find user with ID %s in update_users", _roll.user_ce_id
            )
            continue

        user2 = None
        if _roll.partner_ce_id is not None:
            user2 = users_by_id.get(_roll.partner_ce_id)
            if user2 is None:
                logger.error(
                    "Could not find partner (User ID %s) in Supabase.",
                    _roll.partner_ce_id,
                )
                continue

        games: list[CEGame] = []
        for game_id in _roll.games:
            game_obj = games_by_id.get(game_id)
            if game_obj is None:
                logger.error("Could not find game with ID %s in Supabase.", game_id)
                continue
            games.append(game_obj)

        _update, _roll_updated, _delete = update_one_roll(_roll, user1, user2, games)

        if _update is not None:
            updates.append(_update)
        if _roll_updated is not None:
            rolls_updated.append(_roll_updated)
        if _delete:
            rolls_deleted.append(_roll)

    return updates, rolls_updated, rolls_deleted


def generate_database_tier(database_name: Sequence[CEGame]) -> dict | None:
    """
    Generates database_tier using the Steam and SteamHunters APIs.

    Parameters
    ---
    database_name: `list[CEGame]`
        The current database_name. This is
        needed so that we can place each
        game in the correct tier and category.

    Returns
    ---
    database_tier: `dict`
        This will be formatted as such:
        database_tier[str(tiernum)][category] = [entry, ...]
        Each entry will have three keys:
        "ce_id", "sh_hours", and "price".
    """
    # separate out games by tier and category
    database_tier: dict[str, dict[str, list[dict]]] = {}
    for tier in range(1, 8):
        database_tier[str(tier)] = {}
        for category in typing.get_args(hm.CATEGORIES):
            database_tier[str(tier)][category] = []

    steam_ids: list[int] = []

    for game in database_name:
        if game.platform != "steam":
            continue

        steam_ids.append(int(game.platform_id))

    # this copy is needed because when we remove the ids mid scrape it moves
    #   the array back so a) some games get skipped and b) we may pull an empty list
    steam_ids_copy = steam_ids.copy()

    prices: dict[str, int] = {}
    hours: dict[str, int] = {}

    # grab all prices and hours
    logger.info("Begin scraping of Steam and SteamHunters APIs.")
    GAMES_PER_REQUEST = 100
    for i in range(0, len(steam_ids), GAMES_PER_REQUEST):
        logger.debug(
            "Scraping games %d through %d of %d.",
            i,
            i + GAMES_PER_REQUEST,
            len(steam_ids),
        )

        # prices

        logger.debug("Pulling from Steam...")
        response_prices = requests.get(
            "https://store.steampowered.com/api/appdetails?",
            params={
                "appids": str(steam_ids_copy[i : i + GAMES_PER_REQUEST])[1:-1],
                "cc": "US",
                "filters": "price_overview",
            },
            timeout=15,
        )

        response_prices_json: dict[str, dict] = json.loads(response_prices.text)

        if isinstance(response_prices_json, list):
            logger.error(
                "Something went wrong. Response has been read as a list instead of a dict."
            )
            logger.error("app_ids=%s", steam_ids[i : i + GAMES_PER_REQUEST])
            logger.error("response_prices_json=%s", response_prices_json)
            return None

        for key, value in response_prices_json.items():
            if not value["success"]:
                steam_ids.remove(int(key))
                logger.warning(
                    "json['success'] was False (or null) for game with AppId=%s. Skipping...",
                    key,
                )
                continue

            if len(value["data"]) == 0:
                prices[key] = 0
                continue

            if value["data"]["price_overview"]["discount_percent"] == 100:
                prices[key] = 0

            else:
                prices[key] = value["data"]["price_overview"]["final"]

        # hours
        logger.debug("Pulling from SteamHunters...")
        response_hours = requests.get(
            "https://steamhunters.com/api/apps/?",
            params={
                "appids": str(steam_ids_copy[i : i + GAMES_PER_REQUEST])[
                    1:-1
                ]  # appIds=220,480,730
            },
            timeout=15,
        )

        response_hours_json: list[dict[str, int]] = json.loads(response_hours.text)
        for item in response_hours_json:
            if "medianCompletionTime" not in item:
                steam_ids.remove(int(item["appId"]))
                logger.warning(
                    "No medianCompletionTime listed for AppId %s.", item["appId"]
                )
                continue
            hours[str(item["appId"])] = item["medianCompletionTime"]

    for game in database_name:
        if game.platform != "steam":
            continue  # non steam game
        if game.tier_num == 0:
            continue  # t0
        if game.platform_id not in prices or game.platform_id not in hours:
            continue  # no success from api

        for _cat in game.categories:
            database_tier[str(game.tier_num)][_cat].append(
                {
                    "ce_id": game.ce_id,
                    "price": prices[game.platform_id],
                    "sh_hours": hours[game.platform_id],
                }
            )

    return database_tier


""" BOTTOM LEVEL FUNCTIONS """


def update_one_game(
    game_old: CEGame | None, game_new: CEAPIGame | None
) -> tuple[UpdateMessageForScraperProcess | None, list[str] | None]:
    """
    Generates an update for a game.
    """
    # NEW GAME
    if game_old is None and game_new is not None:
        return create_update_new_game(game_new), []

    # REMOVED GAME
    if game_new is None and game_old is not None:
        return create_update_removed_game(game_old), []

    # by this point neither should be none but they could both be...?
    if game_new is None or game_old is None:
        return None, None

    return create_update_updated_game(game_old, game_new)


def update_one_user(
    user: CEUser,
    site_data: CEAPIUser,
    database_name_old: list[CEGame],
    database_name_new: list[CEGame],
) -> list[UpdateMessageForScraperProcess]:
    """
    Provides updates for one user.

    Parameters
    ---
    user: `CEUser`
        The original data for the user (pulled from Supabase)
    site_data: `CEAPIUser`
        The user's data that was *just* pulled down from the CEDB API
    database_name_old: `list[CEGame]`
        The previous iteration of the games database. This is here to
        determine if a game is "newly completed", or if the requirements
        just changed.
    database_name_new: `list[CEGame]`.
        The new iteration of the games database.

    Returns
    ---
    updates: `list[UpdateMessageForScraperProcess]`.
        A list of updates regarding this user.
        Examples of updates:
        - rank up
        - high tier completion
        - completion count is a new multiple of 25
        - unlocked a new role (high points in a category, etc.)
    """

    updates: list[UpdateMessageForScraperProcess] = []

    # gather old info
    points_original = user.total_points
    completed_games_original, overcompleted_games_original = (
        user.get_completed_games_all(database_name_old)
    )
    rank_original = user.rank
    games_original = user.owned_games.copy()

    # update the user!
    user.owned_games = site_data.owned_games

    # gather new info
    points_new = user.total_points
    completed_games_new, overcompleted_games_new = user.get_completed_games_all(
        database_name_new
    )
    rank_new = user.rank
    games_new = user.owned_games.copy()

    # -- CHECK ROLES --
    updates.extend(
        check_roles(
            games_original, games_new, database_name_old, database_name_new, user
        )
    )

    # -- CHECK FOR NEWLY COMPLETED GAMES --
    updates.extend(
        check_newly_completed_games(
            completed_games_original,
            completed_games_new,
            user,
            overcompleted_games_original,
            overcompleted_games_new,
        )
    )

    _result: None | UpdateMessageForScraperProcess = None

    # -- RANK UPDATE --
    _result = check_rank(rank_original, rank_new, points_original, points_new, user)
    if _result is not None:
        updates.append(_result)

    # -- COMPLETION COUNT UPDATE --
    _result = check_completion_count(
        len(completed_games_original), len(completed_games_new), user
    )
    if _result is not None:
        updates.append(_result)

    user.last_updated = hm.get_datetime("now")
    return updates


def update_one_roll(
    roll: CERoll, user1: CEUser, user2: CEUser | None, games: list[CEGame]
) -> tuple[UpdateMessageForScraperProcess | None, CERoll | None, bool]:
    """
    Provides updates for one roll.

    Parameters
    ---
    roll: `CERoll`
        The roll we're generating the update for
    user1: `CEUser`
        The data corresponding to roll.user1_ce_id
    user2: `CEUser | None`
        The data corresponding to roll.user2_ce_id,
        if it exists. `None` otherwise.
    games: `list[CEGame]`
        The data corresponding to each game in the
        roll.games array.

    Returns
    ---
    update: `UpdateMessageForScraperProcess | None`
        An update regarding this roll, if one was
        generated. `None` otherwise.
    roll_updated: `CERoll | None`
        If an update to the roll was made, this will
        be the updated data. `None` otherwise.
    delete_pending: `bool`
        If a roll is 'pending', and that 'pending'
        roll needs to be deleted, this will be
        set to True.
    """

    # ERROR CHECKING: sending in a bad roll
    status = roll.status
    if status not in ["current", "pending"]:
        return None, None, False

    # ERROR CHECKING: handle the problem where a roll's game gets removed from the site
    update = UpdateMessageForScraperProcess()
    if None in games:
        update.is_embed = False
        _user2_text = ""
        if user2 is not None:
            _user2_text = f" and {user2.mention}"

        update.text = (
            f"{user1.mention}{_user2_text}, you rolled a game that has now been removed"
            + " from the site. This will not impact your casino score. Apologies for the inconvenience."
            + " Please feel free to reach out to Andy for more information or reroll. No cooldown has"
            + " been applied."
        )
        update.location = "casino"

        roll.set_status("removed")
        return update, roll, False

    # pendings
    if roll.status == "pending":
        due_dt = (
            roll._normalize_datetime(roll.due_time)
            if hasattr(roll, "_normalize_datetime")
            else roll.due_time
        )
        if due_dt is not None and due_dt <= hm.get_datetime("now"):
            update.is_embed = False
            update.location = "casino"
            _user2_text = ""
            if user2 is not None:
                _user2_text = f"and {user2.mention}"
            update.text = (
                f"{user1.mention} {_user2_text}, you may now re-initiate {roll.roll_name}. "
                + "Any button presses to the previous message will do nothing."
            )
            return update, None, True
        return None, None, False

    update = UpdateMessageForScraperProcess()
    won = roll.is_won(games, user1, user2)

    # Case 1: The roll is multi-stage, and we're not on the last stage.
    if roll.is_multi_stage and not roll.in_final_stage and won:
        update.location = "casino"
        update.is_embed = False
        update.text = (
            f"{user1.mention}, you've finished the current stage in {roll.roll_name}. "
            + f"To roll your next stage, type /solo-roll {roll.roll_name} in <#{hm.CASINO_ID}> at any time."
        )

        roll.set_status("between_stages")
        roll.due_time = None
        return update, roll, False

    # Case 2: The roll is won (single-player or co-op).
    if won:
        update.location = "casinolog"
        update.is_embed = False
        update.text = roll.get_win_message(games, user1, user2)
        roll.completed_time = hm.get_datetime("now")
        roll.set_status("won")
        return update, roll, False

    if roll.is_expired:
        update.location = "casino"
        update.is_embed = False
        update.text = roll.get_fail_message(games, user1, user2)
        roll.set_status("failed")

        return update, roll, False

    # If we get here, then none of the following happened:
    #  -- roll was pending
    #  -- roll was current and won
    #  -- roll was current and expired
    return None, None, False


def check_curator_steam():
    """
    Checks steam for the last 10 curated games.
    Returns
    ---
    games: `list[str]`
        A list of the Steam IDs for the most recent 10 games
        put onto the Steam curator.
    """

    # TODO: fill in this function
    return


""" BASEMENT LEVEL FUNCTIONS """


def create_update_new_game(game_new: CEAPIGame) -> UpdateMessageForScraperProcess:
    """
    Creates the `UpdateMessageForScraperProcess` for a new game.

    Example
    ---
    GAMENAME added to the site:
    - Tier4Emoji, ActionEmoji
    - 3 Primary Objectives worth 25 points (+2 Uncleareds)
    - 5 Secondary Objectives worth 100 points (+1 Uncleared)
    - 1 Community Objective
    """
    update = UpdateMessageForScraperProcess()
    update.is_embed = True
    update.title = f"__ {game_new.game_name} __ added to the site:"
    update.color = 0x48B474
    update.description = f"\n- {game_new.emojis}"
    update.url = f"https://cedb.me/game/{game_new.ce_id}"
    update.location = "gameadditions"
    update.game_ce_id = game_new.ce_id

    # primary
    num_pos = len(game_new.get_primary_objectives())
    num_po_uncleareds = (
        len(game_new.get_primary_objectives(include_uncleareds=True)) - num_pos
    )
    if num_pos != 0 or num_po_uncleareds != 0:
        update.description += (
            f"\n- {num_pos} Primary Objective{'s' if num_pos != 1 else ''} "
            f"worth {game_new.get_po_points()} {hm.get_emoji('Points')}"
        )

    # primary (uncleared)
    if num_po_uncleareds != 0:
        update.description += (
            f" (+{num_po_uncleareds} Uncleared{'s' if num_po_uncleareds != 1 else ''})"
        )

    # secondary
    num_sos = len(game_new.get_secondary_objectives())
    num_so_uncleareds = (
        len(game_new.get_secondary_objectives(include_uncleareds=True)) - num_sos
    )
    if num_sos != 0 or num_so_uncleareds != 0:
        update.description += (
            f"\n- {num_sos} Secondary Objective{'s' if num_sos != 1 else ''} "
            f"worth {game_new.get_so_points()} {hm.get_emoji('Points')}"
        )

    # secondary (uncleared)
    if num_so_uncleareds != 0:
        update.description += (
            f" (+{num_so_uncleareds} Uncleared{'s' if num_so_uncleareds != 1 else ''})"
        )

    # community
    num_cos = len(game_new.get_community_objectives())
    if num_cos != 0:
        update.description += (
            f"\n- {num_cos} Community Objective{'s' if num_cos != 1 else ''} "
        )

    update.image = game_new.header
    return update


def create_update_removed_game(game_old: CEGame) -> UpdateMessageForScraperProcess:
    """Creates the `UpdateMessageForScraperProcess` for a removed game."""
    update = UpdateMessageForScraperProcess()
    update.is_embed = True
    update.title = f"__ {game_old.game_name} __ removed from the site"
    update.color = 0xCE4E2C
    update.image = hm.GAME_REMOVED_IMAGE
    update.location = "gameadditions"
    update.game_ce_id = game_old.ce_id

    return update


def create_update_updated_game(
    game_old: CEGame, game_new: CEGame | CEAPIGame
) -> tuple[UpdateMessageForScraperProcess | None, list[str] | None]:
    """Creates the `UpdateMessageForScraperProcess` for an updated game.

    Parameters
    ---
    game_old: `CEGame`
        The previous data for this game.
    game_new: `CEGame` or `CEAPIGame`
        The new data for this game. If a `CEAPIGame` is passed, it comes
        with the added bonus of having additional site information, and
        the update image uses its `.header`. If a plain `CEGame` is passed
        instead (e.g. data read back from storage), the update image falls
        back to its `._banner`.

    Returns
    -------
    update: `UpdateMessageForScraperProcess | None`
        The update that comes out of this game. It can also be None.
    removed_objective_ids: `list[str]` or `None`
        A list of Objective IDs that need to be removed.

    Example
    ---
    Celeste updated on the site:
    - Total points unchanged!
    - PO 'Strawberry Lunatic' updated
      - Description updated
      - Requirements updated
      - 3 achievements added
    - New Secondary Objective 'Double Dash' added:
      - 100
      - Complete 9D.
    - SO 'Speed Berry' decreased from 30 to 20
      - 1 achievement removed, 17 achievements added
    - CO 'Solid Gold' updated
      - Description updated
    """

    update = UpdateMessageForScraperProcess()
    update.is_embed = True
    update.title = f"__ {game_new.game_name} __ updated on the site:"
    update.color = 0xEFD839
    update.description = ""
    update.url = f"https://cedb.me/game/{game_new.ce_id}"
    update.location = "gameadditions"
    update.game_ce_id = game_new.ce_id
    update.image = game_new.header if isinstance(game_new, CEAPIGame) else game_new._banner

    # POINT/TIER CHANGE
    if game_old.get_total_points() == game_new.get_total_points():
        update.description += "\n- Total points unchanged!"
    else:
        update.description += (
            f"\n- {game_old.get_total_points()} {hm.get_emoji('Points')} "  # 75 points
            + f"{hm.get_emoji('Arrow')} "  # -->
            + f"{game_new.get_total_points()} {hm.get_emoji('Points')}"  # 220 points
        )
        if game_old.tier_num != game_new.tier_num:
            update.description += f" ({game_old.tier_emoji} {hm.get_emoji('Arrow')} {game_new.tier_emoji})"

    # CATEGORY CHANGE
    if game_old.categories != game_new.categories:
        update.description += (
            f"\n- {game_old.category_emojis} ({game_old.categories_string})"
            + f"{hm.get_emoji('Arrow')}"
            + f"{game_new.category_emojis} ({game_new.categories_string})"
        )

    # objective changes...
    old_objective_ce_ids = [
        old_objective.ce_id for old_objective in game_old.all_objectives
    ]
    for new_objective in game_new.all_objectives:
        # if objective is new
        if new_objective.ce_id not in old_objective_ce_ids:
            "Objective is new!"
            if new_objective.is_uncleared() and new_objective.type != "Community":
                update.description += f"\n- New Uncleared {new_objective.type_short} '**{new_objective.name}**' added:"
            else:
                update.description += f"\n- New {new_objective.type} Objective '**{new_objective.name}**' added:"
                if new_objective.type == "Primary" or new_objective.type == "Secondary":
                    update.description += (
                        f"\n  - {new_objective.point_value} {hm.get_emoji('Points')}"
                    )
            update.description += f"\n  - {new_objective.description}"
            continue

        # update objective tracker and get the old objective
        old_objective_ce_ids.remove(new_objective.ce_id)
        old_objective = hm.get_item_from_list(
            new_objective.ce_id, game_old.all_objectives
        )
        if old_objective is None:
            logger.error(
                "Could not retrieve Objective with ID %s from game_old with ID %s",
                new_objective.ce_id,
                game_old.ce_id,
            )
            continue

        # if objective is updated
        if not new_objective.equals(old_objective):
            "Objective is updated."
            # if the points have changed
            if old_objective.is_uncleared() and not new_objective.is_uncleared():
                update.description += (
                    f"\n- {new_objective.type_short} '**{new_objective.name}**' cleared, valued at "
                    f"{new_objective.point_value} {hm.get_emoji('Points')}"
                )
            elif old_objective.point_value > new_objective.point_value:
                update.description += (
                    f"\n- {new_objective.type_short} '**{new_objective.name}**' decreased from {old_objective.point_value} "
                    + f"{hm.get_emoji('Points')} to {new_objective.point_value} {hm.get_emoji('Points')}"
                )
            elif old_objective.point_value < new_objective.point_value:
                update.description += (
                    f"\n- {new_objective.type_short} '**{new_objective.name}**' increased from {old_objective.point_value} "
                    + f"{hm.get_emoji('Points')} to {new_objective.point_value} {hm.get_emoji('Points')}"
                )
            else:
                update.description += (
                    f"\n- {new_objective.type_short} '**{new_objective.name}**' updated"
                )

            # if the type has changed
            if old_objective.type != new_objective.type:
                update.description += f"\n  - Type changed from {old_objective.type} to {new_objective.type}"

            # if the description was updated
            if old_objective.description != new_objective.description:
                update.description += "\n  - Description updated"

            # if the requirements were updated
            if old_objective.requirements != new_objective.requirements:
                update.description += "\n  - Requirements updated"

            # if the achievements were updated
            _old_set = set(old_objective.achievement_ce_ids or [])
            _new_set = set(new_objective.achievement_ce_ids or [])
            _count_removed = len(_old_set - _new_set)
            _count_added = len(_new_set - _old_set)
            parts = []
            if _count_removed != 0:
                parts.append(
                    f"{_count_removed} achievement{'s' if _count_removed != 1 else ''} removed"
                )
            if _count_added != 0:
                parts.append(
                    f"{_count_added} achievement{'s' if _count_added != 1 else ''} added"
                )
            if parts:
                update.description += "\n  - " + ", ".join(parts)

            # if the partial points were updated
            if old_objective.partial_points != new_objective.partial_points:
                update.description += (
                    f"\n  - Partial points changed from {old_objective.partial_points} {hm.get_emoji('Points')} "
                    + f"to {new_objective.partial_points} {hm.get_emoji('Points')}"
                )

            # if the name was changed
            # if the objective was cleared, we don't need to make a whole note about the name change unless the name was changed
            if old_objective.name != new_objective.name and (
                (
                    old_objective.is_uncleared()
                    and not new_objective.is_uncleared()
                    and (old_objective.name_uncleared != new_objective.name)
                )
                or not old_objective.is_uncleared()
                or new_objective.is_uncleared()
            ):
                update.description += f"\n  - Name changed from '{old_objective.name}' to '{new_objective.name}'"

    for old_objective_ce_id in old_objective_ce_ids:
        old_objective = game_old.get_objective(old_objective_ce_id)
        if old_objective is None:
            logger.error(
                "Could not retrieve Objective with ID %s from game_old with ID %s",
                old_objective_ce_id,
                game_old.ce_id,
            )
            continue
        update.description += (
            f"\n- {old_objective.type_short} {old_objective.name} removed."
        )

    # CHECK FOR GHOST UPDATE
    # all objectives have been reflected
    description_test = update.description
    description_test = (
        description_test.replace("\n", "")
        .replace("\t", "")
        .replace("- Total points unchanged!", "")
    )

    # if there wasn't any real change, ignore this embed
    if description_test == "":
        return None, None

    return update, old_objective_ce_ids


def check_roles(
    games_old: list[CEUserGame],
    games_new: list[CEUserGame],
    database_name_old: list[CEGame],
    database_name_new: list[CEGame],
    user: CEUser,
) -> list[UpdateMessageForScraperProcess]:
    "Gets updates based on roles the user has achieved."

    # POINT CHANGES
    old_tiers = [0, 0, 0, 0, 0, 0, 0]
    old_categories = [0, 0, 0, 0, 0, 0]  # action arcade bh fps platformer strategy
    new_tiers = [0, 0, 0, 0, 0, 0, 0]
    new_categories = [0, 0, 0, 0, 0, 0]
    updates: list[UpdateMessageForScraperProcess] = []

    for game_old in games_old:
        game_database = hm.get_item_from_list(game_old.ce_id, database_name_old)

        if game_database is None:
            continue

        # if the game is completed
        if game_old.is_overcompleted(game_database):
            old_tiers[game_database.tier_num_include_so - 1] += game_old.user_points
        elif game_old.is_completed(game_database):
            old_tiers[game_database.tier_num - 1] += game_old.primary_points

        # category roles don't care about completion
        # PO points only?
        for c_num in game_database.categories_num:
            old_categories[c_num - 1] += game_old.user_points

    for game_new in games_new:
        game_database = hm.get_item_from_list(game_new.ce_id, database_name_new)

        if game_database is None:
            continue

        # if the game is completed
        if game_new.is_overcompleted(game_database):
            new_tiers[game_database.tier_num_include_so - 1] += game_new.user_points
        elif game_new.is_completed(game_database):
            new_tiers[game_database.tier_num - 1] += game_new.primary_points

        # category roles don't care about completion
        # PO points only?
        for c_num in game_database.categories_num:
            new_categories[c_num - 1] += game_new.user_points

    # CATEGORIES
    CATEGORY_ROLE_NAMES = ["Expert", "Master", "Grandmaster"]
    for index_point, point_value in enumerate([500, 1000, 2000]):
        for index_category, category in enumerate(list(typing.get_args(hm.CATEGORIES))):
            if (
                old_categories[index_category] < point_value
                and new_categories[index_category] >= point_value
            ):
                update = UpdateMessageForScraperProcess()
                update.is_embed = False
                update.text = (
                    f"Congratulations to {user.mention} ({user.display_name_with_link})! "
                    + f"You have unlocked {category} {CATEGORY_ROLE_NAMES[index_point]} ({point_value}+ points)"
                )
                update.location = "userlog"
                updates.append(update)

    # TIERS
    for i in range(1, 5):
        if old_tiers[i - 1] < (i * 500) and new_tiers[i - 1] >= (i * 500):
            update = UpdateMessageForScraperProcess()
            update.is_embed = False
            update.text = (
                f"Congratulations to {user.mention} ({user.display_name_with_link})! "
                + f"You have unlocked Tier {i} Enthusiast ({i * 500} points in Tier {i} completed games)."
            )
            update.location = "userlog"
            updates.append(update)

    # conglomerates
    """
    Master of All	    500+ points in all categories simultaneously
    Grandmaster of All  1000+ points in all categories simultaneously
    Overpowered	        3,000 or more points in a single category
    Omnipotent (Red)    Complete* a T4+ game in each category
    Omnipotent (Black)  Complete* a T5 game in each category
    """
    for i in [500, 1000]:
        if min(old_categories) < i and min(new_categories) >= i:
            update = UpdateMessageForScraperProcess()
            update.is_embed = False

            update.text = (
                f"Woah. {user.mention} ({user.display_name_with_link}) just unlocked "
                f"{'Grandm' if i == 1000 else 'M'}aster of All ({i} points in every category). Congratulations!"
            )
            update.location = "userlog"
            updates.append(update)

    if max(old_categories) < 3000 and max(new_categories) >= 3000:
        update = UpdateMessageForScraperProcess()
        update.is_embed = False

        update.text = (
            f"Everyone listen up. {user.mention} ({user.display_name_with_link}) has just unlocked "
            "Overpowered, by having 3000 points in a single category. Well done!"
        )
        update.location = "userlog"
        updates.append(update)

    # TODO: omnipotent roles

    return updates


def check_newly_completed_games(
    completed_games_old: list[CEGame],
    completed_games_new: list[CEGame],
    user: CEUser,
    overcompleted_games_old: list[CEGame],
    overcompleted_games_new: list[CEGame],
) -> list[UpdateMessageForScraperProcess]:
    """
    Generates updates for completions (and overcompletions!)

    Example
    ---
    - "Wow <@12345> (andyisindecisive)! You've completed Hollow Knight, a T4 worth 150 points."
    - "Holy moly <@12345> (andyisindecisive)! You've now *over*completed Hollow Knight, a T4 worth 150
      points, with an additional 150 points worth of SOs."

    Nits
    ---
    - A game must be a certain tier for its base completion (PO points only) to be
      worthy of report.
    - In addition, a game must have a certain amount of SO points
      for its overcompletion (PO points *and* SO points) to be worthy of report.
    - For example, a game with 140 PO points and 10 PO points would
      receive a completion message but no overcompletion message.
    - Similarly, a game with 10 PO points and 140 PO points would
      *only* receive a message on its overcompletion.

    """
    updates: list[UpdateMessageForScraperProcess] = []

    # filter out ids
    completed_games_old_ids: set[str] = {g.ce_id for g in completed_games_old}
    overcompleted_games_old_ids: set[str] = {g.ce_id for g in overcompleted_games_old}

    # Step 2: Games that are newly completed but NOT overcompleted (message 1).
    newly_completed: list[CEGame] = [
        g for g in completed_games_new if g.ce_id not in completed_games_old_ids
    ]

    # Step 3: Games that were already completed and are now newly overcompleted (message 2))
    newly_overcompleted: list[CEGame] = [
        g for g in overcompleted_games_new if g.ce_id not in overcompleted_games_old_ids
    ]

    # Step 4: Generate messages
    TIER_MINIMUM = 4
    SO_POINTS_MINIMUM = 80
    SO_PERCENTAGE_MINIMUM = 40

    # --- completion only ----------
    for game in newly_completed:
        if game.tier_num < TIER_MINIMUM:
            continue

        update = UpdateMessageForScraperProcess()

        # check mutelist
        if user.is_muted:
            update.location = "privatelog"
            update.text = f"⚪ Muted user {user.display_name_with_link} update:\n"
        else:
            update.location = "userlog"

        update.is_embed = False
        update.text += (
            "Wow {} ({})! You've completed {}, a {} worth {} points {}".format(
                user.mention,
                user.display_name_with_link,
                game.name_with_link,
                game.tier_emoji,
                game.get_po_points(),
                hm.get_emoji("Points"),
            )
        )
        updates.append(update)

    # --- was completed, now overcompleted ----------
    for game in newly_overcompleted:
        # game at minimum needs to be a T4 (in terms of total points, not just PO points)
        if game.tier_num_include_so < TIER_MINIMUM:
            continue

        # game at minimum needs to have 80 SO points...
        # ... OR it can have 40 SO points and be 40% SO points...
        # ... OR it can have been bumped from sub T4 to above T4.
        if (
            game.get_so_points() < SO_POINTS_MINIMUM
            and (
                game.get_so_points() < (SO_POINTS_MINIMUM / 2)
                or game.so_percentage() < SO_PERCENTAGE_MINIMUM
            )
            and game.tier_num >= TIER_MINIMUM
        ):
            continue

        # Case 1: 75 PO, 5 SO --> sends message
        # Case 2: 150 PO, 10 SO --> doesn't send message
        # Case 3: 150 PO, 80 SO --> sends message
        # Case 4: 50 PO, 30 SO --> sends message
        # Case 5: 195 PO, 5 SO --> doesn't send message
        # Case 6: 0 PO, 80 SO --> sends message

        update = UpdateMessageForScraperProcess()

        # check mutelist
        if user.is_muted:
            update.location = "privatelog"
            update.text = f"⚪ Muted user {user.display_name_with_link} update:\n"
        else:
            update.location = "userlog"

        update.is_embed = False
        update.text += (
            f"Holy moly {user.mention} ({user.display_name_with_link})! You've now *over*completed {game.name_with_link}, a {game.tier_emoji} worth {game.get_po_points()} points, with an additional {game.get_so_points()} points "
            "worth of SOs."
        )
        updates.append(update)

    # REPORTING
    if len(updates) != 0:
        logger.debug(
            "User with ID %s went from %d completed games to %d completed games (%d difference).",
            user.ce_id,
            len(completed_games_old),
            len(completed_games_new),
            len(completed_games_new) - len(completed_games_old),
        )
    return updates


def check_rank(
    rank_old: str, rank_new: str, points_old: int, points_new: int, user: CEUser
) -> UpdateMessageForScraperProcess | None:
    """
    Generates an Update Message for a user's rank up.
    Parameters
    ---
    rank_old: `str`
        The previous rank.
    rank_new: `str`
        The newly computed rank.
    points_old: `int`
        The number of points the user had before this scrape
    points_new: `int`
        The number of points the user has now
    user: `CEUser`
        The user we're checking in the first place
    """
    # no update needed
    if rank_new == rank_old or points_new <= points_old:
        return None

    if not user.is_muted:
        update = UpdateMessageForScraperProcess()
        update.location = "userlog"
        update.is_embed = False
        update.text = (
            f"Congrats to {user.mention} ({user.display_name_with_link}) for ranking up from Rank "
            + f"{hm.get_emoji(rank_old)} to Rank {hm.get_emoji(rank_new)}!"  # type: ignore
        )
    else:
        update = UpdateMessageForScraperProcess()
        update.location = "privatelog"
        update.is_embed = False
        update.text = f"🤫 Muted user {user.display_name_with_link} ranked up from {rank_old} to {rank_new}."
    return update


def check_completion_count(
    num_completions_og: int, num_completions_new: int, user: CEUser
) -> None | UpdateMessageForScraperProcess:
    """
    Checks if a user has completed a new increment of COMPLETION_INCREMENT Games.
    Currently set at 25.
    """
    COMPLETION_INCREMENT = 25

    if int(num_completions_og / COMPLETION_INCREMENT) >= int(
        num_completions_new / COMPLETION_INCREMENT
    ):
        return None
    if not user.is_muted:
        update = UpdateMessageForScraperProcess()
        update.location = "userlog"
        update.is_embed = False
        update.text = (
            f"Amazing! {user.mention} ({user.display_name_with_link}) has passed the milestone of "
            + f"{int(num_completions_new / COMPLETION_INCREMENT) * COMPLETION_INCREMENT} completed games!"
        )
    else:
        update = UpdateMessageForScraperProcess()
        update.location = "privatelog"
        update.is_embed = False
        update.text = (
            f"🤫 Muted user {user.display_name_with_link} has passed the milestone of "
            + f"{int(num_completions_new / COMPLETION_INCREMENT) * COMPLETION_INCREMENT} completed games."
        )
    return update


def database_reload():
    "Reloads the Supabase database will all data from CEDB database."
    raise NotImplementedError


async def main():
    try:
        await process_loop()
    finally:
        await http_session.close_session()


# if __name__ == "__main__":
#     asyncio.run(main())
