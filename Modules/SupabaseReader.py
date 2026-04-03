import asyncio
import datetime
import json
from typing import Literal
import uuid
from Modules import CEAPIReader
import Modules.hm as hm
from supabase import create_client, Client

# -- local --
from Classes.CE_Cooldown import CECooldown
from Classes.CE_Game import CEAPIGame, CEGame
from Classes.CE_Objective import CEObjective
from Classes.CE_Roll import CERoll
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Classes.OtherClasses import *

with open('secret_info.json') as f:
    x = json.load(f)
    SUPABASE_URL = x['supabase_url']
    SUPABASE_KEY = x['supabase_key_secret']

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# GET LIST
def get_list(database: Literal['name', 'user', 'input']) -> list[str]:
    table = None
    if database == "name": table = "games"
    if database == "user": table = "users"
    if table is None: raise Exception("Invalid get_list argument!")

    out = supabase.table(table).select('ce_id').execute()

    return [item['ce_id'] for item in out.data]

# GET GAME
def get_game(ce_id: str) -> CEGame | None:
    games_json = supabase.table('games').select().eq('ce_id', ce_id).execute().data
    if len(games_json) == 0: return None

    objectives_json = supabase.table('objectives').select().eq('game_ce_id', ce_id).execute().data
    objective_ids = [item['ce_id'] for item in objectives_json]

    requirements_json = supabase.table("objectiveRequirements").select().in_("objective_ce_id", objective_ids).execute().data

    return __supabase_to_game(games_json[0], objectives_json, requirements_json)

# GET USER
def get_user(ce_id: str, use_discord_id: bool = False) -> CEUser | None:
    # TODO: simplify this stuff with joins
    if not use_discord_id:
        user_json = supabase.table('users').select().eq('ce_id', ce_id).execute().data
    else:
        user_json = supabase.table('users').select().eq('discord_id', ce_id).execute().data
    if len(user_json) == 0: return None
    if use_discord_id: ce_id = user_json['ce_id'] 

    userGames_json = supabase.table('userGames').select().eq('user_ce_id', ce_id).execute().data
    userObjectives_json = supabase.table('userObjectives').select().eq('user_ce_id', ce_id).execute().data
    userobjectives_list = [o['objective_ce_id'] for o in userObjectives_json]
    objectives_json = supabase.table('objectives').select().in_('ce_id', userobjectives_list).execute().data

    rolls_json = supabase.table('rolls').select().or_(f"user1_ce_id.eq.{ce_id},user2_ce_id.eq.{ce_id}").execute().data
    roll_ids = [item['id'] for item in rolls_json]
    
    userRollGames_json = supabase.table('rollGames').select().in_("roll_id", roll_ids).order("index").execute().data

    return __supabase_to_user(user_json, userGames_json, userObjectives_json, rolls_json, userRollGames_json, objectives)


# === SUPABASE CONVERTERS ===

def __supabase_to_game(game: dict, obj = list[dict], reqs = list[dict]) -> CEGame: 
    objectives = []
    for o in obj:
        objectives.append(__supabase_to_objective(o, [req for req in reqs if req['objective_ce_id'] == o['ce_id']]))
    return CEGame(
        ce_id=game['ce_id'],
        game_name=game['name'],
        platform=game['platform'],
        platform_id=game['platform_id'],
        category=game['category_primary'],
        last_updated=int(datetime.datetime.fromisoformat(game['updated_at_CE']).timestamp()),
        banner=game['image_header'],
        objectives=objectives
    )

def __supabase_to_objective(obj: dict, reqs: list[dict]) -> CEObjective:
    requirement = [req['data'] for req in reqs if req['requirement_type'] == 'custom']
    if len(requirement) > 1: raise Exception("More than one custom requirement found")
    requirement = None if len(requirement) == 0 else requirement[0]
    return CEObjective(
        ce_id=obj['ce_id'],
        objective_type=obj['type'],
        description=obj['description'],
        point_value=obj['points'],
        point_value_partial=obj['points_partial'],
        name=obj['name'],
        game_ce_id=obj['game_ce_id'],
        achievement_ce_ids=[req['data'] for req in reqs if req['requirement_type'] == 'achievement'],
        requirements=requirement
    )

def __supabase_to_user(user: dict, userGames: list[dict], userObjectives: list[dict],
                       rolls: list[dict], rollGames: list[dict], objectives) -> CEUser:
    _rolls = []
    for roll in rolls:
        _rolls.append(__supabase_to_roll(roll, [g for g in rollGames if g['roll_id'] == roll['id']]))
    _games = []
    for game in userGames:
        objectives = []
        for obj in userObjectives:
            
        _games.append(__supabase_to_user_game(game, [o for o in userObjectives if o['game_ce_id'] == game['ce_id']]))

    return CEUser(
        discord_id=user['discord_id'],
        ce_id=user['ce_id'],
        owned_games=_games,
        rolls=rolls,
        display_name=user['display_name'],
        avatar=user['image_avatar'],
        last_updated=user['updated_at_CE'],
        steam_id=user['steam_id']
    )

def __supabase_to_user_game(game: dict, objectives: list[dict]) -> CEUserGame:
    return CEUserGame(
        ce_id=game['game_ce_id'],
        user_objectives=[__supabase_to_user_objective(o, game['game_ce_id']) for o in objectives],
        name="missing"
    )

def __supabase_to_user_objective(objective: dict, game_ce_id: str) -> CEUserObjective:
    return CEUserObjective(
        ce_id=objective["objective_ce_id"],
        game_ce_id=game_ce_id,
        user_points=objective['user_points'],
        type="Badge",
        name="missing"
    )


def __supabase_to_roll(roll: dict, rollGames: list[dict]) -> CERoll:
    return CERoll(
        roll_name=roll['event_name'],
        init_time=roll['time_created'],
        due_time=roll['time_due'],
        completed_time=roll['time_completed'],
        user_ce_id=roll['user1_ce_id'],
        partner_ce_id=roll['user2_ce_id'],
        rerolls=roll['rerolls_remaining'],
        status=roll['status'],
        _id=roll['id'],
        games=[g['game_id'] for g in rollGames]
    )