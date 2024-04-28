# -------- discord imports -----------
import discord
from discord import app_commands

# -------- json imports ----------
import json

# --------- local class imports --------
from CE_User import CEUser
from CE_User_Game import CEUserGame
from CE_User_Objective import CEObjective
from CE_Game import CEGame
from CE_Objective import CEObjective
from CE_Roll import CERoll, _roll_event_names
import CEAPIReader
import Mongo_Reader
from FailedScrapeException import FailedScrapeException



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
with open('Jasons/secret_info.json') as f :
    local_json_data = json.load(f)
    if in_ce :
        discord_token = local_json_data['discord_token']
        guild_id = local_json_data['ce_guild_ID']
    else :
        discord_token = local_json_data['third_discord_token']
        guild_id = local_json_data['test_guild_id']

# set up client
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=guild_id)

# register command
@tree.command(name = "register", description = "Register with CE Assistant to unlock all features!", guild = guild)
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
            if objective.get_name() in _roll_event_names :
                ce_user.add_completed_roll(CERoll(objective.get_name(), None, None, None, None, None, None, None))

    # add the user to users and dump it
    users.append(ce_user)
    await Mongo_Reader.dump_users(users)

        



# on ready function
@client.event
async def on_ready() :
    await tree.sync(guild = guild)
    log_channel = client.get_channel(1)
    await log_channel.send("The bot has now been restarted.")