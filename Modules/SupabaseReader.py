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

# == GETTERS ==

# GET LIST
def get_list(database: Literal['name', 'user', 'input', 'objectives']) -> list[str]:
    table = None
    if database == "name": table = "games"
    if database == "user": table = "users"
    if database == 'objectives': table = 'objectives'
    if table is None: raise Exception(f"Invalid get_list argument! argument: {database}")

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
    user_json = user_json[0]
    if use_discord_id: ce_id = user_json['ce_id'] 

    userGames_json = supabase.table('userGames').select().eq('user_ce_id', ce_id).execute().data
    userObjectives_json = supabase.table('userObjectives').select().eq('user_ce_id', ce_id).execute().data
    userobjectives_list = [o['objective_ce_id'] for o in userObjectives_json]
    objectives_json = supabase.table('objectives').select().in_('ce_id', userobjectives_list).execute().data

    rolls_json = supabase.table('rolls').select().or_(f"user1_ce_id.eq.{ce_id},user2_ce_id.eq.{ce_id}").execute().data
    roll_ids = [item['id'] for item in rolls_json]
    
    userRollGames_json = supabase.table('rollGames').select().in_("roll_id", roll_ids).order("index").execute().data

    return __supabase_to_user(user_json, userGames_json, userObjectives_json, rolls_json, userRollGames_json, objectives_json)

# DATABASE NAME
def get_database_name() -> list[CEGame]:
    response_games = supabase.table('games').select().execute().data
    response_objectives = supabase.table('objectives').select().execute().data
    response_requirements = supabase.table('objectiveRequirements').select().execute().data

    _games = []
    for game in response_games:
        objectives = [o for o in response_objectives if o['game_ce_id'] == game['ce_id']]
        ids_objectives = [o['ce_id'] for o in objectives]
        requirements = [r for r in response_requirements if r['objective_ce_id'] in ids_objectives]
        _games.append(__supabase_to_game(game, objectives, requirements))
    
    return _games

# DATABASE USER
def get_database_user() -> list[CEUser]:
    response_user = supabase.table('users').select().execute().data
    response_ugames = supabase.table('userGames').select().execute().data
    response_uobjectives = supabase.table('userObjectives').select().execute().data

    response_rolls = supabase.table('rolls').select().execute().data
    response_rgames = supabase.table('rollGames').select().execute().data

    response_objectives = supabase.table('objectives').select().execute().data

    _users = []
    for user in response_user:
        ugames = [g for g in response_ugames if g['user_ce_id'] == user['ce_id']]
        uobjectives = [o for o in response_uobjectives if o['user_ce_id'] == user['ce_id']]

        rolls = [r for r in response_rolls if r['user1_ce_id'] == user['ce_id']]
        rgames = [g for g in response_rgames if g['roll_id'] in [r['id'] for r in rolls]]

        _users.append(__supabase_to_user(
            user, ugames, uobjectives, rolls, rgames, 
            [o for o in response_objectives if o['ce_id'] in [u['objective_ce_id'] for u in uobjectives]] #works?
        ))
    
    return _users

def get_roll(roll_id: str) -> CERoll:
    roll_json = supabase.table('rolls').select().eq('id', roll_id).execute().data
    if len(roll_json) == 0: return None
    roll_json = roll_json[0]
    
    rollGames_json = supabase.table('rollGames').select().eq('roll_id', roll_id).order('index').execute().data
    
    return __supabase_to_roll(roll_json, rollGames_json)

def get_all_rolls() -> list[CERoll]:
    rolls_json = supabase.table('rolls').select().execute().data
    rollGames_json = supabase.table('rollGames').select().execute().data
    
    _rolls = []
    for roll in rolls_json:
        _rolls.append(__supabase_to_roll(roll, [g for g in rollGames_json if g['roll_id'] == roll['id']]))
    
    return _rolls

def get_input(ce_id: str) -> CEInput:
    # TODO: Implement after input schema is finalized
    raise NotImplementedError

def get_database_tier() -> list[dict]:
    response = supabase.table('tier').select().execute().data
    return response

def get_curator_ids() -> list[str]:
    # Assuming curator_ids table exists with curator_id column
    response = supabase.table('curator_ids').select('curator_id').execute().data
    return [item['curator_id'] for item in response]

def get_curator_count() -> int:
    # Not currently needed, but can be implemented if required
    raise NotImplementedError

def get_last_loop() -> datetime.datetime:
    data = supabase.table('loopruns').select('ran_at').order('ran_at', desc=True).limit(1).execute().data

    return datetime.datetime.fromisoformat(data['ran_at'])



# === DUMPERS ===
def dump_game(game: CEGame):
    game_data = {
        'ce_id': game.ce_id,
        'name': game.game_name,
        'platform': game.platform,
        'platform_id': game.platform_id,
        'category_primary': game.category,
        'image_header': game.banner,
        'image_icon': '',  # TODO: populate if available
        'updated_at_CE': game.last_updated.isoformat() if isinstance(game.last_updated, datetime.datetime) else game.last_updated
    }
    supabase.table('games').upsert(game_data).execute()
    
    for objective in game.objectives:
        dump_objective(objective)

def dump_user(user: CEUser):
    user_data = {
        'ce_id': user.ce_id,
        'discord_id': user.discord_id,
        'display_name': user.display_name,
        'image_avatar': user.avatar,
        'steam_id': user.steam_id,
        'created_at_CE': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'updated_at_CE': user.last_updated if isinstance(user.last_updated, str) else (user.last_updated.isoformat() if hasattr(user.last_updated, 'isoformat') else datetime.datetime.now(datetime.timezone.utc).isoformat())
    }
    supabase.table('users').upsert(user_data).execute()
    
    for game in user.owned_games:
        game_data = {
            'user_ce_id': user.ce_id,
            'game_ce_id': game.ce_id,
            'updated_at_CE': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        supabase.table('userGames').upsert(game_data).execute()
        
        for objective in game.user_objectives:
            obj_data = {
                'user_ce_id': user.ce_id,
                'objective_ce_id': objective.ce_id,
                'user_points': objective.user_points,
                'updated_at_CE': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            supabase.table('userObjectives').upsert(obj_data).execute()
    
    for roll in user.rolls:
        dump_roll(roll)

def dump_roll(roll: CERoll):
    roll_data = {
        'id': roll._id,
        'event_name': roll.roll_name,
        'user1_ce_id': roll.user_ce_id,
        'user2_ce_id': roll.partner_ce_id,
        'time_created': roll.init_time if isinstance(roll.init_time, str) else roll.init_time.isoformat() if hasattr(roll.init_time, 'isoformat') else str(roll.init_time),
        'time_due': roll.due_time if isinstance(roll.due_time, str) else roll.due_time.isoformat() if hasattr(roll.due_time, 'isoformat') else str(roll.due_time),
        'time_completed': roll.completed_time if isinstance(roll.completed_time, str) else (roll.completed_time.isoformat() if (roll.completed_time and hasattr(roll.completed_time, 'isoformat')) else None),
        'is_lucky': False,  # TODO: determine from roll data
        'chosen_tier': None,  # TODO: populate if available
        'status': roll.status,
        'rerolls_remaining': roll.rerolls,
        'rerolls_used': 0,  # TODO: calculate or track
        'winner': None  # TODO: determine on completion
    }
    supabase.table('rolls').upsert(roll_data).execute()
    
    for idx, game_id in enumerate(roll.games):
        game_data = {
            'roll_id': roll._id,
            'game_id': game_id,
            'index': idx,
            'rolled_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        supabase.table('rollGames').upsert(game_data).execute()

def dump_input(input: CEInput):
    # TODO: Implement after input schema is finalized
    raise NotImplementedError

def dump_curator_ids(ids: list[str]):
    for curator_id in ids:
        supabase.table('curator_ids').upsert({'curator_id': curator_id}).execute()

def dump_curator_count(cc: int):
    # Not currently needed
    raise NotImplementedError

def dump_database_tier(database_tier: list[dict]):
    for tier_record in database_tier:
        supabase.table('tier').upsert(tier_record).execute()

def dump_loop():
    supabase.table('loopruns').insert({'ran_at', datetime.datetime.now(datetime.timezone.utc).isoformat()})
    return 

# === SUPABASE DELETERS ===
def delete_game(ce_id: str):
    # Delete objectives first (foreign key constraint)
    objectives = supabase.table('objectives').select('ce_id').eq('game_ce_id', ce_id).execute().data
    for obj in objectives:
        supabase.table('objectiveRequirements').delete().eq('objective_ce_id', obj['ce_id']).execute()
    supabase.table('objectives').delete().eq('game_ce_id', ce_id).execute()
    
    # Delete game
    supabase.table('games').delete().eq('ce_id', ce_id).execute()

def delete_user(ce_id: str):
    # Delete user games and objectives
    supabase.table('userGames').delete().eq('user_ce_id', ce_id).execute()
    supabase.table('userObjectives').delete().eq('user_ce_id', ce_id).execute()
    
    # Delete rolls and associated roll games
    rolls = supabase.table('rolls').select('id').or_(f"user1_ce_id.eq.{ce_id},user2_ce_id.eq.{ce_id}").execute().data
    for roll in rolls:
        supabase.table('rollGames').delete().eq('roll_id', roll['id']).execute()
    supabase.table('rolls').delete().or_(f"user1_ce_id.eq.{ce_id},user2_ce_id.eq.{ce_id}").execute()
    
    # Delete user
    supabase.table('users').delete().eq('ce_id', ce_id).execute()

def delete_roll(roll_id: str):
    # Delete roll games first
    supabase.table('rollGames').delete().eq('roll_id', roll_id).execute()
    
    # Delete roll
    supabase.table('rolls').delete().eq('id', roll_id).execute()

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
        last_updated=updated_dt,
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
                       rolls: list[dict], rollGames: list[dict], objectives: list[dict]) -> CEUser:
    _rolls = []
    for roll in rolls:
        _rolls.append(__supabase_to_roll(roll, [g for g in rollGames if g['roll_id'] == roll['id']]))
    
    # TODO: optimize this please
    mapping: dict[str, list[dict]] = {}
    for game in userGames:
        mapping[game['game_ce_id']] = []
    for obj_u in userObjectives:
        found_objective: dict = None
        for obj in objectives:
            if obj['ce_id'] == obj_u['objective_ce_id'] :
                found_objective = obj
                break
        if found_objective is None: 
            print(f"No found objective for {obj_u}.")
            continue

        if found_objective['game_ce_id'] not in mapping:
            mapping[found_objective['game_ce_id']] = [obj_u]
            continue
        mapping[found_objective['game_ce_id']].append(obj_u)

    
    _games = []
    for game in userGames:
        _games.append(__supabase_to_user_game(game, mapping[game['game_ce_id']]))

    return CEUser(
        discord_id=user['discord_id'],
        ce_id=user['ce_id'],
        owned_games=_games,
        rolls=_rolls,
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

def __supabase_to_roll(roll: dict, rollGames: list[dict]) -> CERoll:
    return CERoll(
        roll_name=roll.get('event_name', ''),
        init_time=roll.get('time_created'),
        due_time=roll.get('time_due'),
        completed_time=roll.get('time_completed'),
        user_ce_id=roll.get('user1_ce_id'),
        partner_ce_id=roll.get('user2_ce_id'),
        rerolls=roll.get('rerolls_remaining', 0),
        status=roll.get('status', 'pending'),
        _id=roll.get('id'),
        games=[g['game_id'] for g in rollGames] if rollGames else []
    )

def dump_objective(objective: CEObjective):
    obj_data = {
        'ce_id': objective.ce_id,
        'game_ce_id': objective.game_ce_id,
        'type': objective.objective_type,
        'name': objective.name,
        'description': objective.description,
        'points': objective.point_value,
        'points_partial': objective.point_value_partial,
        'updated_at_CE': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    supabase.table('objectives').upsert(obj_data).execute()
    
    # Dump achievement requirements
    if objective.achievement_ce_ids:
        for achievement_id in objective.achievement_ce_ids:
            req_data = {
                'objective_ce_id': objective.ce_id,
                'requirement_type': 'achievement',
                'data': achievement_id,
                'updated_at_CE': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            supabase.table('objectiveRequirements').upsert(req_data).execute()
    
    # Dump custom requirement if it exists
    if objective.requirements:
        req_data = {
            'objective_ce_id': objective.ce_id,
            'requirement_type': 'custom',
            'data': objective.requirements,
            'updated_at_CE': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        supabase.table('objectiveRequirements').upsert(req_data).execute()