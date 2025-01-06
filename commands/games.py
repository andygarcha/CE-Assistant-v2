import typing
import discord
from discord import app_commands

from Classes.CE_User import CEUser
from Modules import CEAPIReader, Discord_Helper, Mongo_Reader, hm


def setup(cli : discord.Client, tree : app_commands.CommandTree, gui : discord.Guild) :
    global client, guild
    client = cli
    guild = gui

    @tree.command(name="get-game", description="Get information about any game on CE!", guild=guild)
    @app_commands.autocomplete(game=get_game_auto)
    async def get_game_command(interaction : discord.Interaction, game : str) :
        await get_game(interaction, game)

    

    pass


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
