# -------- discord imports -----------
import discord
from discord import app_commands

# -------- json imports ----------
import json
from typing import Literal, get_args

# --------- local class imports --------
from CE_User import CEUser
from CE_User_Game import CEUserGame
from CE_User_Objective import CEObjective
from CE_Game import CEGame
from CE_Objective import CEObjective
from CE_Roll import CERoll
import CEAPIReader
import hm
import Mongo_Reader
import Discord_Helper
from FailedScrapeException import FailedScrapeException

# ----------- to-be-sorted imports -------------
import random



# -------------------------------- normal bot code -----------------------------------

# set up intents
intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.guilds = True
intents.message_content = True

# parameters for me to change at any time
in_ce : bool = False


# open secret_info.json
with open('secret_info.json') as f :
    local_json_data = json.load(f)
    if in_ce :
        discord_token = local_json_data['discord_token']
        guild_id = local_json_data['ce_guild_ID']
    else :
        discord_token = local_json_data['third_discord_token']
        guild_id = local_json_data['test_guild_ID']

# set up client
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=guild_id)


# register command
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
        if user.get_discord_id() == interaction.user.id :
            return await interaction.followup.send("You are already registered in the " +
                                                   "CE Assistant database!")
        if user.get_ce_id() == ce_id : 
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
            if objective.get_name() in get_args(hm.roll_event_names) :
                ce_user.add_completed_roll(CERoll(
                    roll_name=objective.get_name(),
                    user_ce_id=ce_user.get_ce_id(),
                    games=None,
                    partner_ce_id=None,
                    cooldown_days=None,
                    init_time=None,
                    due_time=None,
                    completed_time=None,
                    rerolls=None
                ))

    # add the user to users and dump it
    users.append(ce_user)
    await Mongo_Reader.dump_users(users)

    return await interaction.followup.send("You've been successfully registered!")

        
@tree.command(name = "solo-roll",
              description = "Roll a solo event with CE Assistant!",
              guild = guild)
@app_commands.describe(event_name = "The event you'd like to roll.")
async def solo_roll(interaction : discord.Interaction, event_name : hm.solo_roll_event_names) :
    await interaction.response.defer()
    view = discord.ui.View(timeout=600)

    # pull mongo database
    database_user = await Mongo_Reader.get_mongo_users()
    database_name = await Mongo_Reader.get_mongo_games()

    user = None
    user_index = -1
    for i, u in enumerate(database_user) :
        if u.get_discord_id() == interaction.user.id :
            user = u
            user_index = i
            break

    if user == None :
        return await interaction.followup.send(
            "Sorry, you're not registered in the CE Assistant database. Please run `/register` first!"
        )
    if user.has_cooldown(event_name) :
        return await interaction.followup.send(
            f"You are currently on cooldown for {event_name} until {user.get_cooldown_time(event_name)}. "
        )
    if user.has_current_roll(event_name) :
        return await interaction.followup.send(
            f"You're currently attempting {event_name}! Please finish this instance before rerolling."
        )
    if user.has_pending(event_name) :
        return await interaction.followup.send(
            f"You just tried rolling this event. Please wait about 10 minutes before trying again."
        )
    
    if random.randint(0, 99) : "" #TODO: send a message to the log channel saying they've won jarvis's random thing

    match(event_name) :
        case "One Hell of a Day" :
            # -- grab games --
            rolled_game = hm.get_rollable_game(
                database_name=database_name,
                completion_limit=10,
                price_limit=10,
                tier_number=1,
                user=user
            )

            # -- create roll object --
            roll = CERoll(
                roll_name='One Hell of a Day',
                user_ce_id=user.get_ce_id(),
                games=[rolled_game],
                is_current=True
            )
            user.add_current_roll(roll)

            # -- create embeds --
            embeds = Discord_Helper.get_roll_embeds(
                roll=roll,
                database_name=database_name,
                database_user=database_user
            )
        
        case "One Hell of a Week" :
            # -- if the user hasn't done day, return --
            if not user.has_completed_roll('One Hell of a Day') :
                return await interaction.followup.send(
                    f"You need to complete One Hell of a Day before rolling {event_name}!"
                )
            
            # -- grab games --
            rolled_games : list[str] = []
            valid_categories = hm.get_categories()
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
                    hm.get_item_from_list(rolled_games[i], database_name).get_category()
                )

            # -- make roll object --
            roll = CERoll(
                roll_name='One Hell of a Week',
                user_ce_id=user.get_ce_id(),
                games=rolled_games,
                is_current=True
            )
            user.add_current_roll(roll)
            
            # -- get embeds --
            embeds = Discord_Helper.get_roll_embeds(
                roll=roll,
                database_name=database_name,
                database_user=database_user
            )

        case "One Hell of a Month" :
            # -- if user doesn't have week, return --
            if not user.has_completed_roll('One Hell of a Week') :
                return await interaction.followup.send(
                    f"You need to complete One Hell of a Week before rolling {event_name}!"
                )
            
            # -- grab games --
            rolled_games : list[str] = []
            valid_categories = hm.get_categories()
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
            
            # -- create roll object --
            roll = CERoll(
                roll_name="One Hell of a Month",
                user_ce_id=user.get_ce_id(),
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

# on ready function
@client.event
async def on_ready() :
    await tree.sync(guild = guild)
    log_channel = client.get_channel(788158122907926611)
    await log_channel.send("version 2 babyyyyy")

client.run(discord_token)