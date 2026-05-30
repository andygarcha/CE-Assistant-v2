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
        price_restriction="Set this to false if you'd like to be able to roll any game, regardless of price."
    )
    @app_commands.describe(
        hours_restriction="Set this to false if you'd like to be able to roll any game, regardless of SH hours."
    )
    async def solo_roll_command(
        interaction: discord.Interaction,
        event_name: hm.SOLO_ROLL_EVENT_NAMES,
        price_restriction: bool = True,
        hours_restriction: bool = True,
    ):
        # return await interaction.response.send_message("Under construction.")
        await solo_roll(interaction, event_name, price_restriction, hours_restriction)
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
    price_restriction: bool = True,
    hours_restriction: bool = True,
):
    await interaction.response.defer()

    lucky = False

    # pull mongo database
    database_name = SupabaseReader.get_database_name()
    database_tier = SupabaseReader.get_database_tier(database_name)

    # grab the user
    user = SupabaseReader.get_user(interaction.user.id, use_discord_id=True)
    if user is None:
        return await interaction.followup.send(
            "Sorry, you're not registered in the CE Assistant database. Please run `/register` first!"
        )

    # user has cooldown
    if user.has_cooldown(event_name):
        return await interaction.followup.send(
            f"You are currently on cooldown for {event_name} until <t:{user.get_cooldown_time(event_name)}>. "
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
            result = RollResult(None, "Triple Threat is not currently implemented.")
            # result = roll_triplethreat(database_name, database_tier, user, price_restriction, hours_restriction)
        case "Let Fate Decide":
            result = RollResult(None, "Let Fate Decide is not currently implemented.")
            # result = roll_letfatedecide(database_name, database_tier, user, price_restriction, hours_restriction)
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
        game_strings_backup: list[str] = []
        for g in result.games:
            _game_object = hm.get_item_from_list(g, database_name)
            if _game_object is None:
                return await interaction.followup.send(
                    f"Error: Could not find {g} in database_name."
                )

            game_strings.append(_game_object.name_with_link)
            game_strings_backup.append(_game_object.game_name)

        message = (
            f"In your {event_name} roll, "
            f"you rolled the following games: {hm.get_grammar_str(game_strings)}. "
            f"You have until {roll.due_discord_timestamp} to complete this event!"
        )

        if len(message) > 2000:
            message = (
                f"In your {event_name} roll, "
                f"you rolled the following games: {hm.get_grammar_str(game_strings_backup)}. "
                f"You have until {roll.due_discord_timestamp} to complete this event!"
            )

    SupabaseReader.dump_roll(roll)

    if len(message) > 2000:
        message = (
            f"Could not display all {len(result.games)} games in one message. "
            f"You have until {roll.due_discord_timestamp} to complete this event!"
        )
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
            already_rolled_games=[],
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
            "You must first complete 'One Hell of a Week' to attempt One Hell of a Month!",
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
        allow_multi_category=True,
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


""" === CLASSES === """


class DestinyAlignmentAgreeView(discord.ui.View):
    "The agree-button view for Destiny Alignment. Only `partner` can click these buttons."

    def __init__(self, user_ce_id: str, partner_ce_id: str):
        self.__user_ce_id = user_ce_id
        self.__partner_ce_id = partner_ce_id
        self.__button_clicked = False
        super().__init__(timeout=600)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.__button_clicked:
            return
        self.__button_clicked = True

        # make sure only the partner can touch the buttons.
        user = SupabaseReader.get_user(self.__user_ce_id)
        partner = SupabaseReader.get_user(self.__partner_ce_id)
        if interaction.user.id != partner.discord_id:
            self.__button_clicked = False
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )

        # defer
        await interaction.response.defer()

        # pull database name
        database_name = SupabaseReader.get_database_name()
        database_tier = SupabaseReader.get_database_tier()

        # get the game for the user from the partner's library
        game_for_user = await hm.get_rollable_game(
            partner.get_completed_games_2(database_name),
            database_tier=database_tier,
            completion_limit=None,
            price_limit=20,
            tier_number=None,
            user=user,
            has_points_restriction=True,
        )

        # check to make sure one exists
        if game_for_user is None:
            return await interaction.followup.send(
                f"There are no completed games in {partner.mention()}'s library that are rollable "
                + f"to {user.mention()}."
            )

        # get the game for the partner from the user's library
        game_for_partner = await hm.get_rollable_game(
            user.get_completed_games_2(database_name),
            database_tier=database_tier,
            completion_limit=None,
            price_limit=20,
            tier_number=None,
            user=partner,
            has_points_restriction=True,
        )

        # check to make sure one exists
        if game_for_partner is None:
            return await interaction.followup.send(
                f"There are no completed games in {user.mention()}'s library that are rollable "
                + f"to {partner.mention()}."
            )

        # add the roll to the user...
        user.add_current_roll(
            CERoll(
                roll_name="Destiny Alignment",
                user_ce_id=user.ce_id,
                games=[game_for_user, game_for_partner],
                partner_ce_id=partner.ce_id,
                is_current=True,
            )
        )

        # ...and the partner.
        partner.add_current_roll(
            CERoll(
                roll_name="Destiny Alignment",
                user_ce_id=partner.ce_id,
                games=[game_for_partner, game_for_user],
                partner_ce_id=user.ce_id,
                is_current=True,
            )
        )

        # and then dump them both.
        SupabaseReader.dump_user(user)
        SupabaseReader.dump_user(partner)

        self.clear_items()

        game_for_user_object = hm.get_item_from_list(game_for_user, database_name)
        game_for_partner_object = hm.get_item_from_list(game_for_partner, database_name)

        return await interaction.followup.edit_message(
            content=(
                f"{user.mention()} must complete {game_for_user_object.name_with_link} and "
                + f"{partner.mention()} must complete {game_for_partner_object.name_with_link}. Your cooldown "
                + f"ends on <t:{user.get_current_roll('Destiny Alignment').calculate_cooldown_date(database_name)}>."
            ),
            message_id=interaction.message.id,
            view=discord.ui.View(),
        )

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # make sure only the partner can touch the buttons
        partner = SupabaseReader.get_user(self.__partner_ce_id)
        if interaction.user.id != partner.discord_id:
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )

        # clear the items
        self.clear_items()
        return await interaction.response.edit_message(
            content="Roll cancelled.", view=self
        )

    pass


class SoulMatesDropdown(discord.ui.Select):
    "The dropdown-select for choosing a Tier in Soul Mates. Only `user` can select the tier."

    def __init__(self, user_ce_id: str, partner_ce_id: str):
        self.__user_ce_id = user_ce_id
        self.__partner_ce_id = partner_ce_id
        options: list[discord.SelectOption] = []
        for i in range(5):
            options.append(
                discord.SelectOption(
                    label=f"Tier {i + 1}",
                    value=f"{i + 1}",
                    description=f"Roll a Tier {i + 1}",
                    emoji=hm.get_emoji(f"Tier {i + 1}"),
                )
            )
        options.append(
            discord.SelectOption(
                label="Tier 5+", value="6", description="Roll a Tier 5 (or above)"
            )
        )

        super().__init__(
            placeholder="Choose a Tier.", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user = SupabaseReader.get_user(self.__user_ce_id)
        partner = SupabaseReader.get_user(self.__partner_ce_id)

        # make sure only the user can pick the tier
        if interaction.user.id != user.discord_id:
            return await interaction.response.send_message(
                "You cannot select this.", ephemeral=True
            )

        # send message
        if self.values[0] == "6":
            return await interaction.response.edit_message(
                content=(
                    f"{partner.mention()}, would you like to enter a Tier 5+ Soul Mates "
                    + f"with {user.mention()}?"
                ),
                view=SoulMatesAgreeView(user.ce_id, partner.ce_id, self.values[0]),
            )
        return await interaction.response.edit_message(
            content=(
                f"{partner.mention()}, would you like to enter a Tier {self.values[0]} Soul Mates "
                + f"with {user.mention()}?"
            ),
            view=SoulMatesAgreeView(user.ce_id, partner.ce_id, self.values[0]),
        )

    pass


class SoulMatesAgreeView(discord.ui.View):
    "The agree-button view for Soul Mates. Only `partner` can push the buttons."

    def __init__(self, user_ce_id: str, partner_ce_id: str, tier: str):
        self.__user_ce_id = user_ce_id
        self.__partner_ce_id = partner_ce_id
        self.__tier = tier
        self.__button_clicked = False
        super().__init__(timeout=600)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        user = SupabaseReader.get_user(self.__user_ce_id)
        partner = SupabaseReader.get_user(self.__partner_ce_id)

        if self.__button_clicked:
            return
        self.__button_clicked = True

        # make sure only the partner can click this.
        if interaction.user.id != partner.discord_id:
            self.__button_clicked = False
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )

        # defer
        await interaction.response.defer()

        hour_limit = [None, 15, 40, 80, 160, None, None]

        tier_num = int(self.__tier)

        database_name = SupabaseReader.get_database_name()
        database_tier = SupabaseReader.get_database_tier()

        rolled_game = await hm.get_rollable_game(
            database_name=database_name,
            database_tier=database_tier,
            completion_limit=hour_limit[tier_num],
            price_limit=20,
            tier_number=tier_num,
            user=[user, partner],
            has_points_restriction=True,
        )

        if rolled_game is None:
            return await interaction.followup.send(
                "It seems no rollable games are available right now. Please ping andy!"
            )

        user_roll = CERoll(
            roll_name="Soul Mates",
            user_ce_id=user.ce_id,
            games=[rolled_game],
            partner_ce_id=partner.ce_id,
            is_current=True,
            tier_num=tier_num,
        )

        partner_roll = CERoll(
            roll_name="Soul Mates",
            user_ce_id=partner.ce_id,
            games=[rolled_game],
            partner_ce_id=user.ce_id,
            is_current=True,
            tier_num=tier_num,
        )

        user.add_current_roll(user_roll)
        partner.add_current_roll(partner_roll)

        SupabaseReader.dump_user(user)
        SupabaseReader.dump_user(partner)

        game_object = hm.get_item_from_list(rolled_game, database_name)

        return await interaction.followup.edit_message(
            message_id=interaction.message.id,
            content=(
                f"{user.mention()} and {partner.mention()} have until <t:{user_roll.due_timestamp}> "
                + f"to complete {game_object.name_with_link}."
            ),
            view=discord.ui.View(),
        )

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        partner = SupabaseReader.get_user(self.__partner_ce_id)

        # make sure it was the right person who clicked it
        if interaction.user.id != partner.discord_id:
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )

        # clear items
        self.clear_items()
        return await interaction.response.edit_message(
            content="Roll cancelled.", view=self
        )

    pass


class TeamworkMakesTheDreamWorkAgreeView(discord.ui.View):
    "The agree-button view for Teamwork Makes the Dream Work. Only `partner` can select the buttons."

    def __init__(self, user_ce_id: str, partner_ce_id: str):
        self.__user_ce_id = user_ce_id
        self.__partner_ce_id = partner_ce_id
        self.__button_clicked = False
        super().__init__(timeout=600)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.__button_clicked:
            return
        self.__button_clicked = True

        user = SupabaseReader.get_user(self.__user_ce_id)
        partner = SupabaseReader.get_user(self.__partner_ce_id)

        # make sure the right person clicked
        if interaction.user.id != partner.discord_id:
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )

        await interaction.response.defer()

        database_name = SupabaseReader.get_database_name()
        database_tier = SupabaseReader.get_database_tier()

        rolled_games: list[str] = []
        for i in range(4):
            rolled_games.append(
                await hm.get_rollable_game(
                    database_name=database_name,
                    database_tier=database_tier,
                    completion_limit=40,
                    price_limit=20,
                    tier_number=3,
                    user=[user, partner],
                    already_rolled_games=rolled_games,
                    has_points_restriction=True,
                )
            )

        if None in rolled_games:
            return await interaction.followup.edit_message(
                content="It looks like there aren't enough rollable games at this time. Please alert Andy.",
                message_id=interaction.message.id,
            )

        user_roll = CERoll(
            roll_name="Teamwork Makes the Dream Work",
            user_ce_id=user.ce_id,
            games=rolled_games,
            partner_ce_id=partner.ce_id,
            is_current=True,
        )
        user.add_current_roll(user_roll)
        partner.add_current_roll(
            CERoll(
                roll_name="Teamwork Makes the Dream Work",
                user_ce_id=partner.ce_id,
                games=rolled_games,
                partner_ce_id=user.ce_id,
                is_current=True,
            )
        )
        SupabaseReader.dump_user(user)
        SupabaseReader.dump_user(partner)

        rolled_games_objects = [
            hm.get_item_from_list(game_id, database_name) for game_id in rolled_games
        ]

        content = (
            f"{user.mention()} and {partner.mention()} must complete the following games by "
            + f"<t:{user_roll.due_timestamp}>: "
        )
        for i, game in enumerate(rolled_games_objects):
            content += f"{game.name_with_link}"
            if i != 3:
                content += ", "
        content += "."

        return await interaction.followup.edit_message(
            message_id=interaction.message.id, content=content, view=discord.ui.View()
        )

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        partner = SupabaseReader.get_user(self.__partner_ce_id)

        # make sure it was the right person who clicked it
        if interaction.user.id != partner.discord_id:
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )

        # clear items
        self.clear_items()
        return await interaction.response.edit_message(
            content="Roll cancelled.", view=self
        )

    pass


async def coop_roll(
    interaction: discord.Interaction,
    event_name: hm.COOP_ROLL_EVENT_NAMES,
    partner: discord.Member,
):
    await interaction.response.defer()

    # helps with variable names
    partner_discord = partner
    del partner
    partner = None

    # make the view
    view = discord.ui.View()

    # check they didn't roll with themselves
    if interaction.user.id == partner_discord.id:
        return await interaction.followup.send("You can't roll with yourself!")

    # grab the user
    user = SupabaseReader.get_user(interaction.user.id, use_discord_id=True)
    try:
        partner: CEUser = SupabaseReader.get_user(
            partner_discord.id, use_discord_id=True
        )
    except ValueError:
        partner = None

    # user doesn't exist
    if user is None:
        return await interaction.followup.send(
            "Sorry, you're not registered in the CE Assistant database. Please run `/register` first!"
        )

    # partner doesn't exist
    if partner is None:
        return await interaction.followup.send(
            "Sorry, your partner is not registered in the CE Assistant database. "
            + "Please have them run `/register` first!"
        )

    # destiny alignment allows for multiple concurrent rolls - apply different logic vs other co-op rolls
    if event_name == "Destiny Alignment":
        # check if the user / partner combo have an active DA roll underway
        if user.has_DA_roll(partner.ce_id, event_name):
            return await interaction.followup.send(
                f"You and your partner are currently attempting {event_name}!"
            )

        # check if the user has the maximum number of concurrent DA rolls
        if user.count_DA_rolls(event_name) >= 5:
            return await interaction.followup.send(
                f"You currently have the maximum number [5] of concurrent {event_name} rolls!"
            )

        # check if partner has the maximum number of concurrent DA rolls
        if partner.count_DA_rolls(event_name) >= 5:
            return await interaction.followup.send(
                f"Your partner currently has the maximum number [5] of concurrent {event_name} rolls!"
            )

    else:
        if user.has_current_roll(event_name):
            return await interaction.followup.send(
                f"You are currently attempting {event_name}!"
            )

        if partner.has_current_roll(event_name):
            return await interaction.followup.send(
                f"Your partner is currently attempting {event_name}!"
            )

    # user has cooldown
    database_name = SupabaseReader.get_database_name()
    if user.has_cooldown(event_name, database_name):
        return await interaction.followup.send(
            f"You are currently on cooldown for {event_name} until <t:{user.get_cooldown_time(event_name, database_name)}>. "
        )

    # partner has cooldown
    if partner.has_cooldown(event_name, database_name):
        return await interaction.followup.send(
            f"Your partner is currently on cooldown for {event_name} until <t:{user.get_cooldown_time(event_name, database_name)}>. "
        )

    # user has pending
    if user.has_pending(event_name):
        return await interaction.followup.send(
            "You just tried rolling this event. Please wait about 10 minutes before trying again."
            + " (P.S. This is not a cooldown. Just has to do with how the bot backend works.)"
        )

    # partner has pending
    if partner.has_pending(event_name):
        return await interaction.followup.send(
            "Your partner just tried rolling this event. Please wait about 10 minutes before trying again."
            + " (P.S. This is not a cooldown. Just has to do with how the bot backend works.)"
        )

    user.add_pending(event_name)
    partner.add_pending(event_name)
    SupabaseReader.dump_user(user)
    SupabaseReader.dump_user(partner)

    match event_name:
        case "Destiny Alignment":
            # check if the users are the same rank
            if (user.rank_num() < 6 and partner.rank_num() < 6) and (
                user.get_rank() != partner.get_rank()
            ):
                return await interaction.followup.send(
                    "For Destiny Alignment, both you and your partner have to be the same rank "
                    + f"(or both be SS Rank or above). You are {user.get_rank()} and your partner is {partner.get_rank()}."
                )
            return await interaction.followup.send(
                f"{partner.mention()}, would you like to enter into Destiny Alignment with {user.mention()}?",
                view=DestinyAlignmentAgreeView(user.ce_id, partner.ce_id),
            )

        case "Soul Mates":
            view = discord.ui.View(timeout=600)
            view.add_item(SoulMatesDropdown(user.ce_id, partner.ce_id))
            return await interaction.followup.send(
                f"{user.mention()}, select a Tier.", view=view
            )

        case "Teamwork Makes the Dream Work":
            return await interaction.followup.send(
                f"{partner.mention()}, would you like to enter into Teamwork Makes the Dream Work with {user.mention()}?",
                view=TeamworkMakesTheDreamWorkAgreeView(user.ce_id, partner.ce_id),
            )
            pass

        case "Winner Takes All" | "Game Theory":
            return await interaction.followup.send(
                f"{event_name} has retired. Look forward to future events!"
            )
    pass


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
        "[click me :)]https://ce-assistant-frontend.vercel.app/rolls"
    )
