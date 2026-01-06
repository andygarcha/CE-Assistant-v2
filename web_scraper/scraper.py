"""
THIS FILE SHOULD BE RUN IN A DIFFERENT PROCESS
"""

import asyncio
import datetime
import json
import time
import typing
import discord
import requests
from Classes.CE_Game import CEGame, CEAPIGame
from Classes.CE_User import CEUser, CEAPIUser
from Classes.CE_User_Game import CEUserGame
from Classes.OtherClasses import UPDATEMESSAGE_LOCATIONS
import Modules.hm as hm
from Modules import CEAPIReader, Mongo_Reader

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

""" TOP LEVEL FUNCTION """

async def process_loop():
    # Update database name
    database_name_old, database_name_new = await update_database_name()

    # Update database user
    await update_database_user(database_name_old, database_name_new)

    # TODO: Check curator
    check_curator()

    # Generate database tier










""" MEDIUM LEVEL FUNCTIONS """

async def update_database_name():
    """
    Updates database_name.

    Returns
    ---
    - database_name_old: the database_name from before this scrape
    - database_name_new: the database_name from after this scrape
    """
    # (initially) empty list for us to store the old data in
    database_name_old: list[CEGame] = []
    # 'up to date' copy of the database from CE itself.
    database_name_new: list[CEAPIGame] = await CEAPIReader.get_api_games_full()
    # a list of all the ce ids from the current local (mongodb) database
    #   this will be useful for finding removed games.
    game_list = await Mongo_Reader.get_list('name')

    updates = []

    # let's iterate through all the new games
    for i, game_new in enumerate(database_name_new):
        game_old = await Mongo_Reader.get_game(game_new.ce_id)
        if game_old is not None:
            database_name_old.append(game_old)
        
        if game_new.ce_id in game_list:
            game_list.remove(game_new.ce_id)

        # game hasn't been updated
        if (game_old is not None and
            game_old.last_updated == game_new.last_updated):
                continue
        
        return_value = update_one_game(game_old, game_new)
        if return_value is not None:
            updates.append(return_value)

        # dump the new game to mongodb
        await Mongo_Reader.dump_game(game_new)

    # remove all removed games
    for removed_game in game_list:
        game_old = await Mongo_Reader.get_game(removed_game)

        return_value = update_one_game(game_old, None)
        if return_value is not None:
            updates.append(return_value)
        
        await Mongo_Reader.delete_game(removed_game)

        database_name_old.append(game_old)
    
    # TODO: upload the updates to mongodb

    return database_name_old, database_name_new

async def update_database_user(database_name_old: list[CEGame], database_name_new: list[CEAPIGame]):
    user_list = await Mongo_Reader.get_list('user')
    database_user_new = await CEAPIReader.get_api_users_all(user_list)

    updates: list[UpdateMessageForScraperProcess] = []

    for i, user_new in enumerate(database_user_new):
        if i % 10 == 0: print(f"User {i} of {len(database_user_new)}", end="... ")

        user_old = await Mongo_Reader.get_user(user_new.ce_id)

        # call the update function
        return_value = await update_one_user(
            user=user_old,
            site_data=user_new,
            database_name_old=database_name_old,
            database_name_new=database_name_new
        )

        updates.extend(return_value)
    
    # TODO: upload the updates to mongodb

async def check_curator():
    """Create any updates related to the curator."""

    # TODO: fill in this function
    pass

def generate_database_tier(database_name: list[CEAPIGame]):
    # separate out games by tier and category
    database_tier: dict[int, dict[str, list[dict]]] = {}
    for tier in range(1, 8):
        database_tier[tier] = {}
        for category in typing.get_args(hm.CATEGORIES):
            database_tier[tier][category] = []
    
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
        print(f'scraping for prices and hours at {i=} out of {len(steam_ids)}')

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
                steam_ids.remove(int(item['appId']))
                print(f'medianCompletion time not listed for app id {item['appId']}')
                continue
            hours[str(item['appId'])] = item['medianCompletionTime']

    for game in database_name:
        if not game.platform == 'steam': 
            continue #non steam game
        if game.get_tier_num() == 0:
            continue #t0
        if game.platform_id not in prices or game.platform_id not in hours:
            continue #no success from api

        database_tier[game.get_tier_num()][game.category].append(
            {
                'ce_id': game.ce_id,
                'name': game.game_name,
                'price': prices[game.platform_id],
                'sh_hours': hours[game.platform_id]
            }
        )

    return database_tier







""" BOTTOM LEVEL FUNCTIONS """
def update_one_game(game_old: CEGame, game_new: CEAPIGame) -> UpdateMessageForScraperProcess:
    # NEW GAME
    if game_old is None:
        return create_update_new_game(game_new)
    
    # REMOVED GAME
    elif game_new is None:
        return create_update_removed_game(game_old)
    
    return create_update_updated_game(game_old, game_new)

async def update_one_user(user: CEUser, site_data: CEAPIUser, database_name_old: list[CEGame], 
                          database_name_new: list[CEAPIGame]) -> list[UpdateMessageForScraperProcess]:
    """Provides updates for one user."""

    updates: list[UpdateMessageForScraperProcess] = []

    points_original = user.get_total_points()
    completed_games_original = user.get_completed_games_2(database_name_old)
    rank_original = user.get_rank()
    games_original = user.owned_games

    # update the user!
    user.owned_games = site_data.owned_games

    points_new = user.get_total_points()
    completed_games_new = user.get_completed_games_2(database_name_new)
    rank_new = user.get_rank()
    games_new = user.owned_games

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
        != int(len(completed_games_new) / COMPLETION_INCREMENT)):
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
    for i, roll in enumerate(user.rolls[:]) :
        if roll.status == "pending" and roll.due_time <= hm.get_unix("now") :
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
        if roll.partner_ce_id is not None : partner = await Mongo_Reader.get_user(roll.partner_ce_id)
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
            roll.completed_time = hm.get_unix("now")

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
                partner = await Mongo_Reader.get_user(roll.partner_ce_id)
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
                    await Mongo_Reader.dump_user(partner)

        
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
                partner = await Mongo_Reader.get_user(roll.partner_ce_id)
                if partner.has_current_roll(roll.roll_name) :
                    partner.fail_current_roll(roll.roll_name)
                    await Mongo_Reader.dump_user(user)
    
    user.set_last_updated(hm.get_unix("now"))

    await Mongo_Reader.dump_user(user)

    return updates

def check_curator_steam(): 
    """Checks steam for the last 10 curated games."""

    # TODO: fill in this function





""" BASEMENT LEVEL FUNCTIONS """

def create_update_new_game(game_new: CEAPIGame) -> UpdateMessageForScraperProcess:
    """Creates the `UpdateMessageForScraperProcess` for a new game."""
    update = UpdateMessageForScraperProcess()
    update.is_embed = True
    update.title = f"__ {game_new.game_name} __ added to the site:"
    update.color = 0x48b474
    update.description = f"\n- {game_new.get_emojis()}"
    update.url = f"https://cedb.me/game/{game_new.ce_id}"

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

    return update

def create_update_updated_game(game_old: CEGame, game_new: CEAPIGame) -> UpdateMessageForScraperProcess:
    """Creates the `UpdateMessageForScraperProcess` for an updated game."""
    update = UpdateMessageForScraperProcess()
    update.title = f"__ {game_new.game_name} __ updated on the site:"
    update.color = 0xefd839
    update.description = ""
    update.url = f"https://cedb.me/game/{game_new.ce_id}"

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
    description_test = description_test.replace('\n','').replace('\t','').replace('- Total points unchanged','')

    # if there wasn't any real change, ignore this embed
    if description_test == "" : return None

    return update

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

    return updates

def check_rank(rank_old: str, rank_new: str, points_old: int, 
               points_new: int, user: CEUser) -> UpdateMessageForScraperProcess:
    if rank_new != rank_old and points_new > points_old:
        update = UpdateMessageForScraperProcess()
    #TODO: complete this function

def check_completion_count():
    #TODO: complete this function
    pass

async def test():
    print('pulling db name')
    database_name = await Mongo_Reader.get_database_name()

    print('generating db tier!')
    database_tier = generate_database_tier(database_name)

    with open("other2.json", "w") as file:
        json.dump(database_tier, file, indent=4)

asyncio.run(test())