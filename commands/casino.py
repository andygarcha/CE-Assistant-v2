"""This module is for all casino-related commands."""

from dataclasses import dataclass
import random
from typing import get_args
import uuid
import discord
from discord import app_commands
from Classes.CE_User import CEUser
from Classes.CE_Game import CEGame
from Classes.CE_Roll import CERoll
from Modules import SupabaseReader, hm
import logging

""" === GETTING CLIENT TO WORK === """
logger = logging.getLogger(__name__)


def setup(cli: discord.Client, tree: app_commands.CommandTree, gui: discord.Guild):
    global client, guild
    client = cli
    guild = gui

    # ---- solo roll command ----
    @tree.command(
        name="solo-roll",
        description="Roll a solo event with CE Assistant!",
        guild=guild,
    )
    @app_commands.describe(event_name="The event you'd like to roll.")
    @app_commands.describe(
        category="If the event requires a chosen category, select it here. If the event doesn't require it, it will be ignored."
    )
    @app_commands.describe(
        price_restriction="Set this to false if you'd like to be able to roll any game, regardless of price."
    )
    @app_commands.describe(
        hours_restriction="Set this to false if you'd like to be able to roll any game, regardless of SH hours."
    )
    async def solo_roll_command(
        interaction: discord.Interaction,
        event_name: hm.SOLO_ROLL_EVENT_NAMES,
        category: hm.CATEGORIES | None = None,
        price_restriction: bool = True,
        hours_restriction: bool = True,
    ):
        # return await interaction.response.send_message("Under construction.")
        await solo_roll(interaction, event_name, category, price_restriction, hours_restriction)
        pass

    # ---- coop roll command ----
    @tree.command(
        name="coop-roll",
        description="Roll a Co-Op or PvP roll with a friend!",
        guild=guild,
    )
    @app_commands.describe(event_name="The event you'd like to roll.")
    @app_commands.describe(partner="The partner you'd like to roll with.")
    async def coop_roll_command(
        interaction: discord.Interaction,
        event_name: hm.COOP_ROLL_EVENT_NAMES,
        partner: discord.Member,
    ):
        return await interaction.response.send_message("Under construction.")
        await coop_roll(interaction, event_name, partner)
        pass

    # ---- check rolls command ----
    @tree.command(
        name="check-rolls",
        description="Check the status of your current and completed casino rolls!",
        guild=guild,
    )
    async def check_rolls_command(interaction: discord.Interaction):
        await check_rolls(interaction)
        pass

    pass


#   _____    ____    _         ____      _____     ____    _        _
#  / ____|  / __ \  | |       / __ \    |  __ \   / __ \  | |      | |
# | (___   | |  | | | |      | |  | |   | |__) | | |  | | | |      | |
#  \___ \  | |  | | | |      | |  | |   |  _  /  | |  | | | |      | |
#  ____) | | |__| | | |____  | |__| |   | | \ \  | |__| | | |____  | |____
# |_____/   \____/  |______|  \____/    |_|  \_\  \____/  |______| |______|


async def solo_roll(
    interaction: discord.Interaction,
    event_name: hm.SOLO_ROLL_EVENT_NAMES,
    category: hm.CATEGORIES | None = None,
    price_restriction: bool = True,
    hours_restriction: bool = True,
):
    await interaction.response.defer()

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

    # user currently rolled => is rerollable
    if event_name in ["Never Lucky", "Let Fate Decide"]:
        _current_roll = user.get_current_roll(event_name)

        if _current_roll is not None:
            _cooldown_date = _current_roll.calculate_cooldown_date()

            if _cooldown_date is None or _cooldown_date <= hm.get_datetime("now"):
                return await interaction.followup.send(
                    f"Rerolling {event_name} rolls is not yet implemented."
                )
            
    # roll requires category
    #  (must come after rerolling bc user could just try rerolling... no category needed)
    CATEGORY_REQUIRED = ["Triple Threat", "Let Fate Decide", "Fourward Thinking"]
    if event_name in CATEGORY_REQUIRED and category is None:
        return await interaction.followup.send(
            f"{event_name} requires a chosen category. Please rerun the command and select your category."
        )

    # user currently rolled => not rerollable
    if user.has_current_roll(event_name):
        return await interaction.followup.send(
            f"You're currently attempting {event_name}! Please finish this instance before rerolling."
        )

    # user has pending
    if user.has_pending(event_name):
        return await interaction.followup.send(
            "You just tried rolling this event. Please wait about 10 minutes before trying again."
            + " (P.S. This is not a cooldown. Just has to do with how the bot backend works.)"
        )

    # jarvis's random event!
    # -- make sure to not reroll this on every time they move forward
    if random.randint(0, 99) == 0 and not user.has_waiting_roll(event_name):
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
            assert category is not None
            result = roll_triplethreat(database_name, database_tier, user, price_restriction, hours_restriction, category)
        case "Let Fate Decide":
            assert category is not None
            result = roll_letfatedecide(database_name, database_tier, user, price_restriction, hours_restriction, category)
        case "Fourward Thinking":
            result = RollResult(None, "Fourward Thinking is not currently implemented.")
        case _:
            result = RollResult(None, f"{event_name} is not a valid event name.")

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

        game = hm.get_item_from_list(result.games[0], database_name)
        if game is None:
            return await interaction.followup.send(
                f"Error: Could not find {result.games[0]} in database_name."
            )
        message = (
            f"The next stage of your {event_name} roll is {game.name_with_link}. "
            f"You have until {roll.due_discord_timestamp} to complete this. Good luck!"
        )

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
        # get the
        game_strings: list[str] = []
        for g in result.games:
            _game_object = hm.get_item_from_list(g, database_name)
            if _game_object is None:
                return await interaction.followup.send(
                    f"Error: Could not find {g} in the game database."
                )
            game_strings.append(_game_object.name_with_link)

        message = (
            f"In your {event_name} roll, "
            f"you rolled the following games: {hm.get_grammar_str(game_strings)}. "
            f"You have until {roll.due_discord_timestamp} to complete this event!"
        )

        if len(message) > 2000:
            message = (
                f"In your {event_name} roll, "
                f"the games you rolled did not fit in one message. Please run /check-rolls to see the full list. "
                f"You have until {roll.due_discord_timestamp} to complete this event!"
            )

    SupabaseReader.dump_roll(roll)
    return await interaction.followup.send(message)


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
        category_curr = random.choice(categories_remaining)
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
    category: hm.CATEGORIES,
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
    category: hm.CATEGORIES,
) -> RollResult:
    """
    Let Fate Decide.
    - No completion limit.
    - $20 price limit.
    - Tier 4
    - Chosen category
    - No time limit! Can reroll 3 months after init time.
    """

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
    raise NotImplementedError

#   _____   _    _   ______    _____   _  __           _____     ____    _        _         _____
#  / ____| | |  | | |  ____|  / ____| | |/ /          |  __ \   / __ \  | |      | |       / ____|
# | |      | |__| | | |__    | |      | ' /   ______  | |__) | | |  | | | |      | |      | (___
# | |      |  __  | |  __|   | |      |  <   |______| |  _  /  | |  | | | |      | |       \___ \
# | |____  | |  | | | |____  | |____  | . \           | | \ \  | |__| | | |____  | |____   ____) |
#  \_____| |_|  |_| |______|  \_____| |_|\_\          |_|  \_\  \____/  |______| |______| |_____/


async def check_rolls(interaction: discord.Interaction):
    # defer the message
    await interaction.response.defer()

    return await interaction.followup.send(
        "[click me :)](https://ce-assistant-frontend.vercel.app/rolls)"
    )
