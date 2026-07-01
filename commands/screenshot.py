import io
import json

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

    @tree.command(
        name="get-diff-screenshot",
        description="[Admin] Test a diff-highlighted screenshot of one objective field change.",
        guild=guild,
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(game=get_game_auto)
    @app_commands.describe(
        game="The game the objective belongs to.",
        objective_id="The objective's UUID (from /api/game/<id>).",
        old="The old value of the field that changed.",
        new="The new value of the field that changed.",
    )
    async def get_diff_screenshot_command(
        interaction: discord.Interaction,
        game: str,
        objective_id: str,
        old: str,
        new: str,
    ):
        return await get_diff_screenshot(interaction, game, objective_id, old, new)

    @tree.command(
        name="get-game-diff-screenshot",
        description="[Admin] Test a whole-table diff screenshot from a JSON list of old objectives.",
        guild=guild,
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(game=get_game_auto)
    @app_commands.describe(
        game="The game to screenshot.",
        old_objectives_json="A JSON list of old objective snapshots (id, name, description, points, requirements, type).",
    )
    async def get_game_diff_screenshot_command(
        interaction: discord.Interaction, game: str, old_objectives_json: str
    ):
        return await get_game_diff_screenshot(interaction, game, old_objectives_json)

    return


def _format_timings(timings: dict[str, str]) -> str:
    "Turns `X-Timing-*` response headers into readable `Phase: 1.23s` lines."
    lines = []
    for header, seconds in timings.items():
        label = header.removeprefix("X-Timing-").replace("-", " ")
        lines.append(f"{label}: {seconds}s")
    return "\n".join(lines)


async def get_screenshot(interaction: discord.Interaction, game: str):
    # defer
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(client, interaction, "get-screenshot", False, game=game)

    session = await http_session.get_session()
    try:
        image_bytes, timings = await PiScreenshot.fetch_screenshot(session, game)
    except PiScreenshot.ScreenshotError as e:
        return await interaction.followup.send(
            f"Sorry, I couldn't get a screenshot: {e}"
        )

    file = discord.File(io.BytesIO(image_bytes), filename=f"{game}.png")
    return await interaction.followup.send(content=_format_timings(timings), file=file)


async def get_diff_screenshot(
    interaction: discord.Interaction,
    game: str,
    objective_id: str,
    old: str,
    new: str,
):
    # defer
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client,
        interaction,
        "get-diff-screenshot",
        True,
        game=game,
        objective_id=objective_id,
        old=old,
        new=new,
    )

    session = await http_session.get_session()
    try:
        image_bytes, timings = await PiScreenshot.fetch_diff_screenshot(
            session, game, objective_id, old, new
        )
    except PiScreenshot.ScreenshotError as e:
        return await interaction.followup.send(
            f"Sorry, I couldn't get a diff screenshot: {e}"
        )

    file = discord.File(io.BytesIO(image_bytes), filename=f"{objective_id}-diff.png")
    return await interaction.followup.send(content=_format_timings(timings), file=file)


async def get_game_diff_screenshot(
    interaction: discord.Interaction, game: str, old_objectives_json: str
):
    # defer
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client,
        interaction,
        "get-game-diff-screenshot",
        True,
        game=game,
        old_objectives_json=old_objectives_json,
    )

    try:
        old_objectives = json.loads(old_objectives_json)
    except json.JSONDecodeError as e:
        return await interaction.followup.send(f"Invalid JSON for old_objectives: {e}")

    session = await http_session.get_session()
    try:
        image_bytes, timings = await PiScreenshot.fetch_game_diff_screenshot(
            session, game, old_objectives
        )
    except PiScreenshot.ScreenshotError as e:
        return await interaction.followup.send(
            f"Sorry, I couldn't get a game diff screenshot: {e}"
        )

    file = discord.File(io.BytesIO(image_bytes), filename=f"{game}-diff.png")
    return await interaction.followup.send(content=_format_timings(timings), file=file)
