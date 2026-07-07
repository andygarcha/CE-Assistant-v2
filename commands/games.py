import typing
import discord
from discord import app_commands

from Modules import Discord_Helper, SupabaseReader, hm


def setup(cli: discord.Client, tree: app_commands.CommandTree, gui: discord.Guild):
    global client, guild
    client = cli
    guild = gui

    # -- /get-game {game} -----------------------------------------------------
    @tree.command(
        name="get-game",
        description="Get information about any game on CE!",
        guild=guild,
    )
    @app_commands.autocomplete(game=get_game_auto)
    @app_commands.describe(game="The game you'd like information about.")
    async def get_game_command(interaction: discord.Interaction, game: str):
        return await get_game(interaction, game)

    return


async def get_game_auto(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    """
    Autocompletion function that takes in a game name and spits out the game's CE ID.
    Use this function when you're trying to take in a game for a command, like this:
    ```python
    @app_commands.autocomplete(game=get_game_auto)
    async def command(...):
    ```

    Parameters
    ---
    interaction: `discord.Interaction`
        The command that we're attached to.
    current: `str`
        The current value that the user has typed into the parameter.
    """

    # log this interaction
    await hm.log_command(client, interaction, "get_game_auto", True)

    database_name = SupabaseReader.get_game_id_by_name(current)
    choices: list = []

    for game in database_name:
        if current.lower() in game.game_name.lower():
            choices.append(app_commands.Choice(name=game.game_name, value=game.ce_id))
        if len(choices) >= 25:
            break

    return choices[0:25]


async def get_game(interaction: discord.Interaction, game: str):
    """
    Sends an embed displaying information about a game.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    game: `str`
        The CE ID of the game whose information is being requested.
    """
    # defer
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(client, interaction, "get-game", False, game=game)

    chosen_game = SupabaseReader.get_game(game)
    if chosen_game is None:
        return await interaction.followup.send(
            "Sorry, I encountered a strange error. Try again later!"
        )

    # pull the game embed
    database_name = SupabaseReader.get_database_name()
    game_embed = await Discord_Helper.get_game_embed(chosen_game.ce_id, database_name)

    # and return
    return await interaction.followup.send(embed=game_embed)  # type: ignore
