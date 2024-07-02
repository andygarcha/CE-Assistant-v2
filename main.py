# -------- discord imports -----------
import datetime
import time
from types import NoneType
import discord
from discord import app_commands

# -------- json imports ----------
import json
from typing import Literal, get_args

import requests

# --------- local class imports --------
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
        discord_token = local_json_data['third_discord_token']
        guild_id = local_json_data['test_guild_ID']

# set up client
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=guild_id)

# ------------------------------ commands -------------------------------------

# ---- test command ----
@tree.command(name='test', description='test',guild=guild)
async def test(interaction : discord.Interaction) :
    await interaction.response.defer()

    return await interaction.followup.send('test done')

@tree.command(name="prove", description="proive", guild=guild)
async def prove(interaction : discord.Interaction) :
    await interaction.response.defer()
    #await SpreadsheetHandler.dump_prove_yourselves()
    print('done"')
    return await interaction.followup.send('fjksda')



# ---- register command ----
@tree.command(name = "register", 
              description = "Register with CE Assistant to unlock all features!", 
              guild = guild)
@app_commands.describe(ce_id = "The link to your Challenge Enthusiasts profile!")
async def register(interaction : discord.Interaction, ce_id : str) : 
    await interaction.response.defer()

    # format correctly
    ce_id = ce_id.replace("https://","").replace("www.","").replace("cedb.me", "").replace("/","").replace("games","").replace("user","")
    if not (ce_id[8:9] == ce_id[13:14] == ce_id[18:19] == ce_id[23:24] == "-") :
        return await interaction.followup.send("An incorrect link was sent. Please try again.")

    # try and get database_user
    try :
        users = await Mongo_Reader.get_mongo_users()
    except FailedScrapeException :
        return await interaction.followup.send("There was an issue with the Challenge " 
                                               + "Enthusiast API. Please try again later.")
    
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
    ce_user.set_discord_id(interaction.user.id)

    # grab the user's pre-existing rolls
    challenge_enthusiast_game = (
        ce_user.get_owned_game("76574ec1-42df-4488-a511-b9f2d9290e5d"))
    if (challenge_enthusiast_game != None) :
        for objective in (challenge_enthusiast_game.get_user_community_objectives()) :
            if objective.name in get_args(hm.ALL_ROLL_EVENT_NAMES) :
                ce_user.add_completed_roll(CERoll(
                    roll_name=objective.name,
                    user_ce_id=ce_user.ce_id,
                    games=None,
                    partner_ce_id=None,
                    init_time=None,
                    due_time=None,
                    completed_time=None,
                    rerolls=None
                ))

    # add the user to users and dump it
    users.append(ce_user)
    await Mongo_Reader.dump_users(users)

    return await interaction.followup.send("You've been successfully registered!")




# ---- solo roll command ----
@tree.command(name = "solo-roll",
              description = "Roll a solo event with CE Assistant!",
              guild = guild)
@app_commands.describe(event_name = "The event you'd like to roll.")
async def solo_roll(interaction : discord.Interaction, event_name : hm.SOLO_ROLL_EVENT_NAMES) :
    await interaction.response.defer()
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

    match(event_name) :
        case "One Hell of a Day" :
            # -- grab games --
            rolled_games = [hm.get_rollable_game(
                database_name=database_name,
                completion_limit=10,
                price_limit=10,
                tier_number=1,
                user=user
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
                    already_rolled_games=rolled_games
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
                        already_rolled_games=rolled_games
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
                        already_rolled_games=r.games
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
                    completion_limit=20,
                    price_limit=20,
                    tier_number = 2,
                    user=user
                )]
        case "Two \"Two Week T2 Streak\" Streak" :
            if not user.has_completed_roll("Two Week T2 Streak") :
                return await interaction.followup.send(
                    f"You need to complete Two Week T2 Steak before rolling {event_name}!"
                )
            if user.has_current_roll("Two \"Two Week T2 Streak\" Streak") :
                # if the user is currently working 
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
                        already_rolled_games=r.games
                    ))
                    user.current_rolls[past_roll_index] = past_roll
                    database_user[user_index] = user

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


# ---- initiate loop ----
@tree.command(name="initiate-loop", description="Initiate the loop. ONLY RUN WHEN NECESSARY.", guild=guild)
async def loop(interaction : discord.Interaction) :
    await interaction.response.defer()

    await master_loop(client)

    return await interaction.followup.send('looping...')


@tree.command(name="get-game-data", description="return the local data on a game.", guild=guild)
async def get_game_data(interaction : discord.Interaction, ce_id : str) :
    await interaction.response.defer()

    database_name = await Mongo_Reader.get_mongo_games()

    for game in database_name :
        if game.ce_id == ce_id : return await interaction.followup.send(str(game))
    return await interaction.followup.send('game not found')

@tree.command(name="check-rolls", description="Check the status of your current and completed casino rolls!", guild=guild)
async def check_rolls(interaction : discord.Interaction) :
    # defer the message
    await interaction.response.defer()

    # create the view
    view = discord.ui.View(timeout=None)

    # add the buttons
    for roll_name in get_args(hm.ALL_ROLL_EVENT_NAMES) :
        # create the button
        button = discord.ui.Button(label=roll_name, style=discord.ButtonStyle.gray)

        print(roll_name)

        # designate its unique callback
        async def c(interaction : discord.Interaction) : return await show_rolls(interaction, roll=roll_name)
        button.callback = c

        view.add_item(button)

        del c
        

    # create the callback for each button
    async def show_rolls(interaction : discord.Interaction, roll : hm.ALL_ROLL_EVENT_NAMES) :
        # defer 
        await interaction.response.defer()

        def a(r=roll) :
            return r
        
        roll_name = a()

        # pull database_name and database_user
        database_name = await Mongo_Reader.get_mongo_games()
        database_user = await Mongo_Reader.get_mongo_users()

        # find the user
        for user in database_user :
            if user.discord_id == interaction.user.id : break

        # initialize the embed
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Rolls",
            description="",
            timestamp=datetime.datetime.now(),
            color=0x000000
        )

        # let them know if they are on cooldown.
        if user.has_cooldown(roll_name) : 
            embed.description = f"You are on cooldown for {roll_name} until <t:{user.get_cooldown_time(roll)}>."
        else :
            embed.description = f"You are not currently on cooldown for {roll_name}."

        # current rolls
        current_roll = user.get_current_roll(roll_name)
        string = ""
        if current_roll == None : string = f"You do not have a current roll in {roll_name}."
        else : string = current_roll.display_str(database_name=database_name, database_user=database_user)
        embed.add_field(name="Current Roll", value=string)

        # completed rolls
        completed_rolls = user.get_completed_rolls(roll_name)
        string = ""
        if completed_rolls == None : string = f"You do not have any completed rolls in {roll_name}."
        else :
            for completed_roll in completed_rolls :
                string += f"{completed_roll.display_str(database_name=database_name, database_user=database_user)}\n"
        embed.add_field(name="Completed Rolls", value=string)

        for button in view.children :
            button.disabled = False
            if button.label == roll_name :
                button.disabled = True

        return await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)

    # initialize the embed
    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Rolls",
        description="",
        timestamp=datetime.datetime.now(),
        color=0x000000
    )

    await interaction.followup.send(embed=embed, view=view)



# ---- on ready function ----
@client.event
async def on_ready() :
    # sync commands
    await tree.sync(guild = guild)

    # set up channels
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)

    # send online update
    await private_log_channel.send(f"bot started at <t:{hm.get_unix('now')}>")

client.run(discord_token)