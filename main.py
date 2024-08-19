# -------- discord imports -----------
import datetime
from enum import Enum
import time
from types import NoneType
import typing
import discord
from discord import app_commands

# -------- json imports ----------
import json
from typing import Literal, get_args

import requests

# --------- local class imports --------
from Classes.CE_Cooldown import CECooldown
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEObjective
from Classes.CE_Game import CEGame
from Classes.CE_Objective import CEObjective
from Classes.CE_Roll import CERoll
from Classes.OtherClasses import SteamData, CECompletion, RAData
from Modules import WebInteractor
import Modules.CEAPIReader as CEAPIReader
from Modules.WebInteractor import master_loop
import Modules.hm as hm
import Modules.Mongo_Reader as Mongo_Reader
import Modules.Discord_Helper as Discord_Helper
import Modules.SpreadsheetHandler as SpreadsheetHandler
from Exceptions.FailedScrapeException import FailedScrapeException

# ----------- to-be-sorted imports -------------
import random
from functools import partial

# ----------- selenium and beautiful soup stuff -----------
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import io
from PIL import Image
from webdriver_manager.core.os_manager import ChromeType


# -------------------------------- normal bot code -----------------------------------

# set up intents
intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.guilds = True
intents.message_content = True


# open secret_info.json
with open('secret_info.json') as f :
    local_json_data = json.load(f)
    if hm.IN_CE :
        discord_token = local_json_data['discord_token']
        guild_id = local_json_data['ce_guild_ID']
    else :
        RUNNING_LOCALLY = False
        if RUNNING_LOCALLY : discord_token = local_json_data['other_discord_token']
        else : discord_token = local_json_data['third_discord_token']
        guild_id = local_json_data['test_guild_ID']

# set up client
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=guild_id)

# ------------------------------ commands -------------------------------------



#  _______   ______    _____   _______ 
# |__   __| |  ____|  / ____| |__   __|
#    | |    | |__    | (___      | |   
#    | |    |  __|    \___ \     | |   
#    | |    | |____   ____) |    | |   
#    |_|    |______| |_____/     |_|   



# ---- test command ----
@tree.command(name='test', description='test',guild=guild)
async def test(interaction : discord.Interaction) :
    await interaction.response.defer()

    """
    HOTS = "e5b91554-215a-41b9-8974-e921044b2081"
    MYID = "d7cb0869-5ed9-465c-87bf-0fb95aaebbd5"

    database_user = await Mongo_Reader.get_mongo_users()
    user = hm.get_item_from_list(MYID, database_user)
    roll = user.get_current_roll("Fourward Thinking")
    roll._games = [HOTS]
    user.replace_current_roll(roll)
    await Mongo_Reader.dump_user(user)
    """

    return await interaction.followup.send('test done')




#  _____    ______    _____   _____    _____   _______   ______   _____  
# |  __ \  |  ____|  / ____| |_   _|  / ____| |__   __| |  ____| |  __ \ 
# | |__) | | |__    | |  __    | |   | (___      | |    | |__    | |__) |
# |  _  /  |  __|   | | |_ |   | |    \___ \     | |    |  __|   |  _  / 
# | | \ \  | |____  | |__| |  _| |_   ____) |    | |    | |____  | | \ \ 
# |_|  \_\ |______|  \_____| |_____| |_____/     |_|    |______| |_|  \_\



# ---- register command ----
@tree.command(name = "register", 
              description = "Register with CE Assistant to unlock all features!", 
              guild = guild)
@app_commands.describe(ce_id = "The link to your Challenge Enthusiasts profile.")
async def register(interaction : discord.Interaction, ce_id : str) : 
    await interaction.response.defer()

    # format correctly
    ce_id = hm.format_ce_link(ce_id)
    if ce_id is None : return await interaction.followup.send(f"'{ce_id}' is not a valid link or ID. Please try again!")

    # get database_user
    users = await Mongo_Reader.get_mongo_users()
    
    # make sure they're not already registered
    for user in users :
        if user.discord_id == interaction.user.id :
            return await interaction.followup.send("You are already registered in the " +
                                                   "CE Assistant database!")
        if user.ce_id == ce_id : 
            return await interaction.followup.send("This Challenge Enthusiast page is " +
                                                   "already connected to another account!")
    
    # grab their data from CE
    ce_user : CEUser = CEAPIReader.get_api_page_data("user", ce_id)
    if ce_user == None :
        return await interaction.followup.send("Your Challenge Enthusiast page was not found. " + 
                                               "Please try again later or contact andy.")
    ce_user.discord_id = interaction.user.id

    # grab the user's pre-existing rolls
    rolls = ce_user.get_ce_rolls()
    for roll in rolls :
        user.add_completed_roll(roll)

    # add the user to users and dump it
    users.append(ce_user)
    await Mongo_Reader.dump_users(users)

    # get the role and attach it
    cea_registered_role = discord.utils.get(interaction.guild.roles, name = "CEA Registered")
    await interaction.user.add_roles(cea_registered_role)

    # and return.
    return await interaction.followup.send("You've been successfully registered!")



#  ______    ____    _____     _____   ______     _____    ______    _____   _____    _____   _______   ______   _____  
# |  ____|  / __ \  |  __ \   / ____| |  ____|   |  __ \  |  ____|  / ____| |_   _|  / ____| |__   __| |  ____| |  __ \ 
# | |__    | |  | | | |__) | | |      | |__      | |__) | | |__    | |  __    | |   | (___      | |    | |__    | |__) |
# |  __|   | |  | | |  _  /  | |      |  __|     |  _  /  |  __|   | | |_ |   | |    \___ \     | |    |  __|   |  _  / 
# | |      | |__| | | | \ \  | |____  | |____    | | \ \  | |____  | |__| |  _| |_   ____) |    | |    | |____  | | \ \ 
# |_|       \____/  |_|  \_\  \_____| |______|   |_|  \_\ |______|  \_____| |_____| |_____/     |_|    |______| |_|  \_\



@tree.command(name='force-register', description='Register another user with CE Assistant!', guild=guild)
@app_commands.describe(ce_link="The link to their CE page (or their ID, either works)")
@app_commands.describe(user="The user you want to link this page (or ID) to.")
async def register_other(interaction : discord.Interaction, ce_link : str, user : discord.Member) :
    await interaction.response.defer(ephemeral=True)

    # log this interaction
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":white_large_square: dev command run by <@{interaction.user.id}>: /force-register, "
                     + f"params: ce_link={ce_link}, user={user.id}", allowed_mentions=discord.AllowedMentions.none())

    # format correctly
    ce_id = hm.format_ce_link(ce_link)
    if ce_id is None : return await interaction.followup.send(f"'{ce_id}' is not a valid link or ID. Please try again!")

    # get users
    users = await Mongo_Reader.get_mongo_users()
    
    # make sure they're not already registered
    for mongo_user in users :
        if mongo_user.discord_id == user.id :
            return await interaction.followup.send("This user is already registered in the " +
                                                   "CE Assistant database!")
        if mongo_user.ce_id == ce_id : 
            return await interaction.followup.send("This Challenge Enthusiast page is " +
                                                   "already connected to another account!")
        
    # grab their data from CE
    ce_user : CEUser = CEAPIReader.get_api_page_data("user", ce_id)
    if ce_user == None :
        return await interaction.followup.send("This Challenge Enthusiast page was not found. " + 
                                               "Please try again later or contact andy.")
    ce_user.discord_id = user.id

    # grab the user's pre-existing rolls
    rolls = ce_user.get_ce_rolls()
    for roll in rolls :
        ce_user.add_completed_roll(roll)

    # add the user to users and dump it
    users.append(ce_user)
    await Mongo_Reader.dump_users(users)

    # get the role and attach it
    cea_registered_role = discord.utils.get(interaction.guild.roles, name = "CEA Registered")
    await user.add_roles(cea_registered_role)

    # and return.
    return await interaction.followup.send(f"<@{user.id}> been successfully registered. " + 
                                           "Please make sure they received the CEA Registered role!")






#   _____    ____    _         ____      _____     ____    _        _      
#  / ____|  / __ \  | |       / __ \    |  __ \   / __ \  | |      | |     
# | (___   | |  | | | |      | |  | |   | |__) | | |  | | | |      | |     
#  \___ \  | |  | | | |      | |  | |   |  _  /  | |  | | | |      | |     
#  ____) | | |__| | | |____  | |__| |   | | \ \  | |__| | | |____  | |____ 
# |_____/   \____/  |______|  \____/    |_|  \_\  \____/  |______| |______|




# ---- solo roll command ----
@tree.command(name = "solo-roll",
              description = "Roll a solo event with CE Assistant!",
              guild = guild)
@app_commands.describe(event_name = "The event you'd like to roll.")
@app_commands.describe(price_restriction="Set this to false if you'd like to be able to roll any game, regardless of price.")
async def solo_roll(interaction : discord.Interaction, event_name : hm.SOLO_ROLL_EVENT_NAMES, price_restriction : bool = True) :
    await interaction.response.defer()

    return await interaction.followup.send("Sorry, but rolling is still under construction! Please come back later...")
    view = discord.ui.View()

    # pull mongo database
    database_user = await Mongo_Reader.get_mongo_users()
    database_name = await Mongo_Reader.get_mongo_games()

    # define channel
    user_log_channel = client.get_channel(hm.USER_LOG_ID)

    # grab the user
    user = None
    user_index = -1
    for i, u in enumerate(database_user) :
        if u.discord_id == interaction.user.id :
            user = u
            user_index = i
            break

    # user doesn't exist
    if user == None :
        return await interaction.followup.send(
            "Sorry, you're not registered in the CE Assistant database. Please run `/register` first!"
        )
    # user has cooldown
    if user.has_cooldown(event_name) :
        return await interaction.followup.send(
            f"You are currently on cooldown for {event_name} until {user.get_cooldown_time(event_name)}. "
        )
    # user currently rolled
    if user.has_current_roll(event_name) and event_name not in ["Two Week T2 Streak", "Two \"Two Week T2 Streak\" Streak"
                                                                , "Fourward Thinking"] :
        return await interaction.followup.send(
            f"You're currently attempting {event_name}! Please finish this instance before rerolling."
        )
    # user has pending
    if user.has_pending(event_name) :
        return await interaction.followup.send(
            f"You just tried rolling this event. Please wait about 10 minutes before trying again." +
            " (P.S. This is not a cooldown. Just has to do with how the bot backend works.)"
        )
    
    # jarvis's random event!
    if random.randint(0, 99) == 0 : 
        user_log_channel.send(
            f"Congratulations <@{interaction.user.id}>! You've won Jarvis's super secret random thing! " +
            "Please DM him for your prize :)"
        )
        
    # -- set up vars --
    rolled_games : list[str] = []

    # in this switch statement, grab the games. the roll will be set up at the end.
    match(event_name) :
        case "One Hell of a Day" :
            # -- grab games --
            rolled_games = [hm.get_rollable_game(
                database_name=database_name,
                completion_limit=10,
                price_limit=10,
                tier_number=1,
                user=user,
                price_restriction=price_restriction
            )]
        
        case "One Hell of a Week" :
            # -- if the user hasn't done day, return --
            if not user.has_completed_roll('One Hell of a Day') :
                return await interaction.followup.send(
                    f"You need to complete One Hell of a Day before rolling {event_name}!"
                )
            
            # -- grab games --
            rolled_games : list[str] = []
            valid_categories = list(get_args(hm.CATEGORIES))
            for i in range(5) :
                rolled_games.append(hm.get_rollable_game(
                    database_name=database_name,
                    completion_limit=10,
                    price_limit=10,
                    tier_number=1,
                    user=user,
                    category=valid_categories,
                    already_rolled_games=rolled_games,
                    price_restriction=price_restriction
                ))
                valid_categories.remove(
                    hm.get_item_from_list(rolled_games[i], database_name).category
                )

        case "One Hell of a Month" :
            # -- if user doesn't have week, return --
            if not user.has_completed_roll('One Hell of a Week') :
                return await interaction.followup.send(
                    f"You need to complete One Hell of a Week before rolling {event_name}!"
                )
            
            # -- grab games --
            rolled_games : list[str] = []
            valid_categories = list(get_args(hm.CATEGORIES))
            for i in range(5) :
                selected_category = random.choice(valid_categories)
                for j in range(j) :
                    rolled_games.append(hm.get_rollable_game(
                        database_name=database_name,
                        completion_limit=10,
                        price_limit=10,
                        tier_number=1,
                        user=user,
                        category=selected_category,
                        already_rolled_games=rolled_games,
                        price_restriction=price_restriction
                    ))
                valid_categories.remove(selected_category)
    
        case "Two Week T2 Streak" :
            if user.has_current_roll('Two Week T2 Streak') :
                "If user's current roll is ready for next stage, roll it for them."
                past_roll : CERoll
                past_roll_index : int
                for i, r in enumerate(user.current_rolls) :
                    if r.roll_name == event_name : 
                        past_roll = r
                        past_roll_index = i
                        break
                if past_roll.ready_for_next() :
                    past_roll.add_game(hm.get_rollable_game(
                        database_name=database_name,
                        completion_limit=40,
                        price_limit=20,
                        tier_number=2,
                        user=user,
                        already_rolled_games=r.games,
                        price_restriction=price_restriction
                    ))
                    user.current_rolls[past_roll_index] = past_roll
                    database_user[user_index] = user
                else :
                    return await interaction.followup.send(
                        "You need to finish the first half of Two Week T2 Streak first!"
                    )
                
            else :
                rolled_games = [hm.get_rollable_game(
                    database_name=database_name,
                    completion_limit=40,
                    price_limit=20,
                    tier_number = 2,
                    user=user,
                    price_restriction=price_restriction
                )]
        case "Two \"Two Week T2 Streak\" Streak" :
            if not user.has_completed_roll("Two Week T2 Streak") :
                return await interaction.followup.send(
                    f"You need to complete Two Week T2 Steak before rolling {event_name}!"
                )
            if user.has_current_roll("Two \"Two Week T2 Streak\" Streak") :
                # if the user is currently working 
                past_roll = user.get_current_roll("Two \"Two Week T2 Streak\" Streak")
                if past_roll.ready_for_next() :
                    new_game_id = hm.get_rollable_game(
                        database_name=database_name,
                        completion_limit=40,
                        price_limit=20,
                        tier_number=2,
                        user=user,
                        already_rolled_games=past_roll.games,
                        price_restriction=price_restriction
                    )
                    past_roll.add_game(new_game_id)
                    new_game_object = hm.get_item_from_list(new_game_id, database_name)
                    user.replace_current_roll(past_roll)
                    database_user[user_index] = user
                    return await interaction.followup.send(
                        f"Your next game is [{new_game_object.game_name}](https://cedb.me/game/{new_game_object.ce_id}). " +
                        f"Run /check-rolls to see more information."
                    )
                else :
                    return await interaction.followup.send("You need to finish your current games before you roll your next one!")
            
            else :
                rolled_games = [hm.get_rollable_game(
                    database_name=database_name,
                    completion_limit=40,
                    price_limit=20,
                    tier_number=2,
                    user=user,
                    price_restriction=price_restriction
                )]
        case "Never Lucky" :
            rolled_games = [hm.get_rollable_game(
                database_name=database_name,
                completion_limit=None,
                price_limit=20,
                tier_number=3,
                user=user,
                price_restriction=price_restriction
            )]
        case "Triple Threat" :
            if not user.has_completed_roll("Never Lucky") :
                return await interaction.followup.send(f"You need to complete Never Lucky before rolling Triple Threat!")
            rolled_games = []
            for i in range(3) :
                rolled_games.append(hm.get_rollable_game(
                    database_name=database_name,
                    completion_limit=40,
                    price_limit=20,
                    tier_number=3,
                    user=user,
                    already_rolled_games=rolled_games,
                    price_restriction=price_restriction
                ))
        case "Let Fate Decide" :
            rolled_games = [hm.get_rollable_game(
                database_name=database_name,
                completion_limit=None,
                price_limit=20,
                tier_number=4,
                user=user,
                price_restriction=price_restriction
            )]
        case "Fourward Thinking" :
            #if not user.has_completed_roll("Let Fate Decide") :
            #    return await interaction.followup.send("You need to complete Let Fate Decide before rolling Fourward Thinking!")

            # grab the previous roll (if there is one)
            past_roll : CERoll | None = user.get_current_roll("Fourward Thinking")

            # check to make sure this person is ready for the next iteration of their roll
            if past_roll is not None and not past_roll.ready_for_next() :
                return await interaction.followup.send("You need to finish your previous game first! Run /check-rolls to check them.")
            
            class FourwardThinkingDropdown(discord.ui.Select) :
                def __init__(self) :
                    # store the user
                    self.__user = user

                    # initialize options
                    options : list[discord.SelectOption] = []

                    # if haven't rolled before, here are options
                    if past_roll is None : options = [
                        discord.SelectOption(label=cat, emoji=hm.get_emoji(cat)) for cat in get_args(hm.CATEGORIES)
                    ]

                    # if they have rolled before, get new options
                    else :
                        already_rolled_categories = past_roll.rolled_categories(database_name=database_name)
                        for cat in get_args(hm.CATEGORIES) :
                            if cat not in already_rolled_categories : options.append(
                                discord.SelectOption(label=cat, emoji=hm.get_emoji(cat))
                            )
                    
                    super().__init__(placeholder="Select a category.", min_values=1, max_values=1, options=options)

                async def callback(self, interaction : discord.Interaction) :
                    "The callback."

                    # stop other users from clicking the dropdown
                    if interaction.user.id != self.__user.discord_id :
                        return await interaction.response.send_message(
                            "Stop that! This isn't your roll.", ephemeral=True
                        )
                    
                    # defer the message
                    await interaction.response.defer()
                    
                    # pull database user
                    database_user = await Mongo_Reader.get_mongo_users()
                    user = hm.get_item_from_list(self.__user.ce_id, database_user)

                    # get past_roll
                    past_roll = user.get_current_roll("Fourward Thinking")
                    if past_roll is None :
                        past_roll = CERoll(
                            roll_name="Fourward Thinking",
                            user_ce_id=user.ce_id,
                            games=[],
                            is_current=True
                        )
                    
                    # get the data
                    next_phase_num = len(past_roll.games) + 1
                    category = self.values[0]
                    game_id = hm.get_rollable_game(
                        database_name=database_name,
                        completion_limit=40*next_phase_num,
                        price_limit=20,
                        tier_number=next_phase_num,
                        user=user,
                        category=category,
                        price_restriction=price_restriction
                    )

                    # add the new game and reset the due time.
                    past_roll.add_game(game_id)
                    past_roll.reset_due_time()

                    # replace the roll and push the user to mongo
                    user.replace_current_roll(past_roll)
                    user.remove_pending("Fourward Thinking")
                    await Mongo_Reader.dump_user(user)

                    # now send the message
                    game_object = hm.get_item_from_list(game_id, database_name)
                    view.clear_items()
                    return await interaction.followup.edit_message(
                        message_id=interaction.message.id,
                        content=f"Your new game is [{game_object.game_name}](https://cedb.me/game/{game_object.ce_id}).",
                        view=view
                    )
                
            # add the pending and dump it
            user.add_pending(CECooldown(roll_name="Fourward Thinking", end_time=hm.get_unix(minutes=10)))
            await Mongo_Reader.dump_user(user)
            
            view.timeout = 600
            view.add_item(FourwardThinkingDropdown())
            
            return await interaction.followup.send(
                "Choose your category.", view=view
            )



    # -- check to make sure there were enough rollable games --
    if None in rolled_games :
        return await interaction.followup.send(
            "There weren't enough rollable games that matched this event's criteria." 
            + " Please try again later (and contact andy!)."
        )

    # -- create roll object --
    roll = CERoll(
        roll_name=event_name,
        user_ce_id=user.ce_id,
        games=rolled_games,
        is_current=True
    )
    user.add_current_roll(roll)

    # -- create embeds --
    embeds = Discord_Helper.get_roll_embeds(
        roll=roll,
        database_name=database_name,
        database_user=database_user
    )

    await Discord_Helper.get_buttons(view=view, embeds=embeds)
    await Mongo_Reader.dump_user(user=user)
    return await interaction.followup.send(embed=embeds[0], view=view)




#   _____    _____   _____               _____    ______ 
#  / ____|  / ____| |  __ \      /\     |  __ \  |  ____|
# | (___   | |      | |__) |    /  \    | |__) | | |__   
#  \___ \  | |      |  _  /    / /\ \   |  ___/  |  __|  
#  ____) | | |____  | | \ \   / ____ \  | |      | |____ 
# |_____/   \_____| |_|  \_\ /_/    \_\ |_|      |______|




# ---- scrape function ----
@tree.command(name="scrape", description=("Replace database_name with API data WITHOUT sending messages. RUN WHEN NECESSARY."), guild=guild)
async def scrape(interaction : discord.Interaction) :
    await interaction.response.defer()

    try :
        database_name = await CEAPIReader.get_api_games_full()
    except FailedScrapeException as e :
        return await interaction.followup.send(f"Error FailedScrapeException: {e.get_message()}")

    await Mongo_Reader.dump_games(database_name)

    return await interaction.followup.send("Database replaced.")



#  _____   _   _   _____   _______   _____              _______   ______     _         ____     ____    _____  
# |_   _| | \ | | |_   _| |__   __| |_   _|     /\     |__   __| |  ____|   | |       / __ \   / __ \  |  __ \ 
#   | |   |  \| |   | |      | |      | |      /  \       | |    | |__      | |      | |  | | | |  | | | |__) |
#   | |   | . ` |   | |      | |      | |     / /\ \      | |    |  __|     | |      | |  | | | |  | | |  ___/ 
#  _| |_  | |\  |  _| |_     | |     _| |_   / ____ \     | |    | |____    | |____  | |__| | | |__| | | |     
# |_____| |_| \_| |_____|    |_|    |_____| /_/    \_\    |_|    |______|   |______|  \____/   \____/  |_|     




# ---- initiate loop ----
@tree.command(name="initiate-loop", description="Initiate the loop. ONLY RUN WHEN NECESSARY.", guild=guild)
async def loop(interaction : discord.Interaction) :
    await interaction.response.defer()

    if datetime.datetime.now().minute < 30 and datetime.datetime.now().minute >= 25 :
        return await interaction.followup.send('this loop will run in less than five minutes. please wait!')
    if datetime.datetime.now().minute >= 30 and datetime.datetime.now().minute < 35 :
        return await interaction.followup.send('this loop is probably running now! please wait...')

    await interaction.followup.send("looping...")

    # log this interaction
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":white_large_square: dev command run by <@{interaction.user.id}>: /initiate-loop",
                             allowed_mentions=discord.AllowedMentions.none())

    await master_loop(client)

    return await interaction.followup.send('loop complete.')



#             _____    _____      _   _    ____    _______   ______    _____ 
#     /\     |  __ \  |  __ \    | \ | |  / __ \  |__   __| |  ____|  / ____|
#    /  \    | |  | | | |  | |   |  \| | | |  | |    | |    | |__    | (___  
#   / /\ \   | |  | | | |  | |   | . ` | | |  | |    | |    |  __|    \___ \ 
#  / ____ \  | |__| | | |__| |   | |\  | | |__| |    | |    | |____   ____) |
# /_/    \_\ |_____/  |_____/    |_| \_|  \____/     |_|    |______| |_____/ 




@tree.command(name="add-notes", description="Add notes to any #game-additions post.", guild=guild)
@app_commands.describe(embed_id="The Message ID of the message you'd like to add notes to.")
@app_commands.describe(notes="The notes you'd like to append.")
@app_commands.describe(clear="Set this to true if you want to replace all previous notes with this one.")
async def add_notes(interaction : discord.Interaction, embed_id : str, notes : str, clear : bool) :
    "Adds notes to game additions posts."
    # defer and make ephemeral
    await interaction.response.defer(ephemeral=True)

    # log this interaction
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":white_large_square: dev command run by <@{interaction.user.id}>: /add-notes, "
                     + f"params: embed_id={embed_id}, notes={notes}, clear={clear}", allowed_mentions=discord.AllowedMentions.none())

    # grab the site additions channel
    site_additions_channel = client.get_channel(hm.GAME_ADDITIONS_ID)

    # try to get the message
    try :
        message = await site_additions_channel.fetch_message(int(embed_id))

    # if it errors, message is not in the site-additions channel
    except :
        return await interaction.followup.send(f"This message is not in the <#{hm.GAME_ADDITIONS_ID}> channel.")
    
    if message.author.id != 1108618891040657438 : return await interaction.followup.send("This message was not sent by the bot!")

    # grab the embed
    embed = message.embeds[0]

    # try and see if the embed already has a reason field
    try :
        if(embed.fields[-1].name == "Note") :
            # if clear has been set, set the value to only the new notes
            if clear :
                embed.set_field_at(index=len(embed.fields)-1, name="Note", value=notes)
            
            # else, add the new notes to the end and keep the old notes
            else :
                old_notes = embed.fields[-1].value
                embed.set_field_at(index=len(embed.fields)-1, name="Note", value=f"{old_notes}\n{notes}")
    
    # if it errors, then just add a reason field
    except :
        embed.add_field(name="Note", value=notes, inline=False)

    # edit the message
    await message.edit(embed=embed, attachments="")

    # and send a response to the original interaction
    await interaction.followup.send("Notes added!", ephemeral=True)




#   _____   ______   _______             _____              __  __   ______ 
#  / ____| |  ____| |__   __|           / ____|     /\     |  \/  | |  ____|
# | |  __  | |__       | |     ______  | |  __     /  \    | \  / | | |__   
# | | |_ | |  __|      | |    |______| | | |_ |   / /\ \   | |\/| | |  __|  
# | |__| | | |____     | |             | |__| |  / ____ \  | |  | | | |____ 
#  \_____| |______|    |_|              \_____| /_/    \_\ |_|  |_| |______|


async def get_game_auto(interaction : discord.Interaction, current : str) -> typing.List[app_commands.Choice[str]]:
    """Function that autocompletes whatever the user is trying to type in.
    The game's name will appear on the user's screen, but the game's CE ID will be passed."""
    database_name = await Mongo_Reader.get_mongo_games()
    choices : list = []

    for game in database_name :
        if current.lower() in game.game_name.lower() :
            choices.append(app_commands.Choice(name=game.game_name, value=game.ce_id))
        if len(choices) >= 25 : break

    return choices[0:25]

@tree.command(name="get-game", description="Get information about any game on CE!", guild=guild)
@app_commands.autocomplete(game=get_game_auto)
async def get_game(interaction : discord.Interaction, game : str) :

    # defer
    await interaction.response.defer()

    # pull database name
    database_name = await Mongo_Reader.get_mongo_games()

    # you were only given the game's name, so go find it.
    chosen_game = hm.get_item_from_list(game, database_name)
    if chosen_game is None : return await interaction.followup.send("Sorry, I encountered a strange error. Try again later!")

    # pull the game embed
    game_embed = Discord_Helper.get_game_embed(chosen_game.ce_id, database_name)

    # and return
    return await interaction.followup.send(embed=game_embed)



#   _____   ______   _______             _____              __  __   ______     _____    ______  __      __
#  / ____| |  ____| |__   __|           / ____|     /\     |  \/  | |  ____|   |  __ \  |  ____| \ \    / /
# | |  __  | |__       | |     ______  | |  __     /  \    | \  / | | |__      | |  | | | |__     \ \  / / 
# | | |_ | |  __|      | |    |______| | | |_ |   / /\ \   | |\/| | |  __|     | |  | | |  __|     \ \/ /  
# | |__| | | |____     | |             | |__| |  / ____ \  | |  | | | |____    | |__| | | |____     \  /   
#  \_____| |______|    |_|              \_____| /_/    \_\ |_|  |_| |______|   |_____/  |______|     \/    

    
@tree.command(name="get-game-data", description="return the local data on a game.", guild=guild)
@app_commands.autocomplete(ce_id=get_game_auto)
async def get_game_data(interaction : discord.Interaction, ce_id : str) :
    await interaction.response.defer()

    database_name = await Mongo_Reader.get_mongo_games()

    for game in database_name :
        if game.ce_id == ce_id : return await interaction.followup.send(f"{str(game)}")
    return await interaction.followup.send('game not found')


#   _____   _    _   ______    _____   _  __           _____     ____    _        _         _____ 
#  / ____| | |  | | |  ____|  / ____| | |/ /          |  __ \   / __ \  | |      | |       / ____|
# | |      | |__| | | |__    | |      | ' /   ______  | |__) | | |  | | | |      | |      | (___  
# | |      |  __  | |  __|   | |      |  <   |______| |  _  /  | |  | | | |      | |       \___ \ 
# | |____  | |  | | | |____  | |____  | . \           | | \ \  | |__| | | |____  | |____   ____) |
#  \_____| |_|  |_| |______|  \_____| |_|\_\          |_|  \_\  \____/  |______| |______| |_____/ 


@tree.command(name="check-rolls", description="Check the status of your current and completed casino rolls!", guild=guild)
async def check_rolls(interaction : discord.Interaction) :
    # defer the message
    await interaction.response.defer()

    # create the view
    view = discord.ui.View(timeout=None)

    # pull database_name and database_user
    database_name = await Mongo_Reader.get_mongo_games()
    database_user = await Mongo_Reader.get_mongo_users()

    # find the user
    user : CEUser = None
    for u in database_user :
        if u.discord_id == interaction.user.id : 
            user = u
            break
    if user is None : return await interaction.followup.send(content="You're not registered! Please run /register.")

    class CheckRollsDropdown(discord.ui.Select) :
        def __init__(self, user : CEUser) :

            # define variable
            self.__user = user

            # set up options
            options : list[discord.SelectOption] = []
            for roll_name in get_args(hm.ALL_ROLL_EVENT_NAMES) :
                options.append(discord.SelectOption(label=roll_name))

            # super init
            super().__init__(placeholder="Select a roll event!", min_values=1, max_values=1, options=options)
        
        @property
        def user(self) -> CEUser :
            "The user who called the view."
            return self.__user
        
        async def callback(self, interaction : discord.Interaction) :
            # make sure only caller can change the values
            if interaction.user.id != self.user.discord_id : 
                return await interaction.response.send_message(
                    "You can't change this person's values! Run /check-rolls yourself to see yours.", ephemeral=True
                    )

            # defer 
            await interaction.response.defer()

            # initialize the embed
            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Rolls",
                description="",
                timestamp=datetime.datetime.now(),
                color=0x000000
            )

            # get roll name
            roll_name = self.values[0]

            # let them know if they are on cooldown.
            if user.has_cooldown(roll_name) : 
                embed.description = f"You are on cooldown for {roll_name} until <t:{user.get_cooldown_time(roll_name)}>."
            else :
                embed.description = f"You are not currently on cooldown for {roll_name}."

            # current rolls
            current_roll = user.get_current_roll(roll_name)
            current_string = ""
            if current_roll == None : current_string = f"You do not have a current roll in {roll_name}."
            else : current_string = current_roll.display_str(database_name=database_name, database_user=database_user)
            embed.add_field(name="Current Roll", value=current_string)

            # completed rolls
            completed_rolls = user.get_completed_rolls(roll_name)
            completed_string = ""
            if completed_rolls == None : completed_string = f"You do not have any completed rolls in {roll_name}."
            else :
                for completed_roll in completed_rolls :
                    completed_string += f"{completed_roll.display_str(database_name=database_name, database_user=database_user)}\n"
            embed.add_field(name="Completed Rolls", value=completed_string)

            return await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)
    
    view.add_item(CheckRollsDropdown(user))

    # initialize the embed
    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Rolls",
        description="",
        timestamp=datetime.datetime.now(),
        color=0x000000
    )

    await interaction.followup.send(embed=embed, view=view)

@tree.command(name='set-color', description='Set your discord username color!', guild=guild)
async def set_color(interaction : discord.Interaction) :
    "Sets the color."
    await interaction.response.defer(ephemeral=True)

    # pull database_user and get the user
    database_user = await Mongo_Reader.get_mongo_users()
    user = Discord_Helper.get_user_by_discord_id(interaction.user.id, database_user)

    # set up ranks values


    class Rank(Enum) :
        E = 0
        D = 1
        C = 2
        B = 3
        A = 4
        S = 5
        SS = 6
        SSS = 7
        EX = 8
    class Color(Enum) :
        Grey = Rank.E
        Brown = Rank.D
        Green = Rank.C
        Blue = Rank.B
        Purple = Rank.A
        Orange = Rank.S
        Yellow = Rank.SS
        Red = Rank.SSS
        Black = Rank.EX     
    
    ranks = [(rank.name + " Rank") for rank in Rank]

    # set up the callback
    async def color_callback(interaction : discord.Interaction, color : Color) :
        "Updates the user's color."
        color_roles = [(discord.utils.get(interaction.guild.roles, name = f.name)) for f in Color]

    # get the rank
    user_rank = user.get_rank()[:-5]

    Rank.E.name






#  _____    _____     ____    ______   _____   _        ______ 
# |  __ \  |  __ \   / __ \  |  ____| |_   _| | |      |  ____|
# | |__) | | |__) | | |  | | | |__      | |   | |      | |__   
# |  ___/  |  _  /  | |  | | |  __|     | |   | |      |  __|  
# | |      | | \ \  | |__| | | |       _| |_  | |____  | |____ 
# |_|      |_|  \_\  \____/  |_|      |_____| |______| |______|

@tree.command(name="profile", description="See information about you or anyone else in Challenge Enthusiasts!", guild=guild) 
@app_commands.describe(user="The user you'd like to see information about (leave blank to see yourself!)")
async def profile(interaction : discord.Interaction, user : discord.User = None) :
    await interaction.response.defer()

    # pull databases
    database_name = await Mongo_Reader.get_mongo_games()
    database_user = await Mongo_Reader.get_mongo_users()

    # check to see if they asked for info on another person.
    asked_for_friend : bool = True
    if user is None :
        user = interaction.user
        asked_for_friend = False

    # make sure they're registered
    ce_user = Discord_Helper.get_user_by_discord_id(user.id, database_user)
    if ce_user is None and asked_for_friend : 
        return await interaction.followup.send(f"Sorry! <@{user.id}> is not registered. Please have them run /register!", 
                                               allowed_mentions=discord.AllowedMentions.none())
    if ce_user is None and not asked_for_friend :
        return await interaction.followup.send("Sorry! You are not registered. Please run /register and try again!")
    
    # get the embed and the view
    returns = await Discord_Helper.get_user_embeds(user=ce_user, database_name=database_name, database_user=database_user)
    summary_embed = returns[0]
    view = returns[1]

    # and send
    return await interaction.followup.send(view=view, embed=summary_embed)



#   _____   _        ______              _____  
#  / ____| | |      |  ____|     /\     |  __ \ 
# | |      | |      | |__       /  \    | |__) |
# | |      | |      |  __|     / /\ \   |  _  / 
# | |____  | |____  | |____   / ____ \  | | \ \ 
#  \_____| |______| |______| /_/    \_\ |_|  \_\


@tree.command(name="clear-roll", description="Clear any user's current/completed rolls, cooldowns, or pendings.", guild=guild)
async def clear_roll(interaction : discord.Interaction, member : discord.Member, roll_name : hm.ALL_ROLL_EVENT_NAMES, 
                     current : bool = False, completed : bool = False, cooldown : bool = False, pending : bool = False) :
    await interaction.response.defer()

    # log this interaction
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":white_large_square: dev command run by <@{interaction.user.id}>: /clear-roll, "
                     + f"params: member=<@{member.id}>, roll_name={roll_name}, current={current}, completed={completed}, "
                     + f"cooldown={cooldown}, pending={pending}", allowed_mentions=discord.AllowedMentions.none())

    # get database user and the user
    database_user = await Mongo_Reader.get_mongo_users()
    user = Discord_Helper.get_user_by_discord_id(member.id, database_user)

    if current : user.remove_current_roll(roll_name)
    if completed : user.remove_completed_rolls(roll_name)
    if cooldown : user.remove_cooldown(roll_name)
    if pending : user.remove_pending(roll_name)

    await Mongo_Reader.dump_user(user)
    return await interaction.followup.send("Done!")

"""
#   _____   ______   _______            _____     ____    _        _                  _____              __  __   ______ 
#  / ____| |  ____| |__   __|          |  __ \   / __ \  | |      | |                / ____|     /\     |  \/  | |  ____|
# | (___   | |__       | |     ______  | |__) | | |  | | | |      | |       ______  | |  __     /  \    | \  / | | |__   
#  \___ \  |  __|      | |    |______| |  _  /  | |  | | | |      | |      |______| | | |_ |   / /\ \   | |\/| | |  __|  
#  ____) | | |____     | |             | | \ \  | |__| | | |____  | |____           | |__| |  / ____ \  | |  | | | |____ 
# |_____/  |______|    |_|             |_|  \_\  \____/  |______| |______|           \_____| /_/    \_\ |_|  |_| |______|

@tree.command(name="set-roll-game", description="Set any game in a user's current rolls.", guild=guild)
async def set_roll_game(interaction : discord.Interaction, member : discord.Member, 
                        roll_name : hm.ALL_ROLL_EVENT_NAMES, game_id : str) :
    await interaction.response.defer(ephemeral=True)

    # pull databases
    database_name = await Mongo_Reader.get_mongo_games()
    database_user = await Mongo_Reader.get_mongo_users()

    # get objects
    game = hm.get_item_from_list(game_id, database_name)
    user = Discord_Helper.get_user_by_discord_id(member.id, database_user)

    # make sure they're registered
    if user is None : return await interaction.followup.send("This user is not registered.")

    # make sure they have the roll
    roll = user.get_current_roll(roll_name)
    if roll is None : return await interaction.followup.send("This user doesn't have this roll.")

    class SetRollDropdown(discord.ui.Select) :
        def __init__(self, roll : CERoll) :
            self.__roll = roll
            self.__replacement_id = game_id

            game_objects = [hm.get_item_from_list(game, database_name) for game in roll.games]

            options = [discord.SelectOption(label=game.game_name) for game in game_objects]

            super().__init__(placeholder="Select a game to replace.", min_values=1, max_values=1, options=options)

        async def callback(self, interaction : discord.Interaction) :
            "Callback."
            await interaction.response.defer()

            # get the id of the game they want to swap out
            game_id = self.values[0]

            database_name = await Mongo_Reader.get_mongo_games()

            # go through and find that id and swap it out
            for i, rollgameid in enumerate(self.__roll.games) :
                if rollgameid == game_id : self.__roll._games[i] = self.__replacement_id
            
            # pull database name
            database_user = await Mongo_Reader.get_mongo_users()

            # get the user and replace the roll
            user = hm.get_item_from_list(self.__roll.user_ce_id, database_user)
            user.replace_current_roll(self.__roll)

            replaced_game = hm.get_item_from_list(game_id, database_name)
            game_that_replaced = hm.get_item_from_list(self.__replacement_id, database_name)

            return await interaction.followup.send(
                f"Replaced {replaced_game.game_name if replaced_game is not None else ''} with ({game_that_replaced.game_name})" 
                + f"[https://cedb.me/game/{game_that_replaced.ce_id}]."
            )

    view = discord.ui.View(timeout=None)
    view.add_item(SetRollDropdown(roll))

    return await interaction.followup.send("Select which game you'd like to replace.", view=view, ephemeral=True)
"""


"""
#   ____    _   _     __  __   ______    _____    _____               _____   ______ 
#  / __ \  | \ | |   |  \/  | |  ____|  / ____|  / ____|     /\      / ____| |  ____|
# | |  | | |  \| |   | \  / | | |__    | (___   | (___      /  \    | |  __  | |__   
# | |  | | | . ` |   | |\/| | |  __|    \___ \   \___ \    / /\ \   | | |_ | |  __|  
# | |__| | | |\  |   | |  | | | |____   ____) |  ____) |  / ____ \  | |__| | | |____ 
#  \____/  |_| \_|   |_|  |_| |______| |_____/  |_____/  /_/    \_\  \_____| |______|
@client.event
async def on_message(message : discord.Message) :
    "This runs for every message that is sent. This might get fucked."

    if message.author.bot : return
    
    if message.channel.id == hm.PROOF_SUBMISSIONS_ID :
        "The message is in the #proof-submissions channel."

        # pull the user
        database_user = await Mongo_Reader.get_mongo_users()
        user = Discord_Helper.get_user_by_discord_id(message.author.id, database_user)
        
        # scenario 2: is registered but forget link
        if "cedb.me/user" not in message.content and user is not None :
            await message.channel.send(f"https://cedb.me/user/{user.ce_id}/")
        
        # scenario 3: is not registered but sends link
        elif "cedb.me/user" in message.content and user is None :
            ""
        
        # scenario 4: is not registered and forgets link
        elif "cedb.me/user" not in message.content and user is not None :
            content = message.content
            await message.delete()
            try :
                await message.author.send(f"Your message was removed because you forgot")
            except :
                ""
"""

#   ____    _   _     _____    ______              _____   __     __
#  / __ \  | \ | |   |  __ \  |  ____|     /\     |  __ \  \ \   / /
# | |  | | |  \| |   | |__) | | |__       /  \    | |  | |  \ \_/ / 
# | |  | | | . ` |   |  _  /  |  __|     / /\ \   | |  | |   \   /  
# | |__| | | |\  |   | | \ \  | |____   / ____ \  | |__| |    | |   
#  \____/  |_| \_|   |_|  \_\ |______| /_/    \_\ |_____/     |_|   

# ---- on ready function ----
@client.event
async def on_ready() :
    # sync commands
    await tree.sync(guild = guild)

    # set up channels
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)

    # send online update
    await private_log_channel.send(f":arrows_counterclockwise: bot started at <t:{hm.get_unix('now')}>")
    
    # master loop
    if hm.IN_CE or True :
        await master_loop.start(client)


client.run(discord_token)