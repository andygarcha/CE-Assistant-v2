"""This module contains all the admin commands for the bot."""

import datetime
import discord
import logging
from discord import app_commands
from Classes.CE_Roll import CERoll
from commands.user import register
from Modules import CEAPIReader, hm, SupabaseReader

from web_scraper.scraper import process_loop
from Modules import http_session

logger = logging.getLogger(__name__)


def setup(cli: discord.Client, tree: app_commands.CommandTree, gui: discord.Guild):
    global client, guild
    client = cli
    guild = gui

    # ---- test command ----
    @tree.command(name="test", description="test", guild=guild)
    async def test_command(interaction: discord.Interaction):
        await test(interaction)
        pass

    # ---- force-register command ----
    @tree.command(
        name="force-register",
        description="Register another user with CE Assistant!",
        guild=guild,
    )
    @app_commands.describe(
        ce_link="The link to their CE page (or their ID, either works)"
    )
    @app_commands.describe(user="The user you want to link this page (or ID) to.")
    async def force_register_command(
        interaction: discord.Interaction, ce_link: str, user: discord.Member
    ):
        await register(interaction, ce_link, user)

    # ---- scrape command ----
    """
    @tree.command(name="scrape", description=("Replace database_name with API data WITHOUT sending messages. RUN WHEN NECESSARY."), guild=guild)
    async def scrape_command(interaction : discord.Interaction) :
        await scrape(interaction)
    """

    @tree.command(
        name="full-scrape",
        description="Run the loop on ALL games in the CE database.",
        guild=guild,
    )
    async def full_scrape_command(interaction: discord.Interaction, send_updates: bool = True):
        await loop(interaction, True, send_updates=send_updates)

    # ---- initiate loop command ----
    @tree.command(
        name="initiate-loop",
        description="Initiate the loop. ONLY RUN WHEN NECESSARY.",
        guild=guild,
    )
    async def initiate_loop_command(interaction: discord.Interaction):
        await loop(interaction, False)

    # ---- add notes command ----
    @tree.command(
        name="add-notes",
        description="Add notes to any #game-additions post.",
        guild=guild,
    )
    @app_commands.describe(
        embed_id="The Message ID of the message you'd like to add notes to."
    )
    @app_commands.describe(notes="The notes you'd like to append.")
    @app_commands.describe(
        clear="Set this to true if you want to replace all previous notes with this one."
    )
    async def add_notes_command(
        interaction: discord.Interaction, embed_id: str, notes: str, clear: bool
    ):
        await add_notes(interaction, embed_id, notes, clear)

    # ---- clear roll command ----
    @tree.command(
        name="clear-roll",
        description="Clear any user's current/completed rolls, cooldowns, or pendings.",
        guild=guild,
    )
    async def clear_roll_command(
        interaction: discord.Interaction,
        member: discord.Member,
        roll_name: hm.ALL_ROLL_EVENT_NAMES,
        current: bool = False,
        completed: bool = False,
        pending: bool = False,
    ):
        await clear_roll(interaction, member, roll_name, current, completed, pending)

    @tree.command(
        name="clear-roll-portion",
        description="Clear the most recently rolled game in a multi-stage roll",
        guild=guild,
    )
    async def clear_roll_portion_command(
        interaction: discord.Interaction,
        member: discord.Member,
        roll_name: hm.ALL_ROLL_EVENT_NAMES,
    ):
        await clear_roll_portion(interaction, member, roll_name)

    # ---- force add command ----
    @tree.command(
        name="force-add",
        description="Force add a roll to a user's completed rolls section.",
        guild=guild,
    )
    async def force_add_command(
        interaction: discord.Interaction,
        member: discord.Member,
        roll_name: hm.ALL_ROLL_EVENT_NAMES,
    ):
        await force_add(interaction, member, roll_name)

    @tree.command(
        name="force-unlink", description="Unlink someone from the bot.", guild=guild
    )
    async def force_unlink_command(
        interaction: discord.Interaction, member: discord.Member
    ):
        await force_unlink(interaction, member)

    @tree.command(name="shutdown", description="Shut the bot down.", guild=guild)
    @app_commands.default_permissions(administrator=True)
    async def shutdown_command(interaction: discord.Interaction):
        await shutdown(interaction)

    pass


#  _______   ______    _____   _______
# |__   __| |  ____|  / ____| |__   __|
#    | |    | |__    | (___      | |
#    | |    |  __|    \___ \     | |
#    | |    | |____   ____) |    | |
#    |_|    |______| |_____/     |_|


async def test(interaction: discord.Interaction):
    await interaction.response.defer()

    return await interaction.followup.send("testsss done")


#   _____    _____   _____               _____    ______
#  / ____|  / ____| |  __ \      /\     |  __ \  |  ____|
# | (___   | |      | |__) |    /  \    | |__) | | |__
#  \___ \  | |      |  _  /    / /\ \   |  ___/  |  __|
#  ____) | | |____  | | \ \   / ____ \  | |      | |____
# |_____/   \_____| |_|  \_\ /_/    \_\ |_|      |______|


# ---- scrape function ----


async def scrape(interaction: discord.Interaction):
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(client, interaction, "scrape", True)

    return await interaction.followup.send("Out of date command.")

    user_list = SupabaseReader.get_list("user")
    database_user = await CEAPIReader.get_api_users_all(user_list)
    database_name = await CEAPIReader.get_api_games_full()

    for user in database_user:
        SupabaseReader.dump_user(user)

    for game in database_name:
        SupabaseReader.dump_game(game)

    return await interaction.followup.send("Database replaced.")


#  _____   _   _   _____   _______   _____              _______   ______     _         ____     ____    _____
# |_   _| | \ | | |_   _| |__   __| |_   _|     /\     |__   __| |  ____|   | |       / __ \   / __ \  |  __ \
#   | |   |  \| |   | |      | |      | |      /  \       | |    | |__      | |      | |  | | | |  | | | |__) |
#   | |   | . ` |   | |      | |      | |     / /\ \      | |    |  __|     | |      | |  | | | |  | | |  ___/
#  _| |_  | |\  |  _| |_     | |     _| |_   / ____ \     | |    | |____    | |____  | |__| | | |__| | | |
# |_____| |_| \_| |_____|    |_|    |_____| /_/    \_\    |_|    |______|   |______|  \____/   \____/  |_|


# ---- initiate loop ----


async def loop(interaction: discord.Interaction, full_scrape=False, send_updates: bool = True):
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client,
        interaction,
        "full-scrape" if full_scrape else "initiate-loop",
        True,
        full_scrape=full_scrape,
        send_updates=send_updates
    )

    if hm.IN_CE:
        if (
            datetime.datetime.now().minute < 30
            and datetime.datetime.now().minute >= 25
            and full_scrape
        ):
            return await interaction.followup.send(
                "this loop will run in less than five minutes. please wait!"
            )
        if (
            datetime.datetime.now().minute >= 30
            and datetime.datetime.now().minute < 35
            and full_scrape
        ):
            return await interaction.followup.send(
                "this loop is probably running now! please wait..."
            )

    await interaction.followup.send("looping...")

    await process_loop(client, full_scrape, send_updates)

    return await interaction.followup.send("loop complete.")


async def shutdown(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    # log this interaction
    await hm.log_command(client, interaction, "shutdown", True)

    await interaction.followup.send("Shutting down the bot...", ephemeral=True)

    if process_loop.is_running():
        process_loop.stop()
        task = process_loop.get_task()
        if task is not None:
            await task

    await http_session.close_session()
    await client.close()


#             _____    _____      _   _    ____    _______   ______    _____
#     /\     |  __ \  |  __ \    | \ | |  / __ \  |__   __| |  ____|  / ____|
#    /  \    | |  | | | |  | |   |  \| | | |  | |    | |    | |__    | (___
#   / /\ \   | |  | | | |  | |   | . ` | | |  | |    | |    |  __|    \___ \
#  / ____ \  | |__| | | |__| |   | |\  | | |__| |    | |    | |____   ____) |
# /_/    \_\ |_____/  |_____/    |_| \_|  \____/     |_|    |______| |_____/


async def add_notes(
    interaction: discord.Interaction, embed_id: str, notes: str, clear: bool
):
    "Adds notes to game additions posts."
    # defer and make ephemeral
    await interaction.response.defer(ephemeral=True)

    # log this interaction
    await hm.log_command(
        client,
        interaction,
        "add-notes",
        True,
        embed_id=embed_id,
        notes=notes,
        clear=clear,
    )

    # grab the site additions channel
    site_additions_channel = client.get_channel(hm.GAME_ADDITIONS_ID)
    if isinstance(
        site_additions_channel,
        (discord.ForumChannel, discord.CategoryChannel, discord.abc.PrivateChannel),
    ):
        raise Exception(
            f"Cannot fetch messages from channel of type {type(site_additions_channel)}"
        )
    if site_additions_channel is None:
        raise Exception("Could not find site additions channel. Returned None")

    # try to get the message
    try:
        message = await site_additions_channel.fetch_message(int(embed_id))
    except discord.NotFound:
        return await interaction.followup.send(
            f"This message is not in the <#{hm.GAME_ADDITIONS_ID}> channel."
        )

    # TODO swap this out with a constant or client.user.id or smthn
    if message.author.id != 1108618891040657438:
        return await interaction.followup.send("This message was not sent by the bot!")

    # grab the embed
    embed = message.embeds[0]

    # try and see if the embed already has a reason field
    try:
        if embed.fields[-1].name == "Note":
            # if clear has been set, set the value to only the new notes
            if clear:
                embed.set_field_at(
                    index=len(embed.fields) - 1, name="Note", value=notes
                )

            # else, add the new notes to the end and keep the old notes
            else:
                old_notes = embed.fields[-1].value
                embed.set_field_at(
                    index=len(embed.fields) - 1,
                    name="Note",
                    value=f"{old_notes}\n{notes}",
                )

    # if it errors, then just add a reason field
    except Exception as e:
        logger.exception(e)
        embed.add_field(name="Note", value=notes, inline=False)

    # edit the message
    await message.edit(embed=embed, attachments=[])

    # and send a response to the original interaction
    await interaction.followup.send("Notes added!", ephemeral=True)


#   _____   _        ______              _____
#  / ____| | |      |  ____|     /\     |  __ \
# | |      | |      | |__       /  \    | |__) |
# | |      | |      |  __|     / /\ \   |  _  /
# | |____  | |____  | |____   / ____ \  | | \ \
#  \_____| |______| |______| /_/    \_\ |_|  \_\


async def clear_roll(
    interaction: discord.Interaction,
    member: discord.Member,
    roll_name: hm.ALL_ROLL_EVENT_NAMES,
    current: bool = False,
    completed: bool = False,
    pending: bool = False,
):
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client,
        interaction,
        "clear_roll",
        True,
        member=member.mention,
        roll_name=roll_name,
        current=current,
        completed=completed,
        pending=pending,
    )

    # get database user and the user
    user = SupabaseReader.get_user(member.id, use_discord_id=True)
    if user is None:
        await interaction.followup.send("Could not find user!")
        raise Exception(f"Could not find user with discord {member.id} in Supabase.")

    if current:
        user.remove_current_roll(roll_name)
    if completed:
        user.remove_completed_rolls(roll_name)
    if pending:
        user.remove_pending(roll_name)

    SupabaseReader.dump_user(user)
    return await interaction.followup.send("Done!")


async def clear_roll_portion(
    interaction: discord.Interaction,
    member: discord.Member,
    roll_name: hm.ALL_ROLL_EVENT_NAMES,
):
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client,
        interaction,
        "clear_roll_portion",
        True,
        member=member.mention,
        roll_name=roll_name,
    )

    user = SupabaseReader.get_user(member.id, use_discord_id=True)
    if user is None:
        await interaction.followup.send(
            f"Could not find user with discord id {member.id} in Supabase."
        )
        raise Exception(f"Could not find user with discord id {member.id} in supabase.")

    roll = user.get_current_roll(roll_name)
    if roll is None:
        return await interaction.followup.send(
            "User does not have roll that is current"
        )

    game_removed = roll.remove_game_last()
    game_removed = SupabaseReader.get_game(game_removed)
    if game_removed is None:
        game_removed = "<error, removed game was 'null'>"
    else:
        game_removed = game_removed.name_with_link
    roll.set_status("waiting")
    roll.due_time = None

    logger.info("Roll (after changes): %s", roll.to_dict())

    logger.debug("Printing all rolls in user.rolls.")
    for roll in user.rolls:
        logger.debug("%s", roll.to_dict())

    SupabaseReader.dump_user(user)
    return await interaction.followup.send(
        f"Removed {game_removed} from {user.display_name}'s {roll_name} roll. "
        + "Status set to 'waiting'."
    )


async def force_add(
    interaction: discord.Interaction,
    member: discord.Member,
    roll_name: hm.ALL_ROLL_EVENT_NAMES,
):
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client,
        interaction,
        "force_add",
        True,
        member=member.mention,
        roll_name=roll_name,
    )

    # get database user and the user
    user = SupabaseReader.get_user(member.id, use_discord_id=True)
    if user is None:
        await interaction.followup.send(
            f"Could not find user with discord id {member.id} in supabase."
        )
        raise Exception(f"Could not find user with discord id {member.id} in supabase.")

    user.add_completed_roll(
        CERoll(
            roll_name=roll_name,
            user_ce_id=user.ce_id,
            games=None,
            status="won",
            completed_time=datetime.datetime.now(),
        )
    )

    SupabaseReader.dump_user(user)
    return await interaction.followup.send("Done!")


class UnlinkView(discord.ui.View):
    def __init__(self, member_id: int):
        self._member_id = member_id
        super().__init__(timeout=None)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        user = SupabaseReader.get_user(self._member_id, use_discord_id=True)
        if user is None:
            raise Exception(
                f"Could not find user with discord id {self._member_id} in Supabase."
            )

        # user._discord_id = None
        SupabaseReader.dump_user(user)

        self.clear_items()
        await interaction.response.edit_message(
            content=f"{user.display_name} has been removed.", view=self
        )

    @discord.ui.button(label="No!", style=discord.ButtonStyle.red)
    async def no_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.clear_items()
        await interaction.response.edit_message(
            content="User was not removed.", view=self
        )


async def force_unlink(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client, interaction, "force_unlink", True, member=member.mention
    )

    return await interaction.followup.send(
        "This does not currently work with the updated CE site. Please wait a while, or contact andy for manual unlinking!"
    )
