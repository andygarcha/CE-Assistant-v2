"""This module contains all the admin commands for the bot."""

import datetime
import logging
import uuid

import discord
from discord import app_commands

from Classes.CE_Game import CEGame
from Classes.CE_Roll import CERoll
from commands.games import get_game_auto
from commands.user import register
from Modules import HealthCheck, LocalCache, SupabaseReader, hm, http_session

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
        return await clear_roll_portion(interaction, member, roll_name)

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
        interaction: discord.Interaction, member: discord.User
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

    # -- /ban-game {game} {reason} -----------------------------------------------------------
    @tree.command(
        name="ban-game",
        description="Ban a game from being rolled in the casino.",
        guild=guild,
    )
    @app_commands.describe(
        game="The game you want to ban from the casino.",
        reason="Why do you want to ban this game from the casino?",
    )
    @app_commands.autocomplete(game=get_game_auto)
    async def ban_game_command(
        interaction: discord.Interaction, game: str, reason: str
    ):
        return await ban_game(interaction, game, reason)

    # -- /health-check {include_integrity} ---------------------------------------------------
    @tree.command(
        name="health-check",
        description="Check the database for data-quality issues and report them to #privatelog.",
        guild=guild,
    )
    @app_commands.describe(
        include_integrity="Also run the LocalCache/Supabase integrity check (costs Supabase egress)."
    )
    async def health_check_command(
        interaction: discord.Interaction, include_integrity: bool = False
    ):
        return await health_check(interaction, include_integrity)

    # -- /roll-management {roll_id} ------------------------------------------------------------
    @tree.command(
        name="roll-management", description="Change out a game in a roll.", guild=guild
    )
    @app_commands.describe(roll_id="The ID of the roll you'd like to change.")
    async def roll_management_command(interaction: discord.Interaction, roll_id: str):
        return await interaction.response.send_message("Under construction.")

        return await roll_management(interaction, roll_id)


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

    SupabaseReader.dump_roll(roll)
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

    SupabaseReader.dump_roll(
        CERoll(
            roll_name=roll_name,
            user_ce_id=user.ce_id,
            games=None,
            status="won",
            completed_time=datetime.datetime.now(datetime.UTC),
            _id=str(uuid.uuid4()),
        )
    )

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

        # Deletes the user row, owned games, and objectives. Rolls are
        # intentionally left alone so roll/casino history survives an unlink.
        SupabaseReader.delete_user(user.ce_id)

        self.clear_items()
        await interaction.response.edit_message(
            content=f"{user.display_name} has been unlinked. Their roll history was kept.",
            view=self,
        )

    @discord.ui.button(label="No!", style=discord.ButtonStyle.red)
    async def no_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.clear_items()
        await interaction.response.edit_message(
            content="User was not removed.", view=self
        )


async def force_unlink(interaction: discord.Interaction, member: discord.User):
    """
    Forcefully unlink a user from their CE ID. Deletes their user row, owned
    games, and objectives. Roll/casino history is intentionally preserved.

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

    user = SupabaseReader.get_user(member.id, use_discord_id=True)
    if user is None:
        return await interaction.followup.send(
            f"Could not find a registered user for {member.mention}."
        )

    view = UnlinkView(member.id)
    return await interaction.followup.send(
        f"Are you sure you want to unlink {user.display_name} ({member.mention})? "
        "This deletes their owned games and objectives, but their roll history is kept.",
        view=view,
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


async def ban_game(interaction: discord.Interaction, game: str, reason: str):
    """
    Adds a game to the `banned_games` table in Supabase.

    If this game is already banned, this function will append the given `reason` onto the `reason` column
    in Supabase.

    If the user who initiated this interaction is not registered, this command will exit early.
    The user who initiated this command will have their CE ID listed in the `banned_by` column.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    game: `str`
        The CE ID of the game we're banning.
    reason: `str`
        The reason we're banning this game from the casino.
    """
    await interaction.response.defer()

    await hm.log_command(
        client,
        interaction,
        "ban-game",
        True,
        game=game,
        reason=reason,
    )

    author = SupabaseReader.get_user(interaction.user.id, use_discord_id=True)
    if author is None:
        return await interaction.followup.send(
            "You must be registered in order to ban a game from the casino."
        )

    # verify game exists
    if not SupabaseReader.get_game(game):
        return await interaction.followup.send("This is not a real game.")

    SupabaseReader.ban_game(game, reason, author.ce_id)

    return await interaction.followup.send(
        f"Game with ID {game} was banned by {author.mention} for reason: '{reason}'."
    )


async def health_check(
    interaction: discord.Interaction, include_integrity: bool = False
):
    """
    Runs the database health checks (uncategorized games, miscounted roll
    games, orphaned objectives) and reports any warnings to #privatelog.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    include_integrity: `bool` (default `False`)
        If set to true, also runs the LocalCache/Supabase integrity check.
        This costs Supabase egress, so it's off by default.
    """
    await interaction.response.defer(ephemeral=True)

    await hm.log_command(
        client, interaction, "health-check", True, include_integrity=include_integrity
    )

    warnings = HealthCheck.run_cheap_checks()

    if include_integrity:
        try:
            integrity_report = LocalCache.run_integrity_check()
        except Exception as e:
            logger.exception("Integrity check failed.")
            warnings.append(f":hospital: Integrity check failed: {e}")
        else:
            warnings.append(HealthCheck.format_integrity_report(integrity_report))

    for warning in warnings:
        await hm.send_message(client, "privatelog", warning, allowed_mentions=False)

    if warnings:
        return await interaction.followup.send(
            f"Health check complete. {len(warnings)} warning(s) sent to #privatelog."
        )
    return await interaction.followup.send("Health check complete. No issues found.")


class RollManagementModal(discord.ui.Modal):
    """Modal for replacing a game in a roll and optionally extending its due time.

    TODO: `on_submit` still needs to validate the replacement CEID, swap the
    selected game in `roll.games`, apply `hours_extend` to `roll.due_time`,
    persist via `SupabaseReader.dump_roll`, and send a confirmation message.
    """

    def __init__(self, roll: CERoll, games: list[CEGame]):
        super().__init__(title="Roll Management")
        self.roll = roll

        game_options = [
            discord.SelectOption(label=game.game_name, value=game.ce_id)
            for game in games
        ]
        self.game_select = discord.ui.Select(options=game_options)
        self.add_item(
            discord.ui.Label(text="Game to replace", component=self.game_select)
        )

        self.new_game_id = discord.ui.TextInput(required=True)
        self.add_item(
            discord.ui.Label(text="Replacement game CEID", component=self.new_game_id)
        )

        self.hours_extend = discord.ui.TextInput(required=False)
        self.add_item(
            discord.ui.Label(
                text="Hours to extend due time", component=self.hours_extend
            )
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        new_game = SupabaseReader.get_game(self.new_game_id.value)
        if new_game is None:
            await interaction.response.send_message(
                f"Could not find game with ID {self.new_game_id.value}.", ephemeral=True
            )
            return

        self.roll.replace_game(self.game_select.values[0], new_game.ce_id)

        hour_message = ""
        if self.hours_extend.value != "":
            original_due_time = self.roll.due_discord_timestamp
            self.roll.increase_due_time(int(self.hours_extend.value) * 60 * 60)
            hour_message = f" Extended due time from {original_due_time} to {self.roll.due_discord_timestamp}."
        SupabaseReader.dump_roll(self.roll)

        await interaction.response.send_message(
            f"Replaced https://cedb.me/game/{self.game_select.values[0]} with {new_game.name_with_link}."
            f"{hour_message}"
        )


async def roll_management(interaction: discord.Interaction, roll_id: str):
    """
    This command does the following:
    - Allows you to select one of the corresponding rollGames for replacement
    - Allows a TextInput for the CEID of the game you're replacing it with
    - Allows a TextInput (number) for how many hours you'd like to extend the user's due time.

    This will be sent in the form of a Modal. Once input is sent back, the data
    will be validated (valid game ID) and saved, and then sends a confirmation message.

    Because a Modal must be the interaction's initial response, this command
    cannot `defer()` first: guard-clause failures use `response.send_message`,
    and the success path uses `response.send_modal`.
    """
    await hm.log_command(client, interaction, "roll_management", True, roll_id=roll_id)

    roll = SupabaseReader.get_roll(roll_id)
    if roll is None:
        return await interaction.response.send_message(
            f"No roll with ID {roll_id} was found.", ephemeral=True
        )

    games = SupabaseReader.get_games_bulk(roll.games)

    modal = RollManagementModal(roll, games)
    return await interaction.response.send_modal(modal)
