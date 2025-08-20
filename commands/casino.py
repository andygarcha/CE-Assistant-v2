"""This module is for all casino-related commands."""
import random
from typing import get_args
import discord 
from discord import app_commands
from Classes.CE_User import CEUser
from Classes.CE_Game import CEGame
from Classes.CE_Roll import CERoll
from Modules import Discord_Helper, Mongo_Reader, hm

""" === GETTING CLIENT TO WORK === """
client : discord.Client = None
guild : discord.Guild = None

def setup(cli : discord.Client, tree : app_commands.CommandTree, gui : discord.Guild) :
    global client, guild
    client = cli
    guild = gui

    # ---- solo roll command ----
    @tree.command(name = "solo-roll",
                description = "Roll a solo event with CE Assistant!",
                guild = guild)
    @app_commands.describe(event_name = "The event you'd like to roll.")
    @app_commands.describe(price_restriction=
                           "Set this to false if you'd like to be able to roll any game, regardless of price.")
    @app_commands.describe(hours_restriction =
                           "Set this to false if you'd like to be able to roll any game, regardless of SH hours.")
    async def solo_roll_command(interaction : discord.Interaction, event_name : hm.SOLO_ROLL_EVENT_NAMES, 
                                price_restriction : bool = True, hours_restriction : bool = True) :
        await solo_roll(interaction, event_name, price_restriction, hours_restriction)
        pass

    # ---- coop roll command ----
    @tree.command(name="coop-roll", description="Roll a Co-Op or PvP roll with a friend!", guild=guild)
    @app_commands.describe(event_name="The event you'd like to roll.")
    @app_commands.describe(partner="The partner you'd like to roll with.")
    async def coop_roll_command(interaction : discord.Interaction, event_name : hm.COOP_ROLL_EVENT_NAMES, 
                                partner : discord.Member) :
        await coop_roll(interaction, event_name, partner)
        pass

    # ---- check rolls command ----
    @tree.command(name="check-rolls", description="Check the status of your current and completed casino rolls!", guild=guild)
    async def check_rolls_command(interaction : discord.Interaction) :
        await check_rolls(interaction)
        pass
    pass



""" === CLASSES === """
class TripleThreatDropdown(discord.ui.Select) :
    def __init__(self, user_ce_id : str, price_restriction : bool, hours_restriction : bool) :
        # store the user
        self.__user_ce_id = user_ce_id
        self.__price_restriction = price_restriction
        self.__hours_restriction = hours_restriction

        # initialize and set options
        options : list[discord.SelectOption] = []
        for category in get_args(hm.CATEGORIES) :
            options.append(discord.SelectOption(label=category, emoji=hm.get_emoji(category)))

        # init the superclass
        super().__init__(placeholder="Select a category.", min_values=1, max_values=1, options=options)

    async def callback(self, interaction : discord.Interaction) :
        "The callback."

        user = await Mongo_Reader.get_user(self.__user_ce_id)

        # stop other users from clicking the dropdown
        if interaction.user.id != user.discord_id : 
            return await interaction.response.send_message(
                "Stop that! This isn't your roll.", ephemeral=True
            )

        # defer the message
        await interaction.response.defer()

        # define our category
        category = self.values[0]

        # roll a game with these parameters
        database_name = await Mongo_Reader.get_database_name()
        rolled_games : list[str] = []
        for _ in range(3) :
            rolled_games.append(await hm.get_rollable_game(
                database_name=database_name,
                completion_limit=40,
                price_limit=20,
                tier_number=3,
                user=user,
                price_restriction=self.__price_restriction,
                category=category,
                already_rolled_games=rolled_games,
                hours_restriction=self.__hours_restriction
            ))

        if None in rolled_games :
            user.remove_pending("Triple Threat")
            await Mongo_Reader.dump_user(user)
            return await interaction.followup.send("Not enough qualifiable games. Please try again later!")

        roll : CERoll = CERoll(
            roll_name="Triple Threat",
            user_ce_id=user.ce_id,
            games=rolled_games,
            is_current=True
        )

        user.remove_pending("Triple Threat")
        user.add_current_roll(roll)
        await Mongo_Reader.dump_user(user)

        database_user = await Mongo_Reader.get_database_user()

        view = discord.ui.View()
        embeds = await Discord_Helper.get_roll_embeds(roll=roll, database_name=database_name, database_user=database_user)
        await Discord_Helper.get_buttons(view, embeds)

        return await interaction.followup.edit_message(
            message_id=interaction.message.id,
            #content=f"Your rolled game is [{game_object.game_name}](https://cedb.me/game/{game_object.ce_id}).",
            embed=embeds[0],
            view=view
        )

class LetFateDecideDropdown(discord.ui.Select) :
    def __init__(self, user : CEUser, price_restriction : bool, hours_restriction : bool) :
        # store the user
        self.__user = user
        self.__price_restriction = price_restriction
        self.__hours_restriction = hours_restriction

        # initialize and set options
        options : list[discord.SelectOption] = []
        for category in get_args(hm.CATEGORIES) :
            options.append(discord.SelectOption(label=category, emoji=hm.get_emoji(category)))

        # init the superclass
        super().__init__(placeholder="Select a category.", min_values=1, max_values=1, options=options)

    async def callback(self, interaction : discord.Interaction) :
        "The callback."

        user = await Mongo_Reader.get_user(self.__user.ce_id)

        if user is None : raise ValueError("User is not registered!")

        # stop other users from clicking the dropdown
        if interaction.user.id != user.discord_id : 
            return await interaction.response.send_message(
                "Stop that! This isn't your roll.", ephemeral=True
            )

        # defer the message
        await interaction.response.defer()

        # define our category
        category = self.values[0]

        # roll a game with these parameters
        database_name = await Mongo_Reader.get_database_name()
        rolled_game_id = await hm.get_rollable_game(
            database_name=database_name,
            completion_limit=None,
            price_limit=20,
            tier_number=4,
            user=user,
            price_restriction=self.__price_restriction,
            category=category,
            hours_restriction=self.__hours_restriction
        )

        roll : CERoll = CERoll(
            roll_name="Let Fate Decide",
            user_ce_id=user.ce_id,
            games=[rolled_game_id],
            is_current=True
        )

        user.remove_pending("Let Fate Decide")
        user.add_current_roll(roll)
        await Mongo_Reader.dump_user(user)

        database_user = await Mongo_Reader.get_database_user()

        view = discord.ui.View()
        embeds = await Discord_Helper.get_roll_embeds(roll=roll, database_name=database_name, database_user=database_user)
        await Discord_Helper.get_buttons(view, embeds)

        return await interaction.followup.edit_message(
            message_id=interaction.message.id,
            #content=f"Your rolled game is [{game_object.game_name}](https://cedb.me/game/{game_object.ce_id}).",
            embed=embeds[0],
            view=view
        )


class FourwardThinkingDropdown(discord.ui.Select) :
    def __init__(self, past_roll : CERoll, database_name : list[CEGame], price_restriction : bool,
                 hours_restriction : bool, user_id : str) :
        # store the user
        self.__past_roll = past_roll
        self.__price_restriction = price_restriction
        self.__hours_restriction = hours_restriction
        self.__user_ce_id = user_id

        # initialize options
        options : list[discord.SelectOption] = []

        # if haven't rolled before, here are options
        if past_roll is None : options = [
            discord.SelectOption(label=cat, emoji=hm.get_emoji(cat)) for cat in get_args(hm.CATEGORIES)
        ]

        # if they have rolled before, get new options
        else :
            already_rolled_categories = past_roll.rolled_categories(database_name=database_name)
            for cat in get_args(hm.CATEGORIES) :
                if cat not in already_rolled_categories : options.append(
                    discord.SelectOption(label=cat, emoji=hm.get_emoji(cat))
                )
        
        super().__init__(placeholder="Select a category.", min_values=1, max_values=1, options=options)

    async def callback(self, interaction : discord.Interaction) :
        "The callback."

        user = await Mongo_Reader.get_user(self.__user_ce_id)

        # stop other users from clicking the dropdown
        if interaction.user.id != user.discord_id :
            return await interaction.response.send_message(
                "Stop that! This isn't your roll.", ephemeral=True
            )
        
        # defer the message
        await interaction.response.defer()

        # get past_roll
        past_roll = user.get_waiting_roll("Fourward Thinking")
        if past_roll is None :
            past_roll = CERoll(
                roll_name="Fourward Thinking",
                user_ce_id=user.ce_id,
                games=[],
                is_current=True
            )
        
        # get the data
        database_name = await Mongo_Reader.get_database_name()
        next_phase_num = len(past_roll.games) + 1
        category = self.values[0]
        game_id = await hm.get_rollable_game(
            database_name=database_name,
            completion_limit=40*next_phase_num,
            price_limit=20,
            tier_number=next_phase_num,
            user=user,
            category=category,
            price_restriction=self.__price_restriction,
            hours_restriction=self.__hours_restriction
        )

        # add the new game and reset the due time.
        past_roll.add_game(game_id)
        past_roll.reset_due_time()

        # replace the roll and push the user to mongo
        user.update_waiting_roll(past_roll)
        user.unwait_waiting_roll("Fourward Thinking")
        user.remove_pending("Fourward Thinking")
        await Mongo_Reader.dump_user(user)

        # now send the message
        game_object = hm.get_item_from_list(game_id, database_name)
        return await interaction.followup.edit_message(
            message_id=interaction.message.id,
            content=f"Your new game is [{game_object.game_name}](https://cedb.me/game/{game_object.ce_id}).",
            view=discord.ui.View()
        )
    

class RerollView(discord.ui.View) :
    def __init__(self, user_ce_id : str, event_name : str) :
        self.__user_ce_id = user_ce_id
        self.__event_name = event_name
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction : discord.Interaction, button : discord.ui.Button) :
        # pull database user and get user
        user = await Mongo_Reader.get_user(self.__user_ce_id)

        user.remove_current_roll(self.__event_name) # remove the current roll

        await Mongo_Reader.dump_user(user)

        self.clear_items()
        await interaction.response.edit_message(content=f"You can now reroll {self.__event_name}.", view=self)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction : discord.Interaction, button : discord.ui.Button) :
        self.clear_items()
        await interaction.response.edit_message(content="Reroll cancelled. Your old roll is still intact.", view=self)


#   _____    ____    _         ____      _____     ____    _        _      
#  / ____|  / __ \  | |       / __ \    |  __ \   / __ \  | |      | |     
# | (___   | |  | | | |      | |  | |   | |__) | | |  | | | |      | |     
#  \___ \  | |  | | | |      | |  | |   |  _  /  | |  | | | |      | |     
#  ____) | | |__| | | |____  | |__| |   | | \ \  | |__| | | |____  | |____ 
# |_____/   \____/  |______|  \____/    |_|  \_\  \____/  |______| |______|



async def solo_roll(interaction : discord.Interaction, event_name : hm.SOLO_ROLL_EVENT_NAMES, 
                    price_restriction : bool = True, hours_restriction : bool = True) :
    await interaction.response.defer()

    #return await interaction.followup.send("Sorry, but rolling is still under construction! Please come back later...")
    view = discord.ui.View()

    # pull mongo database
    database_name = await Mongo_Reader.get_database_name()

    # define channel
    user_log_channel = client.get_channel(hm.USER_LOG_ID)

    # grab the user
    try :
        user = await Mongo_Reader.get_user(interaction.user.id, use_discord_id=True)
    except ValueError as e :
        print(e.with_traceback())
        return await interaction.followup.send(
            "Sorry, you're not registered in the CE Assistant database. Please run `/register` first!"
        )

    # user has cooldown
    if user.has_cooldown(event_name, database_name) :
        return await interaction.followup.send(
            f"You are currently on cooldown for {event_name} until <t:{user.get_cooldown_time(event_name, database_name)}>. "
        )
    
    # user currently rolled
    if (event_name in ["Never Lucky", "Let Fate Decide"]) and (user.has_current_roll(event_name)) and not (
        user.get_current_roll(event_name).calculate_cooldown_date(database_name) > hm.get_unix(days="now")
    ) :
        view = RerollView(user.ce_id, event_name)
        return await interaction.followup.send(f"Would you like to reset your {event_name} roll?", view=view)       
    
    if user.has_current_roll(event_name) :
        return await interaction.followup.send(
            f"You're currently attempting {event_name}! Please finish this instance before rerolling."
        )
    # user has pending
    if user.has_pending(event_name) :
        return await interaction.followup.send(
            "You just tried rolling this event. Please wait about 10 minutes before trying again." +
            " (P.S. This is not a cooldown. Just has to do with how the bot backend works.)"
        )
    
    # jarvis's random event!
    if random.randint(0, 99) == 0 : 
        await user_log_channel.send(
            f"Congratulations <@{interaction.user.id}>! You've won Jarvis's super secret reward! " +
            "Please DM him for your prize :)"
        )
        
    # -- set up vars --
    rolled_games : list[str] = []

    # in this switch statement, grab the games. the roll will be set up at the end.
    match(event_name) :
        case "One Hell of a Day" :
            # -- grab games --
            rolled_games = [await hm.get_rollable_game(
                database_name=database_name,
                completion_limit=10,
                price_limit=10,
                tier_number=1,
                user=user,
                price_restriction=price_restriction,
                hours_restriction=hours_restriction
            )]
        
        case "One Hell of a Week" :
            # -- if the user hasn't done day, return --
            if not user.has_completed_roll('One Hell of a Day') :
                return await interaction.followup.send(
                    f"You need to complete One Hell of a Day before rolling {event_name}!"
                )
            
            # -- grab games --
            rolled_games : list[str] = []
            valid_categories = list(get_args(hm.CATEGORIES))
            for i in range(5) :
                rolled_games.append(await hm.get_rollable_game(
                    database_name=database_name,
                    completion_limit=10,
                    price_limit=10,
                    tier_number=1,
                    user=user,
                    category=valid_categories,
                    already_rolled_games=rolled_games,
                    price_restriction=price_restriction,
                    hours_restriction=hours_restriction
                ))
                valid_categories.remove(
                    hm.get_item_from_list(rolled_games[i], database_name).category
                )

        case "One Hell of a Month" :
            # -- if user doesn't have week, return --
            #return await interaction.followup.send("roll under construction for a few days...")
            # if not user.has_completed_roll('One Hell of a Week') :
            #     return await interaction.followup.send(
            #         f"You need to complete One Hell of a Week before rolling {event_name}!"
            #     )
            
            # -- grab games --
            rolled_games : list[str] = []
            valid_categories = list(get_args(hm.CATEGORIES))
            for i in range(5) :
                
                selected_category = random.choice(valid_categories)
                
                for j in range(5) : #roll 5 games from the selected category
                    rolled_temp : list[str] = []
                    rolled_temp.append(await hm.get_rollable_game(
                        database_name=database_name,
                        completion_limit=10,
                        price_limit=10,
                        tier_number=1,
                        user=user,
                        category=selected_category,
                        already_rolled_games=rolled_games,
                        price_restriction=price_restriction,
                        hours_restriction=hours_restriction
                    ))
                
                if None in rolled_temp: #if not enough rolls in a given category, remove the category and try again
                    
                    #for logging
                    failed_category = selected_category
                    print(f"There were not enough valid rolls for this user in the {failed_category} category.")
                    
                    #remove from valid categories and reroll (without incrementing 'i')
                    valid_categories.remove(selected_category)
                    selected_category = random.choice(valid_categories)
                    for j in range(5) :
                        rolled_temp : list[str] = []
                        rolled_temp.append(await hm.get_rollable_game(
                            database_name=database_name,
                            completion_limit=10,
                            price_limit=10,
                            tier_number=1,
                            user=user,
                            category=selected_category,
                            already_rolled_games=rolled_games,
                            price_restriction=price_restriction,
                            hours_restriction=hours_restriction
                        ))
                    if None in rolled_temp: #not enough rolls in two categories
                        return await interaction.followup.send(
                            f"There weren't enough rollable games in two categories: {failed_category} and {selected_category}. " 
                            + "The event is unrollable for you until enough new T1 games with valid criteria get added to the site.")

                for j in range(5): #append the rolled games from the temp list to the main list
                    rolled_games.append(rolled_temp[j])

                valid_categories.remove(selected_category)
    
        case "Two Week T2 Streak" :
            if user.has_waiting_roll('Two Week T2 Streak') :
                "If user's current roll is ready for next stage, roll it for them."
                past_roll : CERoll = user.get_waiting_roll("Two Week T2 Streak")
                if past_roll.ready_for_next() :
                    new_game_id = await hm.get_rollable_game(
                        database_name=database_name,
                        completion_limit=40,
                        price_limit=20,
                        tier_number=2,
                        user=user,
                        already_rolled_games=past_roll.games,
                        price_restriction=price_restriction,
                        hours_restriction=hours_restriction
                    )
                    past_roll.add_game(new_game_id)
                    past_roll.reset_due_time()
                    new_game_object = hm.get_item_from_list(new_game_id, database_name)
                    user.update_waiting_roll(past_roll)
                    user.unwait_waiting_roll("Two Week T2 Streak")
                    await Mongo_Reader.dump_user(user)
                    return await interaction.followup.send(
                        f"Your next game is [{new_game_object.game_name}](https://cedb.me/game/{new_game_object.ce_id}). " +
                        f"It is due on <t:{past_roll.due_time}>. "
                        f"Run /check-rolls  to see more information."
                    )
                else :
                    return await interaction.followup.send(
                        "You need to finish the first half of Two Week T2 Streak first!"
                    )
                
            else :
                rolled_games = [await hm.get_rollable_game(
                    database_name=database_name,
                    completion_limit=40,
                    price_limit=20,
                    tier_number = 2,
                    user=user,
                    price_restriction=price_restriction,
                    hours_restriction=hours_restriction
                )]
        case "Two \"Two Week T2 Streak\" Streak" :
            if not user.has_completed_roll("Two Week T2 Streak") :
                return await interaction.followup.send(
                    f"You need to complete Two Week T2 Steak before rolling {event_name}!"
                )
            if user.has_waiting_roll("Two \"Two Week T2 Streak\" Streak") :
                # if the user is currently working 
                past_roll = user.get_waiting_roll("Two \"Two Week T2 Streak\" Streak")
                if past_roll.ready_for_next() :
                    new_game_id = await hm.get_rollable_game(
                        database_name=database_name,
                        completion_limit=40,
                        price_limit=20,
                        tier_number=2,
                        user=user,
                        already_rolled_games=past_roll.games,
                        price_restriction=price_restriction,
                        hours_restriction=hours_restriction
                    )
                    past_roll.add_game(new_game_id)
                    past_roll.reset_due_time()
                    new_game_object = hm.get_item_from_list(new_game_id, database_name)
                    user.update_waiting_roll(past_roll)
                    user.unwait_waiting_roll("Two \"Two Week T2 Streak\" Streak")
                    await Mongo_Reader.dump_user(user)
                    return await interaction.followup.send(
                        f"Your next game is [{new_game_object.game_name}](https://cedb.me/game/{new_game_object.ce_id}). " +
                        f"It is due on <t:{past_roll.due_time}>. " +
                        "Run /check-rolls to see more information."
                    )
                else :
                    return await interaction.followup.send("You need to finish your current games before you roll your next one!")
            
            else :
                rolled_games = [await hm.get_rollable_game(
                    database_name=database_name,
                    completion_limit=40,
                    price_limit=20,
                    tier_number=2,
                    user=user,
                    price_restriction=price_restriction,
                    hours_restriction=hours_restriction
                )]
        case "Never Lucky" :
            rolled_games = [await hm.get_rollable_game(
                database_name=database_name,
                completion_limit=None,
                price_limit=20,
                tier_number=3,
                user=user,
                price_restriction=price_restriction,
                hours_restriction=hours_restriction
            )]
            
        case "Triple Threat" :
            if not user.has_completed_roll("Never Lucky") :
                return await interaction.followup.send("You need to complete Never Lucky before rolling Triple Threat!")
            user.add_pending("Triple Threat")
            await Mongo_Reader.dump_user(user)

            view.add_item(TripleThreatDropdown(user.ce_id, price_restriction, hours_restriction))
            view.timeout = 600

            return await interaction.followup.send(
                "Choose your category.", view=view
            )
        
        case "Let Fate Decide" :
            # add the pending
            user.add_pending("Let Fate Decide")
            await Mongo_Reader.dump_user(user)

            view.add_item(LetFateDecideDropdown(user, price_restriction, hours_restriction))
            view.timeout = 600

            return await interaction.followup.send(
                "Choose your category.", view=view
            )


        case "Fourward Thinking" :
            if not user.has_completed_roll("Let Fate Decide") :
                return await interaction.followup.send("You need to complete Let Fate Decide before rolling Fourward Thinking!")

            # grab the previous roll (if there is one)
            past_roll : CERoll | None = user.get_current_roll("Fourward Thinking")

            # check to make sure this person is ready for the next iteration of their roll
            if past_roll is not None and not past_roll.ready_for_next() :
                return await interaction.followup.send("You need to finish your previous game first! Run /check-rolls to check them.")

            past_roll = user.get_waiting_roll("Fourward Thinking")
            
            # add the pending and dump it
            user.add_pending("Fourward Thinking")
            await Mongo_Reader.dump_user(user)
            
            view.timeout = 600
            view.add_item(FourwardThinkingDropdown(past_roll, database_name, price_restriction, hours_restriction, 
                                                   user.ce_id))
            
            return await interaction.followup.send(
                "Choose your category.", view=view
            )



    # -- check to make sure there were enough rollable games --
    if None in rolled_games :
        return await interaction.followup.send(
            "There weren't enough rollable games that matched this event's criteria." 
            + " Please try again later (and contact andy!)."
        )

    # -- create roll object --
    roll = CERoll(
        roll_name=event_name,
        user_ce_id=user.ce_id,
        games=rolled_games,
        is_current=True
    )
    user.add_current_roll(roll)

    # -- create embeds --

    embeds = await Discord_Helper.get_roll_embeds(
        roll=roll,
        database_name=database_name,
        database_user=(await Mongo_Reader.get_database_user())
    )

    await Discord_Helper.get_buttons(view=view, embeds=embeds)
    await Mongo_Reader.dump_user(user=user)
    return await interaction.followup.send(embed=embeds[0], view=view)


""" === CLASSES === """


class DestinyAlignmentAgreeView(discord.ui.View) :
    "The agree-button view for Destiny Alignment. Only `partner` can click these buttons."
    def __init__(self, user_ce_id : str, partner_ce_id : str) :
        self.__user_ce_id = user_ce_id
        self.__partner_ce_id = partner_ce_id
        self.__button_clicked = False
        super().__init__(timeout=600)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction : discord.Interaction, button : discord.ui.Button) :

        if self.__button_clicked : return
        self.__button_clicked = True
        

        # make sure only the partner can touch the buttons.
        user = await Mongo_Reader.get_user(self.__user_ce_id)
        partner = await Mongo_Reader.get_user(self.__partner_ce_id)
        if interaction.user.id != partner.discord_id :
            self.__button_clicked = False
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )
        
        
        
        # defer
        await interaction.response.defer()

        # pull database name
        database_name = await Mongo_Reader.get_database_name()

        # get the game for the user from the partner's library
        game_for_user = await hm.get_rollable_game(
            partner.get_completed_games_2(database_name),
            completion_limit=None,
            price_limit=20,
            tier_number=None,
            user=user,
            has_points_restriction=True
        )

        # check to make sure one exists
        if game_for_user == None :
            return await interaction.followup.send(
                f"There are no completed games in {partner.mention()}'s library that are rollable " +
                f"to {user.mention()}."
            )
        
        # get the game for the partner from the user's library
        game_for_partner = await hm.get_rollable_game(
            user.get_completed_games_2(database_name),
            completion_limit=None,
            price_limit=20,
            tier_number=None,
            user=partner,
            has_points_restriction=True
        )

        # check to make sure one exists
        if game_for_partner == None :
            return await interaction.followup.send(
                f"There are no completed games in {user.mention()}'s library that are rollable " +
                f"to {partner.mention()}."
            )

        # add the roll to the user...
        user.add_current_roll(CERoll(
            roll_name="Destiny Alignment",
            user_ce_id=user.ce_id,
            games=[game_for_user, game_for_partner],
            partner_ce_id=partner.ce_id,
            is_current=True
        ))

        # ...and the partner.
        partner.add_current_roll(CERoll(
            roll_name="Destiny Alignment",
            user_ce_id=partner.ce_id,
            games=[game_for_partner, game_for_user],
            partner_ce_id=user.ce_id,
            is_current=True
        ))

        # and then dump them both.
        await Mongo_Reader.dump_user(user)
        await Mongo_Reader.dump_user(partner)

        self.clear_items()

        game_for_user_object = hm.get_item_from_list(game_for_user, database_name)
        game_for_partner_object = hm.get_item_from_list(game_for_partner, database_name)

        return await interaction.followup.edit_message(
            content=(
                f"{user.mention()} must complete {game_for_user_object.name_with_link()} and " +
                f"{partner.mention()} must complete {game_for_partner_object.name_with_link()}. Your cooldown " +
                f"ends on <t:{user.get_current_roll('Destiny Alignment').calculate_cooldown_date(database_name)}>."
            ),
            message_id=interaction.message.id,
            view=discord.ui.View()
        )

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction : discord.Interaction, button : discord.ui.Button) :

        # make sure only the partner can touch the buttons
        partner = await Mongo_Reader.get_user(self.__partner_ce_id)
        if interaction.user.id != partner.discord_id :
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )
        
        # clear the items
        self.clear_items()
        return await interaction.response.edit_message(content="Roll cancelled.", view=self)
    pass


class SoulMatesDropdown(discord.ui.Select) :
    "The dropdown-select for choosing a Tier in Soul Mates. Only `user` can select the tier."
    def __init__(self, user_ce_id : str, partner_ce_id : str) :
        self.__user_ce_id = user_ce_id
        self.__partner_ce_id = partner_ce_id
        options : list[discord.SelectOption] = []
        for i in range(5) :
            options.append(discord.SelectOption(
                label=f"Tier {i+1}", value=f"{i+1}", description=f"Roll a Tier {i+1}", emoji=hm.get_emoji(f'Tier {i+1}')
            ))
        options.append(discord.SelectOption(
            label="Tier 5+", value="6", description="Roll a Tier 5 (or above)"
        ))

        super().__init__(placeholder="Choose a Tier.", min_values=1, max_values=1, options=options)
    
    async def callback(self, interaction : discord.Interaction) :

        user = await Mongo_Reader.get_user(self.__user_ce_id)
        partner = await Mongo_Reader.get_user(self.__partner_ce_id)

        # make sure only the user can pick the tier
        if interaction.user.id != user.discord_id :
            return await interaction.response.send_message(
                "You cannot select this.", ephemeral=True
            )
        
        # send message
        if self.values[0] == "6" :
            return await interaction.response.edit_message(
                content=(f"{partner.mention()}, would you like to enter a Tier 5+ Soul Mates " +
                f"with {user.mention()}?"),
                view=SoulMatesAgreeView(user.ce_id, partner.ce_id, self.values[0])
            )
        return await interaction.response.edit_message(
            content=(f"{partner.mention()}, would you like to enter a Tier {self.values[0]} Soul Mates " +
            f"with {user.mention()}?"),
            view=SoulMatesAgreeView(user.ce_id, partner.ce_id, self.values[0])
        )
    pass


class SoulMatesAgreeView(discord.ui.View) :
    "The agree-button view for Soul Mates. Only `partner` can push the buttons."
    def __init__(self, user_ce_id : str, partner_ce_id : str, tier : str) :
        self.__user_ce_id = user_ce_id
        self.__partner_ce_id = partner_ce_id
        self.__tier = tier
        self.__button_clicked = False
        super().__init__(timeout=600)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction : discord.Interaction, button : discord.ui.Button) :

        user = await Mongo_Reader.get_user(self.__user_ce_id)
        partner = await Mongo_Reader.get_user(self.__partner_ce_id)

        if self.__button_clicked : return
        self.__button_clicked = True

        # make sure only the partner can click this.
        if interaction.user.id != partner.discord_id :
            self.__button_clicked = False
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )
        
        # defer
        await interaction.response.defer()

        hour_limit = [None, 15, 40, 80, 160, None, None]

        tier_num = int(self.__tier)

        database_name = await Mongo_Reader.get_database_name()

        rolled_game = await hm.get_rollable_game(
            database_name=database_name,
            completion_limit=hour_limit[tier_num],
            price_limit=20,
            tier_number=tier_num,
            user=[user, partner],
            has_points_restriction=True
        )

        if rolled_game == None :
            return await interaction.followup.send(
                "It seems no rollable games are available right now. Please ping andy!"
            )

        user_roll = CERoll(
            roll_name="Soul Mates",
            user_ce_id=user.ce_id,
            games=[rolled_game],
            partner_ce_id=partner.ce_id,
            is_current=True,
            tier_num=tier_num
        )

        partner_roll = CERoll(
            roll_name="Soul Mates",
            user_ce_id=partner.ce_id,
            games=[rolled_game],
            partner_ce_id=user.ce_id,
            is_current=True,
            tier_num=tier_num
        )

        user.add_current_roll(user_roll)
        partner.add_current_roll(partner_roll)

        await Mongo_Reader.dump_user(user)
        await Mongo_Reader.dump_user(partner)

        game_object = hm.get_item_from_list(rolled_game, database_name)

        return await interaction.followup.edit_message(
            message_id=interaction.message.id,
            content=(f"{user.mention()} and {partner.mention()} have until <t:{user_roll.due_time}> "
            + f"to complete {game_object.name_with_link()}."),
            view = discord.ui.View()
        )


    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction : discord.Interaction, button : discord.ui.Button) :

        partner = await Mongo_Reader.get_user(self.__partner_ce_id)

        # make sure it was the right person who clicked it
        if interaction.user.id != partner.discord_id :
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )
        
        # clear items
        self.clear_items()
        return await interaction.response.edit_message(content="Roll cancelled.", view=self)
    pass


class TeamworkMakesTheDreamWorkAgreeView(discord.ui.View) :
    "The agree-button view for Teamwork Makes the Dream Work. Only `partner` can select the buttons."
    def __init__(self, user_ce_id : str, partner_ce_id : str) :
        self.__user_ce_id = user_ce_id
        self.__partner_ce_id = partner_ce_id
        self.__button_clicked = False
        super().__init__(timeout=600)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction : discord.Interaction, button : discord.ui.Button) :

        if self.__button_clicked : return
        self.__button_clicked = True

        user = await Mongo_Reader.get_user(self.__user_ce_id)
        partner = await Mongo_Reader.get_user(self.__partner_ce_id)

        # make sure the right person clicked
        if interaction.user.id != partner.discord_id :
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )
        
        await interaction.response.defer()
        
        database_name = await Mongo_Reader.get_database_name()

        rolled_games : list[str] = []
        for i in range(4) :
            rolled_games.append(await hm.get_rollable_game(
                database_name=database_name,
                completion_limit=40,
                price_limit=20,
                tier_number=3,
                user=[user, partner],
                already_rolled_games=rolled_games,
                has_points_restriction=True
            ))

        if None in rolled_games :
            return await interaction.followup.edit_message(
                content="It looks like there aren't enough rollable games at this time. Please alert Andy.",
                message_id=interaction.message.id
            )
        
        user_roll = CERoll(
            roll_name="Teamwork Makes the Dream Work",
            user_ce_id=user.ce_id,
            games=rolled_games,
            partner_ce_id=partner.ce_id,
            is_current=True
        )
        user.add_current_roll(user_roll)
        partner.add_current_roll(CERoll(
            roll_name="Teamwork Makes the Dream Work",
            user_ce_id=partner.ce_id,
            games=rolled_games,
            partner_ce_id=user.ce_id,
            is_current=True
        ))
        await Mongo_Reader.dump_user(user)
        await Mongo_Reader.dump_user(partner)

        rolled_games_objects = [hm.get_item_from_list(game_id, database_name) for game_id in rolled_games]

        content = (
                f"{user.mention()} and {partner.mention()} must complete the following games by " +
                f"<t:{user_roll.due_time}>: "
            )
        for i, game in enumerate(rolled_games_objects) :
            content += (f"{game.name_with_link()}")
            if i != 3 : content += ", "
        content += "."

        return await interaction.followup.edit_message(
            message_id=interaction.message.id,
            content=content,
            view=discord.ui.View()
        )

    
    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction : discord.Interaction, button : discord.ui.Button) :

        partner = await Mongo_Reader.get_user(self.__partner_ce_id)

        # make sure it was the right person who clicked it
        if interaction.user.id != partner.discord_id :
            return await interaction.response.send_message(
                "You cannot touch these buttons.", ephemeral=True
            )
        
        # clear items
        self.clear_items()
        return await interaction.response.edit_message(content="Roll cancelled.", view=self)
    pass


async def coop_roll(interaction : discord.Interaction, event_name : hm.COOP_ROLL_EVENT_NAMES, partner : discord.Member) :
    await interaction.response.defer()

    # helps with variable names
    partner_discord = partner
    del partner
    partner = None

    # make the view
    view = discord.ui.View()

    # define channel
    user_log_channel = client.get_channel(hm.USER_LOG_ID)

    # check they didn't roll with themselves
    if interaction.user.id == partner_discord.id :
        return await interaction.followup.send(
            "You can't roll with yourself!"
        )

    # grab the user
    user = await Mongo_Reader.get_user(interaction.user.id, use_discord_id=True)
    try :
        partner : CEUser = await Mongo_Reader.get_user(partner_discord.id, use_discord_id=True)
    except ValueError :
        partner = None

    # user doesn't exist
    if user == None :
        return await interaction.followup.send(
            "Sorry, you're not registered in the CE Assistant database. Please run `/register` first!"
        )
    
    # partner doesn't exist
    if partner == None :
        return await interaction.followup.send(
            "Sorry, your partner is not registered in the CE Assistant database. " + 
            "Please have them run `/register` first!"
        )
    
    # destiny alignment allows for multiple concurrent rolls - apply different logic vs other co-op rolls
    if event_name == "Destiny Alignment" :
        
        # check if the user / partner combo have an active DA roll underway
        if user.has_DA_roll(partner.ce_id, event_name) :
            return await interaction.followup.send(
                f"You and your partner are currently attempting {event_name}!"
            )
        
        # check if the user has the maximum number of concurrent DA rolls
        if user.count_DA_rolls(event_name) >= 5 :
            return await interaction.followup.send(
                f"You currently have the maximum number [5] of concurrent {event_name} rolls!"
            )
        
        # check if partner has the maximum number of concurrent DA rolls
        if partner.count_DA_rolls(event_name) >= 5 :
            return await interaction.followup.send(
                f"Your partner currently has the maximum number [5] of concurrent {event_name} rolls!"
            )
    
    else:

        if user.has_current_roll(event_name) :
            return await interaction.followup.send(
                f"You are currently attempting {event_name}!"
            )
        
        if partner.has_current_roll(event_name) :
            return await interaction.followup.send(
                f"Your partner is currently attempting {event_name}!"
            )
    
    # user has cooldown
    database_name = await Mongo_Reader.get_database_name()
    if user.has_cooldown(event_name, database_name) :
        return await interaction.followup.send(
            f"You are currently on cooldown for {event_name} until <t:{user.get_cooldown_time(event_name, database_name)}>. "
        )
    
    # partner has cooldown
    if partner.has_cooldown(event_name, database_name) :
        return await interaction.followup.send(
            f"Your partner is currently on cooldown for {event_name} until <t:{user.get_cooldown_time(event_name, database_name)}>. "
        )

    # user has pending
    if user.has_pending(event_name) :
        return await interaction.followup.send(
            "You just tried rolling this event. Please wait about 10 minutes before trying again." +
            " (P.S. This is not a cooldown. Just has to do with how the bot backend works.)"
        )
    
    # partner has pending
    if partner.has_pending(event_name) :
        return await interaction.followup.send(
            "Your partner just tried rolling this event. Please wait about 10 minutes before trying again." +
            " (P.S. This is not a cooldown. Just has to do with how the bot backend works.)"
        )

    user.add_pending(event_name)
    partner.add_pending(event_name)
    await Mongo_Reader.dump_user(user)
    await Mongo_Reader.dump_user(partner)


    match(event_name) :
        case "Destiny Alignment" :
            # check if the users are the same rank
            if (user.rank_num() < 6 and partner.rank_num() < 6) and (user.get_rank() != partner.get_rank()) :
                return await interaction.followup.send(
                    "For Destiny Alignment, both you and your partner have to be the same rank " +
                    f"(or both be SS Rank or above). You are {user.get_rank()} and your partner is {partner.get_rank()}."
                )
            return await interaction.followup.send(
                f"{partner.mention()}, would you like to enter into Destiny Alignment with {user.mention()}?",
                view=DestinyAlignmentAgreeView(user.ce_id, partner.ce_id)
            )

        case "Soul Mates" :
            view = discord.ui.View(timeout=600)
            view.add_item(SoulMatesDropdown(user.ce_id, partner.ce_id))
            return await interaction.followup.send(
                f"{user.mention()}, select a Tier.",
                view=view
            )

        case "Teamwork Makes the Dream Work" :
            return await interaction.followup.send(
                f"{partner.mention()}, would you like to enter into Teamwork Makes the Dream Work with {user.mention()}?",
                view=TeamworkMakesTheDreamWorkAgreeView(user.ce_id, partner.ce_id)
            )
            pass

        case "Winner Takes All" | "Game Theory" :
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


async def check_rolls(interaction : discord.Interaction) :
    # defer the message
    await interaction.response.defer()

    #return await interaction.followup.send("sorry this does not work rn :( shouyld be back up by thursday night...")

    # create the view
    view = discord.ui.View(timeout=None)

    # find the user
    user = await Mongo_Reader.get_user(interaction.user.id, use_discord_id=True)
    if user is None : return await interaction.followup.send(content="You're not registered! Please run /register.")

    return await interaction.followup.send(f'[click me :)](https://ce-assistant-frontend.vercel.app/users/{user.ce_id})')
