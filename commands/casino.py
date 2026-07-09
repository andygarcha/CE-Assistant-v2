"""This module is for all casino-related commands."""

import logging
import secrets
import uuid
from dataclasses import dataclass
from typing import get_args

import discord
from discord import app_commands

from Classes.CE_Game import CEGame
from Classes.CE_Roll import CERoll
from Classes.CE_User import CEUser
from Modules import SupabaseReader, hm

""" === GETTING CLIENT TO WORK === """
logger = logging.getLogger(__name__)


def setup(cli: discord.Client, tree: app_commands.CommandTree, gui: discord.Guild):
    global client, guild
    client = cli
    guild = gui

    # -- /solo-roll {event_name} {category} {price_restriction} {hours_restriction} --------------------
    @tree.command(
        name="solo-roll",
        description="Roll a solo event with CE Assistant!",
        guild=guild,
    )
    @app_commands.describe(
        event_name="The event you'd like to roll.",
        category="If the event requires a chosen category, select it here.",
        price_restriction="Set this to false if you'd like to be able to roll any game, regardless of price.",
        hours_restriction="Set this to false if you'd like to be able to roll any game, regardless of SH hours.",
    )
    async def solo_roll_command(
        interaction: discord.Interaction,
        event_name: hm.SOLO_ROLL_EVENT_NAMES,
        category: hm.CATEGORIES | None = None,
        price_restriction: bool = True,
        hours_restriction: bool = True,
    ):
        await solo_roll(
            interaction, event_name, category, price_restriction, hours_restriction
        )

    # -- /coop-roll {event_name} {partner} {tier} ------------------------------------------------------
    @tree.command(
        name="coop-roll",
        description="Roll a Co-Op or PvP roll with a friend!",
        guild=guild,
    )
    @app_commands.describe(
        event_name="The event you'd like to roll.",
        partner="The partner you'd like to roll with.",
        tier="If the event requires a chosen tier, select it here.",
    )
    async def coop_roll_command(
        interaction: discord.Interaction,
        event_name: hm.COOP_ROLL_EVENT_NAMES,
        partner: discord.Member,
        tier: int | None = None,
    ):
        return await co_op_roll(interaction, partner, event_name, tier, True, True)

    # -- /check-rolls {friend} -------------------------------------------------------------------------
    @tree.command(
        name="check-rolls",
        description="Check the status of your current and completed casino rolls!",
        guild=guild,
    )
    @app_commands.describe(friend="The user whose rolls you want to see.")
    async def check_rolls_command(
        interaction: discord.Interaction, friend: discord.Member | None = None
    ):
        return await check_rolls(interaction, friend)


# -- command implementations -----------------------------------------------------------------------------
async def solo_roll(
    interaction: discord.Interaction,
    event_name: hm.SOLO_ROLL_EVENT_NAMES,
    category: hm.CATEGORIES | None = None,
    price_restriction: bool = True,
    hours_restriction: bool = True,
):
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client,
        interaction,
        "solo-roll",
        False,
        event_name=event_name,
        category=category,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
    )

    lucky = False

    # grab the user
    user = SupabaseReader.get_user(interaction.user.id, use_discord_id=True)
    if user is None:
        return await interaction.followup.send(
            "Sorry, you're not registered in the CE Assistant database. Please run `/register` first!"
        )

    # user has cooldown
    if user.has_cooldown(event_name):
        return await interaction.followup.send(
            f"You are currently on cooldown for {event_name} until <t:{user.get_cooldown_timestamp(event_name)}>. "
        )

    # user has pending
    if user.has_pending(event_name):
        return await interaction.followup.send(
            "You just tried rolling this event. Please wait about 10 minutes before trying again."
            + " (P.S. This is not a cooldown. Just has to do with how the bot backend works.)"
        )

    # user currently rolled => is cancellable
    if event_name in ["Never Lucky", "Let Fate Decide"]:
        _current_roll = user.get_current_roll(event_name)

        if _current_roll is not None:
            _cooldown_date = _current_roll.calculate_cooldown_date()

            if _cooldown_date is not None and _cooldown_date > hm.get_datetime("now"):
                return await interaction.followup.send(
                    f"You can reroll {event_name} after <t:{_current_roll.calculate_cooldown_timestamp()}>"
                )

            _game = SupabaseReader.get_game(_current_roll.games[0])
            if _game is not None:
                _game_message = _game.name_with_link
            else:
                _game_message = "Could not find game in database."
            # if we get here, we can cancel
            # MAKE SURE WE ADD THE PENDING SO THEY CAN'T DOUBLE DO THIS!!!
            SupabaseReader.add_pending(event_name, user.ce_id)

            # and now send the views
            view = ConfirmCancelView(user.discord_id)
            await interaction.followup.send(
                (
                    f"You have an active **{event_name}** roll ({_game_message}). "
                    "Rerolling will **fail** it permanently. Continue?"
                ),
                view=view,
            )
            await view.wait()

            # they said no (or yes) — tear down the pending guard
            SupabaseReader.kill_pending(event_name, user.ce_id)
            if not view.confirmed:
                return await interaction.edit_original_response(
                    content="Reroll cancelled.", view=None
                )

            # they said yes!
            _current_roll.set_status("failed")
            SupabaseReader.dump_roll(_current_roll)
            await interaction.edit_original_response(
                content="Previous roll failed. Rolling new game...", view=None
            )

    # user currently rolled => not cancellable or rerollable
    if user.has_current_roll(event_name):
        return await interaction.followup.send(
            f"You're currently attempting {event_name}! Please finish this instance before rerolling."
        )

    # roll requires category
    #  (must come after rerolling bc user could just try rerolling... no category needed)
    CATEGORY_REQUIRED = ["Triple Threat", "Let Fate Decide", "Fourward Thinking"]
    if event_name in CATEGORY_REQUIRED and category is None:
        return await interaction.followup.send(
            f"{event_name} requires a chosen category. Please rerun the command and select your category."
        )

    # jarvis's random event!
    # -- make sure to not reroll this on every time they move forward
    if secrets.randbelow(100) == 0 and not user.has_waiting_roll(event_name):
        lucky = True
        await hm.send_message(
            client,
            "userlog",
            f"Congratulations {interaction.user.mention}! You've won Jarvis's super secret reward. "
            "Please DM him for your prize :)",
        )

    # fetch game database (only done once all checks have passed)
    database_name = SupabaseReader.get_database_name()
    database_tier = SupabaseReader.get_database_tier(database_name)

    # -- set up vars --
    result: RollResult

    match event_name:
        case "One Hell of a Day":
            result = roll_onehellofaday(
                database_name, database_tier, user, price_restriction, hours_restriction
            )
        case "One Hell of a Week":
            result = roll_onehellofaweek(
                database_name, database_tier, user, price_restriction, hours_restriction
            )
        case "One Hell of a Month":
            result = roll_onehellofamonth(
                database_name, database_tier, user, price_restriction, hours_restriction
            )
        case "Two Week T2 Streak":
            result = roll_twoweekt2streak(
                database_name, database_tier, user, price_restriction, hours_restriction
            )
        case 'Two "Two Week T2 Streak" Streak':
            result = roll_twotwoweekt2streakstreak(
                database_name, database_tier, user, price_restriction, hours_restriction
            )
        case "Never Lucky":
            result = roll_neverlucky(
                database_name, database_tier, user, price_restriction, hours_restriction
            )
        case "Triple Threat":
            result = roll_triplethreat(
                database_name,
                database_tier,
                user,
                price_restriction,
                hours_restriction,
                category,
            )
        case "Let Fate Decide":
            result = roll_letfatedecide(
                database_name,
                database_tier,
                user,
                price_restriction,
                hours_restriction,
                category,
            )
        case "Fourward Thinking":
            result = RollResult(None, "Fourward Thinking is not currently implemented.")
        case _:
            return await interaction.followup.send(
                f"{event_name} is not a valid event name!"
            )

    if result.error:
        return await interaction.followup.send(result.error)
    if result.games is None:
        return await interaction.followup.send(
            "No games were returned, but no error was reported. Please contact andy!"
        )

    roll: CERoll | None = None
    message: str

    # Case 1: We need some kind of user input
    # TODO

    # Case 2: We're initiating a new stage of an existing roll
    roll = user.get_waiting_roll(event_name)
    if roll is not None:
        roll.set_status("current")
        roll.reset_due_time()
        roll.add_game(result.games[0])
        _result = roll.get_reup_message(database_name)
        if _result is None:
            return await interaction.followup.send(
                "Errored when trying to find the game's name."
            )
        message = _result

    # Case 3: We're creating a brand new roll
    else:
        # make the roll
        roll = CERoll(
            roll_name=event_name,
            user_ce_id=user.ce_id,
            games=result.games,
            status="current",
            _id=str(uuid.uuid4()),
            partner_ce_id=None,
            is_current=True,
            lucky=lucky,
        )
        _result = roll.get_initialization_message(database_name)
        if _result is None:
            return await interaction.followup.send(
                "Errored when trying to find game names."
            )
        message = _result

    SupabaseReader.dump_roll(roll)
    return await interaction.followup.send(message)


async def co_op_roll(
    interaction: discord.Interaction,
    partner_: discord.Member,
    event_name: hm.COOP_ROLL_EVENT_NAMES,
    tier: int | None = None,
    price_restriction: bool = True,
    hours_restriction: bool = True,
):
    """
    Co Op Rolling!
    :)

    Parameters
    ---
    interaction: `discord.Interaction`
        The interaction we'll be responding to.
        In our case, this is a slash-command.
    partner_: `discord.Member`
        The partner we'll be rolling along with the
        author of the interaction.
    event_name: `COOP_ROLL_EVENT_NAMES`
        The name of the event we're rolling.
    tier: `int`
        If the event requires a tier to be chosen
        (like, for example, Soul Mates), it will
        be passed in here.
    price_restriction: `bool` (default True)
        A flag that designates whether or not
        we should adhere to the price limit.
        This is optionally turned off by the roller.
    hours_restriction: `bool` (default True)
        A flag that designates whether or not
        we should adhere to the median completion time
        limit.
        This is optionally turned off by the roller.
    """
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client,
        interaction,
        "coop-roll",
        False,
        partner=partner_.mention,
        event_name=event_name,
        tier=tier,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
    )

    lucky = False

    # they tried to roll with themselves
    if interaction.user.id == partner_.id:
        return await interaction.followup.send(
            "You can't roll with yourself. Please stop trying to break me :("
        )

    # grab the user and partner
    user = SupabaseReader.get_user(interaction.user.id, use_discord_id=True)
    if user is None:
        return await interaction.followup.send(
            "Sorry, you're not registered in the CE Assistant database. Please run `/register` first!"
        )
    partner: CEUser | None = SupabaseReader.get_user(partner_.id, use_discord_id=True)
    if partner is None:
        return await interaction.followup.send(
            "Sorry, your partner is not registered in the CE Assistant database. Please have them "
            "run /register first!"
        )

    # user/partner has cooldown
    if user.has_cooldown(event_name) and event_name != "Destiny Alignment":
        return await interaction.followup.send(
            f"You are currently on cooldown for {event_name} until <t:{user.get_cooldown_timestamp(event_name)}>."
        )
    if partner.has_cooldown(event_name) and event_name != "Destiny Alignment":
        return await interaction.followup.send(
            f"Your partner is currently on cooldown for {event_name} "
            f"until <t:{partner.get_cooldown_timestamp(event_name)}>."
        )

    # destiny alignment specific
    if event_name == "Destiny Alignment":
        if user.has_current_roll_with(partner.ce_id, event_name):
            return await interaction.followup.send(
                "You two are already in a Destiny Alignment together. Finish that one first!"
            )
        MAX_DESTINY_ALIGNMENTS = 5
        if user.count_current_rolls(event_name) >= MAX_DESTINY_ALIGNMENTS:
            return await interaction.followup.send(
                "You are already in too many Destiny Alignment rolls to create another one!"
            )
        if partner.count_current_rolls(event_name) >= MAX_DESTINY_ALIGNMENTS:
            return await interaction.followup.send(
                "Your partner is already in too many Destiny Alignment rolls to create another one!"
            )
    # other co-ops don't allow for multiple instances
    else:
        if user.has_current_roll(event_name):
            return await interaction.followup.send(
                f"You are already in a {event_name} roll. Finish that one first!"
            )
        if partner.has_current_roll(event_name):
            return await interaction.followup.send(
                f"Your partner is already in a {event_name} roll. Have them finish that "
                "one first, or choose a new partner."
            )

    # user/partner have pendings
    if user.has_pending(event_name):
        return await interaction.followup.send(
            "You just tried rolling this event. Please wait about 10 minutes before trying again."
            + " (P.S. This is not a cooldown. Just has to do with how the bot backend works.)"
        )
    if partner.has_pending(event_name):
        return await interaction.followup.send(
            "Your partner just tried rolling this event. Please wait about 10 minutes before trying again."
            + " (P.S. This is not a cooldown. Just has to do with how the bot backend works.)"
        )

    SupabaseReader.add_pending(event_name, user.ce_id, partner.ce_id)

    # -- partner confirmation --
    confirm_view = CoOpConfirmView(partner.discord_id)
    confirm_msg = await interaction.followup.send(
        f"Hey {partner.mention}, {user.mention} wants to start a "
        f"**{event_name}** roll with you! Do you accept?",
        view=confirm_view,
        wait=True,
    )
    await confirm_view.wait()

    if confirm_view.confirmed is None:
        SupabaseReader.kill_pending(event_name, user.ce_id, partner.ce_id)
        return await confirm_msg.edit(
            content="This co-op request timed out. Re-run the command if you'd still like to roll together.",
            view=None,
        )
    if not confirm_view.confirmed:
        SupabaseReader.kill_pending(event_name, user.ce_id, partner.ce_id)
        return await confirm_msg.edit(
            content=f"{partner.mention} declined the roll. No worries!",
            view=None,
        )
    await confirm_msg.edit(content=f"{partner.mention} accepted! Rolling...", view=None)

    # jarvis's random event!
    # -- make sure to not reroll this on every time they move forward
    if secrets.randbelow(100) == 0 and not user.has_waiting_roll(event_name):
        lucky = True
        await hm.send_message(
            client,
            "userlog",
            f"Congratulations {user.mention} and {partner.mention}! You've won Jarvis's super secret reward. "
            "Please DM him for your prize :)",
        )

    # -- pull from supabase -----
    database_name = SupabaseReader.get_database_name()
    database_tier = SupabaseReader.get_database_tier(database_name)

    # -- roll the games ----
    result: RollResult
    match event_name:
        case "Destiny Alignment":
            result = roll_destinyalignment(
                database_name,
                database_tier,
                user,
                partner,
                price_restriction,
                hours_restriction,
            )
        case "Soul Mates":
            result = roll_soulmates(
                database_name,
                database_tier,
                user,
                partner,
                price_restriction,
                hours_restriction,
                tier,
            )
        case "Teamwork Makes the Dream Work":
            tier = 3
            tier_partner = 3
            result = roll_teamworkmakesthedreamwork(
                database_name,
                database_tier,
                user,
                partner,
                price_restriction,
                hours_restriction,
            )
        case _:
            result = RollResult(None, f"{event_name} is not a valid co-op roll.")

    # -- report error -----
    if result.error:
        SupabaseReader.kill_pending(event_name, user.ce_id, partner.ce_id)
        return await confirm_msg.edit(content=result.error)
    if result.games is None:
        SupabaseReader.kill_pending(event_name, user.ce_id, partner.ce_id)
        return await confirm_msg.edit(
            content="Error: There were no returned games, but no internal error was reported."
        )

    # -- create the roll object -----
    tier_partner = tier

    # destiny alignment -- manually grab tier
    # soul mates -- decided with a parameter
    # teamwork -- always tier == 3
    if event_name == "Destiny Alignment":
        _game = hm.get_item_from_list(result.games[0], database_name)
        if _game is None:
            SupabaseReader.kill_pending(event_name, user.ce_id, partner.ce_id)
            return await confirm_msg.edit(content="Error 7. Please contact andy.")
        tier = _game.tier_num
        if tier == 0:
            SupabaseReader.kill_pending(event_name, user.ce_id, partner.ce_id)
            return await confirm_msg.edit(
                content="Oops! I accidentally rolled you a T0."
            )
        _game2 = hm.get_item_from_list(result.games[1], database_name)
        if _game2 is None:
            SupabaseReader.kill_pending(event_name, user.ce_id, partner.ce_id)
            return await confirm_msg.edit(content="Error 7. Please contact andy.")
        tier_partner = _game2.tier_num
        if tier_partner == 0:
            SupabaseReader.kill_pending(event_name, user.ce_id, partner.ce_id)
            return await confirm_msg.edit(
                content="Oops! I accidentally rolled you a T0."
            )

    if tier is None:
        raise ValueError("tier was supposed to be NOne by this point!")

    roll = CERoll(
        roll_name=event_name,
        user_ce_id=user.ce_id,
        games=result.games,
        status="current",
        _id=str(uuid.uuid4()),
        partner_ce_id=partner.ce_id,
        is_current=True,
        tier_num=tier,
        lucky=lucky,
        tier_num_partner=tier_partner,
    )

    # -- get message -----
    message = roll.get_initialization_message(database_name)
    if message is None:
        SupabaseReader.kill_pending(event_name, user.ce_id, partner.ce_id)
        return await confirm_msg.edit(content="Error pulling your rolled games.")

    # -- save and quit -----
    SupabaseReader.dump_roll(roll)
    SupabaseReader.kill_pending(event_name, user.ce_id, partner.ce_id)
    return await confirm_msg.edit(content=message)


@dataclass
class RollResult:
    games: list[str] | None = None
    error: str | None = None


def roll_onehellofaday(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
) -> RollResult:
    """
    One Hell of a Day
    - 10 hour completion limit
    - $10 price limit
    - Tier 1
    - Any category
    - 1 game
    - Multi-Category: Allowed
    """
    _game = hm.get_rollable_game(
        database_name=database_name,
        database_tier=database_tier,
        completion_limit=10,
        price_limit=10,
        tier_number=1,
        user=user,
        already_rolled_games=[],
        has_points_restriction=False,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
        allow_multi_category=True,
    )

    if _game is None:
        return RollResult(None, "Not enough rollable games.")
    return RollResult([_game], None)


def roll_onehellofaweek(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
) -> RollResult:
    """
    One Hell of a Week
    - 10 hour completion limit
    - $10 price limit
    - Tier 1
    - Each game from a different category
    - 5 games
    - Multi-Category: Disallowed
    - Requires 'One Hell of a Day' completion.
    """

    if not user.has_completed_roll("One Hell of a Day"):
        return RollResult(
            None,
            "You must first complete 'One Hell of a Day' to attempt One Hell of a Week!",
        )

    # iterate five times
    categories: list[str] = list(get_args(hm.CATEGORIES))
    valid_games: list[str] = []
    while len(valid_games) != 5:
        _game = hm.get_rollable_game(
            database_name=database_name,
            database_tier=database_tier,
            completion_limit=10,
            price_limit=10,
            tier_number=1,
            user=user,
            category=categories,
            already_rolled_games=valid_games,
            has_points_restriction=False,
            price_restriction=price_restriction,
            hours_restriction=hours_restriction,
            allow_multi_category=False,
        )

        if _game is None:
            return RollResult(None, "Not enough rollable games.")

        _game_supa = hm.get_item_from_list(_game, database_name)
        if _game_supa is None:
            return RollResult(
                None, "Rolled game could not be found in Supabase. Please try again."
            )
        categories.remove(
            _game_supa.categories[0]
        )  # guaranteed to have only one category
        valid_games.append(_game)

    return RollResult(valid_games, None)


def roll_onehellofamonth(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
) -> RollResult:
    """
    One Hell of a Month
    - 10 hour completion limit
    - $10 price limit
    - Tier 1
    - 25 games split evenly from 5 categories
    - Multi-Category: Disallowed
    - Requires 'One Hell of a Week' completion.
    """

    if not user.has_completed_roll("One Hell of a Week"):
        return RollResult(
            None,
            "You must first complete 'One Hell of a Week' to attempt One Hell of a Month!",
        )

    categories_total = list(get_args(hm.CATEGORIES))
    categories_remaining = categories_total.copy()
    rolled_games: list[str] = []
    categories_failed: list[str] = []
    max_failures = len(categories_total) - 5

    while len(rolled_games) < 25:
        category_curr = secrets.choice(categories_remaining)
        categories_remaining.remove(category_curr)

        category_games: list[str] = []
        for _ in range(5):
            game = hm.get_rollable_game(
                database_name=database_name,
                database_tier=database_tier,
                completion_limit=10,
                price_limit=10,
                tier_number=1,
                user=user,
                category=category_curr,
                already_rolled_games=category_games,
                has_points_restriction=False,
                price_restriction=price_restriction,
                hours_restriction=hours_restriction,
                allow_multi_category=False,
            )
            if game is None:
                break
            category_games.append(game)

        if len(category_games) < 5:
            categories_failed.append(category_curr)
            if len(categories_failed) > max_failures:
                return RollResult(
                    error=f"Not enough rollable games in: {', '.join(categories_failed)}."
                )
            continue

        rolled_games.extend(category_games)

    return RollResult(rolled_games, None)


def roll_twoweekt2streak(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
) -> RollResult:
    """
    Two Week T2 Streak
    - 40 hour completion limit
    - $20 price limit
    - Tier 2
    - Multi-Category: Allowed
    - Multi-Stage. 2 games total.
    """

    # make sure user has one in limbo already
    _roll = user.get_waiting_roll("Two Week T2 Streak")
    already_rolled_games: list[str] = []
    # if so, pull the game so we don't roll the same one
    if _roll:
        already_rolled_games = _roll.games

    # find out which category / categories were already rolled
    valid_categories = set(get_args(hm.CATEGORIES))
    for _game_ceid in already_rolled_games:
        _game_supa = hm.get_item_from_list(_game_ceid, database_name)
        if _game_supa is None:
            return RollResult(
                None,
                f"Could not find previously rolled game in database. Please notify andy. {_game_ceid}",
            )
        valid_categories -= set(_game_supa.categories)

    # find game
    _game = hm.get_rollable_game(
        database_name=database_name,
        database_tier=database_tier,
        completion_limit=40,
        price_limit=20,
        tier_number=2,
        user=user,
        category=list(valid_categories),
        already_rolled_games=already_rolled_games,
        has_points_restriction=False,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
        allow_multi_category=True,
    )

    if _game is None:
        return RollResult(None, "Not enough rollable games.")
    return RollResult([_game], None)


def roll_twotwoweekt2streakstreak(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
) -> RollResult:
    """
    Two 'Two Week T2 Streak' Streak
    - 40 hour completion limit
    - $20 price limit
    - Tier 2
    - Multi-Category: Disallowed
    - Multi-Stage. 4 games total.
    - Requires 'Two Week T2 Streak' completion.
    """

    if not user.has_completed_roll("Two Week T2 Streak"):
        return RollResult(
            None,
            "You must first complete 'Two Week T2 Streak' to attempt Two \"Two Week T2 Streak\" Streak!",
        )

    # make sure user has one in limbo already
    _roll = user.get_waiting_roll('Two "Two Week T2 Streak" Streak')
    already_rolled_games: list[str] = []
    # if so, pull the game so we don't roll the same one
    if _roll:
        already_rolled_games = _roll.games

    # find out which category / categories were already rolled
    valid_categories = set(get_args(hm.CATEGORIES))
    for _game_ceid in already_rolled_games:
        _game_supa = hm.get_item_from_list(_game_ceid, database_name)
        if _game_supa is None:
            return RollResult(
                None,
                f"Could not find previously rolled game in database. Please notify andy. {_game_ceid}",
            )
        valid_categories -= set(_game_supa.categories)

    # find game
    _game = hm.get_rollable_game(
        database_name=database_name,
        database_tier=database_tier,
        completion_limit=40,
        price_limit=20,
        tier_number=2,
        user=user,
        category=list(valid_categories),
        already_rolled_games=already_rolled_games,
        has_points_restriction=False,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
        allow_multi_category=False,
    )

    if _game is None:
        return RollResult(None, "Not enough rollable games.")
    return RollResult([_game], None)


def roll_neverlucky(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
) -> RollResult:
    """
    Never Lucky.
    - No completion limit!
    - $20 price limit
    - Tier 3
    - Any category
    - No time limit! Can reroll 1 month after init time
    """

    _game = hm.get_rollable_game(
        database_name=database_name,
        database_tier=database_tier,
        completion_limit=None,
        price_limit=20,
        tier_number=3,
        user=user,
        category=None,
        already_rolled_games=None,
        has_points_restriction=False,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
        allow_multi_category=True,
    )

    if _game is None:
        return RollResult(None, "Not enough rollable games.")
    return RollResult([_game], None)


def roll_triplethreat(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
    category: hm.CATEGORIES | None,
) -> RollResult:
    """
    Triple Threat.
    - 40 hour completion limit
    - $20 price limit
    - Tier 3
    - Chosen category.
    - 3 games
    - Requires 'Never Lucky' completion.
    """

    if category is None:
        return RollResult(None, "Please rerun the command and select a category!")

    if not user.has_completed_roll("Never Lucky"):
        return RollResult(
            None, "You must first complete 'Never Lucky' to attempt Triple Threat!"
        )

    rolled_games: list[str] = []
    for _ in range(3):
        _game = hm.get_rollable_game(
            database_name=database_name,
            database_tier=database_tier,
            completion_limit=40,
            price_limit=20,
            tier_number=3,
            user=user,
            category=category,
            already_rolled_games=rolled_games,
            has_points_restriction=False,
            price_restriction=price_restriction,
            hours_restriction=hours_restriction,
            allow_multi_category=True,
        )
        if _game is None:
            return RollResult(None, "Not enough rollable games.")
        rolled_games.append(_game)

    return RollResult(rolled_games, None)


def roll_letfatedecide(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
    category: hm.CATEGORIES | None,
) -> RollResult:
    """
    Let Fate Decide.
    - No completion limit.
    - $20 price limit.
    - Tier 4
    - Chosen category
    - No time limit! Can reroll 3 months after init time.
    """

    if category is None:
        return RollResult(None, "Please rerun the command and select a category!")

    _game = hm.get_rollable_game(
        database_name=database_name,
        database_tier=database_tier,
        completion_limit=None,
        price_limit=20,
        tier_number=4,
        user=user,
        category=category,
        already_rolled_games=None,
        has_points_restriction=False,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
        allow_multi_category=True,
    )

    if _game is None:
        return RollResult(None, "Not enough rollable games.")
    return RollResult([_game], None)


def roll_fourwardthinking(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
    category: hm.CATEGORIES,
) -> RollResult:
    """
    Fourward Thinking.
    - 4 games, multi-stage.
    - Each game is of Tier i, where i starts at 1 and goes to 4.
    - 40 * i completion limit
    - $20 price limit
    - Requires 'Let Fate Decide',
    - Chosen category.
    - Multi-Category: Disallowed
    """

    # Assume that if we're here, the status is between_stages and we're looking for another roll.

    if not user.has_completed_roll("Let Fate Decide"):
        return RollResult(
            None,
            "You must first complete 'Let Fate Decide' to attempt Fourward Thinking!",
        )

    roll = user.get_current_roll("Fourward Thinking")
    already_rolled_games = [] if roll is None else roll.games

    tier = len(already_rolled_games) + 1

    _game = hm.get_rollable_game(
        database_name=database_name,
        database_tier=database_tier,
        completion_limit=40 * tier,
        price_limit=20,
        tier_number=tier,
        user=user,
        category=category,
        already_rolled_games=already_rolled_games,
        has_points_restriction=False,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
        allow_multi_category=False,
    )
    if _game is None:
        return RollResult(None, "Not enough rollable games.")
    return RollResult([_game], None)


def roll_destinyalignment(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    partner: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
) -> RollResult:
    """
    Destiny Alignment.
    - Player 1 rolls a game from Player 2's completed game's list
    - Player 2 rolls a game from Player 1's completed game's list
    - There is no tier or category requirement here.
    - No due time (rerolling this is gonna suck)
    - $20 price limit
    - No hours limit
    - Neither player can have any points in their rolled game.
    - Players must be the same rank
      - UNLESS both players are rank SS and above.
      - e.g. A Rank SSS and a Rank SS may play together.
    """
    # --- error checking ---
    if (
        user.rank_num < 6 or partner.rank_num < 6
    ) and user.rank_num != partner.rank_num:
        return RollResult(
            None,
            (
                "For Destiny Alignment, both users must be either:\n"
                "- the same rank, or\n"
                "- both be rank SS or above.\n"
                f"You are {user.rank} and your partner is {partner.rank}."
            ),
        )

    # roll user's game from partner's library
    _player_1_game = hm.get_rollable_game(
        partner.get_completed_games(database_name),
        database_tier,
        completion_limit=None,
        price_limit=20,
        tier_number=None,
        user=user,
        category=None,
        already_rolled_games=None,
        has_points_restriction=True,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
        allow_multi_category=True,
    )
    if _player_1_game is None:
        return RollResult(
            None, "Your partner did not have enough rollable completed games."
        )

    # roll partner's game from user's library
    _player_2_game = hm.get_rollable_game(
        user.get_completed_games(database_name),
        database_tier,
        completion_limit=None,
        price_limit=20,
        tier_number=None,
        user=partner,
        category=None,
        already_rolled_games=None,
        has_points_restriction=True,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
        allow_multi_category=True,
    )
    if _player_2_game is None:
        return RollResult(None, "You did not have enough rollable completed games.")
    return RollResult([_player_1_game, _player_2_game], None)


def roll_soulmates(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    partner: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
    tier: int | None,
) -> RollResult:
    """
    Soul Mates.
    - One game.
    - Both players must complete it.
    - Hour completion limit is dependent on the chosen tier.
      - HOUR_LIMITS = [15, 40, 80, 160, None, None]
      - If tier == 6, the user may roll any game T5-T7.
      - Tier error checking is done in this function.
    - $20 price limit.
    - Neither player can have any points in this game.
    """
    if tier is None:
        return RollResult(None, "Please rerun the command and select a tier.")
    if tier < 1 or tier > 6:
        return RollResult(None, "Please select a valid tier.")

    HOUR_LIMITS = [15, 40, 80, 160, None, None]

    _game = hm.get_rollable_game(
        database_name=database_name,
        database_tier=database_tier,
        completion_limit=HOUR_LIMITS[tier - 1],
        price_limit=20,
        tier_number=tier,
        user=[user, partner],
        category=None,
        already_rolled_games=None,
        has_points_restriction=True,
        price_restriction=price_restriction,
        hours_restriction=hours_restriction,
        allow_multi_category=True,
    )

    if _game is None:
        return RollResult(None, f"Could not find a rollable game in Tier {tier}.")
    return RollResult([_game], None)


def roll_teamworkmakesthedreamwork(
    database_name: list[CEGame],
    database_tier: dict,
    user: CEUser,
    partner: CEUser,
    price_restriction: bool,
    hours_restriction: bool,
) -> RollResult:
    """
    Teamwork Makes the Dream Work.
    - Four T3s are rolled.
    - Between Player 1 and Player 2, all games must be completed within one month.
    - 40 hour completion limit
    - $20 price limit
    - Neither player can have any points in any of their rolled games.
    """

    rolled_games: list[str] = []
    for _ in range(4):
        _game = hm.get_rollable_game(
            database_name=database_name,
            database_tier=database_tier,
            completion_limit=40,
            price_limit=20,
            tier_number=3,
            user=[user, partner],
            category=None,
            already_rolled_games=rolled_games,
            has_points_restriction=True,
            price_restriction=price_restriction,
            hours_restriction=hours_restriction,
            allow_multi_category=True,
        )
        if _game is None:
            return RollResult(None, "Not enough rollable games.")
        rolled_games.append(_game)
    return RollResult(rolled_games, None)


#   _____   _    _   ______    _____   _  __           _____     ____    _        _         _____
#  / ____| | |  | | |  ____|  / ____| | |/ /          |  __ \   / __ \  | |      | |       / ____|
# | |      | |__| | | |__    | |      | ' /   ______  | |__) | | |  | | | |      | |      | (___
# | |      |  __  | |  __|   | |      |  <   |______| |  _  /  | |  | | | |      | |       \___ \
# | |____  | |  | | | |____  | |____  | . \           | | \ \  | |__| | | |____  | |____   ____) |
#  \_____| |_|  |_| |______|  \_____| |_|\_\          |_|  \_\  \____/  |______| |______| |_____/


async def check_rolls(
    interaction: discord.Interaction, friend: discord.Member | None = None
):
    """
    Returns a message with links to CE Assistant's frontend showing rolls.
    - If the author of the interaction is registered, it will show
      a link to their rolls.
    - If the `friend` parameter is not `None`, and they are registered,
      it will show a link to their rolls as well.

    Parameters
    ---
    interaction: `discord.Interaction`
        The interaction this command is responding to.
    friend: `discord.Member | None` (default None)
        If the user wants to see rolls for somebody else,
        they can select them here.
    """
    # defer the message
    await interaction.response.defer()

    # log this interaction
    await hm.log_command(
        client,
        interaction,
        "check-rolls",
        False,
        friend=(None if friend is None else friend.mention),
    )

    # pull from supabase
    user = SupabaseReader.get_user(interaction.user.id, use_discord_id=True)
    _friend_local = None
    if friend is not None:
        _friend_local = SupabaseReader.get_user(friend.id, use_discord_id=True)

    # if someone puts themselves as friend don't say anything
    if (
        user is not None
        and _friend_local is not None
        and user.ce_id == _friend_local.ce_id
    ):
        _friend_local = None
        friend = None

    # generate the message
    message: str = ""
    if user is not None:
        message += f"[Click here to see all of your rolls](https://cebot.me/rolls/{user.ce_id})\n"
    if friend is not None and _friend_local is not None:
        message += (
            f"[Click here to see all of {_friend_local.display_name}'s rolls]"
            f"(https://cebot.me/rolls/{_friend_local.ce_id})\n"
        )
    elif friend is not None and _friend_local is None:
        message += f"Could not find {friend.name} in CE Assistant's database. Please have them run /register.\n"
    message += "[Click here to see all rolls from the past month](https://cebot.me/rolls/recent)\n"

    return await interaction.followup.send(message)


class CoOpConfirmView(discord.ui.View):
    def __init__(self, partner_discord_id: int):
        super().__init__(timeout=300)  # 5 minutes
        self.confirmed: bool | None = None
        self.partner_id: int = partner_discord_id

    @discord.ui.button(label="I'm in!", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.partner_id:
            return
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Nah", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.partner_id:
            return
        self.confirmed = False
        self.stop()
        await interaction.response.defer()


class ConfirmCancelView(discord.ui.View):
    def __init__(self, user_discord_id: int):
        super().__init__(timeout=60)
        self.confirmed: bool | None = None
        self.user_id: int = user_discord_id

    @discord.ui.button(label="Yes, fail my roll", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        self.confirmed = False
        self.stop()
        await interaction.response.defer()
