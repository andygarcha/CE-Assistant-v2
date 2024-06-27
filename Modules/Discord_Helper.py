"""
This module is made to help me with my discord stuff.
It will:

- take in a `CERoll` object and return an array of `discord.Embed`s denoting exactly what's up.
"""
import datetime
import json
import requests
import discord

# -- local --
from Classes.CE_Roll import CERoll
from Classes.OtherClasses import EmbedMessage
import Modules.Mongo_Reader as Mongo_Reader
import Modules.CEAPIReader as CEAPIReader
import Modules.hm as hm


# selenium and beautiful soup stuff
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import io

async def get_roll_embeds(roll : CERoll, database_user : list, database_name : list) -> list[discord.Embed] :
    """This function returns an array of `discord.Embed`'s to be sent when a roll is initialized."""
    from Classes.CE_Game import CEGame

    # -- set up the array --
    embeds : list[discord.Embed] = []

    # -- set up the intro embed --
    embeds[0] = discord.Embed(
        title=roll.roll_name,
        timestamp=datetime.datetime.now(),
        color = 0x000000
    )
    embeds[0].set_footer(
        text = f'Page 1 of {str(len(roll.games) + 1)}',
        icon_url = hm.FINAL_CE_ICON
    )
    embeds[0].set_author(name="Challenge Enthusiasts")

    # -- set up description --
    description = "__Rolled Games__\n"
    for i, id in roll.games :
        game : CEGame = hm.get_item_from_list(id, database_name)
        description += f"{i + 1}. {game.game_name}\n"
    
    # -- set up roll info --
    description += "__Roll Info__\n"
    if roll.ends() :
        description += f"You must complete {roll.roll_name} by <t:{roll.due_time}>.\n"
        description += f"If you fail, you will have a cooldown until {roll.calculate_cooldown_date()}.\n"
    else :
        description += f"{roll.roll_name} has no time limit. You can reroll on {roll.calculate_cooldown_date()}.\n"

    # -- set the description --
    embeds[0].description = description

    # -- now grab all the other embeds --
    for i, id in enumerate(roll.games) :
        embeds.append(await get_game_embed(id))
        embeds[i+1].set_footer(
            text=f"Page {i+2} of {len(roll.games) + 1}",
            icon_url = hm.FINAL_CE_ICON
        )

    return embeds





async def get_game_embed(game_id : str) -> discord.Embed :
    """This function returns a `discord.Embed` that holds all information about a game."""
    from Classes.CE_Game import CEGame
    # -- get the api data --
    database_name = await Mongo_Reader.get_mongo_games()
    game : CEGame = hm.get_item_from_list(game_id, database_name)
    if game == None : return None

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
    steam_data = game.get_steam_data()
    embed.set_image(url=steam_data.header_image)
    embed.description = (
        f"- {hm.get_emoji(game.get_tier())}{hm.get_emoji(game.category)}" +
        f" - {game.get_total_points()}{hm.get_emoji('Points')}\n"
    )

    # -- set up price --
    if steam_data.is_free :
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

async def get_user_embed() -> discord.Embed :
    """Returns a `discord.Embed` that represents this user.""" 
    return NotImplemented

def get_image(driver : webdriver.Chrome, new_game) -> io.BytesIO :
    "Takes in the `driver` (webdriver) and the game's `ce_id` and returns an image to be screenshotted."

    # set type hinting
    from Classes.CE_Game import CEGame, CEAPIGame
    new_game : CEGame = new_game

    OBJECTIVE_LIMIT = 7
    "The maximum amount of objectives to be screenshot before cropping." 


def game_additions_updates(old_games : list, new_games : list) -> list[EmbedMessage] :
    "Returns a list of `discord.Embed`s to send to #game-additions."

    # import and type casting
    from Classes.CE_Game import CEGame, CEAPIGame
    old_games : list[CEGame] = old_games
    new_games : list[CEAPIGame] = new_games
    import Modules.Screenshot as Screenshot

    # the list to be returned
    messages : list[EmbedMessage] = []

    # pictures
    

    # variables
    SELENIUM_ENABLE = True
    ON_RASPBERRY_PI = False
    ON_WINDOWS_MACHINE = True

    if ON_RASPBERRY_PI :
        import chromedriver_binary

    # set selenium driver and preferences
    if SELENIUM_ENABLE :
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('log-level=3')

        if ON_RASPBERRY_PI :
            service = Service('/usr/lib/chromium-browser/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
        elif ON_WINDOWS_MACHINE :
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else :
            return "No valid machine option available."
        
        # grab the first game to get color on the rest of them
        CELESTE_CE_URL = "https://cedb.me/game/1e866995-6fec-452e-81ba-1e8f8594f4ea"
        driver.get(CELESTE_CE_URL)

    # get a list of the old ones, so we know if a game was removed or not
    old_ce_ids : list[str] = []
    for old_game in old_games :
        old_ce_ids.append(old_game.ce_id)

    for new_game in new_games :
        # check if it's unfinished
        if not new_game.is_finished :
            if new_game.ce_id in old_ce_ids : old_ce_ids.remove(new_game.ce_id)
            continue

        if new_game.ce_id not in old_ce_ids : 
            "The game is new!"

            # set up the embed
            embed = discord.Embed(
                title=f"__{new_game.game_name}__ added to the site:",
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
                        f"worth {new_game.get_total_points()} points {hm.get_emoji("Points")}"
                    )
            if len(new_game.get_uncleared_objectives()) != 0 :
                num_uncleareds = len(new_game.get_uncleared_objectives())
                embed.description += (f"\n- {num_uncleareds} Uncleared Objective{'s' if num_uncleareds != 1 else ''}")
            if len(new_game.get_community_objectives()) != 0 :
                num_cos = len(new_game.get_community_objectives())
                embed.description += (f"\n- {num_cos} Community Objective{'s' if num_cos != 1 else ''}")
            if len(new_game.get_secondary_objectives()) != 0 :
                num_sos = len(new_game.get_secondary_objectives())
                embed.description += f"\n- {num_sos} Secondary Objective{'s' if num_sos != 1 else ''}"
            if len(new_game.get_badge_objectives()) != 0 :
                num_bos = len(new_game.get_badge_objectives())
                embed.description += f"\n- {num_bos} Badge Objective{'s' if num_bos != 1 else ''}"

            # other embed shit
            embed.set_image(url="attachment://image.png")
            embed.set_author(name='Challenge Enthusiasts', icon_url=new_game.icon)
            embed.set_footer(name='CE Assistant', icon_url=hm.FINAL_CE_ICON)

            image = get_image(driver=driver, new_game=new_game)

            messages.append(EmbedMessage(embed=embed, file=discord.File(image, filename="image.png")))
            continue

        else :
            "The game is updated!"
            # remove the ce id from old_ce_ids
            old_ce_ids.remove(new_game.ce_id)

            # get the old game
            old_game = hm.get_item_from_list(new_game.ce_id, old_games)

            # if the game hasn't been updated since last time, continue
            if old_game.last_updated <= new_game.last_updated : continue