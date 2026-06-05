from __future__ import annotations

from collections.abc import Sequence
import datetime
import json
import time
import uuid
from typing import Literal, cast
import logging
import typing

import httpx
from postgrest import APIError
from supabase import ClientOptions, create_client, Client

# -- local --
from Classes.CE_Game import CEGame
from Classes.CE_Objective import CEObjective
from Classes.CE_Roll import CERoll
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Classes.OtherClasses import CEInput
from Modules import hm

with open("secret_info.json") as f:
    x = json.load(f)
    SUPABASE_URL = x["supabase_url"]
    SUPABASE_KEY = x["supabase_key_secret"]

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=ClientOptions(httpx_client=httpx.Client(timeout=120, verify=True)),
)

logger = logging.getLogger(__name__)


def _iso_or_none(value):
    """
    Return ISO string for datetime-like values.
    - Return the original string if already a string
    - Return None for falsy/unparseable values.

    Example
    ---
    dt = datetime.datetime(2025, 1, 2, 3, 40, 5) # 3:40:05PM on January 2, 2025
    _iso_or_none(dt) --> '2025-01-02T03:40:05+00:00'

    """
    if value is None:
        return None
    if isinstance(value, str):
        # ensure not the literal 'None'
        return None if value == "None" else value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return None
    return None


def _fetch_in_chunks(
    table_name: str, column: str, values: list, chunk_size: int = 100
) -> list[dict]:
    """
    Fetch rows using .in_() in chunks to avoid oversized requests/Bad Request errors.

    Supabase/PostgREST can reject very long `in()` queries (URL length or server limits).
    This helper splits `values` into batches and aggregates results.

    Parameters
    ---
    table_name: `str`
        The name of the table you're pulling from.
    column: `str`
        The column you're checking if certain values are in
    values: `list`
        The values you're checking against a column
    chunk_size: `int` (default 100)
        The chunk size. Probably shouldn't adjust this.

    Example
    ---
    I want to find all userGames that belong to users with ids ['a', 'b', 'c']\n
    `_fetch_in_chunks('userGames', 'user_ce_id', ['a', 'b', 'c'])`
    """
    if not values:
        return []
    out: list[dict] = []
    for i in range(0, len(values), chunk_size):
        chunk = values[i : i + chunk_size]
        for attempt in range(3):
            try:
                resp = supabase.table(table_name).select().in_(column, chunk).execute()
                out.extend(resp.data or [])
                break
            except httpx.ReadTimeout:
                if attempt == 2:
                    raise
                logger.warning(
                    "ReadTimeout on %s (attempt %d/3), retrying...",
                    table_name,
                    attempt + 1,
                )
                time.sleep(2**attempt)
    return out


def _delete_in_chunks(
    table_name: str, column: str, values: list, chunk_size: int = 100
) -> int:
    """Delete rows using .in_() in chunks and return the number of requested ids."""
    if not values:
        return 0
    deleted = 0
    for i in range(0, len(values), chunk_size):
        chunk = values[i : i + chunk_size]
        supabase.table(table_name).delete().in_(column, chunk).execute()
        deleted += len(chunk)
    return deleted


# == GETTERS ==


# GET LIST
def get_list(database: Literal["name", "user", "input", "objectives"]) -> list[str]:
    """
    Returns a list of ce-ids in that database.
    - name = games
    - user = users
    - input = ???
    - objectives = objectives
    """
    table = None
    match database:
        case "name":
            table = "games"
        case "user":
            table = "users"
        case "objectives":
            table = "objectives"
        case _:
            raise Exception(f"Invalid get_list argument! argument: {database}")

    out = supabase.table(table).select("ce_id").execute()

    return [item["ce_id"] for item in out.data]


# GET GAME
def get_game(ce_id: str) -> CEGame | None:
    """
    Gets the data for a game signified by `ce_id` from Supabase.

    Parameters
    ---
    ce_id: `str`
        The CE ID of the game you are looking for.
    """
    games_json = supabase.table("games").select().eq("ce_id", ce_id).execute().data
    if len(games_json) == 0:
        return None

    objectives_json = (
        supabase.table("objectives").select().eq("game_ce_id", ce_id).execute().data
    )
    objective_ids = [item["ce_id"] for item in objectives_json]

    requirements_json = (
        supabase.table("objectiveRequirements")
        .select()
        .in_("objective_ce_id", objective_ids)
        .execute()
        .data
    )

    if objective_ids:
        requirements_json = (
            supabase.table("objectiveRequirements")
            .select()
            .in_("objective_ce_id", objective_ids)
            .execute()
            .data
        )
    else:
        requirements_json = []

    categories_json = (
        supabase.table("categories")
        .select()
        .eq("game_id", ce_id)
        .order(column="index", desc=False)
        .execute()
        .data
    )

    return __supabase_to_game(
        games_json[0], objectives_json, requirements_json, categories_json
    )


# GET USER
def get_user(ce_id: str | int, use_discord_id: bool = False) -> CEUser | None:
    # TODO: simplify this stuff with joins

    # table: "users"
    if not use_discord_id:
        user_json = supabase.table("users").select().eq("ce_id", ce_id).execute().data
    else:
        user_json = (
            supabase.table("users").select().eq("discord_id", ce_id).execute().data
        )
    if len(user_json) == 0:
        return None
    user_json = user_json[0]
    if use_discord_id:
        ce_id = user_json["ce_id"]

    # table: "userGames"
    userGames_json = (
        supabase.table("userGames").select().eq("user_ce_id", ce_id).execute().data
    )

    # table: "userObjectives"
    userObjectives_json = (
        supabase.table("userObjectives").select().eq("user_ce_id", ce_id).execute().data
    )
    userobjectives_list = [o["objective_ce_id"] for o in userObjectives_json]

    # table: "objectives"
    objectives_json = _fetch_in_chunks(
        "objectives", "ce_id", userobjectives_list, chunk_size=100
    )

    # table: "rolls"
    rolls_json = (
        supabase.table("rolls")
        .select()
        .or_(f"user1_ce_id.eq.{ce_id},user2_ce_id.eq.{ce_id}")
        .execute()
        .data
    )
    roll_ids = [item["id"] for item in rolls_json]

    # table: "rollGames"
    if roll_ids:
        userRollGames_json = (
            supabase.table("rollGames")
            .select()
            .in_("roll_id", roll_ids)
            .order("index")
            .execute()
            .data
        )
    else:
        userRollGames_json = []

    # transform them
    return __supabase_to_user(
        user_json,
        userGames_json,
        userObjectives_json,
        rolls_json,
        userRollGames_json,
        objectives_json,
    )


# DATABASE NAME
def get_database_name() -> list[CEGame]:
    response_games = supabase.table("games").select().execute().data
    response_objectives = supabase.table("objectives").select().execute().data
    response_requirements = (
        supabase.table("objectiveRequirements").select().execute().data
    )
    response_categories = supabase.table("categories").select().execute().data

    _games = []
    for game in response_games:
        objectives = [
            o for o in response_objectives if o["game_ce_id"] == game["ce_id"]
        ]
        ids_objectives = [o["ce_id"] for o in objectives]
        requirements = [
            r for r in response_requirements if r["objective_ce_id"] in ids_objectives
        ]
        categories = [c for c in response_categories if c["game_id"] == game["ce_id"]]
        _games.append(__supabase_to_game(game, objectives, requirements, categories))

    return _games


def get_games_bulk(ce_ids: list[str]) -> list[CEGame]:
    """Fetch many games and their objectives/requirements in bulk using chunked requests.

    Returns a list of `CEGame` objects in the same order as the provided `ce_ids` when possible.
    Uses `_fetch_in_chunks` to avoid oversized `.in_()` requests.
    """
    if not ce_ids:
        return []

    games_json = _fetch_in_chunks("games", "ce_id", ce_ids, chunk_size=100)
    if not games_json:
        return []

    game_ce_ids = [game["ce_id"] for game in games_json]
    objectives_json = _fetch_in_chunks(
        "objectives", "game_ce_id", game_ce_ids, chunk_size=200
    )
    objective_ids = [objective["ce_id"] for objective in objectives_json]
    requirements_json = (
        _fetch_in_chunks(
            "objectiveRequirements", "objective_ce_id", objective_ids, chunk_size=200
        )
        if objective_ids
        else []
    )

    categories_json = _fetch_in_chunks("categories", "game_id", ce_ids, chunk_size=200)
    categories_by_game: dict[str, list[dict]] = {}
    for _category in categories_json:
        categories_by_game.setdefault(_category["game_id"], []).append(_category)

    objectives_by_game: dict[str, list[dict]] = {}
    for objective in objectives_json:
        objectives_by_game.setdefault(objective["game_ce_id"], []).append(objective)

    requirements_by_objective: dict[str, list[dict]] = {}
    for requirement in requirements_json:
        requirements_by_objective.setdefault(requirement["objective_ce_id"], []).append(
            requirement
        )

    games_index = {game["ce_id"]: game for game in games_json}
    out_games: list[CEGame] = []
    for ce_id in ce_ids:
        game_json = games_index.get(ce_id)
        if not game_json:
            continue

        game_categories = categories_by_game.get(ce_id)
        if not game_categories and ce_id not in [
            hm.GAME_ID_CHALLENGE_ENTHUSIASTS,
            hm.GAME_ID_CLOWN_TOWN,
        ]:
            logger.error("Game with ID %s has no categories.", ce_id)
            continue
        game_objectives = objectives_by_game.get(ce_id, [])
        game_requirements: list[dict] = []
        for objective in game_objectives:
            game_requirements.extend(
                requirements_by_objective.get(objective["ce_id"], [])
            )

        out_games.append(
            __supabase_to_game(
                game_json, game_objectives, game_requirements, game_categories
            )
        )

    return out_games


# DATABASE USER
def get_database_user() -> list[CEUser]:
    response_user = supabase.table("users").select().execute().data
    response_ugames = supabase.table("userGames").select().execute().data
    response_uobjectives = supabase.table("userObjectives").select().execute().data

    response_rolls = supabase.table("rolls").select().execute().data
    response_rgames = supabase.table("rollGames").select().execute().data

    response_objectives = supabase.table("objectives").select().execute().data

    _users = []
    for user in response_user:
        ugames = [g for g in response_ugames if g["user_ce_id"] == user["ce_id"]]
        uobjectives = [
            o for o in response_uobjectives if o["user_ce_id"] == user["ce_id"]
        ]

        rolls = [r for r in response_rolls if r["user1_ce_id"] == user["ce_id"]]
        rgames = [
            g for g in response_rgames if g["roll_id"] in [r["id"] for r in rolls]
        ]

        _users.append(
            __supabase_to_user(
                user,
                ugames,
                uobjectives,
                rolls,
                rgames,
                [
                    o
                    for o in response_objectives
                    if o["ce_id"] in [u["objective_ce_id"] for u in uobjectives]
                ],  # works?
            )
        )

    return _users


def get_users_bulk(ce_ids: list[str], include_rolls=True) -> list[CEUser]:
    """Fetch many users and their related data in bulk using chunked requests.

    Returns a list of `CEUser` objects corresponding to the provided `ce_ids`.
    Uses `_fetch_in_chunks` to avoid oversized `.in_()` requests.
    """
    # null check
    if not ce_ids:
        return []

    # users
    users_json = _fetch_in_chunks("users", "ce_id", ce_ids, chunk_size=100)
    if not users_json:
        return []

    user_ce_ids = [u["ce_id"] for u in users_json]

    # userGames and userObjectives
    userGames_json = _fetch_in_chunks(
        "userGames", "user_ce_id", user_ce_ids, chunk_size=200
    )
    userObjectives_json = _fetch_in_chunks(
        "userObjectives", "user_ce_id", user_ce_ids, chunk_size=200
    )

    # userId --> userGame and userId --> userObjective mapping
    ugames_by_user: dict[str, list[dict]] = {}
    for ug in userGames_json:
        ugames_by_user.setdefault(ug["user_ce_id"], []).append(ug)
    uobjs_by_user: dict[str, list[dict]] = {}
    for uo in userObjectives_json:
        uobjs_by_user.setdefault(uo["user_ce_id"], []).append(uo)

    # objectives
    objective_ids = list({o["objective_ce_id"] for o in userObjectives_json})
    objectives_json = (
        _fetch_in_chunks("objectives", "ce_id", objective_ids, chunk_size=200)
        if objective_ids
        else []
    )

    # rolls (if include_rolls == True)
    if include_rolls:
        # pull rolls
        rolls_user1 = _fetch_in_chunks(
            "rolls", "user1_ce_id", user_ce_ids, chunk_size=200
        )
        rolls_user2 = _fetch_in_chunks(
            "rolls", "user2_ce_id", user_ce_ids, chunk_size=200
        )
        # roll id --> roll mapping
        rolls_map: dict[str, dict] = {}
        for r in (rolls_user1 or []) + (rolls_user2 or []):
            rolls_map[r["id"]] = r
        rolls = list(rolls_map.values())
        # pull rollGames
        roll_ids = [r["id"] for r in rolls]
        rollGames_json = (
            _fetch_in_chunks("rollGames", "roll_id", roll_ids, chunk_size=200)
            if roll_ids
            else []
        )
        # userId --> roll mapping
        rolls_by_user: dict[str, list[dict]] = {}
        for r in rolls:
            rolls_by_user.setdefault(r["user1_ce_id"], []).append(r)
            if r["user2_ce_id"] is not None:
                rolls_by_user.setdefault(r["user2_ce_id"], []).append(r)
    else:
        rolls_user1 = []
        rolls_user2 = []
        rolls_map = {}
        rolls = []
        roll_ids = []
        rollGames_json = []
        rolls_by_user = {}

    # merge users
    out_users: list[CEUser] = []
    users_index = {u["ce_id"]: u for u in users_json}
    for ce_id in ce_ids:
        user_json = users_index.get(ce_id)
        if not user_json:
            continue

        ugames = ugames_by_user.get(ce_id, [])
        uobjectives = uobjs_by_user.get(ce_id, [])
        if include_rolls:
            user_rolls = [r for r in rolls_by_user.get(ce_id, []) if r is not None]

            # rollGames relevant for this user's rolls
            user_roll_ids = [r["id"] for r in user_rolls]
            user_rollgames = [
                rg for rg in rollGames_json if rg["roll_id"] in user_roll_ids
            ]
        else:
            user_rolls = []
            user_roll_ids = []
            user_rollgames = []

        # objectives subset already fetched above
        user_objectives_list = objectives_json

        out_users.append(
            __supabase_to_user(
                user_json,
                ugames,
                uobjectives,
                user_rolls,
                user_rollgames,
                user_objectives_list,
            )
        )

    return out_users


def get_roll(roll_id: str) -> CERoll | None:
    roll_json = supabase.table("rolls").select().eq("id", roll_id).execute().data
    if len(roll_json) == 0:
        return None
    roll_json = roll_json[0]

    rollGames_json = (
        supabase.table("rollGames")
        .select()
        .eq("roll_id", roll_id)
        .order("index")
        .execute()
        .data
    )

    return __supabase_to_roll(roll_json, rollGames_json)


def get_all_rolls(event_names: list[str] | None = None) -> list[CERoll]:
    if event_names:
        rolls_json = (
            supabase.table("rolls")
            .select()
            .in_("event_name", event_names)
            .execute()
            .data
        )
        ids = [r["id"] for r in rolls_json]
        rollGames_json = (
            supabase.table("rollGames").select().in_("roll_id", ids).execute().data
        )
    else:
        rolls_json = supabase.table("rolls").select().execute().data
        rollGames_json = supabase.table("rollGames").select().execute().data

    _rolls = []
    for roll in rolls_json:
        _rolls.append(
            __supabase_to_roll(
                roll, [g for g in rollGames_json if g["roll_id"] == roll["id"]]
            )
        )

    return _rolls


def get_checkable_rolls() -> list[CERoll]:
    """
    This function differs from `get_all_rolls` in only one manner:
    we only pull rolls that are 'current' or 'pending'. This will
    drastically speed up our time spent pulling from Supabase as
    the majority of rolls are already completed.
    """
    # pull rolls
    rolls_json = (
        supabase.table("rolls")
        .select()
        .in_("status", ["current", "pending"])
        .execute()
        .data
    )

    # pull rollgames
    ids = [r["id"] for r in rolls_json]
    roll_games_json = _fetch_in_chunks("rollGames", "roll_id", ids)

    # convert and return
    _rolls = []
    for roll in rolls_json:
        _rolls.append(
            __supabase_to_roll(
                roll, [g for g in roll_games_json if g["roll_id"] == roll["id"]]
            )
        )
    return _rolls


def get_user_rolls(user_id: str) -> list[CERoll]:
    """
    Pulls all rolls pertaining to a certain user.
    """
    # table: "rolls"
    rolls_json = (
        supabase.table("rolls")
        .select()
        .or_(f"user1_ce_id.eq.{user_id},user2_ce_id.eq.{user_id}")
        .execute()
        .data
    )
    roll_ids = [item["id"] for item in rolls_json]
    rollGames_json = (
        supabase.table("rollGames").select().in_("roll_id", roll_ids).execute().data
    )

    # convert and return
    _rolls = []
    for roll in rolls_json:
        _rolls.append(
            __supabase_to_roll(
                roll, [g for g in rollGames_json if g["roll_id"] == roll["id"]]
            )
        )
    return _rolls


def get_input(ce_id: str) -> CEInput:
    # TODO: Implement after input schema is finalized
    raise NotImplementedError


def get_database_tier(database_name: list[CEGame]) -> dict:
    """
    Gets database_tier from Supabase.
    The output `database_tier` will be formatted like this:
    database_tier[str(tiernum)][category] = `entries`,
    where `entries` is a list of dicts with keys:
    'ce_id', 'price', 'sh_hours'
    - Note that multi-category games will be placed
      in all category arrays that they belong to.
    """
    response = supabase.table("tier").select().execute().data

    database_name_mapping: dict[str, CEGame] = {}
    for game in database_name:
        # neither of these conditions should ever happen
        if game.is_t0:
            continue
        if game.platform != "steam":
            continue
        database_name_mapping[game.ce_id] = game

    # separate out games by tier and category
    database_tier: dict[str, dict[str, list[dict]]] = {}

    for tier in range(1, 8):
        database_tier[str(tier)] = {}
        for category in typing.get_args(hm.CATEGORIES):
            database_tier[str(tier)][category] = []

    for tier_entry in response:
        _game_object = database_name_mapping.get(tier_entry["ce_id"])
        if _game_object is None:
            logger.warning(
                "Could not find game %s from database_name when generating database tier.",
                tier_entry["ce_id"],
            )
            continue

        for _cat in _game_object.categories:
            database_tier[str(_game_object.tier_num)][_cat].append(tier_entry)

    return database_tier


def get_curator_ids() -> list[str]:
    # Assuming curator_ids table exists with curator_id column
    response = supabase.table("curator_ids").select("curator_id").execute().data
    return [item["curator_id"] for item in response]


def get_curator_count() -> int:
    # Not currently needed, but can be implemented if required
    raise NotImplementedError


def get_last_loop(offset=True) -> datetime.datetime:
    data = (
        supabase.table("loopruns")
        .select("ran_at")
        .order("ran_at", desc=True)
        .limit(1)
        .execute()
        .data
    )

    dt = datetime.datetime.fromisoformat(data[0]["ran_at"])
    if offset:
        dt = dt - datetime.timedelta(hours=2, minutes=10)

    return dt


# === DUMPERS ===
def dump_game(game: CEGame):
    return bulk_dump_games([game])


def bulk_dump_games(
    games: Sequence[CEGame], batch_size: int = 50, pause_seconds: float = 0.1
):
    """Bulk dump many games at once in batches to reduce HTTP calls and avoid connection termination.

    - groups games into batches of `batch_size`
    - for each batch: collect games, objectives, achievement requirements, and custom requirements
    - delete existing custom requirements for all objectives in the batch in a single call
    - bulk upsert games, objectives, achievement requirements, and custom requirements
    - optional `pause_seconds` between batches to avoid overwhelming the server
    """
    if not games:
        return

    # process in batches
    for i in range(0, len(games), batch_size):
        batch = games[i : i + batch_size]
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        games_payload = []
        objectives_payload = []
        achievement_reqs_payload = []
        custom_reqs_payload = []
        objective_ids = []
        categories_payload = []
        game_ids = []

        for game in batch:
            game_ids.append(game.ce_id)
            games_payload.append(
                {
                    "ce_id": game.ce_id,
                    "name": game.game_name,
                    "platform": game.platform,
                    "platform_id": game.platform_id,
                    "category_primary": None,
                    "image_header": game._banner,
                    "image_icon": "",
                    "updated_at_CE": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                }
            )

            for i, _cat in enumerate(game.categories):
                # We sort these on the way in so dw about sorting on the way out
                categories_payload.append(
                    {"game_id": game.ce_id, "category": _cat, "index": i}
                )

            for objective in game.all_objectives:
                objective_ids.append(objective.ce_id)
                objectives_payload.append(
                    {
                        "ce_id": objective.ce_id,
                        "game_ce_id": objective.game_ce_id,
                        "type": objective.type,
                        "name": objective.name,
                        "description": objective.description,
                        "points": objective.point_value,
                        "points_partial": objective.partial_points,
                        "updated_at_CE": now_iso,
                    }
                )

                for achievement_id in objective.achievement_ce_ids or []:
                    achievement_reqs_payload.append(
                        {
                            "objective_ce_id": objective.ce_id,
                            "requirement_type": "achievement",
                            "data": achievement_id,
                            "updated_at_CE": now_iso,
                        }
                    )

                if objective.requirements:
                    custom_reqs_payload.append(
                        {
                            "objective_ce_id": objective.ce_id,
                            "requirement_type": "custom",
                            "data": objective.requirements,
                            "updated_at_CE": now_iso,
                        }
                    )

        # Delete all achievements and requirements for all objectives in this batch
        if objective_ids:
            supabase.table("objectiveRequirements").delete().in_(
                "objective_ce_id", objective_ids
            ).execute()

        # Bulk upsert games
        if games_payload:
            supabase.table("games").upsert(games_payload).execute()

        if categories_payload:
            _delete_in_chunks("categories", "game_id", game_ids, chunk_size=200)
            supabase.table("categories").upsert(categories_payload).execute()

        # Bulk upsert objectives
        if objectives_payload:
            supabase.table("objectives").upsert(objectives_payload).execute()

        # Bulk upsert achievement requirements
        if achievement_reqs_payload:
            supabase.table("objectiveRequirements").upsert(
                achievement_reqs_payload
            ).execute()

        # Bulk upsert custom requirements
        if custom_reqs_payload:
            supabase.table("objectiveRequirements").upsert(
                custom_reqs_payload
            ).execute()

        # small pause to avoid overloading the server
        if pause_seconds and (i + batch_size) < len(games):
            time.sleep(pause_seconds)


def bulk_dump_users(
    users: Sequence[CEUser], batch_size: int = 50, pause_seconds: float = 0.1
):
    """Bulk dump many users at once in batches to reduce HTTP calls and avoid connection termination.

    - groups users into batches of `batch_size`
    - for each batch: collect users, userGames, and userObjectives
    - bulk upsert users, userGames, and userObjectives
    - optional `pause_seconds` between batches to avoid overwhelming the server
    - rolls are dumped individually (per user) after batch
    """
    if not users:
        return

    # process in batches
    for i in range(0, len(users), batch_size):
        batch = users[i : i + batch_size]
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        users_payload = []
        user_games_payload = []
        user_objectives_payload = []
        user_ids = []

        for user in batch:
            user_ids.append(user.ce_id)
            users_payload.append(
                {
                    "ce_id": user.ce_id,
                    "discord_id": user.discord_id,
                    "display_name": user.display_name,
                    "image_avatar": user.avatar,
                    "steam_id": user._steam_id,
                    "created_at_CE": now_iso,
                    "updated_at_CE": user.last_updated
                    if isinstance(user.last_updated, str)
                    else (
                        user.last_updated.isoformat()
                        if hasattr(user.last_updated, "isoformat")
                        else now_iso
                    ),
                }
            )

            for game in user.owned_games:
                user_games_payload.append(
                    {
                        "user_ce_id": user.ce_id,
                        "game_ce_id": game.ce_id,
                        "updated_at_CE": now_iso,
                    }
                )

                for objective in game.user_objectives:
                    user_objectives_payload.append(
                        {
                            "user_ce_id": user.ce_id,
                            "objective_ce_id": objective.ce_id,
                            "user_points": objective.user_points,
                            "updated_at_CE": now_iso,
                        }
                    )

        # Bulk upsert users
        if users_payload:
            supabase.table("users").upsert(users_payload).execute()

        # TODO inefficient
        # Bulk remove userObjectives
        if user_ids:
            # (do we need this?)  _delete_in_chunks('userGames', 'user_ce_id', user_ids, chunk_size=200)
            _delete_in_chunks("userObjectives", "user_ce_id", user_ids, chunk_size=200)

        # Bulk upsert userGames
        if user_games_payload:
            game_collision = True
            while game_collision:
                game_collision = False
                try:
                    supabase.table("userGames").upsert(user_games_payload).execute()
                except APIError as e:
                    if e.message is None:
                        raise Exception("No message in APIError, userGames")
                    if e.details is None:
                        raise Exception("No details in APIError, userGames")

                    if "violates foreign key constraint" not in e.message:
                        raise e
                    game_id = e.details.replace("Key (game_ce_id)=(", "").replace(
                        ') is not present in table "games".', ""
                    )
                    user_games_payload = [
                        row
                        for row in user_games_payload
                        if row["game_ce_id"] != game_id
                    ]
                    game_collision = True
                    logger.error(
                        "Found UserGame with foreign-key constraint on GameID=%s.",
                        game_id,
                    )

        # Bulk upsert userObjectives
        if user_objectives_payload:
            objective_collision = True
            while objective_collision:
                objective_collision = False
                try:
                    supabase.table("userObjectives").upsert(
                        user_objectives_payload
                    ).execute()
                except APIError as e:
                    if e.message is None:
                        raise Exception("No message in APIError, userObjectives")
                    if e.details is None:
                        raise Exception("No details in APIError, userObjectives")

                    if "violates foreign key constraint" not in e.message:
                        raise e
                    objective_id = e.details.replace(
                        "Key (objective_ce_id)=(", ""
                    ).replace(') is not present in table "objectives".', "")
                    user_objectives_payload = [
                        row
                        for row in user_objectives_payload
                        if row["objective_ce_id"] != objective_id
                    ]
                    objective_collision = True
                    logger.error(
                        "Found UserObjective with foreign-key constraint on ObjectiveID=%s.",
                        objective_id,
                    )

        # Dump rolls individually per user (keep serial for now to avoid overwhelming connection)
        for user in batch:
            for roll in user.rolls:
                dump_roll(roll)

        # small pause to avoid overloading the server
        if pause_seconds and (i + batch_size) < len(users):
            time.sleep(pause_seconds)


def dump_user(user: CEUser):
    user_data = {
        "ce_id": user.ce_id,
        "discord_id": user.discord_id,
        "display_name": user.display_name,
        "image_avatar": user.avatar,
        "steam_id": user._steam_id,
        "created_at_CE": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at_CE": user.last_updated
        if isinstance(user.last_updated, str)
        else (
            user.last_updated.isoformat()
            if hasattr(user.last_updated, "isoformat")
            else datetime.datetime.now(datetime.timezone.utc).isoformat()
        ),
    }
    supabase.table("users").upsert(user_data).execute()

    for game in user.owned_games:
        game_data = {
            "user_ce_id": user.ce_id,
            "game_ce_id": game.ce_id,
            "updated_at_CE": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        supabase.table("userGames").upsert(game_data).execute()

        for objective in game.user_objectives:
            obj_data = {
                "user_ce_id": user.ce_id,
                "objective_ce_id": objective.ce_id,
                "user_points": objective.user_points,
                "updated_at_CE": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
            }
            supabase.table("userObjectives").upsert(obj_data).execute()

    # for roll in user.rolls:
    #     dump_roll(roll)


def __dump_JUST_user(d: dict):
    "Just used for discord id updating. No games/objectives propogated."
    supabase.table("users").upsert(d).execute()


def bulk_dump_rolls(
    rolls: list[CERoll], batch_size: int = 100, pause_seconds: float = 0.05
):
    """Bulk dump many rolls and rollGames in batches to reduce HTTP calls.

    - deletes existing rollGames and rolls for batch roll ids before inserting
    - bulk inserts rolls, then rollGames
    - small pause between batches to avoid connection issues
    """
    if not rolls:
        return

    for i in range(0, len(rolls), batch_size):
        batch = rolls[i : i + batch_size]
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        roll_ids = [r._id for r in batch]
        rolls_payload = []
        rollgames_payload = []

        for r in batch:
            rolls_payload.append(
                {
                    "id": r._id,
                    "event_name": r.roll_name,
                    "user1_ce_id": r.user_ce_id,
                    "user2_ce_id": r.partner_ce_id,
                    "time_created": _iso_or_none(r.init_time),
                    "time_due": _iso_or_none(r.due_time),
                    "time_completed": _iso_or_none(r.completed_time),
                    "is_lucky": False,
                    "chosen_tier": r._tier_num,
                    "chosen_tier_partner": r._tier_num_partner,
                    "status": r.status,
                    "rerolls_remaining": r.rerolls,
                    "rerolls_used": 0,
                    "winner": None,
                }
            )

            for idx, game_id in enumerate(r.games):
                rollgames_payload.append(
                    {
                        "roll_id": r._id,
                        "game_id": game_id,
                        "index": idx,
                        "rolled_at": now_iso,
                    }
                )

        # Delete existing rollGames and rolls for this batch
        if roll_ids:
            supabase.table("rollGames").delete().in_("roll_id", roll_ids).execute()
            supabase.table("rolls").delete().in_("id", roll_ids).execute()

        # Bulk insert rolls and rollGames
        if rolls_payload:
            supabase.table("rolls").insert(rolls_payload).execute()

        if rollgames_payload:
            supabase.table("rollGames").insert(rollgames_payload).execute()

        if pause_seconds and (i + batch_size) < len(rolls):
            time.sleep(pause_seconds)


def dump_roll(roll: CERoll):
    roll_data = {
        "id": roll._id,
        "event_name": roll.roll_name,
        "user1_ce_id": roll.user_ce_id,
        "user2_ce_id": roll.partner_ce_id,
        "time_created": _iso_or_none(roll.init_time),
        "time_due": _iso_or_none(roll.due_time),
        "time_completed": _iso_or_none(roll.completed_time),
        "is_lucky": roll.lucky,  # TODO: determine from roll data
        "chosen_tier": roll._tier_num,
        "chosen_tier_partner": roll._tier_num_partner,
        "status": roll.status,
        "rerolls_remaining": roll.rerolls,
        "rerolls_used": 0,  # TODO: calculate or track
        "winner": None,  # TODO: determine on completion
    }
    supabase.table("rolls").upsert(roll_data).execute()

    for idx, game_id in enumerate(roll.games):
        game_data = {
            "roll_id": roll._id,
            "game_id": game_id,
            "index": idx,
            "rolled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        supabase.table("rollGames").upsert(game_data).execute()


def dump_input(input: CEInput):
    # TODO: Implement after input schema is finalized
    raise NotImplementedError


def dump_curator_ids(ids: list[str]):
    for curator_id in ids:
        supabase.table("curator_ids").upsert({"curator_id": curator_id}).execute()


def dump_curator_count(cc: int):
    # Not currently needed
    raise NotImplementedError


def dump_database_tier(database_tier: dict):
    """
    Dumps database_tier back to Supabase.
    The input `database_tier` will be formatted like this:
    database_tier[str(tiernum)][category] = `entries`,
    where `entries` is a list of dicts with keys:
    'ce_id', 'price', 'sh_hours'
    """

    # sort out
    all_entries: list[dict] = []

    for tier in range(1, 8):
        for category in list(typing.get_args(hm.CATEGORIES)):
            all_entries.extend(database_tier[str(tier)][category])

    # remove duplicates (multi-category)
    all_entries = list({e["ce_id"]: e for e in all_entries}.values())

    # dump 100 at a time
    BATCH_SIZE = 100
    for i in range(0, len(all_entries), BATCH_SIZE):
        batch = all_entries[i : i + BATCH_SIZE]

        payload = []

        for entry in batch:
            payload.append(entry)

        if payload:
            supabase.table("tier").upsert(payload).execute()


def dump_loop(dt: datetime.datetime):
    supabase.table("loopruns").insert({"ran_at": dt.isoformat()}).execute()
    return


# === SUPABASE DELETERS ===
def delete_game(ce_id: str):
    # Delete objectives first (foreign key constraint)
    objectives = (
        supabase.table("objectives")
        .select("ce_id")
        .eq("game_ce_id", ce_id)
        .execute()
        .data
    )
    for obj in objectives:
        supabase.table("objectiveRequirements").delete().eq(
            "objective_ce_id", obj["ce_id"]
        ).execute()
    supabase.table("objectives").delete().eq("game_ce_id", ce_id).execute()

    # Delete game
    supabase.table("games").delete().eq("ce_id", ce_id).execute()


def delete_user(ce_id: str):
    # Delete user games and objectives
    supabase.table("userGames").delete().eq("user_ce_id", ce_id).execute()
    supabase.table("userObjectives").delete().eq("user_ce_id", ce_id).execute()

    # Delete rolls and associated roll games
    # rolls = supabase.table('rolls').select('id').or_(f"user1_ce_id.eq.{ce_id},user2_ce_id.eq.{ce_id}").execute().data
    # for roll in rolls:
    #     supabase.table('rollGames').delete().eq('roll_id', roll['id']).execute()
    # supabase.table('rolls').delete().or_(f"user1_ce_id.eq.{ce_id},user2_ce_id.eq.{ce_id}").execute()

    # Delete user
    supabase.table("users").delete().eq("ce_id", ce_id).execute()


def delete_roll(roll_id: str):
    # Delete roll games first
    supabase.table("rollGames").delete().eq("roll_id", roll_id).execute()

    # Delete roll
    supabase.table("rolls").delete().eq("id", roll_id).execute()


def add_pending(
    event_name: hm.ALL_ROLL_EVENT_NAMES,
    user1_ce_id: str,
    user2_ce_id: str | None = None,
):
    """
    Adds a dummy "pending" roll for user1 and user2.

    Parameters
    ---
    event_name: `ALL_ROLL_EVENT_NAMES`
        The name of the event we'd like to
        create the pending for.
    user1_ce_id: `str`
        The CE ID of the user whose pending we
        are trying to create.
    user2_ce_id: `str | None` (default None)
        Optional second user to create the pending for.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    due = now + datetime.timedelta(minutes=10)

    user_ids = [user1_ce_id] + ([user2_ce_id] if user2_ce_id is not None else [])
    payload = [
        {
            "id": str(uuid.uuid4()),
            "event_name": event_name,
            "user1_ce_id": user_ce_id,
            "user2_ce_id": None,
            "time_created": _iso_or_none(now),
            "time_due": _iso_or_none(due),
            "time_completed": None,
            "is_lucky": False,
            "chosen_tier": None,
            "status": "pending",
            "rerolls_remaining": None,
            "rerolls_used": 0,
            "winner": None,
        }
        for user_ce_id in user_ids
    ]
    supabase.table("rolls").insert(payload).execute()


def kill_pending(
    event_name: hm.ALL_ROLL_EVENT_NAMES,
    user1_ce_id: str,
    user2_ce_id: str | None = None,
):
    """
    Removes any pendings from this user involving `event_name`.

    Parameters
    ---
    event_name: `ALL_ROLL_EVENT_NAMES`
        The name of the event we'd like to
        kill the pending for.
    user1_ce_id: `str`
        The CE ID of the user whose pending we
        are trying to kill.
    user2_ce_id: `str | None` (default None)
        Optional second user to kill the pending for.
    """
    user_ids = [user1_ce_id] + ([user2_ce_id] if user2_ce_id is not None else [])
    or_filter = ",".join(f"user1_ce_id.eq.{uid}" for uid in user_ids)
    ids = [
        row["id"]
        for row in (
            supabase.table("rolls")
            .select("id")
            .eq("event_name", event_name)
            .eq("status", "pending")
            .or_(or_filter)
            .execute()
            .data
        )
    ]
    if not ids:
        return
    supabase.table("rollGames").delete().in_("roll_id", ids).execute()
    supabase.table("rolls").delete().in_("id", ids).execute()


def delete_objectives_many(objs: list[str]):
    "Delete all objectives given in `objs`."
    supabase.table("objectives").delete().in_("ce_id", objs).execute()
    supabase.table("objectiveRequirements").delete().in_(
        "objective_ce_id", objs
    ).execute()


# === MAINTENANCE ===
def clean_db():
    """Cleans out the database. Any user games and user objectives with no corresponding
    real game or objective  deleted."""
    games = supabase.table("games").select("ce_id").execute().data or []
    objectives = supabase.table("objectives").select("ce_id").execute().data or []

    game_ids = {game["ce_id"] for game in games}
    objective_ids = {objective["ce_id"] for objective in objectives}

    user_games = (
        supabase.table("userGames").select("user_ce_id,game_ce_id").execute().data or []
    )
    orphan_user_game_ids = [
        row["game_ce_id"] for row in user_games if row.get("game_ce_id") not in game_ids
    ]

    user_objectives = (
        supabase.table("userObjectives")
        .select("user_ce_id,objective_ce_id")
        .execute()
        .data
        or []
    )
    orphan_user_objective_ids = [
        row["objective_ce_id"]
        for row in user_objectives
        if row.get("objective_ce_id") not in objective_ids
    ]

    deleted_user_games = _delete_in_chunks(
        "userGames", "game_ce_id", orphan_user_game_ids
    )
    deleted_user_objectives = _delete_in_chunks(
        "userObjectives", "objective_ce_id", orphan_user_objective_ids
    )

    logger.info(
        "clean_db removed %d orphan userGames and %d orphan userObjectives",
        deleted_user_games,
        deleted_user_objectives,
    )


# === SUPABASE CONVERTERS ===


def __supabase_to_game(
    game: dict, obj: list[dict], reqs: list[dict], cats: list[dict] | None
) -> CEGame:
    objectives = []
    for o in obj:
        objectives.append(
            __supabase_to_objective(
                o, [req for req in reqs if req["objective_ce_id"] == o["ce_id"]]
            )
        )
    # TODO update this logic
    if cats is None:
        if game["ce_id"] == hm.GAME_ID_CHALLENGE_ENTHUSIASTS:
            categories = ["Arcade"]
        elif game["ce_id"] == hm.GAME_ID_CLOWN_TOWN:
            categories = ["Action"]
        else:
            raise Exception("Sent in cats=None and game is not CE or Clown Town.")
    else:
        sorted_cats = sorted(cats, key=lambda c: c["index"])
        categories: list[str] = [c["category"] for c in sorted_cats]
    return CEGame(
        ce_id=game["ce_id"],
        game_name=game["name"],
        platform=game["platform"],
        platform_id=game["platform_id"],
        categories=cast(list[hm.CATEGORIES], categories),
        last_updated=game["updated_at_CE"],
        banner=game["image_header"],
        objectives=objectives,
    )


def __supabase_to_objective(obj: dict, reqs: list[dict]) -> CEObjective:
    custom_reqs = [req for req in reqs if req["requirement_type"] == "custom"]

    if len(custom_reqs) > 1:
        # Multiple custom requirements - select the one with the most recent updated_at_CE
        sorted_reqs = sorted(
            custom_reqs, key=lambda r: r.get("updated_at_CE", ""), reverse=True
        )
        requirement = sorted_reqs[0]["data"]
    elif len(custom_reqs) == 1:
        requirement = custom_reqs[0]["data"]
    else:
        requirement = None

    return CEObjective(
        ce_id=obj["ce_id"],
        objective_type=obj["type"],
        description=obj["description"],
        point_value=obj["points"],
        point_value_partial=obj["points_partial"],
        name=obj["name"],
        game_ce_id=obj["game_ce_id"],
        achievement_ce_ids=[
            req["data"] for req in reqs if req["requirement_type"] == "achievement"
        ],
        requirements=requirement,
    )


def __supabase_to_user(
    user: dict,
    userGames: list[dict],
    userObjectives: list[dict],
    rolls: list[dict],
    rollGames: list[dict],
    objectives: list[dict],
) -> CEUser:
    _rolls = []
    for roll in rolls:
        _rolls.append(
            __supabase_to_roll(
                roll, [g for g in rollGames if g["roll_id"] == roll["id"]]
            )
        )

    mapping: dict[str, list[dict]] = {}
    objective_index = {obj["ce_id"]: obj for obj in objectives}
    for game in userGames:
        mapping[game["game_ce_id"]] = []
    for obj_u in userObjectives:
        found_objective = objective_index.get(obj_u["objective_ce_id"])
        if found_objective is None:
            logger.warning(
                "No Objective object found for UserObjective with User ID %s and Objective ID %s",
                user["ce_id"],
                obj_u["objective_ce_id"],
            )
            continue

        enriched_objective = {
            "objective_ce_id": obj_u["objective_ce_id"],
            "user_points": obj_u["user_points"],
            "type": found_objective["type"],
            "name": found_objective["name"],
        }

        if found_objective["game_ce_id"] not in mapping:
            mapping[found_objective["game_ce_id"]] = [enriched_objective]
            continue
        mapping[found_objective["game_ce_id"]].append(enriched_objective)

    _games = []
    for game in userGames:
        _games.append(__supabase_to_user_game(game, mapping[game["game_ce_id"]]))

    return CEUser(
        discord_id=user["discord_id"],
        ce_id=user["ce_id"],
        owned_games=_games,
        rolls=_rolls,
        display_name=user["display_name"],
        avatar=user["image_avatar"],
        last_updated=user["updated_at_CE"],
        steam_id=user["steam_id"],
    )


def __supabase_to_user_game(game: dict, objectives: list[dict]) -> CEUserGame:
    return CEUserGame(
        ce_id=game["game_ce_id"],
        user_objectives=[
            __supabase_to_user_objective(o, game["game_ce_id"]) for o in objectives
        ],
        name="missing",
    )


def __supabase_to_user_objective(objective: dict, game_ce_id: str) -> CEUserObjective:
    return CEUserObjective(
        ce_id=objective["objective_ce_id"],
        game_ce_id=game_ce_id,
        user_points=objective["user_points"],
        type=objective.get("type", "Badge"),
        name=objective.get("name", "missing"),
    )


def __supabase_to_roll(roll: dict, rollGames: list[dict]) -> CERoll:
    return CERoll(
        roll_name=roll.get("event_name", ""),
        init_time=roll.get("time_created"),
        due_time=roll.get("time_due"),
        completed_time=roll.get("time_completed"),
        user_ce_id=roll["user1_ce_id"],
        partner_ce_id=roll.get("user2_ce_id"),
        rerolls=roll.get("rerolls_remaining", 0),
        status=roll.get("status", "pending"),
        _id=roll["id"],
        games=[g["game_id"] for g in rollGames] if rollGames else [],
        tier_num=roll.get("chosen_tier", None),
        tier_num_partner=roll.get("chosen_tier_partner", None),
    )


def dump_objective(objective: CEObjective):
    # Delete all previous custom requirements for this objective to prevent duplicates
    supabase.table("objectiveRequirements").delete().eq(
        "objective_ce_id", objective.ce_id
    ).eq("requirement_type", "custom").execute()

    obj_data = {
        "ce_id": objective.ce_id,
        "game_ce_id": objective.game_ce_id,
        "type": objective.type,
        "name": objective.name,
        "description": objective.description,
        "points": objective.point_value,
        "points_partial": objective.partial_points,
        "updated_at_CE": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    supabase.table("objectives").upsert(obj_data).execute()

    # Dump achievement requirements
    if objective.achievement_ce_ids:
        for achievement_id in objective.achievement_ce_ids:
            req_data = {
                "objective_ce_id": objective.ce_id,
                "requirement_type": "achievement",
                "data": achievement_id,
                "updated_at_CE": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
            }
            supabase.table("objectiveRequirements").upsert(req_data).execute()

    # Dump custom requirement if it exists
    if objective.requirements:
        req_data = {
            "objective_ce_id": objective.ce_id,
            "requirement_type": "custom",
            "data": objective.requirements,
            "updated_at_CE": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        supabase.table("objectiveRequirements").upsert(req_data).execute()
