"""This module contains all the commands about users for the bot."""
import discord
from discord import app_commands

from Classes.CE_User import CEUser
from Modules import CEAPIReader, Discord_Helper, Mongo_Reader, hm


def setup(cli : discord.Client, tree : app_commands.CommandTree, gui : discord.Guild) :
    global client, guild
    client = cli
    guild = gui

    # ---- register command ----
    @tree.command(name = "register", 
                description = "Register with CE Assistant to unlock all features!", 
                guild = guild)
    @app_commands.describe(ce_id = "The link to your Challenge Enthusiasts profile.")
    async def register_command(interaction : discord.Interaction, ce_id : str) :
        await register(interaction, ce_id)
        pass

    @tree.command(name="profile", description="See information about you or anyone else in Challenge Enthusiasts!", guild=guild) 
    @app_commands.describe(user="The user you'd like to see information about (leave blank to see yourself!)")
    async def profile_command(interaction : discord.Interaction, user : discord.User = None) :
        await profile(interaction, user) 
    pass



#  _____    ______    _____   _____    _____   _______   ______   _____  
# |  __ \  |  ____|  / ____| |_   _|  / ____| |__   __| |  ____| |  __ \ 
# | |__) | | |__    | |  __    | |   | (___      | |    | |__    | |__) |
# |  _  /  |  __|   | | |_ |   | |    \___ \     | |    |  __|   |  _  / 
# | | \ \  | |____  | |__| |  _| |_   ____) |    | |    | |____  | | \ \ 
# |_|  \_\ |______|  \_____| |_____| |_____/     |_|    |______| |_|  \_\


async def register(interaction : discord.Interaction, ce_id : str, discord_user : discord.Member = None) : 
    """This command registers a user with CE Assistant. 
    Parameters:
        interaction (discord.Interaction): The interaction object.
        ce_id (str): The Challenge Enthusiast ID to register with.
        discord_user (discord.Member, optional): The user to link this CE ID to. Defaults to None.
        
        """
    await interaction.response.defer()

    # if a new user was sent in, then we need to log that it was a force-register
    if discord_user is not None :
        private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
        await private_log_channel.send(f":white_large_square: dev command run by <@{interaction.user.id}>: /force-register, "
                         + f"params: ce_link={ce_id}, user={discord_user.id}", allowed_mentions=discord.AllowedMentions.none())

    # format correctly
    ce_id = hm.format_ce_link(ce_id)
    if ce_id is None : return await interaction.followup.send(f"'{ce_id}' is not a valid link or ID. Please try again!")

    # get database_user
    users = await Mongo_Reader.get_database_user()
    
    # make sure they're not already registered
    for user in users :
        if user.discord_id == interaction.user.id :
            return await interaction.followup.send("This discord account is already registered in the " +
                                                   "CE Assistant database!")
        if user.ce_id == ce_id : 
            return await interaction.followup.send("This Challenge Enthusiast page is " +
                                                   "already connected to another account!")
    
    # grab their data from CE
    ce_user : CEUser = await CEAPIReader.get_api_page_data("user", ce_id)
    if ce_user == None :
        return await interaction.followup.send("This Challenge Enthusiast page was not found. " + 
                                               "Please try again later or contact andy.")
    
    # we need to account for a new discord user being sent in from force-register...
    if discord_user is not None : ce_user.discord_id = discord_user.id
    else : ce_user.discord_id = interaction.user.id

    # grab the user's pre-existing rolls
    rolls = ce_user.get_ce_rolls()
    for roll in rolls :
        ce_user.add_completed_roll(roll)

    # add the user to users and dump it
    await Mongo_Reader.dump_user(ce_user)

    # get the role and attach it
    cea_registered_role = discord.utils.get(interaction.guild.roles, name = "CEA Registered")
    if discord_user is not None : await discord_user.add_roles(cea_registered_role) # attach it if force-register
    else : await interaction.user.add_roles(cea_registered_role) # attach it if regular register

    # send a message to log
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    await private_log_channel.send(f":arrow_up: new user registered: <@{interaction.user.id}>: https://cedb.me/user/{ce_id}")

    # and return.
    return await interaction.followup.send(f"<@{ce_user.discord_id}> has been successfully registered!")



#  _____    _____     ____    ______   _____   _        ______ 
# |  __ \  |  __ \   / __ \  |  ____| |_   _| | |      |  ____|
# | |__) | | |__) | | |  | | | |__      | |   | |      | |__   
# |  ___/  |  _  /  | |  | | |  __|     | |   | |      |  __|  
# | |      | | \ \  | |__| | | |       _| |_  | |____  | |____ 
# |_|      |_|  \_\  \____/  |_|      |_____| |______| |______|


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
    returns = await Discord_Helper.get_user_embeds(user=ce_user, database_name=database_name)
    summary_embed = returns[0]
    view = returns[1]

    # and send
    return await interaction.followup.send(view=view, embed=summary_embed)

