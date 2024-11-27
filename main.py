# -------- discord imports -----------
import datetime
from enum import Enum
import math
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
from Classes.OtherClasses import CEInput, SteamData, CECompletion, RAData
from Modules import WebInteractor
import Modules.CEAPIReader as CEAPIReader
from Modules.WebInteractor import master_loop
import Modules.hm as hm
import Modules.Mongo_Reader as Mongo_Reader
import Modules.Discord_Helper as Discord_Helper
import Modules.SpreadsheetHandler as SpreadsheetHandler
from Exceptions.FailedScrapeException import FailedScrapeException
from commands import load_commands

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

load_commands.load_commands(client, tree, guild)

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

    from Modules import Reformatter



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
    users = await Mongo_Reader.get_database_user()
    
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
        ce_user.add_completed_roll(roll)

    # add the user to users and dump it
    await Mongo_Reader.dump_user(ce_user)

    # get the role and attach it
    cea_registered_role = discord.utils.get(interaction.guild.roles, name = "CEA Registered")
    await interaction.user.add_roles(cea_registered_role)

    # send a message to log
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":arrow_up: new user registered: <@{interaction.user.id}>: https://cedb.me/user/{ce_id}")

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
    users = await Mongo_Reader.get_database_user()
    
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
    await Mongo_Reader.dump_user(ce_user)

    # get the role and attach it
    cea_registered_role = discord.utils.get(interaction.guild.roles, name = "CEA Registered")
    await user.add_roles(cea_registered_role)

    # send a message to log
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":arrow_up: new user registered: <@{user.id}>: https://cedb.me/user/{ce_id}")

    # and return.
    return await interaction.followup.send(f"<@{user.id}> been successfully registered. " + 
                                           "Please make sure they received the CEA Registered role!")













#   _____    _____   _____               _____    ______ 
#  / ____|  / ____| |  __ \      /\     |  __ \  |  ____|
# | (___   | |      | |__) |    /  \    | |__) | | |__   
#  \___ \  | |      |  _  /    / /\ \   |  ___/  |  __|  
#  ____) | | |____  | | \ \   / ____ \  | |      | |____ 
# |_____/   \_____| |_|  \_\ /_/    \_\ |_|      |______|



"""
# ---- scrape function ----

@tree.command(name="scrape", description=("Replace database_name with API data WITHOUT sending messages. RUN WHEN NECESSARY."), guild=guild)
async def scrape(interaction : discord.Interaction) :
    await interaction.response.defer()

    # log this interaction
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":white_large_square: dev command run by <@{interaction.user.id}>: /scrape",
                             allowed_mentions=discord.AllowedMentions.none())

    user_list = await Mongo_Reader.get_list("user")
    database_user = await CEAPIReader.get_api_users_all(user_list)
    database_name = await CEAPIReader.get_api_games_full()

    for user in database_user :
        await Mongo_Reader.dump_user(user)

    for game in database_name :
        await Mongo_Reader.dump_game(game)

    return await interaction.followup.send("Database replaced.")
"""


#   _____               _____   _____   _   _    ____       _____    _____    ____    _____    ______ 
#  / ____|     /\      / ____| |_   _| | \ | |  / __ \     / ____|  / ____|  / __ \  |  __ \  |  ____|
# | |         /  \    | (___     | |   |  \| | | |  | |   | (___   | |      | |  | | | |__) | | |__   
# | |        / /\ \    \___ \    | |   | . ` | | |  | |    \___ \  | |      | |  | | |  _  /  |  __|  
# | |____   / ____ \   ____) |  _| |_  | |\  | | |__| |    ____) | | |____  | |__| | | | \ \  | |____ 
#  \_____| /_/    \_\ |_____/  |_____| |_| \_|  \____/    |_____/   \_____|  \____/  |_|  \_\ |______|

update_casino_score_options = Literal["INCREASE", "DECREASE", "SET"]
@tree.command(name="manual-update-casino-score", description="Update any user's casino score.", guild=guild)
@app_commands.describe(member="The user you'd like to update the casino score for.")
@app_commands.describe(value="The increase, decrease, or new value for the user's casino score.")
@app_commands.describe(type="Whether you'd like to increase, decrease, or set the user's casino score to value.")
async def manual_update_casino_score(interaction : discord.Interaction, member : discord.Member, value : int, type : update_casino_score_options) :
    await interaction.response.defer(ephemeral=True)

    await interaction.followup.send("Not Implemented.")




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

    if hm.IN_CE :
        if datetime.datetime.now().minute < 30 and datetime.datetime.now().minute >= 25 :
            return await interaction.followup.send('this loop will run in less than five minutes. please wait!')
        if datetime.datetime.now().minute >= 30 and datetime.datetime.now().minute < 35 :
            return await interaction.followup.send('this loop is probably running now! please wait...')

    await interaction.followup.send("looping...")

    # log this interaction
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":white_large_square: dev command run by <@{interaction.user.id}>: /initiate-loop",
                             allowed_mentions=discord.AllowedMentions.none())

    await master_loop(client, guild_id)

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
    database_name = await Mongo_Reader.get_database_name()
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

    chosen_game = await Mongo_Reader.get_game(game)
    if chosen_game is None : return await interaction.followup.send("Sorry, I encountered a strange error. Try again later!")

    # pull the game embed
    database_name = await Mongo_Reader.get_database_name()
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

    game = await Mongo_Reader.get_game(ce_id)
    if game is None :
        return await interaction.followup.send('game not found')
    else :
        return await interaction.followup.send(game)




"""
@tree.command(name='set-color', description='Set your discord username color!', guild=guild)
async def set_color(interaction : discord.Interaction) :
    "Sets the color."
    await interaction.response.defer(ephemeral=True)

    # pull database_user and get the user
    database_user = await Mongo_Reader.get_database_user()
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
"""





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
    database_name = await Mongo_Reader.get_database_name()

    # check to see if they asked for info on another person.
    asked_for_friend : bool = True
    if user is None :
        user = interaction.user
        asked_for_friend = False

    # make sure they're registered
    ce_user = await Mongo_Reader.get_user(user.id, use_discord_id=True)
    if ce_user is None and asked_for_friend : 
        return await interaction.followup.send(f"Sorry! <@{user.id}> is not registered. Please have them run /register!", 
                                               allowed_mentions=discord.AllowedMentions.none())
    if ce_user is None and not asked_for_friend :
        return await interaction.followup.send("Sorry! You are not registered. Please run /register and try again!")
    
    # get the embed and the view
    returns = Discord_Helper.get_user_embeds(user=ce_user, database_name=database_name)
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
                     current : bool = False, completed : bool = False, pending : bool = False) :
    await interaction.response.defer()

    # log this interaction
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":white_large_square: dev command run by <@{interaction.user.id}>: /clear-roll, "
                     + f"params: member=<@{member.id}>, roll_name={roll_name}, current={current}, completed={completed}, "
                     + f"pending={pending}", allowed_mentions=discord.AllowedMentions.none())

    # get database user and the user
    user = await Mongo_Reader.get_user(member.id, use_discord_id=True)

    if current : user.remove_current_roll(roll_name)
    if completed : user.remove_completed_rolls(roll_name)
    if pending : user.remove_pending(roll_name)

    await Mongo_Reader.dump_user(user)
    return await interaction.followup.send("Done!")

@tree.command(name='force-add', description="Force add a roll to a user's completed rolls section.", guild=guild)
async def force_add(interaction : discord.Interaction, member : discord.Member, roll_name : hm.ALL_ROLL_EVENT_NAMES) :
    await interaction.response.defer()

    # log this interaction
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":white_large_square: dev command run by <@{interaction.user.id}>: /force-add, "
                     + f"params: member=<@{member.id}>, roll_name={roll_name}", 
                     allowed_mentions=discord.AllowedMentions.none())
    
    # get database user and the user
    user = await Mongo_Reader.get_user(member.id, use_discord_id=True)

    user.add_completed_roll(CERoll(
        roll_name=roll_name,
        user_ce_id=user.ce_id,
        games=None
    ))

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
    database_name = await Mongo_Reader.get_database_name()
    database_user = await Mongo_Reader.get_database_user()

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

            database_name = await Mongo_Reader.get_database_name()

            # go through and find that id and swap it out
            for i, rollgameid in enumerate(self.__roll.games) :
                if rollgameid == game_id : self.__roll._games[i] = self.__replacement_id
            
            # pull database name
            database_user = await Mongo_Reader.get_database_user()

            # get the user and replace the roll
            user = hm.get_item_from_list(self.__roll.user_ce_id, database_user)
            user.update_current_roll(self.__roll)

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
        database_user = await Mongo_Reader.get_database_user()
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
    
    # https://patorjk.com/software/taag/#p=display&h=0&v=0&f=Big&t=TEST
"""


#  _____   _   _   _____    _    _   _______ 
# |_   _| | \ | | |  __ \  | |  | | |__   __|
#   | |   |  \| | | |__) | | |  | |    | |   
#   | |   | . ` | |  ___/  | |  | |    | |   
#  _| |_  | |\  | | |      | |__| |    | |   
# |_____| |_| \_| |_|       \____/     |_|   

"""
An example of how the new input MongoDB document will look.
[
    {
        "ce-id" : "c23a06b2-9fc7-49ed-9b34-05e012cdd19a",
        "value" : [
            {
                "objective-ce-id" : "97f8da7d-26b6-4103-a387-3d969b51fc4e",
                "evaluations" : [
                    {
                        "user-ce-id" : "d7cb0869-5ed9-465c-87bf-0fb95aaebbd5",
                        "recommendation" : 20
                    },
                    {
                        "user-ce-id" : "df0a0319-c1be-4a22-9152-4267216832d1",
                        "recommendation" : 35
                    }
                ]
            },
            {
                "objective-ce-id" : "d30facc3-214c-4357-92bc-d61f0c595e81",
                "evaluations" : [
                    {
                        "user-ce-id" : "d7cb0869-5ed9-465c-87bf-0fb95aaebbd5",
                        "recommendation" : 15
                    },
                    {
                        "user-ce-id" : "df0a0319-c1be-4a22-9152-4267216832d1",
                        "recommendation" : 20
                    }
                ]
            }
        ],

        "curate" : [
            {
                "user-ce-id" : "d7cb0869-5ed9-465c-87bf-0fb95aaebbd5",
                "curate" : True
            },
            {
                "user-ce-id" : "df0a0319-c1be-4a22-9152-4267216832d1",
                "curate" : True
            }
        ],

        "tags" : [
            {
                "user-ce-id" : "d7cb0869-5ed9-465c-87bf-0fb95aaebbd5",
                "tags" : [
                    "A",
                    "B",
                    "F"
                ]
            },
            {
                "user-ce-id" : "df0a0319-c1be-4a22-9152-4267216832d1",
                "tags" : [
                    "C",
                    "D",
                    "E",
                    "F",
                    "G"
                ]
            }
        ]

    }
]

"""

INPUT_MESSAGES_ARE_EPHEMERAL : bool = True

# -- value --
class ValueModal(discord.ui.Modal) :
    def __init__(self, game : CEGame, objective : CEObjective) :
        self.__game = game
        self.__objective = objective
        
        title = f"Value Input for {objective.name}"
        if len(title) >= 45 : super().__init__(title="Value Input")
        else : super().__init__(title=f"Value Input for {objective.name}")

    new_value = discord.ui.TextInput(
        label=f"Revalue Objective",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=4,
        required=True,
        placeholder=f"Proposed value"
    )
    
    def __is_valid_recommendation(self, input : int, value : int) -> bool :
        "Returns true if the input is within the valid range for the objective."
        # imports
        import Modules.hm as hm

        # if value <= VALUE_LIMIT_X, check if within RANGE_LIMIT_X
        VALUE_LIMIT_0 = 10
        RANGE_LIMIT_0 = 200
        VALUE_LIMIT_1 = 35
        RANGE_LIMIT_1 = 100
        RANGE_LIMIT_2 = 50

        if value <= VALUE_LIMIT_0 : return hm.is_within_percentage(input, RANGE_LIMIT_0, value)
        if value <= VALUE_LIMIT_1 : return hm.is_within_percentage(input, RANGE_LIMIT_1, value)
        return hm.is_within_percentage(input, RANGE_LIMIT_2, value)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # make sure the recommendation was actually a number
        if not self.new_value.value.isdigit() :
            return await interaction.followup.send(
                f"{self.new_value.value} is not a number. Try again.",
                ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
            )

        # make sure the recommendation was within 50% of the objective's value
        objective_point_value = self.__objective.point_value
        proposed_value = int(self.new_value.value)

        # make sure we recommended a positive number
        if proposed_value < 0 :
            return await interaction.followup.send(
                f"You cannot recommend a negative number! Please try again."
            )

        # make sure the recommendation was within valid percentage range of the objective's value
        if not self.__is_valid_recommendation(proposed_value, objective_point_value) :
            return await interaction.followup.send(
                f"Your evaluation of {proposed_value} is outside of the recommendable range. Please try again, "
                + "or DM a mod if you believe this is wrong.",
                ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
            )

        if float(abs(objective_point_value - proposed_value)) > (float(objective_point_value) / 2.0) :
            return await interaction.followup.send(
                f"Your evaluation of {self.__game.game_name}'s {self.__objective.get_type_short()} " +
                f"{self.__objective.name} at {self.new_value} is outside of the 50% range. Please try again or " +
                "DM a mod if you believe this is wrong.",
                ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
            )
        
        # make sure its divisible by 5 too lol
        if (int(self.new_value.value) % 5 != 0) :
            return await interaction.followup.send(
                f"{self.new_value.value} is not divisible by 5.",
                ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
            )
        
        # pull databases
        database_name = await Mongo_Reader.get_database_name()

        # grab the current input. we can guarantee this exists because we set it up previously.
        curr_input = await Mongo_Reader.get_input(self.__game.ce_id)
        value_input = curr_input.get_value_input(objective_id=self.__objective.ce_id)

        # we now need to check if our average has changed enough to enter scary territory
        old_average = value_input.average_is_okay(
            database_name, self.__game.ce_id
        )

        # add the value input for the newly grabbed data.
        curr_input.add_value_input(
            objective_id=self.__objective.ce_id,
            user_id=(await Mongo_Reader.get_user(interaction.user.id, use_discord_id=True)).ce_id,
            value=int(self.new_value.value)
        )

        # and dump it back to mongo
        await Mongo_Reader.dump_input(curr_input)

        # now lets grab the new average
        new_average = value_input.average_is_okay(
            database_name, self.__game.ce_id
        )

        # and if the old average was okay, but the new average is not, send a message to the input channel.
        if old_average and not new_average :
            log_channel = client.get_channel(hm.INPUT_LOG_ID)

            await log_channel.send(
                f":bell: Alert! {self.__game.name_with_link()}'s PO {self.__objective.name} " +
                f"({self.__objective.point_value} points) has an average evaluation of {value_input.average()} points."
            )

        # return a quick little confirmation message
        return await interaction.followup.send(
            f"You've valued {self.__game.name_with_link()}'s " +
            f"{self.__objective.get_type_short()} '{self.__objective.name}' at {self.new_value} points.",
            ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
        )
    




class ValueDropdown(discord.ui.Select) :
    def __init__(self, game : CEGame, valid_objectives : list[CEObjective]) :

        options : list[discord.SelectOption] = []
        for po in valid_objectives :
            options.append(discord.SelectOption(label=po.name, value=po.ce_id, description=f"Current value: {po.point_value}"))

        self.__game = game

        super().__init__(placeholder="Choose an Objective.", min_values=1, max_values=1, options=options)
    
    @property
    def game(self) :
        "The game that this dropdown is associated with."
        return self.__game

    async def callback(self, interaction : discord.Interaction) : 
        objective_object = self.game.get_objective(self.values[0])
        await interaction.response.send_modal(ValueModal(self.game, objective_object))





class ValueButtonView(discord.ui.View) :
    def __init__(self, game : CEGame, valid_objectives : list[CEObjective]) :
        self.__game = game
        super().__init__(timeout=600)

        self.add_item(ValueDropdown(game, valid_objectives))
    
    @property
    def game(self) :
        "The game that's being re-evaluated."
        return self.__game

    async def on_timeout(self) -> NoneType:
        return await super().on_timeout()






# -- curate --
class CurateButtonYesOrNoView(discord.ui.View) :
    def __init__(self, has_selected_yes : bool, has_selected_no : bool, game_id : str) :
        self.__has_selected_yes = has_selected_yes
        self.__has_selected_no = has_selected_no
        self.__game_id = game_id
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction : discord.Interaction, button : discord.ui.Button) :
        await interaction.response.defer()

        # pull from mongo
        input_object = await Mongo_Reader.get_input(self.game_id)
        game_object = await Mongo_Reader.get_game(self.game_id)

        old_curatable = input_object.is_curatable()

        # add the curate input
        input_object.add_curate_input(
            (await Mongo_Reader.get_user(interaction.user.id, use_discord_id=True)).ce_id,
            True
        )

        new_curatable = input_object.is_curatable()

        # and push back to mongo
        await Mongo_Reader.dump_input(input_object)

        # log
        if not old_curatable and new_curatable :
            input_channel = client.get_channel(hm.INPUT_LOG_ID)
            await input_channel.send(
                f":bell: Alert! {game_object.name_with_link()} has been voted curatable! " +
                f"Curate percentage: {input_object.average_curate()}, votes: {input_object.curator_count()}."
            )

        # now return a confirmation message
        return await interaction.followup.edit_message(
            message_id=interaction.message.id,
            content="You have voted 'Yes'!",
            view = discord.ui.View()
        )
    
    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction : discord.Interaction, button : discord.ui.Button) :
        await interaction.response.defer()

        # pull from mongo
        input_object = await Mongo_Reader.get_input(self.game_id)
        game_object = await Mongo_Reader.get_game(self.game_id)

        old_curatable = input_object.is_curatable()

        # add the curate input
        input_object.add_curate_input(
            (await Mongo_Reader.get_user(interaction.user.id, use_discord_id=True)).ce_id,
            False
        )

        new_curatable = input_object.is_curatable()

        # and push back to mongo
        await Mongo_Reader.dump_input(input_object)

        # log
        if old_curatable and not new_curatable :
            input_channel = client.get_channel(hm.INPUT_LOG_ID)
            await input_channel.send(
                f":bell: Alert! {game_object.name_with_link()}'s curatable status has been removed! " +
                f"Curate percentage: {input_object.average_curate()}, votes: {input_object.curator_count()}."
            )
        
        # send a confirmation message
        return await interaction.followup.edit_message(
            message_id=interaction.message.id,
            content="You have voted 'No'!",
            view=discord.ui.View()
        )

    @property
    def has_selected_yes(self) :
        "This user has selected yes in the past."
        return self.__has_selected_yes
    
    @property
    def has_selected_no(self) :
        "This user has selected no in the past."
        return self.__has_selected_no
    
    @property
    def game_id(self) :
        "The game ID."
        return self.__game_id

    def message(self) :
        "The message that should be sent with the curate message."
        if self.has_selected_yes : return "Would you recommend this game for the curator? (You previously said 'Yes')."
        if self.has_selected_no : return "Would you recommend this game for the curator? (You previously said 'No')."
        return "Would you recommend this game for the curator?"
        






# -- input --
class GameInputView(discord.ui.View) :
    "This view will be sent along with any /input command."

    def __init__(self, ce_id : str) :
        self.__ce_id = ce_id
        super().__init__(timeout = None)

    @property
    def ce_id(self) :
        """The CE ID of the game that this command was run with."""
        return self.__ce_id
    
    @staticmethod
    def set_up_input(game_id : str) -> list[CEInput] :
        return CEInput(
                game_ce_id=game_id,
                value_inputs=[],
                curate_inputs=[],
                tag_inputs=[]
            )

    @discord.ui.button(label="Value")
    async def value_button(self, interaction : discord.Interaction, button : discord.ui.Button) :
        await interaction.response.defer()

        # pull from mongo
        game = await Mongo_Reader.get_game(self.ce_id)
        user = await Mongo_Reader.get_user(interaction.user.id, use_discord_id=True)

        # if this game hasn't been evaluated yet, add it to `inputs`.
        found = await Mongo_Reader.get_input(self.ce_id) != None
        
        if not found : 
            new_input = self.set_up_input(game.ce_id)
            await Mongo_Reader.dump_input(new_input)

        # go through objectives and only let users select POs they've completed
        valid_objectives : list[CEObjective] = []
        for objective in game.get_primary_objectives() :
            if user.get_owned_game(game.ce_id).has_completed_objective(objective.ce_id, objective.point_value) :
                valid_objectives.append(objective)
        
        # if they haven't completed any of the objectives, then don't let them vote!
        if valid_objectives == [] :
            return await interaction.followup.send(
                f"You haven't completed any objectives in {game.game_name}!",
                ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
            )

        # if they have, then send them to the next view.
        return await interaction.followup.send(
            "Select an objective to revalue!", 
            view=ValueButtonView(
                game=game,
                valid_objectives=valid_objectives
            ),
            ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
        )

    
    @discord.ui.button(label="Curate")
    async def curate_button(self, interaction : discord.Interaction, button : discord.ui.Button) :
        await interaction.response.defer()

        # pull from mongo
        game = await Mongo_Reader.get_game(self.ce_id)
        user = await Mongo_Reader.get_user(interaction.user.id, use_discord_id=True)

        # if this game hasn't been evaluated yet, add it to `inputs`.
        found = await Mongo_Reader.get_input(self.ce_id) != None
        
        if not found : 
            new_input = self.set_up_input(game.ce_id)
            await Mongo_Reader.dump_input(new_input)

        # grab the input object itself
        input_object = await Mongo_Reader.get_input(game.ce_id)

        view = CurateButtonYesOrNoView(
            input_object.user_has_selected_yes(user.ce_id), 
            input_object.user_has_selected_no(user.ce_id),
            game.ce_id
        )
        await interaction.followup.send(view.message(), view=view, ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL)

    @discord.ui.button(label="Tags", disabled=True)
    async def tags_button(self, interaction : discord.Interaction, button : discord.ui.Button) :
        await interaction.response.defer()
        await interaction.followup.send("Tags have not yet been released!.", ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL)







@tree.command(name="input", description="Send in input on any CE game.", guild=guild)
@app_commands.describe(game="The game you'd like to provide input on.")
@app_commands.autocomplete(game=get_game_auto)
async def game_input(interaction : discord.Interaction, game : str) :
    await interaction.response.defer(ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL)

    game_object = await Mongo_Reader.get_game(game)
    user = await Mongo_Reader.get_user(interaction.user.id, use_discord_id=True)

    # make sure a valid game was passed
    if game_object is None : 
        return await interaction.followup.send(
            f"{game} is not a valid game.",
            ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
        )

    # make sure the user owns the game
    if not user.owns_game(game_object.ce_id) : 
        return await interaction.followup.send(
            f"You don't own {game_object.game_name}!",
            ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
        )
    
    # set up the message
    content = f"Game chosen: {game_object.name_with_link()}"
    database_name = await Mongo_Reader.get_database_name()
    if user.has_completed_game(game_object.ce_id, database_name) : content += hm.get_emoji('Crown')
    content += "."

    # and send it.
    return await interaction.followup.send(
        content, 
        view=GameInputView(game),
        ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
    )

@tree.command(name="check-inputs", description="View any previous inputs from a CE game.", guild=guild)
@app_commands.describe(game="The game you'd like to see previous input in.")
@app_commands.describe(simple="Whether you want the full report or the simple version.")
@app_commands.autocomplete(game=get_game_auto)
async def check_inputs(interaction : discord.Interaction, game : str, simple : bool) :
    await interaction.response.defer()

    # pull from mongo
    game_object = await Mongo_Reader.get_game(game)
    input_object = await Mongo_Reader.get_input(game)

    # make sure a valid game was passed
    if game_object is None : 
        return await interaction.followup.send(
            f"{game} is not a valid game.",
            ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
        )
    
    # check to see if any inputs have even been provided.
    if (input_object is None) :
        return await interaction.followup.send(
            f"No inputs have been provided on {game_object.name_with_link()}.",
            ephemeral=INPUT_MESSAGES_ARE_EPHEMERAL
        )
    
    # now get the actual to_string()
    database_user = await Mongo_Reader.get_database_user()
    database_name = await Mongo_Reader.get_database_name()
    if not simple : input_object_string = input_object.to_string(database_name, database_user)
    else : input_object_string = input_object.to_string_simple(database_name)

    # check if it needs to be sent as a file
    if len(input_object_string) > 2000 :
        with io.BytesIO() as file :
            file.write(input_object_string.encode())
            file.seek(0)

            return await interaction.followup.send(
                file=discord.File(file, filename="input_message.txt")
            )

    return await interaction.followup.send(
        input_object_string
    )



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
    await private_log_channel.send(f":arrow_right_hook: bot started at <t:{hm.get_unix('now')}>")
    
    # master loop
    if hm.IN_CE :
        await master_loop.start(client, guild_id)


client.run(discord_token)