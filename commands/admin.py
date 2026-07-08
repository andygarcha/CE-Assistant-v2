"""This module contains all the admin commands for the bot."""

import datetime
import logging
import uuid

import discord
from discord import app_commands

from Classes.CE_Roll import CERoll
from commands.user import register
from Modules import SupabaseReader, hm, http_session

logger = logging.getLogger(__name__)


def setup(cli: discord.Client, tree: app_commands.CommandTree, gui: discord.Guild):
    global client, guild
    client = cli
    guild = gui

    # -- /test ------------------------------------------------------------------------------
    @tree.command(name="test", description="test", guild=guild)
    async def test_command(interaction: discord.Interaction):
        await test(interaction)

    # -- /force-register {ce_link} {user} ---------------------------------------------------
    @tree.command(
        name="force-register",
        description="Register another user with CE Assistant!",
        guild=guild,
    )
    @app_commands.describe(
        ce_link="The link to their CE page (or their ID, either works)",
        user="The user you want to link this page (or ID) to.",
    )
    async def force_register_command(
        interaction: discord.Interaction, ce_link: str, user: discord.Member
    ):
        await register(interaction, ce_link, user)

    # -- /full_scrape {send_updates} --------------------------------------------------------
    @tree.command(
        name="full-scrape",
        description="Run the loop on ALL games in the CE database.",
        guild=guild,
    )
    @app_commands.describe(send_updates="Set this to false to silently scrape.")
    async def full_scrape_command(
        interaction: discord.Interaction, send_updates: bool = True
    ):
        await loop(interaction, True, send_updates=send_updates)

    # -- /initiate-loop ---------------------------------------------------------------------
    @tree.command(
        name="initiate-loop",
        description="Initiate the loop. ONLY RUN WHEN NECESSARY.",
        guild=guild,
    )
    async def initiate_loop_command(interaction: discord.Interaction):
        await loop(interaction, False)

    # -- /add-notes {embed_id} {notes} {clear} -----------------------------------------------
    @tree.command(
        name="add-notes",
        description="Add notes to any #game-additions post.",
        guild=guild,
    )
    @app_commands.describe(
        embed_id="The Message ID of the message you'd like to add notes to.",
        notes="The notes you'd like to append.",
        clear="Set this to true if you want to replace all previous notes with this one.",
    )
    async def add_notes_command(
        interaction: discord.Interaction, embed_id: str, notes: str, clear: bool
    ):
        await add_notes(interaction, embed_id, notes, clear)

    # -- /clear-roll {roll_id} ----------------------------------------------------------------
    @tree.command(
        name="clear-roll",
        description="Clear any user's current/completed rolls, cooldowns, or pendings.",
        guild=guild,
    )
    @app_commands.describe(
        roll_id="The ID of the roll whose status you're setting to 'removed'."
    )
    async def clear_roll_command(interaction: discord.Interaction, roll_id: str):
        await clear_roll(interaction, roll_id)

    # -- /clear-roll-portion {member} {roll_name} ----------------------------------------------
    @tree.command(
        name="clear-roll-portion",
        description="Clear the most recently rolled game in a multi-stage roll",
        guild=guild,
    )
    @app_commands.describe(
        member="The user whose roll you're adjusting.",
        roll_name="The event you're adjusting.",
    )
    async def clear_roll_portion_command(
        interaction: discord.Interaction,
        member: discord.Member,
        roll_name: hm.ALL_ROLL_EVENT_NAMES,
    ):
        return await interaction.response.send_message("Not available.")

    # -- /fail-roll {roll_id} {is_not_current} --------------------------------------------------
    @tree.command(
        name="fail-roll",
        description="Given a roll ID, change the status from 'current' to 'failed'.",
        guild=guild,
    )
    @app_commands.describe(
        roll_id="The ID of the roll you're updating. See https://cebot.me to find it.",
        is_not_current="Set this to true if you'd like to ignore the current status.",
    )
    async def fail_roll_command(
        interaction: discord.Interaction, roll_id: str, is_not_current: bool = False
    ):
        return await fail_roll(interaction, roll_id, is_not_current)

    # -- /force-add {member} {roll_name} ---------------------------------------------------------
    @tree.command(
        name="force-add",
        description="Force add a roll to a user's completed rolls section.",
        guild=guild,
    )
    @app_commands.describe(
        member="The user who will have the roll added.",
        roll_name="The event that will be added.",
    )
    async def force_add_command(
        interaction: discord.Interaction,
        member: discord.Member,
        roll_name: hm.ALL_ROLL_EVENT_NAMES,
    ):
        await force_add(interaction, member, roll_name)

    # -- /force-unlink {member} --------------------------------------------------------------------
    @tree.command(
        name="force-unlink", description="Unlink someone from the bot.", guild=guild
    )
    @app_commands.describe(member="The user who will be unlinked.")
    async def force_unlink_command(
        interaction: discord.Interaction, member: discord.Member
    ):
        await force_unlink(interaction, member)

    # -- /shutdown ----------------------------------------------------------------------------------
    @tree.command(name="shutdown", description="Shut the bot down.", guild=guild)
    @app_commands.default_permissions(administrator=True)
    async def shutdown_command(interaction: discord.Interaction):
        await shutdown(interaction)

    # -- /debug {user} ------------------------------------------------------------------------------
    @tree.command(
        name="debug", description="Show information regarding this user", guild=guild
    )
    @app_commands.describe(user="The user.")
    async def debug_command(interaction: discord.Interaction, user: discord.Member):
        return await debug(interaction, user)


async def test(interaction: discord.Interaction):
    """
    The test function.
    If you add anything here, please remove it before you merge to main!
    """
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(client, interaction, "test", True)

    return await interaction.followup.send("testsss done")


async def loop(
    interaction: discord.Interaction, full_scrape=False, send_updates: bool = True
):
    """
    The initiate-loop functionality.
    This function tells the scraper process to initiate a loop.

    Parameters
    ---
    interaction: `discord.Interaction`
        The interaction for this process.
    full_scrape: `bool` (default `False`)
        If this is set to true, the scraping process
        will do a "full" scrape, rather than just the regular
        loop.
    send_updates: `bool` (default `True`)
        If this is set to true, any updates generated
        by the scraper process will be saved to the database
        and sent by the main Discord process.
    """
    await interaction.response.defer(ephemeral=True)

    await hm.log_command(
        client,
        interaction,
        "full-scrape" if full_scrape else "initiate-loop",
        True,
        full_scrape=full_scrape,
        send_updates=send_updates,
    )

    command = "full_scrape" if full_scrape else "initiate_loop"
    SupabaseReader.write_scraper_command(command)

    running_note = (
        " A scrape is already in progress — your request will be queued."
        if SupabaseReader.is_loop_running()
        else ""
    )
    return await interaction.followup.send(
        f"{'Full scrape' if full_scrape else 'Loop'} requested. "
        f"The scraper will pick this up on its next cycle.{running_note}"
    )


async def shutdown(interaction: discord.Interaction):
    """
    The shutdown command.
    This should *only* be accessible to administrators.
    This will:
    - close the http session
    - close the Discord client

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    """
    await interaction.response.defer(ephemeral=True)

    await hm.log_command(client, interaction, "shutdown", True)

    await interaction.followup.send(
        "Shutting down the bot. The scraper runs independently — "
        "use tmux to manage it.",
        ephemeral=True,
    )
    await http_session.close_session()
    await client.close()


async def add_notes(
    interaction: discord.Interaction, embed_id: str, notes: str, clear: bool
):
    """
    Allows notes to be added to #game-additions posts.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    embed_id: `str`
        The ID of the embed you'd like to add notes to.
    notes: `str`
        The note you'd like to add onto the embed
    clear: `bool`
        If this is set to true, this will clear all previous notes on this
        embed, and set the Notes section to the `notes: str` value.
        If this is set to false, this will simply append the `notes: str`
        value onto the already-existing notes (if one exists).
    """
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
        discord.ForumChannel | discord.CategoryChannel | discord.abc.PrivateChannel,
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

    # update existing Note field if present, otherwise add one
    if embed.fields and embed.fields[-1].name == "Note":
        if clear:
            embed.set_field_at(index=len(embed.fields) - 1, name="Note", value=notes)
        else:
            old_notes = embed.fields[-1].value
            embed.set_field_at(
                index=len(embed.fields) - 1,
                name="Note",
                value=f"{old_notes}\n{notes}",
            )
    else:
        embed.add_field(name="Note", value=notes, inline=False)

    # edit the message
    await message.edit(embed=embed, attachments=[])

    # and send a response to the original interaction
    return await interaction.followup.send("Notes added!", ephemeral=True)


async def clear_roll(interaction: discord.Interaction, roll_id: str):
    """
    Sets a roll object's status to "removed".
    If there is no roll with this ID, the command will exit early.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    roll_id: `str`
        The ID of the roll that you'd like set to removed.
    """
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(client, interaction, "clear_roll", True, roll_id=roll_id)

    roll = SupabaseReader.get_roll(roll_id)
    if roll is None:
        return await interaction.followup.send(
            f"Could not find a roll with id {roll_id}."
        )

    roll.set_status("removed")

    SupabaseReader.dump_roll(roll)

    return await interaction.followup.send(
        f"'{roll.roll_name}' roll with user={roll.user_ce_id} set to removed."
    )


async def clear_roll_portion(
    interaction: discord.Interaction,
    member: discord.Member,
    roll_name: hm.ALL_ROLL_EVENT_NAMES,
):
    """
    Removes the most recently rolled game in a multi-stage roll, and sets the roll's status to "between_stages".
    For example, if a user rolls a game in Two Week T2 Streak that should be edited, this command can be run
    to allow them to effectively "reroll" it.

    If the user is not registered with CE Assistant, this command will exit early.
    If the user does not have a current roll that matches `roll_name`, this command will exit early.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    member: `discord.Member`
        The user whose roll you're changing.
    roll_name: `hm.ALL_ROLL_EVENT_NAMES`
        The roll event you're editing.
    """
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
    roll.set_status("between_stages")
    roll.due_time = None

    logger.info("Roll (after changes): %s", roll.to_dict())

    logger.debug("Printing all rolls in user.rolls.")
    for roll in user.rolls:
        logger.debug("%s", roll.to_dict())

    SupabaseReader.dump_user(user)
    return await interaction.followup.send(
        f"Removed {game_removed} from {user.display_name}'s {roll_name} roll. "
        + "Status set to 'between_stages'."
    )


async def fail_roll(
    interaction: discord.Interaction, roll_id: str, is_not_current: bool = False
):
    """
    Takes in an `interaction: discord.Interaction` and a `roll_id: str`
    and changes the status from 'current' to 'failed'.

    If the status is not 'current', this will exit,
    unless the `is_not_current: bool` is set to `True`.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    roll_id: `str`
        The ID of the roll we're changing the
        status of.
    is_not_current: `bool = False`
        Optional boolean flag. When set to true,
        we force the status to be set to 'failed'
        regardless of what the current status is.
    """

    await interaction.response.defer(ephemeral=True)

    await hm.log_command(
        client,
        interaction,
        "fail_roll",
        True,
        roll_id=roll_id,
        is_not_current=is_not_current,
    )

    roll = SupabaseReader.get_roll(roll_id)
    if roll is None:
        return await interaction.followup.send(f"No roll with ID {roll_id} was found.")

    if roll.status != "current" and not is_not_current:
        return await interaction.followup.send(
            f"The status of this roll is {roll.status}. This command (by default) only fails rolls that have "
            "a status of 'current'. If you would still like to set the status of this roll to 'failed', please "
            "rerun this command with the parameter `is_not_current` set to true."
        )

    roll.set_status("failed")
    SupabaseReader.dump_roll(roll)

    await interaction.followup.send(
        f"Roll with ID {roll_id}'s status has now been set to 'failed'."
    )

    # report failure to #casino
    database_name = SupabaseReader.get_database_name()
    user = SupabaseReader.get_user(roll.user_ce_id)
    if user is None:
        return await hm.send_message(
            client, "casino", f"Roll with ID {roll.id} failed. User not found."
        )
    if roll.partner_ce_id is None:
        partner = None
    else:
        partner = SupabaseReader.get_user(roll.partner_ce_id)
    return await hm.send_message(
        client,
        "casino",
        roll.get_fail_message(database_name, user, partner),
        allowed_mentions=True,
    )


async def force_add(
    interaction: discord.Interaction,
    member: discord.Member,
    roll_name: hm.ALL_ROLL_EVENT_NAMES,
):
    """
    Forcefully adds a roll to a user's 'completed rolls' section.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    member: `discord.Member`
        The user we're adding this roll to.
    roll_name: `hm.ALL_ROLL_EVENT_NAMES`
        The roll that we're adding to the member's completed rolls section.
    """
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
            _id=str(uuid.uuid4()),
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
    """
    Forcefully unlink a user from their CE ID.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    member: `discord.Member`
        The user we're trying to unlink from the database.
    """
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client, interaction, "force_unlink", True, member=member.mention
    )

    return await interaction.followup.send(
        "This does not currently work with the updated CE site. Please wait a while, or contact andy for manual unlinking!"
    )


async def debug(interaction: discord.Interaction, user: discord.Member):
    """
    Prints out a bunch of information about a user.
    - A link to their CE page
    - A link to their CEBot rolls page
    - A link to their CEBot validate page

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    user: `discord.Member`
        The user who we're debugging.
    """
    await interaction.response.defer(ephemeral=True)

    await hm.log_command(client, interaction, "debug", True, user=user.mention)

    user_supa = SupabaseReader.get_user(user.id, use_discord_id=True)
    if user_supa is None:
        return await interaction.followup.send("This user isn't registered.")

    return await interaction.followup.send(
        f"[ce link](https://cedb.me/user/{user_supa.ce_id})\n"
        f"[rolls link](https://cebot.me/rolls/{user_supa.ce_id})\n"
        f"[comparison link](https://cebot.me/users/{user_supa.ce_id}/check)"
    )
