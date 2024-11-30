"""This module contains all the admin commands for the bot."""
import discord
from discord import app_commands
from commands.user import register


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
    pass



#  _______   ______    _____   _______ 
# |__   __| |  ____|  / ____| |__   __|
#    | |    | |__    | (___      | |   
#    | |    |  __|    \___ \     | |   
#    | |    | |____   ____) |    | |   
#    |_|    |______| |_____/     |_|   



async def test(interaction : discord.Interaction) :
    await interaction.response.defer()

    return await interaction.followup.send('test done')