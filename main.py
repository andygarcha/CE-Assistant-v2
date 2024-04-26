# -------- discord imports -----------
import discord
from discord import app_commands

# -------- json imports ----------
import json

# --------- local class imports --------
from CE_User import CE_User
from CE_User_Game import CE_User_Game
from CE_User_Objective import CE_Objective
from CE_Game import CE_Game
from CE_Objective import CE_Objective
from CE_Roll import CE_Roll
import CE_API_Reader



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
    

# on ready function
@client.event
async def on_ready() :
    await tree.sync(guild = guild)
    log_channel = client.get_channel(1)
    await log_channel.send("The bot has now been restarted.")