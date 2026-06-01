# -------- discord imports -----------
import logging
from Modules import hm

logging.basicConfig(
    # since we imported hm first, any utils will have root logging.
    # at the time of writing this, none will use it, but this is why if it starts happening.
    level=logging.INFO if hm.IN_CE else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

import discord  # noqa: E402
from discord import app_commands  # noqa: E402

# -------- json imports ----------
import json  # noqa: E402
from typing import Literal  # noqa: E402

# --------- local class imports --------

# from Modules.WebInteractor import master_loop
from web_scraper.scraper import process_loop  # noqa: E402
from Modules import SupabaseReader  # noqa: E402
from commands import load_commands  # noqa: E402
from commands.games import get_game_auto  # noqa: E402

# ----------- to-be-sorted imports -------------
from discord.ext import tasks  # noqa: E402

# ----------- selenium and beautiful soup stuff -----------


# -------------------------------- normal bot code -----------------------------------

# set up intents
intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.guilds = True
intents.message_content = True


# open secret_info.json
with open("secret_info.json") as f:
    local_json_data = json.load(f)
    if hm.IN_CE:
        discord_token = local_json_data["discord_token"]
        guild_id = local_json_data["ce_guild_ID"]
    else:
        RUNNING_LOCALLY = False
        if RUNNING_LOCALLY:
            discord_token = local_json_data["other_discord_token"]
        else:
            discord_token = local_json_data["third_discord_token"]
        guild_id = local_json_data["test_guild_ID"]

# set up client
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=guild_id)

load_commands.load_commands(client, tree, guild)

# == webhook reception ==
# routes = web.RouteTableDef()

# @routes.post('/webhook')
# async def webhook_handler(request: web.Request):
#     data = await request.json()

#     channel = hm.get_channel(client, "privatelog")
#     if channel:
#         await channel.send(f"webhook recieved: {data=}")

# async def start_webhook_server():
#     app = web.Application()
#     app.add_routes(routes)
#     runner = web.AppRunner(app)
#     await runner.setup()

#     # bind to 0.0.0.0 to accept external connections on port 80
#     site = web.TCPSite(runner, '0.0.0.0', 8080)
#     await site.start()
#     logger.info('Webhook Running.')

# ------------------------------ commands -------------------------------------


#   _____               _____   _____   _   _    ____       _____    _____    ____    _____    ______
#  / ____|     /\      / ____| |_   _| | \ | |  / __ \     / ____|  / ____|  / __ \  |  __ \  |  ____|
# | |         /  \    | (___     | |   |  \| | | |  | |   | (___   | |      | |  | | | |__) | | |__
# | |        / /\ \    \___ \    | |   | . ` | | |  | |    \___ \  | |      | |  | | |  _  /  |  __|
# | |____   / ____ \   ____) |  _| |_  | |\  | | |__| |    ____) | | |____  | |__| | | | \ \  | |____
#  \_____| /_/    \_\ |_____/  |_____| |_| \_|  \____/    |_____/   \_____|  \____/  |_|  \_\ |______|

update_casino_score_options = Literal["INCREASE", "DECREASE", "SET"]


@tree.command(
    name="manual-update-casino-score",
    description="Update any user's casino score.",
    guild=guild,
)
@app_commands.describe(member="The user you'd like to update the casino score for.")
@app_commands.describe(
    value="The increase, decrease, or new value for the user's casino score."
)
@app_commands.describe(
    type="Whether you'd like to increase, decrease, or set the user's casino score to value."
)
async def manual_update_casino_score(
    interaction: discord.Interaction,
    member: discord.Member,
    value: int,
    type: update_casino_score_options,
):
    await interaction.response.defer(ephemeral=True)

    await interaction.followup.send("Not Implemented.")


#   _____   ______   _______             _____              __  __   ______     _____    ______  __      __
#  / ____| |  ____| |__   __|           / ____|     /\     |  \/  | |  ____|   |  __ \  |  ____| \ \    / /
# | |  __  | |__       | |     ______  | |  __     /  \    | \  / | | |__      | |  | | | |__     \ \  / /
# | | |_ | |  __|      | |    |______| | | |_ |   / /\ \   | |\/| | |  __|     | |  | | |  __|     \ \/ /
# | |__| | | |____     | |             | |__| |  / ____ \  | |  | | | |____    | |__| | | |____     \  /
#  \_____| |______|    |_|              \_____| /_/    \_\ |_|  |_| |______|   |_____/  |______|     \/


@tree.command(
    name="get-game-data", description="return the local data on a game.", guild=guild
)
@app_commands.autocomplete(ce_id=get_game_auto)
async def get_game_data(interaction: discord.Interaction, ce_id: str):
    await interaction.response.defer()

    game = SupabaseReader.get_game(ce_id)
    if game is None:
        return await interaction.followup.send("game not found")
    else:
        return await interaction.followup.send(f"{game.to_dict()}")


INPUT_MESSAGES_ARE_EPHEMERAL: bool = True


@tasks.loop(minutes=1)
async def monitor_loop():
    if not process_loop.is_running():
        logger.warning("Main task loop is not running. Restarting...")
        await process_loop.start(client)


#   ____    _   _     _____    ______              _____   __     __
#  / __ \  | \ | |   |  __ \  |  ____|     /\     |  __ \  \ \   / /
# | |  | | |  \| |   | |__) | | |__       /  \    | |  | |  \ \_/ /
# | |  | | | . ` |   |  _  /  |  __|     / /\ \   | |  | |   \   /
# | |__| | | |\  |   | | \ \  | |____   / ____ \  | |__| |    | |
#  \____/  |_| \_|   |_|  \_\ |______| /_/    \_\ |_____/     |_|


# ---- on ready function ----
@client.event
async def on_ready():
    # sync commands
    await tree.sync(guild=guild)

    for name in [
        "httpx",
        "httpcore",
        "postgrest",
        "supabase",
        "urllib3",
        "discord",
        "aiohttp",
    ]:
        logging.getLogger(name).setLevel(logging.WARNING)
        logger.info("Killed logging for %s.", name)

    # set up channels
    await hm.send_message(
        client,
        "privatelog",
        f":arrow_right_hook: bot started at <t:{int(hm.get_datetime('now').timestamp())}>",
    )

    # asyncio.create_task(start_webhook_server())

    # master loop
    if hm.IN_CE:
        if not process_loop.is_running():
            await process_loop.start(client)
        if not monitor_loop.is_running():
            await monitor_loop.start()


# @client.event
# async def on_disconnect() :
#     await http_session.close_session()


client.run(discord_token)
