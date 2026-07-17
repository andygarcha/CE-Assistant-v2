"""This module contains all the commands about users for the bot."""

from typing import TYPE_CHECKING

import discord
from discord import app_commands

if TYPE_CHECKING:
    from Classes.CE_User import CEUser

from Modules import CEAPIReader, Discord_Helper, SupabaseReader, hm


def setup(cli: discord.Client, tree: app_commands.CommandTree, gui: discord.Guild):
    global client, guild
    client = cli
    guild = gui

    # -- /register {ce_id} -----------------------------------------------------------------
    @tree.command(
        name="register",
        description="Register with CE Assistant to unlock all features!",
        guild=guild,
    )
    @app_commands.describe(ce_id="The link to your Challenge Enthusiasts profile.")
    async def register_command(interaction: discord.Interaction, ce_id: str):
        return await register(interaction, ce_id)

    # -- /profile {user} --------------------------------------------------------------------
    @tree.command(
        name="profile",
        description="See information about you or anyone else in Challenge Enthusiasts!",
        guild=guild,
    )
    @app_commands.describe(
        user="The user you'd like to see information about (leave blank to see yourself!)"
    )
    async def profile_command(
        interaction: discord.Interaction, user: discord.User | None = None
    ):
        return await profile(interaction, user)

    # -- /set-color --------------------------------------------------------------------------
    @tree.command(
        name="set-color",
        description="Set your color to the colors you've unlocked!",
        guild=guild,
    )
    async def set_color_command(interaction: discord.Interaction):
        return await set_color(interaction)

    # -- /show-summary {user} ----------------------------------------------------------------
    @tree.command(
        name="show-summary",
        description="Show the CE Summary links for all available years of a user",
        guild=guild,
    )
    @app_commands.describe(
        user="The user you'd like to see the CE Summary for (leave blank to see yourself!)"
    )
    async def show_summary_command(
        interaction: discord.Interaction, user: discord.User | None = None
    ):
        return await show_summary(interaction, user)

    # -- /ping-preference --------------------------------------------------------------------
    @tree.command(
        name="ping-preference",
        description="Set your preferences for different types of pinging.",
        guild=guild,
    )
    async def ping_preference_command(interaction: discord.Interaction):
        return await ping_preference(interaction)


async def register(
    interaction: discord.Interaction,
    ce_link: str,
    discord_user: discord.Member | None = None,
):
    """
    This command registers a user with CE Assistant.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    ce_link: `str`
        The Challenge Enthusiast ID (or link to their page) to register with.
    discord_user: `discord.Member | None` (default `None`)
        The user to link this CE ID to. Defaults to None.

    """
    await interaction.response.defer()

    # if a new user was sent in, then we need to log that it was a force-register
    await hm.log_command(
        client,
        interaction,
        "register",
        False,
        ce_link=f"<{ce_link}>",
        discord_user=(None if discord_user is None else discord_user.mention),
    )

    # format correctly
    ce_id = hm.format_ce_link(ce_link)
    if ce_id is None:
        return await interaction.followup.send(
            f"'{ce_link}' is not a valid link or ID. Please try again!"
        )

    # get database_user
    users = SupabaseReader.get_database_user()

    # make sure they're not already registered
    # (the target being registered is discord_user for force-register, or
    # interaction.user for a normal self-register -- must match the id used
    # everywhere else in this function, not always the command-caller's id)
    target_id = discord_user.id if discord_user is not None else interaction.user.id
    for user in users:
        if user.discord_id == target_id:
            return await interaction.followup.send(
                "This discord account is already registered in the CE Assistant database!"
            )
        if user.ce_id == ce_id:
            return await interaction.followup.send(
                "This Challenge Enthusiast page is already connected to another account!"
            )

    # grab their data from CE
    ce_user: CEUser | None = await CEAPIReader.get_user(ce_id)
    if ce_user is None:
        return await interaction.followup.send(
            "This Challenge Enthusiast page was not found. Please try again later or contact andy."
        )

    # we need to account for a new discord user being sent in from force-register...
    if discord_user is not None:
        ce_user.discord_id = discord_user.id
    else:
        ce_user.discord_id = interaction.user.id

    # add the user to users and dump it
    SupabaseReader.bulk_dump_users([ce_user])

    # get the role and attach it
    if interaction.guild is None:
        raise Exception("Somehow palpatine returned ahh error")

    cea_registered_role = discord.utils.get(
        interaction.guild.roles, name="CEA Registered"
    )
    if cea_registered_role is None:
        raise Exception(
            f"Could not find role titled 'CEA Registered' in guild {interaction.guild.id}"
        )

    if discord_user is not None:
        await discord_user.add_roles(cea_registered_role)  # attach it if force-register
    elif isinstance(interaction.user, discord.Member):
        await interaction.user.add_roles(
            cea_registered_role
        )  # attach it if regular register
    else:
        await interaction.followup.send(
            "User was not registered as a member in the guild. Please contact andy!"
        )

    # send a message to log
    await hm.send_message(
        client,
        "privatelog",
        f":bust_in_silhouette: new user registered: <@{target_id}>: <https://cedb.me/user/{ce_id}>",
        True,
    )

    # and return.
    return await interaction.followup.send(
        f"<@{ce_user.discord_id}> has been successfully registered!"
    )


async def profile(interaction: discord.Interaction, user: discord.User | None = None):
    """
    Returns a set of embeds about a user.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    user: `discord.User | None` (default `None`)
        The user you're requesting to see information about.
        If this is `None`, assume the `interaction.user` is requesting
        information about themselves.
    """
    await interaction.response.defer()

    await hm.log_command(
        client,
        interaction,
        "profile",
        False,
        user=(None if user is None else user.mention),
    )

    # pull databases
    database_name = SupabaseReader.get_database_name()

    # check to see if they asked for info on another person.
    if user is None:
        _user = interaction.user
        asked_for_friend = False
    else:
        _user = user
        asked_for_friend = True

    # make sure they're registered
    ce_user = SupabaseReader.get_user(_user.id, use_discord_id=True)
    if ce_user is None:
        if asked_for_friend:
            return await interaction.followup.send(
                f"Sorry! <@{_user.id}> is not registered. Please have them run /register!",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        return await interaction.followup.send(
            "Sorry! You are not registered. Please run /register and try again!"
        )

    # get the embed and the view
    returns = await Discord_Helper.get_user_embeds(
        user=ce_user, database_name=database_name
    )
    summary_embed = returns[0]
    view = returns[1]

    # and send
    og_message = await interaction.followup.send(
        view=view, embed=summary_embed, wait=True
    )
    if isinstance(view, Discord_Helper.ProfileView):
        view.message = og_message
    return og_message


async def set_color(interaction: discord.Interaction):
    """
    Gives the user the color role that they've requested.
    Also removes their current one (if they have it), so they can
    go up and down as they please.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    """
    await interaction.response.defer(ephemeral=True)

    await hm.log_command(client, interaction, "set-color", False)

    if interaction.guild is None:
        await interaction.followup.send("Error")
        raise Exception("guild was None in set-color")

    # grab the user data
    user_ce = SupabaseReader.get_user(interaction.user.id, use_discord_id=True)
    if user_ce is None:
        return await interaction.followup.send(
            "Please run /register before you do any additional commands!"
        )

    user_rank_num = user_ce.rank_num

    # the actual assigning role function
    async def assign_role(interaction: discord.Interaction, role: discord.Role):
        """
        Assigns the requested role, sends a log, and alerts the user that it happened.
        """
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message("error.")
            raise Exception(
                "interaction.user is discord.User instead of discord.Member!"
            )

        # check to see if they already have the color
        if role in interaction.user.roles:
            return await interaction.response.edit_message(
                embed=discord.Embed(
                    title=f"You already have the {role.name} role!", color=role.color
                )
            )

        # remove all colors
        for r in ROLES:
            if r in interaction.user.roles:
                await interaction.user.remove_roles(r)

        # add correct color
        await interaction.user.add_roles(role)

        # log the color change
        await hm.send_message(
            client,
            "privatelog",
            f":art: <@{interaction.user.id}> ({user_ce.rank}) changed their color to **{role.name}**.",
            allowed_mentions=False,
        )

        # update embed
        return await interaction.response.edit_message(
            content=f"You have been set to the {role.name} role!"
        )

    # Keep these in order of lowest rank to highest rank
    COLORS = [
        "Gray",  # E Rank
        "Brown",  # D Rank
        "Green",  # C Rank
        "Blue",  # B Rank
        "Purple",  # A Rank
        "Orange",  # S Rank
        "Yellow",  # SS Rank
        "Red",  # SSS Rank
        "Black",  # EX Rank
    ]
    # These should be in order of highest to lowest
    EMOJIS = ["⚪", "🟤", "🟢", "🔵", "🟣", "🟠", "🟡", "🔴", "⚫"]
    ROLES: list[discord.Role] = [
        role
        for i in COLORS
        if (role := discord.utils.get(interaction.guild.roles, name=i)) is not None
    ]

    if None in ROLES:
        await interaction.followup.send("error")
        raise Exception(f"None found in ROLES (set_color). {len(ROLES)=}")

    # instantiate the view
    view = discord.ui.View()

    # for each role, create a button and make sure each person can only do what theyre allowed
    for i, role in enumerate(ROLES):
        _button = discord.ui.Button(emoji=EMOJIS[i], disabled=(user_rank_num < i))

        async def callback(interaction, role=role):
            await assign_role(interaction, role)

        _button.callback = callback
        view.add_item(_button)

    # account for the clear button
    async def clear_callback(interaction: discord.Interaction):
        """
        Removes all color roles from the user.
        """
        if isinstance(interaction.user, discord.User):
            raise Exception(
                "set_color.clear_callback() had interaction.user is discord.User!"
            )

        for role in ROLES:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
        return await interaction.response.edit_message(
            content="Colors cleared! You are now set to your default role."
        )

    # create and add the clear button
    clear_button = discord.ui.Button(label="🚫")
    clear_button.callback = clear_callback
    view.add_item(clear_button)

    # send the final message
    return await interaction.followup.send(
        view=view,
        ephemeral=True,
        content=(
            "Select a color! (Note: the colors outside of your Rank are disabled). "
            + "Complete more objectives to unlock more colors!"
        ),
    )


async def show_summary(
    interaction: discord.Interaction, user: discord.User | None = None
):
    """
    Returns a list of links to the CE Summary website for a given user.

    There should be a link for every year this user has been a member of CE.

    Parameters
    ---
    interaction: `discord.Interaction`
        The discord interaction that initiated this command.
    user: `discord.User | None` (default `None`)
        The user that the information has been requested about.
        If this is `None`, assume the `interaction.user` has requested
        information about themselves.
    """
    await interaction.response.defer()

    await hm.log_command(
        client,
        interaction,
        "show-summary",
        False,
        user=(None if user is None else user.mention),
    )

    _user_local = interaction.user if user is None else user

    user_ce = SupabaseReader.get_user(_user_local.id, use_discord_id=True)
    if user_ce is None:
        return await interaction.followup.send(
            "The user you requested is not registered with the bot."
        )

    user_api = await user_ce.get_api_user()
    if user_api is None:
        return await interaction.followup.send(
            "Something went wrong when pulling your data. Please wait a couple seconds and try again."
        )
    join_year = int(user_api.join_date[0:4])

    text = f"**CE Summary for user** {user_ce.display_name_with_link}:\n\n"
    for year in range(join_year, hm.current_year_num() + 1):
        text += f"[{year} Recap](https://cesummary.vercel.app/summary/{year}/{user_ce.ce_id})\n"

    return await interaction.followup.send(text, suppress_embeds=True)


def _yes_no_options(current: bool) -> list[discord.SelectOption]:
    "Builds a fresh pair of Yes/No options per dropdown, pre-selected to `current`."
    return [
        discord.SelectOption(label="Yes", value="true", emoji="✅", default=current),
        discord.SelectOption(
            label="No", value="false", emoji="❌", default=not current
        ),
    ]


class PingPreferenceModal(discord.ui.Modal):
    """Modal for setting a user's opt-in ping preferences."""

    def __init__(self, user: "CEUser"):
        super().__init__(title="Ping Preferences")
        self.ce_id = user.ce_id

        self.casino_fail_select = discord.ui.Select(
            options=_yes_no_options(user.ping_casino_fail)
        )
        self.add_item(
            discord.ui.Label(
                text="Ping when you fail a casino event?",
                component=self.casino_fail_select,
            )
        )

        self.casino_win_select = discord.ui.Select(
            options=_yes_no_options(user.ping_casino_win)
        )
        self.add_item(
            discord.ui.Label(
                text="Ping when you win a casino event?",
                component=self.casino_win_select,
            )
        )

        self.user_log_select = discord.ui.Select(
            options=_yes_no_options(user.ping_user_log)
        )
        self.add_item(
            discord.ui.Label(
                text="Ping for #player-accomplishments messages?",
                component=self.user_log_select,
            )
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        ping_casino_fail = self.casino_fail_select.values[0] == "true"
        ping_casino_win = self.casino_win_select.values[0] == "true"
        ping_user_log = self.user_log_select.values[0] == "true"

        SupabaseReader.update_ping_preferences(
            self.ce_id, ping_casino_fail, ping_casino_win, ping_user_log
        )

        await interaction.response.send_message(
            "Your ping preferences have been updated:\n"
            f"- Ping on casino fail: {'Yes' if ping_casino_fail else 'No'}\n"
            f"- Ping on casino win: {'Yes' if ping_casino_win else 'No'}\n"
            f"- Ping for #player-accomplishments: {'Yes' if ping_user_log else 'No'}",
            ephemeral=True,
        )


async def ping_preference(interaction: discord.Interaction):
    """
    Opens a modal that lets the user set different ping preferences.

    Because a Modal must be the interaction's initial response, this command
    cannot `defer()` first: the guard-clause failure uses `response.send_message`,
    and the success path uses `response.send_modal`.
    """
    await hm.log_command(client, interaction, "ping-preference", True)

    user = SupabaseReader.get_user(interaction.user.id, use_discord_id=True)
    if user is None:
        return await interaction.response.send_message(
            "You are not registered with the bot! Please run /register.", ephemeral=True
        )

    modal = PingPreferenceModal(user)
    return await interaction.response.send_modal(modal)
