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

    @tree.command(
            name="profile", 
            description="See information about you or anyone else in Challenge Enthusiasts!", 
            guild=guild
            ) 
    @app_commands.describe(user="The user you'd like to see information about (leave blank to see yourself!)")
    async def profile_command(interaction : discord.Interaction, user : discord.User = None) :
        await profile(interaction, user) 
        pass

    @tree.command(name="set-color", description="Set your color to the colors you've unlocked!", guild=guild)
    async def set_color_command(interaction: discord.Interaction):
        await set_color(interaction)
        pass

    @tree.command(name='show-summary', description="Show the CE Summary links for all available years of a user", guild=guild)
    async def show_summary_command(interaction: discord.Interaction, user: discord.User = None):
        await show_summary(interaction, user)
        pass

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

async def set_color(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    # grab the user data
    user_ce = await Mongo_Reader.get_user(interaction.user.id, use_discord_id=True)
    user_rank_num = user_ce.rank_num()

    # the actual assigning role function
    async def assign_role(interaction: discord.Interaction, role: discord.Role) :
        # check to see if they already have the color
        if(role in interaction.user.roles) : 
            return await interaction.response.edit_message(
                embed = discord.Embed(
                    title = f"You already have the {role.name} role!", 
                    color = role.color
                )
            )

        # remove all colors
        for r in ROLES: 
            if r in interaction.user.roles: 
                await interaction.user.remove_roles(r) 

        # add correct color
        await interaction.user.add_roles(role)
        
        # update embed
        return await interaction.response.edit_message(
            content = f"You have been set to the {role.name} role!"
        )
    
    # Keep these in order of lowest rank to highest rank
    COLORS = [
        "Gray",     # E Rank
        "Brown",    # D Rank
        "Green",    # C Rank
        "Blue",     # B Rank
        "Purple",   # A Rank
        "Orange",   # S Rank
        "Yellow",   # SS Rank
        "Red",      # SSS Rank
        "Black"     # EX Rank
    ]
    # These should be in order of highest to lowest
    EMOJIS = ["⚪", "🟤", "🟢", "🔵", "🟣", "🟠", "🟡", "🔴", "⚫"]
    ROLES: list[discord.Role] = [
        discord.utils.get(interaction.guild.roles, name=i) for i in COLORS
    ]

    # instantiate the view
    view = discord.ui.View()

    # for each role, create a button and make sure each person can only do what theyre allowed
    for i, role in enumerate(ROLES):
        _button = discord.ui.Button(emoji=EMOJIS[i], disabled=(user_rank_num < i))
        async def callback(interaction, role=role):
            await assign_role(interaction, role)
        _button.callback = callback
        view.add_item(_button)
    
    # account for the clear button
    async def clear_callback(interaction: discord.Interaction) :
        for role in ROLES :
            if role in interaction.user.roles : 
                await interaction.user.remove_roles(role)
        return await interaction.response.edit_message(
            content = "Colors cleared! You are now set to your default role."
        )
    
    # create and add the clear button
    clear_button = discord.ui.Button(label="🚫")
    clear_button.callback = clear_callback
    view.add_item(clear_button)

    # send the final message
    await interaction.followup.send(
        view = view,
        ephemeral=True,
        content = ("Select a color! (Note: the colors outside of your Rank are disabled). " +
                   "Complete more objectives to unlock more colors!")
    )




async def show_summary(interaction: discord.Interaction, user: discord.User = None):
    await interaction.response.defer()

    if user is None: user = interaction.user

    try: 
        user_ce = await Mongo_Reader.get_user(user.id, use_discord_id=True)
    except ValueError:
        return await interaction.followup.send(
            "The user you requested is not registered with the bot."
        )
    
    user_api = await user_ce.get_api_user()
    join_year = int(user_api.join_date[0:4])
    
    text = f"**CE Summary for user** {user_ce.display_name_with_link()}:\n\n"
    for year in range(join_year, hm.current_year_num() + 1):
        text += f"[{year} Recap](https://cesummary.vercel.app/summary/{year}/{user_ce.ce_id})\n"
    
    return await interaction.followup.send(text)
