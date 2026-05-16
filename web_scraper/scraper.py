"""
THIS FILE SHOULD BE RUN IN A DIFFERENT PROCESS
"""

import sys
import os

# Add parent directory to path for direct script execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discord.ext import tasks
import asyncio
import datetime
import json
import time, datetime
import typing
import discord
import requests
from Classes.CE_Game import CEGame, CEAPIGame
from Classes.CE_Roll import CERoll
from Classes.CE_User import CEUser, CEAPIUser
from Classes.CE_User_Game import CEUserGame
from Classes.OtherClasses import UPDATEMESSAGE_LOCATIONS
from Modules import CEAPIReader, SupabaseReader, http_session, hm

SAVEDATA = True
DEBUG = True
SKIPUPDATES = False # doesn't skip roll updates

""" SCRAPER CLASSES """
class UpdateMessageForScraperProcess():
    is_embed: bool
    location: UPDATEMESSAGE_LOCATIONS

    text: str

    title: str
    description: str
    image: str
    url: str
    color: int

    def __init__(self):
        self.is_embed = False
        self.location = None
        self.text = ""
        self.title = ""
        self.description = ""
        self.image = ""
        self.url = ""
        self.color = 0

    def print(self, full=False):
        string = ""
        string += f"update ({'embed' if self.is_embed else 'text'}): "
        if self.is_embed:
            string += f"{repr(self.title)} ----- {repr(self.description)}\n"
        else:
            string += f"{repr(self.text)}\n"
        
        if full: print(string)
        else: print(string[0:100])

""" TOP LEVEL FUNCTION """

utc = datetime.timezone.utc
times = [
  datetime.time(hour=0, minute=0, tzinfo=utc),
  datetime.time(hour=0, minute=30, tzinfo=utc),
  datetime.time(hour=1, minute=0, tzinfo=utc),
  datetime.time(hour=1, minute=30, tzinfo=utc),
  datetime.time(hour=2, minute=0, tzinfo=utc),
  datetime.time(hour=2, minute=30, tzinfo=utc),
  datetime.time(hour=3, minute=0, tzinfo=utc),
  datetime.time(hour=3, minute=30, tzinfo=utc),
  datetime.time(hour=4, minute=0, tzinfo=utc),
  datetime.time(hour=4, minute=30, tzinfo=utc),
  datetime.time(hour=5, minute=0, tzinfo=utc),
  datetime.time(hour=5, minute=30, tzinfo=utc),
  datetime.time(hour=6, minute=0, tzinfo=utc),
  datetime.time(hour=6, minute=30, tzinfo=utc),
  datetime.time(hour=7, minute=0, tzinfo=utc),
  datetime.time(hour=7, minute=30, tzinfo=utc),
  datetime.time(hour=8, minute=0, tzinfo=utc),
  datetime.time(hour=8, minute=30, tzinfo=utc),
  datetime.time(hour=9, minute=0, tzinfo=utc),
  datetime.time(hour=9, minute=30, tzinfo=utc),
  datetime.time(hour=10, minute=0, tzinfo=utc),
  datetime.time(hour=10, minute=30, tzinfo=utc),
  datetime.time(hour=11, minute=0, tzinfo=utc),
  datetime.time(hour=11, minute=30, tzinfo=utc),
  datetime.time(hour=12, minute=0, tzinfo=utc),
  datetime.time(hour=12, minute=30, tzinfo=utc),
  datetime.time(hour=13, minute=0, tzinfo=utc),
  datetime.time(hour=13, minute=30, tzinfo=utc),
  datetime.time(hour=14, minute=0, tzinfo=utc),
  datetime.time(hour=14, minute=30, tzinfo=utc),
  datetime.time(hour=15, minute=0, tzinfo=utc),
  datetime.time(hour=15, minute=30, tzinfo=utc),
  datetime.time(hour=16, minute=0, tzinfo=utc),
  datetime.time(hour=16, minute=30, tzinfo=utc),
  datetime.time(hour=17, minute=0, tzinfo=utc),
  datetime.time(hour=17, minute=30, tzinfo=utc),
  datetime.time(hour=18, minute=0, tzinfo=utc),
  datetime.time(hour=18, minute=30, tzinfo=utc),
  datetime.time(hour=19, minute=0, tzinfo=utc),
  datetime.time(hour=19, minute=30, tzinfo=utc),
  datetime.time(hour=20, minute=0, tzinfo=utc),
  datetime.time(hour=20, minute=30, tzinfo=utc),
  datetime.time(hour=21, minute=0, tzinfo=utc),
  datetime.time(hour=21, minute=30, tzinfo=utc),
  datetime.time(hour=22, minute=0, tzinfo=utc),
  datetime.time(hour=22, minute=30, tzinfo=utc),
  datetime.time(hour=23, minute=0, tzinfo=utc),
  datetime.time(hour=23, minute=30, tzinfo=utc),
]

@tasks.loop(time=times)
async def process_loop(client: discord.Client = None):
    if client is None:
        print("HEY NO CLIENT WAS GIVEN TO PROCESS_LOOP()!!")    
    print("process_loop() invoked.")

    assistant_log = client.get_channel(hm.id_num("privatelog"))

    if assistant_log is not None:
        await assistant_log.send(
            f"🔄 Scraper loop started at {hm.get_datetime('now')}"
        )

    if DEBUG: print(f"FLAGS: {SAVEDATA=}, {DEBUG=}, {SKIPUPDATES=}")
    time_current = datetime.datetime.now(datetime.timezone.utc)

    updates: list[UpdateMessageForScraperProcess] = []

    # FLAGS
    JUSTGAMES = False
    SENDUPDATES = True

    # Step 1: Update Games
    _updates, games_new, removed_games, removed_objectives = await update_games()
    updates.extend(_updates)

    if DEBUG: 
        print(f"{len(updates)=} (games only!)")
        for update in updates:
            update.print(full=True)

    # Step 2: Update Users
    #  -- now to do this we have to generate databasename_old and databasename_new
    #  -- generating old is easy, that's just what's in the supabase. 
    #  -- but the new has updates and removals and additions.
    # TODO
    # fix this is mad inefficient

    # step 2a) generate name_old and name_new
    database_name_old = SupabaseReader.get_games_bulk(SupabaseReader.get_list('name'))
    database_name_new = database_name_old.copy()

    # propogate all removals
    for entry in database_name_old:
        if entry.ce_id in removed_games:
            database_name_new.remove(entry)

    # propogate all updates
    for _game_new in games_new:
        replaced = False
        for i, entry in enumerate(database_name_new.copy()): # necessary bc of removals
            if entry.ce_id == _game_new.ce_id:
                database_name_new[i] = _game_new
                replaced = True
                break
        # propogate additions
        if not replaced:
            database_name_new.append(_game_new)
    
    print(f"{len(database_name_old)=}")
    print(f"{len(database_name_new)=}")

    if DEBUG: print("UPDATE USERS: begin")
    _updates, users_new, removed_users, rolls_updated = await update_users(
        database_name_old,
        database_name_new
    )
    updates.extend(_updates)
    if DEBUG: print("UPDATE USERS: complete")

    # Step 3: Check curator
    check_curator_steam()

    # Step 4: write all of our stuff
    if SAVEDATA:
        if DEBUG: print('saving data')

        if DEBUG: print(f"{len(games_new)=}")
        if DEBUG: print(f"BULK GAMES")
        SupabaseReader.bulk_dump_games(games_new)
        
        if DEBUG: print(f"{len(removed_games)=}")
        for i, _game_id in enumerate(removed_games):
            if DEBUG and i % 5 == 0: print(i)
            SupabaseReader.delete_game(_game_id)

        if DEBUG: print(f"{len(removed_objectives)=}")
        SupabaseReader.delete_objectives_many(removed_objectives)
        
        if DEBUG: print(f"{len(users_new)=}")
        if DEBUG: print(f"BULK USERS")
        SupabaseReader.bulk_dump_users(users_new)

        if DEBUG: print(f"{len(removed_users)=}")
        for i, _user_id in enumerate(removed_users):
            if DEBUG and i % 5 == 0: print(i)
            SupabaseReader.delete_user(_user_id)

        
        if DEBUG: print(f"{len(rolls_updated)=}")
        if DEBUG: print("BULK ROLLS")
        SupabaseReader.bulk_dump_rolls(rolls_updated)

    # Send updates!
    # TODO upload these to the database in a future update
    for update in updates:
        if not isinstance(update, UpdateMessageForScraperProcess):
            print(update)
            print(type(update))
        if SENDUPDATES:
            # TODO future update
            # this is gonna back us up a bit
            channel = client.get_channel(hm.id_num(update.location))

        if not update.is_embed:
            if SENDUPDATES: 
                if channel is None:
                    print(update.location)
                await channel.send(update.text, allowed_mentions=discord.AllowedMentions.none())
            else: update.print(full=True)
            continue
        
        embed = discord.Embed()
        embed.color = update.color
        embed.title = update.title
        embed.description = update.description
        # TODO removal image
        if update.image is not None and update.image != "":
            embed.set_image(url=update.image)
        embed.url = update.url

        # regular stuff
        embed.color = 0x000000
        embed.timestamp = datetime.datetime.now()
        embed.set_author(name='Challenge Enthusiasts', icon_url=hm.CE_MOUNTAIN_ICON)
        embed.set_footer(text='CE Assistant', icon_url=hm.FINAL_CE_ICON)

        if SENDUPDATES: 
            if channel is None:
                print(update.location)
            await channel.send(embed=embed)
        else: update.print(full=True)
    
    if DEBUG: print(f"process_loop() complete at {hm.get_datetime('now')}")

    if assistant_log is not None:
        await assistant_log.send(
            f"✅ Scraper loop finished at {hm.get_datetime('now')}"
        )

    if SAVEDATA: SupabaseReader.dump_loop(time_current)


""" MEDIUM LEVEL FUNCTIONS """

async def update_games() -> tuple[list[UpdateMessageForScraperProcess], list[CEAPIGame], list[str], list[str]]:
    """
    Updates all games. This version began April 9, 2026 for Supabase.
    Returns
    ---
    - updates: a list of updates to be sent
    - games_new: the games that have been updated
    - removed_games: a list of ceids of games that have been removed.
    """

    # Step 0: Determine the last time the loop ran.
    last_run = SupabaseReader.get_last_loop()
    if DEBUG: print(f"GAMES: {last_run=}")
    updates: list[UpdateMessageForScraperProcess] = []
    objectives_removed: list[str] = []

    # Step 1: Go through /api/games and /api/objectives and find the list of all games that have been updated.
    # 1a) get the ids of all games that have been updated from /api/games
    session = await http_session.get_session()
    params = {"sortBy": "updatedAt", "sortOrder": "DESC"}
    async with session.get(f'https://cedb.me/api/games') as _r :
        response = await _r.json()

    print(f"GAMES: {len(response)=} (response pulled from /api/games)")
    _updated_game_ids = set()
    for game in response:
        timestamp_game = datetime.datetime.fromisoformat(game['updatedAt'])

        if timestamp_game < last_run : continue
        _updated_game_ids.add(game['id'])

    print(f"GAMES: {len(_updated_game_ids)=} (found from /api/games only)")

    # 1b) get the ids of all games that have been updated from /api/objectives
    params = {"sortBy": "updatedAt", "sortOrder": "DESC", "limit": 100, "offset": 0}
    while (1):
        async with session.get(f'https://cedb.me/api/objectives', params=params) as _r:
            _response_local = await _r.json()
            # all objectives are new
            if datetime.datetime.fromisoformat(_response_local[-1]['updatedAt']) >= last_run: 
                _updated_game_ids.update(r['gameId'] for r in _response_local)
                params['offset'] += 100
                continue
                
            # we found something wrong. go thru one by one.
            for objective in _response_local:
                if datetime.datetime.fromisoformat(objective['updatedAt']) < last_run:
                    #TODO: can we confirm sorting works?
                    break

                _updated_game_ids.add(objective['gameId'])
    
            break

    print(f"GAMES: {len(_updated_game_ids)=} (found from /api/games + /api/objectives)")
    
    # 1c) get the ids of all games that have removed objectives
    #  -- solved! folkius changed the schema so now any removed objective updates the game's updatedAt entry.
            
    # 1d) get the actual data for all those games
    games: list[CEAPIGame] = []
    if DEBUG: print(f"PULL GAMES: pulling {len(_updated_game_ids)} games from cedb.")
    for i, gameId in enumerate(_updated_game_ids):
        if DEBUG and i % 10 == 0: print(f"PULL GAMES: {i}")
        games.append(await CEAPIReader.get_game(gameId))
    if DEBUG: print("PULL GAMES: done")

    while None in games: games.remove(None)

    # Step 2: Generate updates for those by comparing with Supabase games.
    if not SKIPUPDATES:
        if DEBUG: print("GAME UPDATES: begin")
        for i, game_new in enumerate(games):
            if DEBUG and i % 10 == 0: print(f"GAME UPDATES: {i}")
            game_old = SupabaseReader.get_game(game_new.ce_id)
            _update, _or = update_one_game(game_old, game_new)
            if _update is not None:
                updates.append(_update)
            if _or is not None:
                objectives_removed.extend(_or)
        if DEBUG: print("GAME UPDATES: done")

    # Step 3: Find all removed games.
    game_list_old = set(SupabaseReader.get_list('name'))
    game_list_new = set(await CEAPIReader.get_api_games())

    game_list_removed = game_list_old.difference(game_list_new)

    # Step 4: Generate updates for those removed games.
    if not SKIPUPDATES:
        for game_removed in game_list_removed:
            _update, _or = update_one_game(SupabaseReader.get_game(game_removed), None)
            if _update is not None:
                updates.append(_update)
            if _or is not None:
                objectives_removed.extend(_or)
    
    return updates, games, game_list_removed, objectives_removed

async def update_users(games_old: list[CEGame], games_new: list[CEAPIGame]):
    """
    Updates all users. This version began April 9, 2026 for Supabase.
    """

    # Step 0: Determine the last time the loop ran.
    last_run = SupabaseReader.get_last_loop()
    updates: list[UpdateMessageForScraperProcess] = []

    # Step 1: Go through /api/userObjectives and find the list of all users that have been updated.
    #   -- or: if folkius makes /api/userGames, that should work too? plus it comes with the added benefit
    #          of marking that a user owns a game, which is important for rolls.
    _updated_user_ids: set[str] = set()

    _users_registered = SupabaseReader.get_list('user')

    # TODO once folkius makes the new endpoint with MAX(updatedAt)
    # 1a) Go through api/userGames/updatedAt (or whatever it's called) and find the last updated
    # 1b) Do the same but with userObjectives
    # NOTE maybe folkius could make a combined one....
    session = await http_session.get_session()
    async with session.get(f'http://cedb.me/api/userGames/lastUpdatedAt') as _r :
        response = await _r.json()

    for user in response:
        timestamp_user = datetime.datetime.fromisoformat(user['lastUpdatedAt'])

        if timestamp_user < last_run : break
        if user['userId'] not in _users_registered: continue

        _updated_user_ids.add(user['userId'])

    print(f"USERS: {len(_updated_user_ids)=} (found from /api/userGames/lastUpdatedAt)")

    # Step 2: Pull all of those users
    users: list[CEAPIUser] = []
    # TODO 
    # re-implement this once /api/users/query is up
    # i will step through the indexes (not the items!) in the list
    # 100 at a time,
    # for i in range(0, len(_updated_user_ids), 10):
    #     if DEBUG: print(f"posting /api/users/query for users {i} through {i+9} (of {len(_updated_user_ids)})")
    #     users.extend(await CEAPIReader.post_users_query(users[i:i+10]))
    if DEBUG: print(f'PULL USERS: begin, {len(_updated_user_ids)=}')
    for i, _user_id in enumerate(_updated_user_ids):
        if DEBUG and i % 10 == 0: print(f"PULL USERS: {i}")
        _user = await CEAPIReader.get_user(_user_id)
        if _user is not None: users.append(_user)
    if DEBUG: print('PULL USERS: done')

    # Step 3: Generate updates for these changed users by comparing with Supabase users.
    if not SKIPUPDATES:
        if DEBUG: print(f"UPDATE USERS: begin, {len(users)=}")

        # Bulk-fetch the existing users from Supabase to avoid blocking the event loop
        ce_ids = [u.ce_id for u in users]
        users_old: list = []
        batch_size = 100
        for bstart in range(0, len(ce_ids), batch_size):
            batch_ids = ce_ids[bstart:bstart+batch_size]
            if DEBUG: print(f"FETCH SUPABASE USERS: batch {bstart}..{bstart+len(batch_ids)}")
            batch_users = await asyncio.to_thread(SupabaseReader.get_users_bulk, batch_ids)
            users_old.extend(batch_users)

        users_old_map = {u.ce_id: u for u in users_old}

        for i, user_new in enumerate(users):
            if DEBUG and i % 5 == 0: print(f"UPDATE USERS: {i}")
            user_old = users_old_map.get(user_new.ce_id)
            _updates = update_one_user(user_old, user_new, games_old, games_new, update_rolls=False)
            if _updates is not None:
                updates.extend(_updates)

            if user_old is not None:
                users[i]._discord_id = user_old.discord_id

        if DEBUG: print(f"UPDATE USERS: done")

    # Step 4: Find any removed users
    # TODO future update
    user_list_removed: list[str] = []

    # Step 5: Update all the rolls
    # TODO future update
    # only pull the second user **after** you've confirmed it would potentially pass the current player's game
    SKIPROLLS = True
    rolls_updated = []
    if not SKIPROLLS:
        if DEBUG: print("pulling rolls from supabase")
        rolls = SupabaseReader.get_all_rolls()
        rolls_updated: list[CERoll] = []

        for _roll in rolls:
            if _roll.status != 'current' and _roll.status != 'pending': continue

            # first, see if we have any updated data from the user.
            # if that misses, just get them from Supabase
            user1 = hm.get_item_from_list(_roll.user_ce_id, users)
            if user1 is None: user1 = SupabaseReader.get_user(_roll.user_ce_id)

            # and now for the partner
            user2 = None
            if _roll.partner_ce_id is not None:
                print(f'looking for {_roll.partner_ce_id=}')
                user2 = hm.get_item_from_list(_roll.partner_ce_id, users)
                if user2 is None: user2 = SupabaseReader.get_user(_roll.partner_ce_id)

            # and for the games
            games: list[CEGame] = []
            for _game in _roll.games:
                game_obj = hm.get_item_from_list(_game, games_new)
                if game_obj is None: game_obj = SupabaseReader.get_game(_game)
                games.append(game_obj)

            print('updating roll -- ', end='')
            _update, _roll_updated = update_one_roll(_roll, user1, user2, games)

            if _update is not None: updates.append(_update)
            if _roll_updated is not None: rolls_updated.append(_roll_updated)

    # TODO future update
    # only return users who *actually* had something changed.
    return updates, users, user_list_removed, rolls_updated

def generate_database_tier(database_name: list[CEAPIGame]):
    # separate out games by tier and category
    database_tier: dict[str, dict[str, list[dict]]] = {}
    for tier in range(1, 8):
        database_tier[str(tier)] = {}
        for category in typing.get_args(hm.CATEGORIES):
            database_tier[str(tier)][category] = []
    
    steam_ids: list[int] = []

    for game in database_name:
        if not game.platform == 'steam':
            continue
            
        steam_ids.append(int(game.platform_id))

    # this copy is needed because when we remove the ids mid scrape it moves 
    #   the array back so a) some games get skipped and b) we may pull an empty list
    steam_ids_copy = steam_ids.copy()

    prices: dict[str, int] = {}
    hours: dict[str, int] = {}
    
    # grab all prices and hours
    for i in range(0, len(steam_ids), 100):
        print(f'scraping for prices and hours at {i=} out of {len(steam_ids_copy)}')

        # prices
        response_prices = requests.get(
            'https://store.steampowered.com/api/appdetails?',
            params = {
                'appids': str(steam_ids_copy[i:i+100])[1:-1],
                'cc': 'US',
                'filters': 'price_overview'
            }
        )

        response_prices_json: dict[str, dict] = json.loads(response_prices.text)
        if type(response_prices_json) is list:
            print(f'something went wrong. response_prices_json is being read as a list. i will now print it.')
            print(f'app_ids={str(steam_ids[i:i+100])[1:-1]}')
            print(response_prices_json)
        for key, value in response_prices_json.items():
            if not value['success']:
                steam_ids.remove(int(key))
                print(f'price failed for app id {key}')
                continue
            
            if len(value['data']) == 0:
                prices[key] = 0
                continue

            if value['data']['price_overview']['discount_percent'] == 100:
                prices[key] = 0

            else:
                prices[key] = value['data']['price_overview']['final']
        
        # hours
        response_hours = requests.get(
            'https://steamhunters.com/api/apps/?',
            params = {
                'appids': str(steam_ids_copy[i:i+100])[1:-1] # appIds=220,480,730
            }
        )

        response_hours_json: list[dict[str, int]] = json.loads(response_hours.text)
        for item in response_hours_json:
            if 'medianCompletionTime' not in item:
                steam_ids.remove(int(item["appId"]))
                print(f'medianCompletion time not listed for app id {item["appId"]}')
                continue
            hours[str(item['appId'])] = item['medianCompletionTime']

    for game in database_name:
        if not game.platform == 'steam': 
            continue #non steam game
        if game.get_tier_num() == 0:
            continue #t0
        if game.platform_id not in prices or game.platform_id not in hours:
            continue #no success from api

        database_tier[str(game.get_tier_num())][game.category].append(
            {
                'ce_id': game.ce_id,
                'name': game.game_name,
                'price': prices[game.platform_id],
                'sh_hours': hours[game.platform_id]
            }
        )

    return database_tier







""" BOTTOM LEVEL FUNCTIONS """
def update_one_game(game_old: CEGame, game_new: CEAPIGame) -> tuple[UpdateMessageForScraperProcess, list[str]]:
    # NEW GAME
    if game_old is None:
        return create_update_new_game(game_new), []
    
    # REMOVED GAME
    elif game_new is None:
        return create_update_removed_game(game_old), []
    
    return create_update_updated_game(game_old, game_new)

def update_one_user(user: CEUser, site_data: CEAPIUser, database_name_old: list[CEGame], 
                          database_name_new: list[CEAPIGame], update_rolls: bool) -> list[UpdateMessageForScraperProcess]:
    """Provides updates for one user."""

    updates: list[UpdateMessageForScraperProcess] = []
    UPDATE_ROLLS = False

    points_original = user.get_total_points()
    completed_games_original = user.get_completed_games_2(database_name_old)
    rank_original = user.get_rank()
    games_original = user.owned_games.copy()

    # update the user!
    user.owned_games = site_data.owned_games

    points_new = user.get_total_points()
    completed_games_new = user.get_completed_games_2(database_name_new)
    rank_new = user.get_rank()
    games_new = user.owned_games.copy()

    # -- CHECK ROLES --
    updates.extend(check_roles(games_original, games_new, database_name_new, user))

    # -- CHECK FOR NEWLY COMPLETED GAMES --
    updates.extend(check_newly_completed_games(completed_games_original, completed_games_new, user))
    
    # -- RANK UPDATE --
    if rank_new != rank_original and points_new > points_original:
        if not user.on_mutelist():
            update = UpdateMessageForScraperProcess()
            update.location = "userlog"
            update.is_embed = False
            update.text = (
                f"Congrats to {user.mention()} ({user.display_name}) for ranking up from Rank " +
                f"{hm.get_emoji(rank_original)} to Rank {hm.get_emoji(rank_new)}!"
            )
        else:
            update = UpdateMessageForScraperProcess()
            update.location = "privatelog"
            update.is_embed = False
            update.text = (
                f"🤫 Muted user {user.display_name_with_link()} ranked up from {rank_original} to {rank_new}."
            )
        updates.append(update)

    # -- COMPLETION COUNT UPDATE -- 
    COMPLETION_INCREMENT = 25
    if (int(len(completed_games_original) / COMPLETION_INCREMENT) 
        < int(len(completed_games_new) / COMPLETION_INCREMENT)):
        if not user.on_mutelist():
            update = UpdateMessageForScraperProcess()
            update.location = "userlog"
            update.is_embed = False
            update.text = (
                f"Amazing! {user.mention()} ({user.display_name}) has passed the milestone of " +
                f"{int(len(completed_games_new) / COMPLETION_INCREMENT) * COMPLETION_INCREMENT} completed games!"
            )
        else:
            update = UpdateMessageForScraperProcess()
            update.location = "privatelog"
            update.is_embed = False
            update.text = (
                f"🤫 Muted user {user.display_name_with_link()} has passed the milestone of" + 
                f"{int(len(completed_games_new) / COMPLETION_INCREMENT) * COMPLETION_INCREMENT}"
            )
        updates.append(update)

    # check pendings
    if update_rolls:
        for i, roll in enumerate(user.rolls[:]) :
            due_dt = roll._normalize_datetime(roll.due_time) if hasattr(roll, '_normalize_datetime') else roll.due_time
            if roll.status == "pending" and due_dt is not None and due_dt <= hm.get_datetime('now') :
                user.remove_pending(roll.roll_name)

        # check rolls
        for index, roll in enumerate(user.rolls) :
            # step 0: check multistage rolls
            # if the roll is multi stage AND its not in the final stage...
            # note: skip this if we're in the final stage because
            #       if it's in its final stage we can finish it out,
            #       this if statement just preps for the next one.
            if not roll.status == "current" : continue
            partner = None
            if roll.partner_ce_id is not None : partner = SupabaseReader.get_user(roll.partner_ce_id)
            if (roll.is_multi_stage() and not roll.in_final_stage() and 
                (roll.is_won(database_name=database_name_new, user=user, partner=partner))) :
                # if we've already hit this roll before, keep moving
                if roll.due_time == None : continue

                # add the update message
                update = UpdateMessageForScraperProcess()
                update.location = 'casino'
                update.is_embed = False
                update.text = (
                    f"{user.mention()}, you've finished your current stage in {roll.roll_name}. " +
                    f"To roll your next stage, type `/solo-roll {roll.roll_name}` in <#{hm.CASINO_ID}>."
                )

                # and kill the due time
                roll.due_time = None
                roll.set_status("waiting")
                user._rolls[index] = roll

            elif roll.is_won(database_name=database_name_new, user=user, partner=partner) :
                # add the update message
                update = UpdateMessageForScraperProcess()
                update.location = "casinolog"
                update.is_embed = False
                update.text = (
                    roll.get_win_message(database_name=database_name_new, user=user, partner=partner)
                )
                updates.append(update)

                # set the completed time to now
                roll.completed_time = hm.get_datetime('now')

                # add the object to completed rolls, and
                # remove it from current
                roll.set_status("won")
                user._rolls[index] = roll

                """
                Let's talk about why this works.
                database-user is being constantly updated. Let's say we have two players, A and B.
                Since the last update, they have completed their requirements for their co-op roll.
                Player A joined the bot first, so their update is processed first. But since Player
                B hasn't been updated yet, the roll doesn't register as "won". So, we pass through
                Player A without removing the roll. But, when we get to Player B, both players have
                updated.
                """
                if roll.is_co_op() :
                    # get the partner and their roll
                    partner = SupabaseReader.get_user(roll.partner_ce_id)
                    if partner.has_current_roll(roll.roll_name) :
                        partner_roll = partner.get_current_roll(roll.roll_name)

                        # update their current roll
                        if roll.is_pvp() and roll.status == "won" :
                            partner.fail_current_roll(partner_roll.roll_name)
                        elif roll.is_pvp() and roll.status == "failed" :
                            partner.win_current_roll(partner_roll.roll_name)
                        else :
                            partner.win_current_roll(partner_roll.roll_name)

                        # and append it to partners
                        SupabaseReader.dump_user(partner)

            
            elif roll.is_expired() :
                # add the update message
                update = UpdateMessageForScraperProcess()
                update.location = "casino"
                update.is_embed = False
                update.text = (
                    roll.get_fail_message(database_name=database_name_new, user=user, partner=partner)
                )
                
                # remove this roll from current rolls
                user.fail_current_roll(roll.roll_name)
                if roll.is_co_op() :
                    partner = SupabaseReader.get_user(roll.partner_ce_id)
                    if partner.has_current_roll(roll.roll_name) :
                        partner.fail_current_roll(roll.roll_name)
                        SupabaseReader.dump_user(user)
    
    user.set_last_updated(hm.get_datetime('now'))

    return updates

def update_one_roll(roll: CERoll, user1: CEUser, user2: CEUser | None, 
                    games: list[CEGame]) -> tuple[UpdateMessageForScraperProcess, CERoll]:
    # Step 1: Filter out the rolls that don't matter.
    """Weird statuses
    waiting = this is a multi stage roll, waiting on user to prompt the next part
    pending = this is a roll that requires some input so we set this to the same timeout as the first message
    """

    # ERROR CHECKING: sending in a bad roll
    status = roll.status2()
    if status not in ["current", "pending"]: return None, None

    # ERROR CHECKING: handle the problem where a roll's game gets removed from the site
    update = UpdateMessageForScraperProcess()
    if None in games:
        update.is_embed = False
        _user2_text = ""
        if user2 is not None:
            _user2_text = f"and {user2.mention()}"

        update.text = (f"{user1.mention()} {_user2_text}, you rolled a game that has now been removed" +
                       " from the site. This will not impact your casino score. Apologies for the inconvenience." +
                       " Please feel free to reach out to Andy for more information or reroll (no cooldown has" +
                       " been applied).")
        update.location = "casino"
        
        roll.set_status("removed")
        return update, roll
        



    # pendings
    if roll.status2() == "pending":
        due_dt = roll._normalize_datetime(roll.due_time) if hasattr(roll, '_normalize_datetime') else roll.due_time
        if due_dt is not None and due_dt <= hm.get_datetime('now'):
            if SAVEDATA: SupabaseReader.delete_roll(roll._id)
            update.is_embed = False
            update.location = 'casino'
            _user2_text = ""
            if user2 is not None:
                _user2_text = f"and {user2.mention()}"
            update.text = (f"{user1.mention()} {_user2_text}, you may now re-initiate {roll.roll_name}. " +
                           "Any button presses to the previous message will do nothing.")
            return update, None
        return []
    
    update = UpdateMessageForScraperProcess()
    won = roll.is_won(games, user1, user2)
    
    # Case 1: The roll is multi-stage, and we're not on the last stage.
    if roll.is_multi_stage() and not roll.in_final_stage() and won:
        update.location = 'casino'
        update.is_embed = False
        update.text = (
            f"{user1.mention()}, you've finished the current stage in {roll.roll_name}. " +
            f"To roll your next stage, type /solo-roll {roll.roll_name} in <#{hm.CASINO_ID}> at any time."
        )

        roll.set_status('waiting')
        roll.due_time = None
        return update, roll

    # Case 2: The roll is won.
    #  -- case 2a) the roll is single-player
    #  -- case 2b) the roll is co-op
    #  -- case 2c) the roll is pvp (currently none... hallelujah.)

    if won:
        update.location = "casinolog"
        update.is_embed = False
        update.text = roll.get_win_message(games, user1, user2)
        roll.completed_time = hm.get_datetime('now')
        roll.set_status('won')

        # Case 2A (singleplayer) and 2B (co-op)
        if not roll.is_pvp(): return update, roll

        # Case 2C (pvp)
        # -- not dealing with this.
        raise NotImplementedError

    if roll.is_expired():
        update.location = 'casino'
        update.is_embed = False
        update.text = roll.get_fail_message(games, user1, user2)

        return update, roll
    
    # If we get here, then none of the following happened:
    #  -- roll was pending
    #  -- roll was current and won
    #  -- roll was current and expired
    return None, None

def check_curator_steam(): 
    """Checks steam for the last 10 curated games."""

    # TODO: fill in this function
    return





""" BASEMENT LEVEL FUNCTIONS """

def create_update_new_game(game_new: CEAPIGame) -> UpdateMessageForScraperProcess:
    """Creates the `UpdateMessageForScraperProcess` for a new game."""
    update = UpdateMessageForScraperProcess()
    update.is_embed = True
    update.title = f"__ {game_new.game_name} __ added to the site:"
    update.color = 0x48b474
    update.description = f"\n- {game_new.get_emojis()}"
    update.url = f"https://cedb.me/game/{game_new.ce_id}"
    update.location = 'gameadditions'

    if len(game_new.get_primary_objectives()) != 0:
        num_pos = len(game_new.get_primary_objectives())
        update.description += (
            f"\n- {num_pos} Primary Objective{'s' if num_pos != 1 else ''} " +
            f"worth {game_new.get_po_points()} {hm.get_emoji('Points')}"
        )
    if len(game_new.get_uncleared_objectives()) != 0 :
        num_uncleareds = len(game_new.get_uncleared_objectives())
        update.description += (f"\n- {num_uncleareds} Uncleared Objective{'s' if num_uncleareds != 1 else ''}")
    if len(game_new.get_community_objectives()) != 0 :
        num_cos = len(game_new.get_community_objectives())
        update.description += (f"\n- {num_cos} Community Objective{'s' if num_cos != 1 else ''}")
    if len(game_new.get_secondary_objectives()) != 0 :
        num_sos = len(game_new.get_secondary_objectives())
        update.description += (
                f"\n- {num_sos} Secondary Objective{'s' if num_sos != 1 else ''}" +
                f"worth {game_new.get_so_points()} {hm.get_emoji('Points')}"
            )
    if len(game_new.get_badge_objectives()) != 0 :
        num_bos = len(game_new.get_badge_objectives())
        update.description += f"\n- {num_bos} Badge Objective{'s' if num_bos != 1 else ''}"
    
    update.image = game_new.header

    return update

def create_update_removed_game(game_old: CEGame) -> UpdateMessageForScraperProcess:
    """Creates the `UpdateMessageForScraperProcess` for a removed game."""
    update = UpdateMessageForScraperProcess()
    update.is_embed = True
    update.title = f"__ {game_old.game_name} __ removed from the site"
    update.color = 0xce4e2c
    update.image = "removal"
    update.location = 'gameadditions'

    return update

def create_update_updated_game(game_old: CEGame, game_new: CEAPIGame) -> tuple[UpdateMessageForScraperProcess, list[str]]:
    """Creates the `UpdateMessageForScraperProcess` for an updated game."""
    update = UpdateMessageForScraperProcess()
    update.is_embed = True
    update.title = f"__ {game_new.game_name} __ updated on the site:"
    update.color = 0xefd839
    update.description = ""
    update.url = f"https://cedb.me/game/{game_new.ce_id}"
    update.location = 'gameadditions'
    update.image = game_new.header

    # POINT/TIER CHANGE
    if game_old.get_total_points() == game_new.get_total_points():
        update.description += "\n- Total points unchanged!"
    else:
        update.description += (
            f"\n- {game_old.get_total_points()} {hm.get_emoji('Points')} " +                            # 75 points
            f"{hm.get_emoji('Arrow')} " +                                                               # -->
            f"{game_new.get_total_points()} {hm.get_emoji('Points')}"                                   # 220 points
        )
        if game_old.get_tier() != game_new.get_tier() :
            update.description += (
                f" ({game_old.get_tier_emoji()} {hm.get_emoji('Arrow')} {game_new.get_tier_emoji()})"
            )

    # CATEGORY CHANGE
    if game_old.category != game_new.category:
        update.description += (
            f"\n- {game_old.get_category_emoji()} ({game_old.category})" +
            f"{hm.get_emoji('Arrow')}" +
            f"{game_new.get_category_emoji()} ({game_new.category})"
        )
    
    # objective changes...
    old_objective_ce_ids = [old_objective.ce_id for old_objective in game_old.all_objectives]
    for new_objective in game_new.all_objectives :

        # if objective is new
        if new_objective.ce_id not in old_objective_ce_ids :
            "Objective is new!"
            update.description += (
                f"\n- New {new_objective.type} Objective '**{new_objective.name}**' added:"
            )
            if new_objective.type == "Primary" or new_objective.type == "Secondary" :
                update.description += f"\n  - {new_objective.point_value} {hm.get_emoji('Points')}"
            update.description += f"\n  - {new_objective.description}"
            continue
        
        # update objective tracker and get the old objective
        old_objective_ce_ids.remove(new_objective.ce_id)
        old_objective = hm.get_item_from_list(new_objective.ce_id, game_old.all_objectives)
        
        # if objective is updated
        if not new_objective.equals(old_objective) :
            "Objective is updated."
            # if the points have changed
            if old_objective.is_uncleared() and not new_objective.is_uncleared() :
                update.description += (f"\n- '**{new_objective.name}**' cleared, valued at {new_objective.point_value} {hm.get_emoji('Points')}")
            elif old_objective.point_value > new_objective.point_value :
                update.description += (f"\n- '**{new_objective.name}**' decreased from {old_objective.point_value} {hm.get_emoji('Points')} " + 
                                    f"to {new_objective.point_value} {hm.get_emoji('Points')}")
            elif old_objective.point_value < new_objective.point_value :
                update.description += (f"\n- '**{new_objective.name}**' increased from {old_objective.point_value} {hm.get_emoji('Points')} " + 
                                    f"to {new_objective.point_value} {hm.get_emoji('Points')}")
            else :
                update.description += (f"\n- {new_objective.get_type_short()} '**{new_objective.name}**' updated")
            
            # if the type has changed
            if old_objective.type != new_objective.type :
                update.description += (f"\n  - Type changed from {old_objective.type} to {new_objective.type}")

            # if the description was updated
            if old_objective.description != new_objective.description :
                update.description += "\n  - Description updated"
            
            # if the requirements were updated
            if old_objective.requirements != new_objective.requirements :
                update.description += "\n  - Requirements updated"
        
            # if the achievements were updated
            # TODO: this can be made more specific in 2.1
            if (not hm.achievements_are_equal(old_objective.achievement_ce_ids, new_objective.achievement_ce_ids)) :
                update.description += "\n  - Achievements updated"

            # if the partial points were updated
            if old_objective.partial_points != new_objective.partial_points :
                update.description += (f"\n  - Partial points changed from {old_objective.partial_points} {hm.get_emoji('Points')} " +
                                        f"to {new_objective.partial_points} {hm.get_emoji('Points')}")
                
            # if the name was changed
            if old_objective.name != new_objective.name :

                # if the objective was cleared, we don't need to make a whole note about the name change unless the name was changed
                if (old_objective.is_uncleared() and not new_objective.is_uncleared() and
                    (old_objective.uncleared_name() != new_objective.name)) :
                        update.description += f"\n  - Name changed from '{old_objective.name}' to '{new_objective.name}'"
                elif not old_objective.is_uncleared() or new_objective.is_uncleared() :
                    update.description += (f"\n  - Name changed from '{old_objective.name}' to '{new_objective.name}'")
    
    for old_objective_ce_id in old_objective_ce_ids :
        old_objective = game_old.get_objective(old_objective_ce_id)
        update.description += (f"\n- {old_objective.get_type_short()} {old_objective.name} removed.")

    # CHECK FOR GHOST UPDATE
    # all objectives have been reflected
    description_test = update.description
    description_test = description_test.replace('\n','').replace('\t','').replace('- Total points unchanged!','')

    # if there wasn't any real change, ignore this embed
    if description_test == "" : return None, None

    return update, old_objective_ce_ids

def check_roles(games_old: list[CEUserGame], games_new: list[CEUserGame],
                         database_name: list[CEGame], user: CEUser) -> list[UpdateMessageForScraperProcess]:
    "Gets updates based on roles the user has achieved."
    
    # POINT CHANGES
    old_tiers = [0, 0, 0, 0, 0, 0, 0]
    old_categories = [0, 0, 0, 0, 0, 0] #action arcade bh fps platformer strategy
    new_tiers = [0, 0, 0, 0, 0, 0, 0]
    new_categories = [0, 0, 0, 0, 0, 0]
    updates: list[UpdateMessageForScraperProcess] = []

    for game_old in games_old:
        points = game_old.get_user_points()
        game_database = hm.get_item_from_list(game_old.ce_id, database_name)

        if game_database == None: continue

        # if the game is completed
        if game_old.get_user_points() == game_database.get_total_points():
            old_tiers[game_database.get_tier_num() - 1] += points
            old_categories[game_database.category_num() - 1] += points
    
    for game_new in games_new:
        points = game_new.get_user_points()
        game_database = hm.get_item_from_list(game_new.ce_id, database_name)
        
        if game_database == None: continue

        # if the game is completed
        if game_new.get_user_points() == game_database.get_total_points():
            new_tiers[game_database.get_tier_num() - 1] += points
            new_categories[game_database.category_num() - 1] += points
    
    # CATEGORIES
    CATEGORY_ROLE_NAMES = ["Master", "Grandmaster (Red Role)", "Grandmaster (Black Role)"]
    for index_point, point_value in enumerate([500, 1000, 2000]):
        for index_category, category in enumerate(list(typing.get_args(hm.CATEGORIES))):
            if old_categories[index_category] < point_value and new_categories[index_category] >= point_value:
                update = UpdateMessageForScraperProcess()
                update.is_embed = False
                update.text = (
                    f"Congratulations to <@{user.discord_id}>! " +
                    f"You have unlocked {category} {CATEGORY_ROLE_NAMES[index_point]} ({point_value}+ points)"
                )
                update.location = "userlog"
                updates.append(update)

    # TIERS
    for i in range(1, 5):
        if old_tiers[i - 1] < (i * 500) and new_tiers[i - 1] >= (i * 500):
            update = UpdateMessageForScraperProcess()
            update.is_embed = False
            update.text = (
                f"Congratulations to <@{user.discord_id}>! " +
                f"You have unlocked Tier {i} Enthusiast ({i * 500} points in Tier {i} completed games)."
            )
            update.location = "userlog"
            updates.append(update)
    
    return updates

def check_newly_completed_games(completed_games_old: list[CEGame], completed_games_new: list[CEGame],
                                user: CEUser) -> list[UpdateMessageForScraperProcess]:
    updates = []

    for game in completed_games_new:
        TIER_MINIMUM = 4

        if game.get_tier_num() < TIER_MINIMUM: continue

        # check if the game's been completed before
        game_old = hm.get_item_from_list(game.ce_id, completed_games_old)
        if game_old != None: continue

        update = UpdateMessageForScraperProcess()
        
        # check mutelist
        if user.on_mutelist():
            update.location = "privatelog"
            update.text = f"⚪ Muted user {user.display_name_with_link()} update:\n"
        else:
            update.location = "userlog"
            update.text = ""

        update.is_embed = False
        update.text += (
            f"Wow {user.mention()} ({user.display_name})! You've completed {game.game_name}, " +
            f"a {game.get_tier_emoji()} worth {game.get_total_points()} points {hm.get_emoji('Points')}"
        )
        updates.append(update)

        if len(updates) != 0:
            print(f"{user.ce_id=}, {len(completed_games_old)=}, {len(completed_games_new)=}")

    return updates

def check_rank(rank_old: str, rank_new: str, points_old: int, 
               points_new: int, user: CEUser) -> UpdateMessageForScraperProcess:
    if rank_new != rank_old and points_new > points_old:
        update = UpdateMessageForScraperProcess()
    #TODO: complete this function

def check_completion_count():
    #TODO: complete this function
    pass

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