"""
Shared factory functions for building minimal valid class instances in tests.
Each factory exposes only the parameters that individual tests care about;
everything else gets a safe default.
"""

import datetime
from typing import cast
import uuid

from Classes.CE_Objective import CEObjective
from Classes.CE_Game import CEGame
from Classes.CE_Roll import CERoll, ROLL_STATUS
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Modules import hm


def make_objective(
    ce_id: str = "obj-0001-0000-0000-000000000000",
    obj_type: str = "Primary",
    point_value: int = 10,
    name: str = "Test Objective",
    game_ce_id: str = "game-001-0000-0000-000000000000",
    requirements: str | None = None,
    achievement_ce_ids: list[str] | None = None,
    point_value_partial: int = 0,
) -> CEObjective:
    return CEObjective(
        ce_id=ce_id,
        objective_type=obj_type, # type: ignore
        description="A test objective.",
        point_value=point_value,
        name=name,
        game_ce_id=game_ce_id,
        requirements=requirements,
        achievement_ce_ids=achievement_ce_ids,
        point_value_partial=point_value_partial,
    )


def make_game(
    ce_id: str = "game-001-0000-0000-000000000000",
    game_name: str = "Test Game",
    categories: list[str] | None = None,
    objectives: list[CEObjective] | None = None,
    platform: str = "steam",
) -> CEGame:
    return CEGame(
        ce_id=ce_id,
        game_name=game_name,
        platform=platform, # type: ignore
        platform_id="123456",
        categories=categories if categories is not None else ["Action"], # type: ignore
        objectives=objectives if objectives is not None else [],
        last_updated=None,
    )


def make_user_objective(
    ce_id: str = "obj-0001-0000-0000-000000000000",
    game_ce_id: str = "game-001-0000-0000-000000000000",
    obj_type: str = "Primary",
    user_points: int = 10,
    name: str = "",
) -> CEUserObjective:
    return CEUserObjective(
        ce_id=ce_id,
        game_ce_id=game_ce_id,
        type=cast(hm.OBJECTIVE_TYPES, obj_type),
        user_points=user_points,
        name=name,
    )


def make_user_game(
    ce_id: str = "game-001-0000-0000-000000000000",
    user_objectives: list[CEUserObjective] | None = None,
    name: str = "Test Game",
) -> CEUserGame:
    return CEUserGame(
        ce_id=ce_id,
        user_objectives=user_objectives if user_objectives is not None else [],
        name=name,
    )


def make_user(
    ce_id: str = "user-001-0000-0000-000000000000",
    discord_id: int = 100000000000000000,
    owned_games: list[CEUserGame] | None = None,
    rolls: list | None = None,
    display_name: str = "TestUser",
) -> CEUser:
    return CEUser(
        discord_id=discord_id,
        ce_id=ce_id,
        owned_games=owned_games if owned_games is not None else [],
        rolls=rolls if rolls is not None else [],
        display_name=display_name,
        avatar="",
        last_updated=datetime.datetime.now(datetime.timezone.utc),
    )


def make_roll(
    roll_name: str = "One Hell of a Day",
    status: str = "current",
    games: list[str] | None = None,
    partner_ce_id: str | None = None,
    init_time: datetime.datetime | None = None,
    due_time: datetime.datetime | None = None,
    completed_time: datetime.datetime | None = None,
    rerolls: int | None = None,
    tier_num: int | None = None,
) -> CERoll:
    return CERoll(
        roll_name=cast(hm.ALL_ROLL_EVENT_NAMES, roll_name),
        user_ce_id="user-001-0000-0000-000000000000",
        games=games if games is not None else ["game-001-0000-0000-000000000000"],
        status=cast(ROLL_STATUS, status),
        partner_ce_id=partner_ce_id,
        init_time=init_time
        if init_time is not None
        else datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        due_time=due_time,
        completed_time=completed_time,
        rerolls=rerolls,
        tier_num=tier_num,
        _id=str(uuid.uuid4()),
    )
