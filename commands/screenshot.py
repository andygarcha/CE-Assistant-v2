import io

import discord
from discord import app_commands

from Modules import PiScreenshot, hm, http_session
from commands.games import get_game_auto


def setup(cli: discord.Client, tree: app_commands.CommandTree, gui: discord.Guild):
    global client, guild
    client = cli
    guild = gui

    @tree.command(
        name="get-screenshot",
        description="Get a screenshot of a game's page on CE!",
        guild=guild,
    )
    @app_commands.autocomplete(game=get_game_auto)
    @app_commands.describe(game="The game you'd like a screenshot of.")
    async def get_screenshot_command(interaction: discord.Interaction, game: str):
        return await get_screenshot(interaction, game)

    return


async def get_screenshot(interaction: discord.Interaction, game: str):
    # defer
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(client, interaction, "get-screenshot", False, game=game)

    session = await http_session.get_session()
    try:
        image_bytes = await PiScreenshot.fetch_screenshot(session, game)
    except PiScreenshot.ScreenshotError as e:
        return await interaction.followup.send(
            f"Sorry, I couldn't get a screenshot: {e}"
        )

    file = discord.File(io.BytesIO(image_bytes), filename=f"{game}.png")
    return await interaction.followup.send(file=file)
