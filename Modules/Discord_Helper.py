"""
This module is made to help me with my discord stuff.
It will:

- take in a `CERoll` object and return an array of `discord.Embed`s denoting exactly what's up.
"""
import datetime
import json
import time
import requests
import discord

# -- local --
from Classes.CE_Roll import CERoll
from Classes.OtherClasses import EmbedMessage, UpdateMessage
import Modules.Mongo_Reader as Mongo_Reader
import Modules.CEAPIReader as CEAPIReader
import Modules.hm as hm
from Modules.Screenshot import Screenshot
import Modules.WebInteractor as WebInteractor


# selenium and beautiful soup stuff
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import io
from PIL import Image
from webdriver_manager.core.os_manager import ChromeType

def get_roll_embeds(roll : CERoll, database_user : list, database_name : list) -> list[discord.Embed] :
    """This function returns an array of `discord.Embed`'s to be sent when a roll is initialized."""
    from Classes.CE_Game import CEGame

    # -- set up the array --
    embeds : list[discord.Embed] = []

    # -- set up the intro embed --
    embeds.append(discord.Embed(
        title=roll.roll_name,
        timestamp=datetime.datetime.now(),
        color = 0x000000
    ))
    embeds[0].set_footer(
        text = f'Page 1 of {str(len(roll.games) + 1)}',
        icon_url = hm.FINAL_CE_ICON
    )
    embeds[0].set_author(name="Challenge Enthusiasts")

    # -- set up description --
    description = "__Rolled Games__\n"
    for i, id in enumerate(roll.games) :
        game : CEGame = hm.get_item_from_list(id, database_name)
        description += f"{i + 1}. {game.game_name}\n"
    
    # -- set up roll info --
    description += "__Roll Info__\n"
    if roll.ends() :
        description += f"You must complete {roll.roll_name} by <t:{roll.due_time}>.\n"
        description += f"If you fail, you will have a cooldown until <t:{roll.calculate_cooldown_date(database_name=database_name)}>.\n"
    else :
        description += f"{roll.roll_name} has no time limit. You can reroll on {roll.calculate_cooldown_date(database_name=database_name)}.\n"

    # -- set the description --
    embeds[0].description = description

    # -- now grab all the other embeds --
    for i, id in enumerate(roll.games) :
        embeds.append(get_game_embed(game_id=id, database_name=database_name))
        embeds[i+1].set_footer(
            text=f"Page {i+2} of {len(roll.games) + 1}",
            icon_url = hm.FINAL_CE_ICON
        )

    return embeds





def get_game_embed(game_id : str, database_name : list) -> discord.Embed :
    """This function returns a `discord.Embed` that holds all information about a game."""

    # imports and type hinting
    from Classes.CE_Game import CEGame
    database_name : list[CEGame] = database_name

    # grab the game
    game : CEGame = hm.get_item_from_list(game_id, database_name)
    if game is None : return None

    # -- instantiate the embed --
    embed = discord.Embed(
        title = game.game_name,
        url=f"https://cedb.me/game/{game_id}",
        description = "To be determined.",
        color = 0x000000,
        timestamp = datetime.datetime.now()
    )
    embed.set_author(name='Challenge Enthusiasts', icon_url=hm.CE_MOUNTAIN_ICON)

    # -- get steam data and set image and description --
    if game.platform == "steam" :
        steam_data = game.get_steam_data()
        embed.set_image(url=steam_data.header_image)
    embed.description = (
        f"- {hm.get_emoji(game.get_tier())}{hm.get_emoji(game.category)}" +
        f" - {game.get_total_points()}{hm.get_emoji('Points')}\n"
    )

    # -- set up price --
    if game.platform == "retroachievements" or steam_data.is_free :
        embed.description += "- Price: Free!\n"
    else :
        embed.description += (f"- Price: {steam_data.current_price_formatted}\n")

    # -- add steamhunters data --
    sh_data = game.get_steamhunters_data()
    if sh_data == None : sh_data = "N/A"
    embed.description += f"- SteamHunters Median Completion Time: {sh_data} hours\n"
    
    # -- get ce data --
    completion_data = game.get_completion_data()
    embed.description += f"- {completion_data.description()}\n"

    return embed




async def get_buttons(view : discord.ui.View, embeds : list[discord.Embed]):
    if len(embeds) == 1 : return
    currentPage = 1
    page_limit = len(embeds)
    buttons = [discord.ui.Button(label=">", style=discord.ButtonStyle.green, disabled=False), discord.ui.Button(label="<", style=discord.ButtonStyle.red, disabled=True)]
    view.add_item(buttons[1])
    view.add_item(buttons[0])

    for i, embed in enumerate(embeds):
        embed.set_footer(text=f"Page {i+1} of {page_limit}")

    async def hehe(interaction : discord.Interaction):
        return await callback(interaction, num=1)

    async def haha(interaction : discord.Interaction):
        return await callback(interaction, num=-1)

    async def callback(interaction : discord.Interaction, num : int):
        nonlocal currentPage, view, embeds, page_limit, buttons
        currentPage+=num
        if(currentPage >= page_limit) :
            buttons[0].disabled = True
        else : buttons[0].disabled = False
        if(currentPage <= 1) :
            buttons[1].disabled = True
        else : buttons[1].disabled = False
        await interaction.response.edit_message(embed=embeds[currentPage-1], view=view)

    buttons[0].callback = hehe
    buttons[1].callback = haha

    async def disable() :
        for button in buttons :
            button.disabled = True
        print("disabled")

    #view.on_timeout = disable

async def get_user_embeds(user, database_name : list, database_user : list) -> tuple[discord.Embed, discord.ui.View] :
    """Returns a `discord.Embed` that represents this user.""" 

    # imports and type hintin
    from Classes.CE_User import CEUser
    from Classes.CE_Game import CEGame
    user : CEUser = user
    database_name : list[CEGame] = database_name
    database_user : list[CEUser] = database_user

    # pull api data
    api_user = user.get_api_user()

    # -- two embeds: summary, completions --
    # summary
    summary_embed = discord.Embed(
        title="Profile",
        color=0xff9494,
        timestamp=datetime.datetime.now()
    )
    summary_embed.add_field(
        name="User", value = f"<@{user.discord_id}> {hm.get_emoji(user.get_rank())}", inline=True
    )
    summary_embed.add_field(
        name = "Current Values", value = f"{user.get_total_points()} {hm.get_emoji('Points')} - Casino Score: {user.casino_score}", inline=True
    )
    summary_embed.add_field(
        name = "CR", value=user.get_cr(database_name=database_name).cr_string(), inline=False
    )
    summary_embed.add_field(
        name="Completions", value=api_user.tier_genre_summary_str(), inline=False
    )

    # recent
    recent_embed = discord.Embed(
        title="Profile",
        color=0xff9494,
        timestamp=datetime.datetime.now()
    )
    recent_embed.add_field(
        name="Recent Completions", value=api_user.most_recent_objectives_str()
    )
    recent_embed.add_field(
        name="Monthly Breakdown", value=api_user.monthly_report_str()
    )

    # set up the view
    class ProfileView(discord.ui.View) :
        def __init__(self) :
            super().__init__(timeout=None)
        
        @discord.ui.button(label="Summary", style=discord.ButtonStyle.gray, disabled=True)
        async def summary_button(self, interaction : discord.Interaction, button : discord.ui.Button) :
            # defer the message
            await interaction.response.defer()

            # un-disable everything
            for child in self.children :
                child.disabled = False
            
            # and disable this one
            button.disabled = True

            # and now edit the message and return
            return await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=summary_embed,
                view=self
            )

        @discord.ui.button(label="Recent", style=discord.ButtonStyle.gray)
        async def recent_buttton(self, interaction : discord.Interaction, button : discord.ui.Button) :
            # defer the message
            await interaction.response.defer()

            # un-disable everything
            for child in self.children :
                child.disabled = False

            # but disable this one
            button.disabled = True

            # and now edit the mesasge
            return await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=recent_embed,
                view=self
            )


    return (summary_embed, ProfileView())



# ---------------------------------- game additions ----------------------------------

    
#   _____              __  __   ______                _____    _____    _____   _______   _____    ____    _   _    _____ 
#  / ____|     /\     |  \/  | |  ____|       /\     |  __ \  |  __ \  |_   _| |__   __| |_   _|  / __ \  | \ | |  / ____|
# | |  __     /  \    | \  / | | |__         /  \    | |  | | | |  | |   | |      | |      | |   | |  | | |  \| | | (___  
# | | |_ |   / /\ \   | |\/| | |  __|       / /\ \   | |  | | | |  | |   | |      | |      | |   | |  | | | . ` |  \___ \ 
# | |__| |  / ____ \  | |  | | | |____     / ____ \  | |__| | | |__| |  _| |_     | |     _| |_  | |__| | | |\  |  ____) |
#  \_____| /_/    \_\ |_|  |_| |______|   /_/    \_\ |_____/  |_____/  |_____|    |_|    |_____|  \____/  |_| \_| |_____/ 




def game_additions_updates(old_games : list, new_games : list) -> tuple[list[EmbedMessage], list[UpdateMessage]] :
    "Returns a list of `discord.Embed`s to send to #game-additions."

    print('start')

    # import and type casting
    from Classes.CE_Game import CEGame, CEAPIGame
    old_games : list[CEGame] = old_games
    new_games : list[CEAPIGame] = new_games
    import Modules.Screenshot as Screenshot

    # the list to be returned
    messages : list[EmbedMessage] = []
    exceptions : list[UpdateMessage] = []

    # variables
    SELENIUM_ENABLE = True
    ON_LINUX_MACHINE = True
    ON_WINDOWS_MACHINE = False

    if ON_LINUX_MACHINE :
        import chromedriver_binary

    # set selenium driver and preferences
    if SELENIUM_ENABLE :
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('log-level=3')

        if ON_LINUX_MACHINE :
            service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
            print('service created')
            driver = webdriver.Chrome(service=service, options=options)
        elif ON_WINDOWS_MACHINE :
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else :
            return "No valid machine option available."
        driver.set_window_size(width=1440, height=8000)

        # uhhh
        print('driver gotten.')
        
        # grab the first game to get color on the rest of them
        # ----- variables -----
        CELESTE_CE_URL = "https://cedb.me/game/1e866995-6fec-452e-81ba-1e8f8594f4ea"
        driver.get(CELESTE_CE_URL)
        time.sleep(5)

    # get a list of the old ones, so we know if a game was removed or not
    old_ce_ids : list[str] = []
    for old_game in old_games :
        old_ce_ids.append(old_game.ce_id)

    CONSOLE_MARKERS = False

    for new_game in new_games :
        # check if it's unfinished, skip if so
        if CONSOLE_MARKERS and False : print(f"current game: {new_game.game_name}")
        if not new_game.is_finished :
            if CONSOLE_MARKERS : print("game is unfinished")
            if new_game.ce_id in old_ce_ids : old_ce_ids.remove(new_game.ce_id)
            continue
            #NOTE: we should add the old game to new_games and return that so that it'll
            #still be stored in the database in the exact state it is in

        # --- the game is new ---
        if new_game.ce_id not in old_ce_ids : 

            print(f'🟢 NEW GAME: {new_game.game_name}, https://cedb.me/game/{new_game.ce_id}')

            # set up the embed
            embed = discord.Embed(
                title=f"__ {new_game.game_name} __ added to the site:",
                color=0x48b474,
                timestamp=datetime.datetime.now(),
                description=(
                    f"\n- {new_game.get_emojis()}"
                ),
                url=f"https://cedb.me/game/{new_game.ce_id}"
            )

            # set up embed description
            if len(new_game.get_primary_objectives())!= 0 :
                num_pos = len(new_game.get_primary_objectives())
                embed.description += (
                        f"\n- {num_pos} Primary Objective{'s' if num_pos != 1 else ''} " +
                        f"worth {new_game.get_po_points()} {hm.get_emoji('Points')}"
                    )
            if len(new_game.get_uncleared_objectives()) != 0 :
                num_uncleareds = len(new_game.get_uncleared_objectives())
                embed.description += (f"\n- {num_uncleareds} Uncleared Objective{'s' if num_uncleareds != 1 else ''}")
            if len(new_game.get_community_objectives()) != 0 :
                num_cos = len(new_game.get_community_objectives())
                embed.description += (f"\n- {num_cos} Community Objective{'s' if num_cos != 1 else ''}")
            if len(new_game.get_secondary_objectives()) != 0 :
                num_sos = len(new_game.get_secondary_objectives())
                embed.description += (
                        f"\n- {num_sos} Secondary Objective{'s' if num_sos != 1 else ''}" +
                        f"worth {new_game.get_so_points()} {hm.get_emoji('Points')}"
                    )
            if len(new_game.get_badge_objectives()) != 0 :
                num_bos = len(new_game.get_badge_objectives())
                embed.description += f"\n- {num_bos} Badge Objective{'s' if num_bos != 1 else ''}"

            # other embed shit
            embed.set_image(url="attachment://image.png")
            embed.set_author(name='Challenge Enthusiasts', icon_url=new_game.icon)
            embed.set_footer(text='CE Assistant', icon_url=hm.FINAL_CE_ICON)

            if SELENIUM_ENABLE : 
                try :
                    image = WebInteractor.get_image(driver=driver, new_game=new_game)
                    if isinstance(image, tuple) :
                        file = image[0]
                        exceptions.append(UpdateMessage("privatelog", f":red_square: {image[1]}"))
                    else :
                        file = image
                except :
                    file = "Assets/image_failed_v2.png"

            #TODO: fix this?

            messages.append(EmbedMessage(embed=embed, file=discord.File(file, filename="image.png")))
            continue

        # --- the game is updated ---
        # remove the ce id from old_ce_ids
        old_ce_ids.remove(new_game.ce_id)

        # get the old game
        old_game = hm.get_item_from_list(new_game.ce_id, old_games)

        # if the game hasn't been updated since last time, continue
        if old_game.last_updated >= new_game.last_updated : 
            if CONSOLE_MARKERS : print("last update, continuing")
            continue

        print(f'🟡 UPDATED GAME: {new_game.game_name}, https://cedb.me/game/{new_game.ce_id}')

        if CONSOLE_MARKERS: print(old_game)
        if CONSOLE_MARKERS: print(new_game)

        # set up embed
        embed = discord.Embed(
            title=f"__ {new_game.game_name} __ updated on the site:",
            color=0xefd839,
            timestamp=datetime.datetime.now(),
            description="",
            url=f"https://cedb.me/game/{new_game.ce_id}/"
        )
        embed.set_image(url="attachment://image.png")
        embed.set_author(name='Challenge Enthusiasts', icon_url=new_game.icon)
        embed.set_footer(text='CE Assistant', icon_url=hm.FINAL_CE_ICON)

        # ----- actual update -----
        # point/tier changes
        if old_game.get_total_points() != new_game.get_total_points() :
            embed.description += (
                f"\n- {old_game.get_total_points()} {hm.get_emoji('Points')} " +                            # 75 points
                f"{hm.get_emoji('Arrow')} " +                                                               # -->
                f"{new_game.get_total_points()} {hm.get_emoji('Points')}"                                   # 220 points
            )
            if old_game.get_tier() != new_game.get_tier() :
                embed.description += (
                    f" ({old_game.get_tier_emoji()} {hm.get_emoji('Arrow')} {new_game.get_tier_emoji()})"
                )
        else :
            embed.description += "\n- Total points unchanged"

        # category changes
        if old_game.category != new_game.category :
            if CONSOLE_MARKERS : print("category change")
            embed.description += f"\n- {old_game.get_category_emoji()} {hm.get_emoji('Arrow')} {new_game.get_category_emoji()}"

        # objective changes...
        old_objective_ce_ids = [old_objective.ce_id for old_objective in old_game.all_objectives]
        for new_objective in new_game.all_objectives :

            # if objective is new
            if new_objective.ce_id not in old_objective_ce_ids :
                "Objective is new!"
                if CONSOLE_MARKERS : print("new objective")
                embed.description += (
                    f"\n- New {new_objective.type} Objective '**{new_objective.name}**' added:"
                )
                if new_objective.type == "Primary" or new_objective.type == "Secondary" :
                    embed.description += f"\n  - {new_objective.point_value} {hm.get_emoji('Points')}"
                embed.description += f"\n  - {new_objective.description}"
                continue
            
            # update objective tracker and get the old objective
            old_objective_ce_ids.remove(new_objective.ce_id)
            old_objective = hm.get_item_from_list(new_objective.ce_id, old_game.all_objectives)
            
            # if objective is updated
            if not new_objective.equals(old_objective) :
                if CONSOLE_MARKERS : print('objective updated')
                "Objective is updated."
                # if the points have changed
                if old_objective.is_uncleared() and not new_objective.is_uncleared() :
                    embed.description += (f"\n- '**{new_objective.name}**' cleared, valued at {new_objective.point_value} {hm.get_emoji('Points')}")
                elif old_objective.point_value > new_objective.point_value :
                    embed.description += (f"\n- '**{new_objective.name}**' decreased from {old_objective.point_value} {hm.get_emoji('Points')} " + 
                                        f"to {new_objective.point_value} {hm.get_emoji('Points')}")
                elif old_objective.point_value < new_objective.point_value :
                    embed.description += (f"\n- '**{new_objective.name}**' increased from {old_objective.point_value} {hm.get_emoji('Points')} " + 
                                        f"to {new_objective.point_value} {hm.get_emoji('Points')}")
                else :
                    embed.description += (f"\n- '**{new_objective.name}**' updated")
                
                # if the type has changed
                if old_objective.type != new_objective.type :
                    embed.description += (f"\n  - Type changed from {old_objective.type} to {new_objective.type}")

                # if the description was updated
                if old_objective.description != new_objective.description :
                    if CONSOLE_MARKERS: print('huh')
                    embed.description += f"\n  - Description updated"
                
                # if the requirements were updated
                if old_objective.requirements != new_objective.requirements :
                    embed.description += "\n  - Requirements updated"
            
                # if the achievements were updated
                # TODO: this can be made more specific in 2.1
                if (not hm.achievements_are_equal(old_objective.achievement_ce_ids, new_objective.achievement_ce_ids)) :
                    embed.description += "\n  - Achievements updated"

                # if the partial points were updated
                if old_objective.partial_points != new_objective.partial_points :
                    embed.description += (f"\n  - Partial points changed from {old_objective.partial_points} {hm.get_emoji('Points')} " +
                                            f"to {new_objective.partial_points} {hm.get_emoji('Points')}")
                    
                # if the name was changed
                if old_objective.name != new_objective.name :

                    # if the objective was cleared, we don't need to make a whole note about the name change unless the name was changed
                    if (old_objective.is_uncleared() and not new_objective.is_uncleared() and
                        (old_objective.uncleared_name() != new_objective.name)) :
                            embed.description += f"\n  - Name changed from '{old_objective.name}' to '{new_objective.name}'"
                    elif not old_objective.is_uncleared() or new_objective.is_uncleared() :
                        embed.description += (f"\n  - Name changed from '{old_objective.name}' to '{new_objective.name}'")
        # -- end objective changes --
        
        for old_objective_ce_id in old_objective_ce_ids :
            if CONSOLE_MARKERS : print("objective removed")
            embed.description += (f"\n- Objective {old_objective_ce_id} removed.")

        # all objectives have been reflected
        description_test = embed.description
        description_test = description_test.replace('\n','').replace('\t','').replace('- Total points unchanged','')

        # if there wasn't any real change, ignore this embed
        if description_test == "" : continue

        print('adding')
        try :
            image = WebInteractor.get_image(driver=driver, new_game=new_game)
            if isinstance(image, tuple):
                file = image[0]
                exceptions.append(UpdateMessage("privatelog", f":red_square: {image[1]}"))
            else :
                file = image
        except :
            file = "Assets/image_failed_v2.png"

        messages.append(EmbedMessage(
            embed=embed, file=discord.File(file, filename="image.png")
        ))
    
    # --- all additions and updates have finished. check for removed games ---
    for game in old_ce_ids :
        game_object = hm.get_item_from_list(game, old_games)

        print(f'🔴 REMOVED GAME: {game_object.game_name}, https://cedb.me/game/{game_object.ce_id}')

        # create the embed
        embed = discord.Embed(
            title=f"__{game_object.game_name}__ removed from the site.",
            color=0xce4e2c,
            timestamp=datetime.datetime.now()
        )
        embed.set_image(url="attachment://image.png")

        # and add the message
        messages.append(EmbedMessage(
            embed=embed, file=discord.File("Assets/removed.png", filename="image.png")
        ))

    # if we're looking for images, close the driver
    try :
        if SELENIUM_ENABLE : 
            driver.close()
            driver.quit()
    except Exception as e:
        exceptions.append(UpdateMessage("privatelog", f":red_square: {e}"))
        print(e)
    
    # and return
    return (messages, exceptions)

def get_user_by_discord_id(discord_id, database_user) :
    "Return the user from their discord id."
    for user in database_user :
        if user.discord_id == discord_id : return user
    return None