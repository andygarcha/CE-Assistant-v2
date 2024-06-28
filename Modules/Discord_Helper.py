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
from Modules.Screenshot import Screenshot


# selenium and beautiful soup stuff
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import io
from PIL import Image

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



# ---------------------------------- game additions ----------------------------------


def get_image(driver : webdriver.Chrome, new_game) -> io.BytesIO :
    "Takes in the `driver` (webdriver) and the game's `ce_id` and returns an image to be screenshotted."

    # set type hinting
    from Classes.CE_Game import CEGame, CEAPIGame
    new_game : CEGame = new_game

    OBJECTIVE_LIMIT = 7
    "The maximum amount of objectives to be screenshot before cropping." 

    # initiate selenium
    url = f"https://cedb.me/game/{new_game.ce_id}/"
    driver.get(url)
    
    # set up variables
    start_time = hm.get_unix('now')
    timeout = hm.get_unix('now') - start_time > 5
    objective_list = []

    # give it five seconds to load the elements.
    while (len(objective_list) < 1 or not objective_list[0].is_displayed()) and not timeout :
        # run this to just fully load the page...
        html_page = driver.execute_script("return document.documentElement.innerHTML;")
        # ...and now get the list.
        objective_list = driver.find_elements(By.CLASS_NAME, "bp4-html-table-striped")
        timeout = hm.get_unix('now') - start_time > 5
    
    # if it took longer than 5 seconds, just return the image failed image.
    if timeout : return "Assets/image_failed.png"

    primary_table = driver.find_element(By.CLASS_NAME, "css-c4zdq5")
    objective_list = primary_table.find_elements(By.CLASS_NAME, "bp4-html-table-striped")
    title = driver.find_element(By.TAG_NAME, "h1")
    top_left = driver.find_element(By.CLASS_NAME, "GamePage-Header-Image").location
    title_size = title.size['width']
    title_location = title.location['x']

    bottom_right = objective_list[len(objective_list)-2].location
    print(f"bottom right dict: {bottom_right}")
    print('\n')
    for i, objective in enumerate(objective_list) :
        print(f"objective {i} location: {objective.location}\nobjective {i} size: {objective.size}\nobjective {i} text: {objective.text}")
    print('\n')
    size = objective_list[len(objective_list)-2].size
    print(f'bottom right size dict: {size}')

    print(f'objectivelist len: {len(objective_list)}')

    objective_list[0]

    header_elements = [
        'bp4-navbar',
        'tr-fadein',
        'css-1ugviwv'
    ]

    BORDER_WIDTH = 15*2

    #NOTE: i multiplied these by two. dk why it's working.
    top_left_x = (top_left['x'])*2 - BORDER_WIDTH
    top_left_y = (top_left['y'])*2 - BORDER_WIDTH
    bottom_right_y = (bottom_right['y'] + size['height'])*2 + BORDER_WIDTH

    if title_location + title_size > bottom_right['x'] + size['width']:
        bottom_right_x = (title_location + title_size)*2 + BORDER_WIDTH
        print('a')
    else:
        bottom_right_x = (bottom_right['x'] + size['width'])*2 + BORDER_WIDTH
        print('b')
    
    print(f'x: {bottom_right_x}\ny: {bottom_right_y}')
    

    ob = Screenshot(bottom_right_y)
    im = ob.full_screenshot(driver, save_path=r'Pictures/', image_name="ss.png", 
                            is_load_at_runtime=True, load_wait_time=10, hide_elements=header_elements)
    im = io.BytesIO(im)
    im_image = Image.open(im)

    SAVE_FULL_IMAGE_LOCALLY = False
    if SAVE_FULL_IMAGE_LOCALLY :
        im_image.save('ss.png')

    im_image = im_image.crop((top_left_x, top_left_y, bottom_right_x, bottom_right_y))

    imgByteArr = io.BytesIO()
    im_image.save(imgByteArr, format='PNG')
    final_im = imgByteArr.getvalue()
    ss = io.BytesIO(final_im)

    SAVE_CROPPED_IMAGE_LOCALLY = False

    if SAVE_CROPPED_IMAGE_LOCALLY :
        im_image.save('ss.png')

    return ss

    
    



def game_additions_updates(old_games : list, new_games : list) -> list[EmbedMessage] :
    "Returns a list of `discord.Embed`s to send to #game-additions."

    # import and type casting
    from Classes.CE_Game import CEGame, CEAPIGame
    old_games : list[CEGame] = old_games
    new_games : list[CEAPIGame] = new_games
    import Modules.Screenshot as Screenshot

    # the list to be returned
    messages : list[EmbedMessage] = []

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
        driver.set_window_size(width=1440, height=8000)
        
        # grab the first game to get color on the rest of them
        # ----- variables -----
        CELESTE_CE_URL = "https://cedb.me/game/1e866995-6fec-452e-81ba-1e8f8594f4ea"
        driver.get(CELESTE_CE_URL)

    # get a list of the old ones, so we know if a game was removed or not
    old_ce_ids : list[str] = []
    for old_game in old_games :
        old_ce_ids.append(old_game.ce_id)

    for new_game in new_games :
        # check if it's unfinished, skip if so
        if not new_game.is_finished :
            if new_game.ce_id in old_ce_ids : old_ce_ids.remove(new_game.ce_id)
            continue

        # --- the game is new ---


        if new_game.ce_id not in old_ce_ids : 

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
                        f"worth {new_game.get_po_points()} {hm.get_emoji("Points")}"
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
            embed.set_footer(name='CE Assistant', icon_url=hm.FINAL_CE_ICON)

            if SELENIUM_ENABLE : image = get_image(driver=driver, new_game=new_game)
            #TODO: fix this?

            messages.append(EmbedMessage(embed=embed, file=discord.File(image, filename="image.png")))
            continue

        # --- the game is updated ---

        # remove the ce id from old_ce_ids
        old_ce_ids.remove(new_game.ce_id)

        # get the old game
        old_game = hm.get_item_from_list(new_game.ce_id, old_games)

        # if the game hasn't been updated since last time, continue
        if old_game.last_updated <= new_game.last_updated : continue

        # set up embed
        embed = discord.Embed(
            title=f"__{new_game.game_name}__ updated on the site:",
            color=0xefd839,
            timestamp=datetime.datetime.now(),
            description="",
            url=f"https://cedb.me/game/{new_game.ce_id}/"
        )
        embed.set_image(url="attachment://image.png")
        embed.set_author(name='Challenge Enthusiasts', icon_url=new_game.icon)
        embed.set_footer(name='CE Assistant', icon_url=hm.FINAL_CE_ICON)

        # ----- actual update -----
        # point/tier changes
        if old_game.get_total_points() != new_game.get_total_points() :
            embed.description += (
                f"\n- {old_game.get_total_points()} {hm.get_emoji('Points')} " +                            # 75 points
                f"{old_game.get_tier_emoji() if old_game.get_tier() != new_game.get_tier() else ''} " +     # tier 3 if tiers are different
                f"{hm.get_emoji('Arrow')} " +                                                               # -->
                f"{new_game.get_total_points()} {hm.get_emoji('Points')} " +                                # 220 points
                f"{new_game.get_tier_emoji() if old_game.get_tier() != new_game.get_tier() else ''}"        # tier 5 if tiers are different
            )
        else :
            embed.description += "\n- Total points unchanged"

        # category changes
        if old_game.category != new_game.category :
            embed.description += f"\n- {old_game.get_category_emoji()} {hm.get_emoji('Points')} {new_game.get_category_emoji()}"

        # objective changes...
        old_objective_ce_ids = [old_objective.ce_id for old_objective in old_game.all_objectives]
        for new_objective in new_game.all_objectives :

            # if objective is new
            if new_objective.ce_id not in old_objective_ce_ids :
                "Objective is new!"
                embed.description += (
                    f"\n- New {new_objective.type} Objective '**{new_objective.name}**' added:"
                )
                if new_objective.type == "Primary" or new_objective.type == "Secondary" :
                    embed.description += f"\n\t- {new_objective.point_value} {hm.get_emoji('Points')}"
                embed.description += f"\n\t- {new_objective.description}"
                continue
            
            # update objective tracker and get the old objective
            old_objective_ce_ids.remove(new_objective.ce_id)
            old_objective = hm.get_item_from_list(new_objective.ce_id, old_game.all_objectives)
            
            # if objective is updated
            if not new_objective.equals(old_objective) :
                "Objective is updated."
                # if the points have changed
                if old_objective.point_value > new_objective.point_value :
                    embed.description += (f"\n- '**{new_objective.name}**' decreased from {old_objective.point_value} {hm.get_emoji('Points')} " + 
                                        f"to {new_objective.point_value} {hm.get_emoji('Points')}:")
                elif old_objective.point_value < new_objective.point_value :
                    embed.description += (f"\n- '**{new_objective.name}**' increased from {old_objective.point_value} {hm.get_emoji('Points')} " + 
                                        f"to {new_objective.point_value} {hm.get_emoji('Points')}:")
                else :
                    embed.description += (f"\n- '**{new_objective.name}**' updated:")
                
                # if the type has changed
                if old_objective.type != new_objective.type :
                    embed.description += (f"\n\t- Type changed from {old_objective.type} to {new_objective.type}")

                # if the description was updated
                if old_objective.description != new_objective.description :
                    embed.description += f"\n\t- Description updated"
                
                # if the requirements were updated
                if old_objective.requirements != new_objective.requirements :
                    embed.description += "\n\t- Requirements updated"
            
                # if the achievements were updated
                if set(old_objective.achievement_ce_ids) != set(new_objective.achievement_ce_ids) :
                    embed.description += "\n\t- Achievements updated"

                # if the partial points were updated
                if old_objective.partial_points != new_objective.partial_points :
                    embed.description += (f"\n\t- Partial points changed from {old_objective.partial_points} {hm.get_emoji('Points')} " +
                                            f"to {new_objective.partial_points} {hm.get_emoji('Points')}")
        
        # all objectives have been reflected
        description_test = embed.description
        description_test = description_test.replace('\n','').replace('\t','').replace('- Total points unchanged','')

        # if there wasn't any real change, ignore this embed
        if description_test == "" : continue

        messages.append(EmbedMessage(
            embed=embed, file=discord.File(get_image(driver=driver,new_game=new_game), filename="image.png")
        ))
    
    # --- all additions and updates have finished. check for removed games ---
    for game in old_ce_ids :
        game_object = hm.get_item_from_list(game, old_games)
        embed = discord.Embed(
            title=f"__{game_object.game_name}__ removed from the site.",
            color=0xce4e2c,
            timestamp=datetime.datetime.now()
        )
        embed.set_image(url="Assets/removed.png")

        messages.append(EmbedMessage(
            embed=embed, file=discord.File("Web_Interaction/removed.png", filename="image.png")
        ))

    if SELENIUM_ENABLE : driver.close()
    
    return messages