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
from typing import Literal  # noqa: E402

# --------- local class imports --------

# from Modules.WebInteractor import master_loop
from update_delivery import deliver_updates  # noqa: E402
from Modules import SupabaseReader  # noqa: E402
from commands import load_commands  # noqa: E402
from commands.games import get_game_auto  # noqa: E402

# ----------- to-be-sorted imports -------------
from discord.ext import tasks  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
import os  # noqa: E402

# ----------- selenium and beautiful soup stuff -----------


# -------------------------------- normal bot code -----------------------------------

# set up intents
intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.guilds = True
intents.message_content = True


# open .env
load_dotenv()
if hm.IN_CE:
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    guild_id = os.getenv("DISCORD_GUILD_ID")
else:
    discord_token = os.getenv("DISCORD_BOT_TOKEN_TERTIARY")
    guild_id = os.getenv("DISCORD_TEST_GUILD_ID")

assert discord_token is not None
assert guild_id is not None

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


@tasks.loop(seconds=60)
async def delivery_loop():
    try:
        count = await deliver_updates(client)
        if count > 0:
            logger.info("Delivered %d scraper updates.", count)
    except Exception:
        logger.exception("delivery_loop failed")


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

    # delivery loop — polls scraper_updates table for messages to send
    if hm.IN_CE:
        if not delivery_loop.is_running():
            delivery_loop.start()


# @client.event
# async def on_disconnect() :
#     await http_session.close_session()


client.run(discord_token)
