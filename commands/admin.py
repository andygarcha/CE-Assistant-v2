"""This module contains all the admin commands for the bot."""
import datetime
import discord
from discord import app_commands
from Classes.CE_Roll import CERoll
from Modules.WebInteractor import master_loop
from commands.user import register
from Modules import CEAPIReader, Mongo_Reader, hm


def setup(cli : discord.Client, tree : app_commands.CommandTree, gui : discord.Guild) :
    global client, guild
    client = cli
    guild = gui

    # ---- test command ----
    @tree.command(name='test', description='test',guild=guild)
    async def test_command(interaction : discord.Interaction) :
        await test(interaction)
        pass

    # ---- force-register command ----
    @tree.command(name='force-register', description='Register another user with CE Assistant!', guild=guild)
    @app_commands.describe(ce_link="The link to their CE page (or their ID, either works)")
    @app_commands.describe(user="The user you want to link this page (or ID) to.")
    async def force_register_command(interaction : discord.Interaction, ce_link : str, user : discord.Member) :
        await register(interaction, ce_link, user)

    # ---- scrape command ----
    """
    @tree.command(name="scrape", description=("Replace database_name with API data WITHOUT sending messages. RUN WHEN NECESSARY."), guild=guild)
    async def scrape_command(interaction : discord.Interaction) :
        await scrape(interaction)
    """

    # ---- initiate loop command ----
    @tree.command(name="initiate-loop", description="Initiate the loop. ONLY RUN WHEN NECESSARY.", guild=guild)
    async def initiate_loop_command(interaction : discord.Interaction) :
        await loop(interaction)

    # ---- add notes command ----
    @tree.command(name="add-notes", description="Add notes to any #game-additions post.", guild=guild)
    @app_commands.describe(embed_id="The Message ID of the message you'd like to add notes to.")
    @app_commands.describe(notes="The notes you'd like to append.")
    @app_commands.describe(clear="Set this to true if you want to replace all previous notes with this one.")
    async def add_notes_command(interaction : discord.Interaction, embed_id : str, notes : str, clear : bool) :
        await add_notes(interaction, embed_id, notes, clear)


    # ---- clear roll command ----
    @tree.command(name="clear-roll", description="Clear any user's current/completed rolls, cooldowns, or pendings.", guild=guild)
    async def clear_roll_command(interaction : discord.Interaction, member : discord.Member, roll_name : hm.ALL_ROLL_EVENT_NAMES, 
                     current : bool = False, completed : bool = False, pending : bool = False) :
        await clear_roll(interaction, member, roll_name, current, completed, pending)

    
    # ---- force add command ----
    @tree.command(name='force-add', description="Force add a roll to a user's completed rolls section.", guild=guild)
    async def force_add_command(interaction : discord.Interaction, member : discord.Member, roll_name : hm.ALL_ROLL_EVENT_NAMES) :
        await force_add(interaction, member, roll_name)
    pass




#  _______   ______    _____   _______ 
# |__   __| |  ____|  / ____| |__   __|
#    | |    | |__    | (___      | |   
#    | |    |  __|    \___ \     | |   
#    | |    | |____   ____) |    | |   
#    |_|    |______| |_____/     |_|   



async def test(interaction : discord.Interaction) :
    await interaction.response.defer()

    from Modules import Mongo_Reader
    from Modules import hm

    database_input = await Mongo_Reader.get_database_input()
    print(database_input)

    return await interaction.followup.send('testsss done')



#   _____    _____   _____               _____    ______ 
#  / ____|  / ____| |  __ \      /\     |  __ \  |  ____|
# | (___   | |      | |__) |    /  \    | |__) | | |__   
#  \___ \  | |      |  _  /    / /\ \   |  ___/  |  __|  
#  ____) | | |____  | | \ \   / ____ \  | |      | |____ 
# |_____/   \_____| |_|  \_\ /_/    \_\ |_|      |______|



# ---- scrape function ----

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



#  _____   _   _   _____   _______   _____              _______   ______     _         ____     ____    _____  
# |_   _| | \ | | |_   _| |__   __| |_   _|     /\     |__   __| |  ____|   | |       / __ \   / __ \  |  __ \ 
#   | |   |  \| |   | |      | |      | |      /  \       | |    | |__      | |      | |  | | | |  | | | |__) |
#   | |   | . ` |   | |      | |      | |     / /\ \      | |    |  __|     | |      | |  | | | |  | | |  ___/ 
#  _| |_  | |\  |  _| |_     | |     _| |_   / ____ \     | |    | |____    | |____  | |__| | | |__| | | |     
# |_____| |_| \_| |_____|    |_|    |_____| /_/    \_\    |_|    |______|   |______|  \____/   \____/  |_|     




# ---- initiate loop ----

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

    await master_loop(client, guild.id)

    return await interaction.followup.send('loop complete.')


#             _____    _____      _   _    ____    _______   ______    _____ 
#     /\     |  __ \  |  __ \    | \ | |  / __ \  |__   __| |  ____|  / ____|
#    /  \    | |  | | | |  | |   |  \| | | |  | |    | |    | |__    | (___  
#   / /\ \   | |  | | | |  | |   | . ` | | |  | |    | |    |  __|    \___ \ 
#  / ____ \  | |__| | | |__| |   | |\  | | |__| |    | |    | |____   ____) |
# /_/    \_\ |_____/  |_____/    |_| \_|  \____/     |_|    |______| |_____/ 





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


#   _____   _        ______              _____  
#  / ____| | |      |  ____|     /\     |  __ \ 
# | |      | |      | |__       /  \    | |__) |
# | |      | |      |  __|     / /\ \   |  _  / 
# | |____  | |____  | |____   / ____ \  | | \ \ 
#  \_____| |______| |______| /_/    \_\ |_|  \_\



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