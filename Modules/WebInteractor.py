import asyncio
import datetime
import functools
import time
import typing
import aiohttp
from discord.ext import tasks
import discord
import requests
from Classes.CE_Cooldown import CECooldown
from Classes.CE_User import CEUser, CEAPIUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_Game import CEAPIGame, CEGame
from Classes.OtherClasses import EmbedMessage, UpdateMessage
from Exceptions.FailedScrapeException import FailedScrapeException
from Modules import CEAPIReader, Discord_Helper, Mongo_Reader
from Modules.Screenshot import Screenshot
import Modules.hm as hm


# selenium and beautiful soup stuff
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
import io
from PIL import Image

def to_thread(func: typing.Callable) -> typing.Coroutine:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper

#   _____   _    _   ______    _____   _  __    _____     ____    _        ______    _____ 
#  / ____| | |  | | |  ____|  / ____| | |/ /   |  __ \   / __ \  | |      |  ____|  / ____|
# | |      | |__| | | |__    | |      | ' /    | |__) | | |  | | | |      | |__    | (___  
# | |      |  __  | |  __|   | |      |  <     |  _  /  | |  | | | |      |  __|    \___ \ 
# | |____  | |  | | | |____  | |____  | . \    | | \ \  | |__| | | |____  | |____   ____) |
#  \_____| |_|  |_| |______|  \_____| |_|\_\   |_|  \_\  \____/  |______| |______| |_____/ 

def check_category_roles(old_games : list[CEUserGame], new_games : list[CEUserGame],
                         database_name : list[CEGame], user : CEUser
                         ) -> list[UpdateMessage] :
    "Takes in the old and newly completed games and returns a list of `UpdateMessage`s to send."

    # ----- set up variables -----
    oldt1s, oldt2s, oldt3s, oldt4s, oldt5s = (0,)*5
    oldac, oldar, oldbh, oldfp, oldpl, oldst = (0,)*6
    newt1s, newt2s, newt3s, newt4s, newt5s = (0,)*5
    newac, newar, newbh, newfp, newpl, newst = (0,)*6
    updates : list[UpdateMessage] = []

    # ----- sort old games -----
    for game in old_games :
        points = game.get_user_points() # grab the points
        database_game = hm.get_item_from_list(game.ce_id, database_name) # get the official game
        
        # if the game was deleted, continue
        if database_game == None : continue

        if game.is_completed(database_name) :
            match(database_game.get_tier()) :
                case "Tier 1" : oldt1s += points
                case "Tier 2" : oldt2s += points
                case "Tier 3" : oldt3s += points
                case "Tier 4" : oldt4s += points
                case "Tier 5" : oldt5s += points
                case "Tier 6" : oldt5s += points # t6
                case "Tier 7" : oldt5s += points # t7

        
        match(database_game.category) :
            case "Action" : oldac += points
            case "Arcade" : oldar += points
            case "Bullet Hell" : oldbh += points
            case "First-Person" : oldfp += points
            case "Platformer" : oldpl += points
            case "Strategy" : oldst += points

    # ----- sort new games -----
    for game in new_games :
        points = game.get_user_points()
        database_game = hm.get_item_from_list(game.ce_id, database_name)
        if database_game == None : continue
        if game.is_completed(database_name) :
            match(database_game.get_tier()) :
                case "Tier 1" : newt1s += points
                case "Tier 2" : newt2s += points
                case "Tier 3" : newt3s += points
                case "Tier 4" : newt4s += points
                case "Tier 5" : newt5s += points
                case "Tier 6" : newt5s += points # t6
                case "Tier 7" : newt5s += points # t7
        match(database_game.category) :
            case "Action" : newac += points
            case "Arcade" : newar += points
            case "Bullet Hell" : newbh += points
            case "First-Person" : newfp += points
            case "Platformer" : newpl += points
            case "Strategy" : newst += points

    old_categories = (oldac, oldar, oldbh, oldfp, oldpl, oldst)
    new_categories = (newac, newar, newbh, newfp, newpl, newst)
    old_tiers = (oldt1s, oldt2s, oldt3s, oldt4s, oldt5s)
    new_tiers = (newt1s, newt2s, newt3s, newt4s, newt5s)

    CATEGORY_ROLE_NAMES = ["Master", "Grandmaster", "Grandmaster (Black Role)"]

    # ----- actually check -----
    # categories
    for point_index, point_value in enumerate([500, 1000, 2000]) :
        for i, category in enumerate(list(typing.get_args(hm.CATEGORIES))) :
            if old_categories[i] < point_value and new_categories[i] >= point_value :
                if not user.on_mutelist():
                    updates.append(UpdateMessage(
                        location="userlog",
                        message=(f"Congratulations to {user.mention()} ({user.display_name})! " +
                                f"You have unlocked {category} {CATEGORY_ROLE_NAMES[point_index]} ({point_value}+ points)")
                    ))
                else:
                    updates.append(UpdateMessage(
                        location="privatelog",
                        message=f"🤫 Muted user {user.display_name_with_link()} has unlocked {category} {CATEGORY_ROLE_NAMES[point_index]}"
                    ))
    # tiers
    for i in range(1, 6) : # 1, 2, 3, 4, 5
        #if    oldt1s       < 500   and    newt1s        >= 500
        if old_tiers[i - 1] < i*500 and new_tiers[i - 1] >= i * 500 :
            if not user.on_mutelist():
                updates.append(UpdateMessage(
                    location="userlog",
                    message=(
                        f"Congratulations to {user.mention()} ({user.display_name})! " +
                        f"You have unlocked Tier {i} Enthusiast ({i * 500} points in Tier {i} completed games)."
                    )
                ))
            else:
                updates.append(UpdateMessage(
                    location="privatelog",
                    message=f"🤫 Muted user {user.display_name_with_link()} has unlocked Tier {i} Enthusiast"
                ))

    return updates

#   _____   ______   _______     _____   __  __               _____   ______ 
#  / ____| |  ____| |__   __|   |_   _| |  \/  |     /\      / ____| |  ____|
# | |  __  | |__       | |        | |   | \  / |    /  \    | |  __  | |__   
# | | |_ | |  __|      | |        | |   | |\/| |   / /\ \   | | |_ | |  __|  
# | |__| | | |____     | |       _| |_  | |  | |  / ____ \  | |__| | | |____ 
#  \_____| |______|    |_|      |_____| |_|  |_| /_/    \_\  \_____| |______|




def get_image(driver : webdriver.Chrome, new_game) -> io.BytesIO | tuple[typing.Literal['Assets/image_failed_v2.png'], str] :
    "Takes in the `driver` (webdriver) and the game's `ce_id` and returns an image to be screenshotted."

    # set type hinting
    from Classes.CE_Game import CEGame
    new_game : CEGame = new_game

    OBJECTIVE_LIMIT = 7
    "The maximum amount of objectives to be screenshot before cropping." 

    CONSOLE_MESSAGES = True

    # initiate selenium
    if CONSOLE_MESSAGES: print('trying')
    try :
        url = f"https://cedb.me/game/{new_game.ce_id}/"
        driver.get(url)
    except Exception as e :
        print(e)
        return "Assets/image_failed_v2.png"
    if CONSOLE_MESSAGES: print('try complete.')
    
    # set up variables
    start_time = hm.get_unix('now')
    timeout = hm.get_unix('now') - start_time > 5
    objective_list = []
    TIMEOUT_LIMIT = 8

    try:
        # give it five seconds to load the elements.
        if CONSOLE_MESSAGES: print('before while')
        while (len(objective_list) < 1 or not objective_list[0].is_displayed()) and not timeout :
            # run this to just fully load the page...
            #html_page = driver.execute_script("return document.documentElement.innerHTML;")
            # ...and now get the list.
            print('whiling..')
            objective_list = driver.find_elements(By.CLASS_NAME, "bp4-html-table-striped")
            print('objective whiling...')
            timeout = hm.get_unix('now') - start_time > TIMEOUT_LIMIT
        
        if CONSOLE_MESSAGES: print('while left.')
        
        # if it took longer than 5 seconds, just return the image failed image.
        if timeout : return ("Assets/image_failed_v2.png", "image timeout")

        # i'm gonna let it sleep here just so that we are SURE the rest of the page loads in.
        if CONSOLE_MESSAGES: print('sleeping...')
        SLEEP_LIMIT = 3
        time.sleep(SLEEP_LIMIT)
        if CONSOLE_MESSAGES: print('sleep over.')


        if CONSOLE_MESSAGES: print('finding elements...')
        primary_table = driver.find_element(By.CLASS_NAME, "css-c4zdq5")
        objective_list = primary_table.find_elements(By.CLASS_NAME, "bp4-html-table-striped")
        title = driver.find_element(By.TAG_NAME, "h1")
        top_left = driver.find_element(By.CLASS_NAME, "GamePage-Header-Image").location
        title_size = title.size['width']
        title_location = title.location['x']

        bottom_right = objective_list[len(objective_list)-2].location
        size = objective_list[len(objective_list)-2].size

        header_elements = [
            'bp4-navbar',
            'tr-fadein',
            'css-1ugviwv'
        ]

        BORDER_WIDTH = 15
        DISPLAY_FACTOR = 1

        top_left_x = (top_left['x'] - BORDER_WIDTH)*DISPLAY_FACTOR
        top_left_y = (top_left['y'] - BORDER_WIDTH)*DISPLAY_FACTOR
        bottom_right_y = (bottom_right['y'] + size['height'] + BORDER_WIDTH)*DISPLAY_FACTOR

        if title_location + title_size > bottom_right['x'] + size['width']:
            bottom_right_x = (title_location + title_size + BORDER_WIDTH)*DISPLAY_FACTOR
        else:
            bottom_right_x = (bottom_right['x'] + size['width'] + BORDER_WIDTH)*DISPLAY_FACTOR
        
        if CONSOLE_MESSAGES: print('elements found')

        if CONSOLE_MESSAGES: print('screenshotting 1...')
        ob = Screenshot(bottom_right_y)
        if CONSOLE_MESSAGES: print('screenshotting 2...')
        im = ob.full_screenshot(driver, save_path=r'Pictures/', image_name="ss.png", 
                                is_load_at_runtime=True, load_wait_time=10, hide_elements=header_elements)
        if CONSOLE_MESSAGES: print('screenshot gotten.')
    except Exception as e :
        return ("Assets/image_failed_v2.png", f"{e}")
    
    if CONSOLE_MESSAGES: print('passed try-except.')
    im = io.BytesIO(im)
    im_image = Image.open(im)

    SAVE_FULL_IMAGE_LOCALLY = False
    if SAVE_FULL_IMAGE_LOCALLY :
        im_image.save('ss.png')

    if CONSOLE_MESSAGES: print('cropping...')
    im_image = im_image.crop((top_left_x, top_left_y, bottom_right_x, bottom_right_y))
    if CONSOLE_MESSAGES: print('cropped.')

    if CONSOLE_MESSAGES: print('bytesio ing...')
    imgByteArr = io.BytesIO()
    im_image.save(imgByteArr, format='PNG')
    final_im = imgByteArr.getvalue()
    ss = io.BytesIO(final_im)
    if CONSOLE_MESSAGES: print('bytesio gotten.')

    SAVE_CROPPED_IMAGE_LOCALLY = False

    if SAVE_CROPPED_IMAGE_LOCALLY :
        im_image.save('ss.png')

    return ss


utc = datetime.timezone.utc
times = [
  datetime.time(hour=0, minute=0, tzinfo=utc),
  datetime.time(hour=0, minute=30, tzinfo=utc),
  datetime.time(hour=1, minute=0, tzinfo=utc),
  datetime.time(hour=1, minute=30, tzinfo=utc),
  datetime.time(hour=2, minute=0, tzinfo=utc),
  datetime.time(hour=2, minute=30, tzinfo=utc),
  datetime.time(hour=3, minute=0, tzinfo=utc),
  datetime.time(hour=3, minute=30, tzinfo=utc),
  datetime.time(hour=4, minute=0, tzinfo=utc),
  datetime.time(hour=4, minute=30, tzinfo=utc),
  datetime.time(hour=5, minute=0, tzinfo=utc),
  datetime.time(hour=5, minute=30, tzinfo=utc),
  datetime.time(hour=6, minute=0, tzinfo=utc),
  datetime.time(hour=6, minute=30, tzinfo=utc),
  datetime.time(hour=7, minute=0, tzinfo=utc),
  datetime.time(hour=7, minute=30, tzinfo=utc),
  datetime.time(hour=8, minute=0, tzinfo=utc),
  datetime.time(hour=8, minute=30, tzinfo=utc),
  datetime.time(hour=9, minute=0, tzinfo=utc),
  datetime.time(hour=9, minute=30, tzinfo=utc),
  datetime.time(hour=10, minute=0, tzinfo=utc),
  datetime.time(hour=10, minute=30, tzinfo=utc),
  datetime.time(hour=11, minute=0, tzinfo=utc),
  datetime.time(hour=11, minute=30, tzinfo=utc),
  datetime.time(hour=12, minute=0, tzinfo=utc),
  datetime.time(hour=12, minute=30, tzinfo=utc),
  datetime.time(hour=13, minute=0, tzinfo=utc),
  datetime.time(hour=13, minute=30, tzinfo=utc),
  datetime.time(hour=14, minute=0, tzinfo=utc),
  datetime.time(hour=14, minute=30, tzinfo=utc),
  datetime.time(hour=15, minute=0, tzinfo=utc),
  datetime.time(hour=15, minute=30, tzinfo=utc),
  datetime.time(hour=16, minute=0, tzinfo=utc),
  datetime.time(hour=16, minute=30, tzinfo=utc),
  datetime.time(hour=17, minute=0, tzinfo=utc),
  datetime.time(hour=17, minute=30, tzinfo=utc),
  datetime.time(hour=18, minute=0, tzinfo=utc),
  datetime.time(hour=18, minute=30, tzinfo=utc),
  datetime.time(hour=19, minute=0, tzinfo=utc),
  datetime.time(hour=19, minute=30, tzinfo=utc),
  datetime.time(hour=20, minute=0, tzinfo=utc),
  datetime.time(hour=20, minute=30, tzinfo=utc),
  datetime.time(hour=21, minute=0, tzinfo=utc),
  datetime.time(hour=21, minute=30, tzinfo=utc),
  datetime.time(hour=22, minute=0, tzinfo=utc),
  datetime.time(hour=22, minute=30, tzinfo=utc),
  datetime.time(hour=23, minute=0, tzinfo=utc),
  datetime.time(hour=23, minute=30, tzinfo=utc),
]

#  __  __               _____   _______   ______   _____      _         ____     ____    _____  
# |  \/  |     /\      / ____| |__   __| |  ____| |  __ \    | |       / __ \   / __ \  |  __ \ 
# | \  / |    /  \    | (___      | |    | |__    | |__) |   | |      | |  | | | |  | | | |__) |
# | |\/| |   / /\ \    \___ \     | |    |  __|   |  _  /    | |      | |  | | | |  | | |  ___/ 
# | |  | |  / ____ \   ____) |    | |    | |____  | | \ \    | |____  | |__| | | |__| | | |     
# |_|  |_| /_/    \_\ |_____/     |_|    |______| |_|  \_\   |______|  \____/   \____/  |_|     

@tasks.loop(time=times)
async def master_loop(client : discord.Client, guild_id : int) :
    """The main looping function that runs every half hour."""
    print('---- loop began... ----')
    # get channels
    casino_log_channel = client.get_channel(hm.CASINO_LOG_ID)
    user_log_channel = client.get_channel(hm.USER_LOG_ID)
    casino_channel = client.get_channel(hm.CASINO_ID)
    private_log_channel = client.get_channel(hm.PRIVATE_LOG_ID)
    game_additions_channel = client.get_channel(hm.GAME_ADDITIONS_ID)
    
    # ---- game ----
    SKIP_GAME_SCRAPE = False
    if not SKIP_GAME_SCRAPE :
        try :
            old_database_name : list[CEGame] = []
            d = await Mongo_Reader.get_database_name()
            print(len(d))
            new_games : list[CEAPIGame] = await CEAPIReader.get_api_games_full()
            game_list = await Mongo_Reader.get_list("name")
            print(f"games: {len(game_list)}")
            embeds : list[EmbedMessage] = []
            exceptions : list[UpdateMessage] = []

            for i, new_game in enumerate(new_games) :
                if i % 50 == 0 : print(f"game {i} of {len(new_games)}", end="... ")

                # grab the old game
                old_game = await Mongo_Reader.get_game(new_game.ce_id)

                # and add it to database name
                if old_game is not None :
                    old_database_name.append(old_game)

                # and the game list (which keeps track of all the old games)
                # needs to be updated.
                if new_game.ce_id in game_list : 
                    game_list.remove(new_game.ce_id)

                if old_game is not None and old_game.last_updated == new_game.last_updated : continue

                # get the update
                game_returns = await thread_single_game_update(
                    old_game=old_game, new_game = new_game, driver=None
                )

                # save the returns
                if game_returns is not None :
                    if game_returns[0] is not None :
                        embeds.append(game_returns[0])
                    exceptions += game_returns[1]

                # and dump the new game
                await Mongo_Reader.dump_game(new_game)


            
            # now at this point, game_list only has the list of games that were in old_games
            # but not in new_games.
            print(game_list)
            print(f'removed games: {len(game_list)}')
            for removed_game in game_list :
                old_game = await Mongo_Reader.get_game(removed_game)

                # get the update
                game_returns = await thread_single_game_update(
                    old_game=old_game, new_game=None, driver=None
                )

                # save the returns
                if game_returns is not None :
                    if game_returns[0] is not None :
                        embeds.append(game_returns[0])
                    exceptions += game_returns[1]

                # delete the game
                await Mongo_Reader.delete_game(old_game.ce_id)

                # and add it to database name
                old_database_name.append(old_game)

            # send embeds
            for embed in embeds :
                if embed.file is not None :
                    await game_additions_channel.send(embed=embed.embed, file=embed.file)
                else :
                    await game_additions_channel.send(embed=embed.embed)
            
            # send exceptions
            print(exceptions)
            for exc in exceptions :
                await private_log_channel.send(f"{exc.message} \n<@413427677522034727>")

        except FailedScrapeException as e :
            await private_log_channel.send(f":warning: {e.get_message()}")
            print('fetching games failed.')
            return

        except Exception as e :
            await private_log_channel.send(f":warning: {e.with_traceback()}")
    
    print(f"old database name: {len(old_database_name)}")

    # ---- users ----
    SKIP_USER_SCRAPE = False
    if not SKIP_USER_SCRAPE :
        if SKIP_GAME_SCRAPE : return
        try :
            database_user = await Mongo_Reader.get_list("user")
            new_users : list[CEAPIUser] = await CEAPIReader.get_api_users_all(database_user)

            # guild
            guild = await client.fetch_guild(guild_id)

            # updates
            updates : list[UpdateMessage] = []

            # get the updates
            # we can iterate over old or new here, the amount of users in both places will be the same.
            for i, new_user in enumerate(new_users) :
                if i % 50 == 0 : print(f"user {i} of {len(new_users)}")

                # grab old user
                old_user = await Mongo_Reader.get_user(new_user.ce_id)

                # grab the update
                updates += (await single_user_update_v2(
                    user=old_user,
                    site_data=new_user,
                    old_database_name=old_database_name,
                    new_database_name=new_games,
                ))

                # the user was already dumped, so we can just loop again
                continue

            for update_message in updates :
                match(update_message.location) :
                    case "userlog" : await user_log_channel.send(update_message.message)
                    case "casinolog" : await casino_log_channel.send(update_message.message)
                    case "gameadditions" : await game_additions_channel.send(update_message.message)
                    case "casino" : await casino_channel.send(update_message.message)
                    case "privatelog" : await private_log_channel.send(update_message.message)

        except FailedScrapeException as e :
            await private_log_channel.send(f":warning: {e.get_message()}")
            print('fetching users failed.')
            return
        
        except Exception as e :
            await private_log_channel.send(f":warning: {e.with_traceback()}")
    
    # ---- curator ----

    # pull the data
    print("checking curator")
    mongo_recent_curated = await Mongo_Reader.get_curator_ids()
    steam_recent_curated, descriptions = await get_recent_curated()
    print(f'{steam_recent_curated=}')
    print(f'{mongo_recent_curated=}')

    uncurated: list[str] = []
    for item in steam_recent_curated:
        if item not in mongo_recent_curated:
            uncurated.append(item)

    # if steam didn't fail and the numbers are different
    if steam_recent_curated is not None and len(uncurated) != 0 :
        print(f"curating {len(uncurated)} update(s)")
        curator_embeds = await thread_curator(uncurated, new_games, descriptions)
        for embed in curator_embeds :
            await game_additions_channel.send(embed=embed)
        await Mongo_Reader.dump_curator_ids(uncurated)
        
    
    else : print('no new curator updates.')
    
    print('---- loop complete. ----')
    return await private_log_channel.send(f":white_check_mark: loop complete at <t:{hm.get_unix('now')}>.")

async def get_recent_curated():
    # set the payload and pull from the curator
    payload = {'cc' : 'us', 'l' : 'english'}
    async with aiohttp.ClientSession(headers={'User-Agent':"andy's-super-duper-bot/0.1"}) as session :
        async with session.get("https://store.steampowered.com/curator/36185934", params=payload) as response :

            # beautiful soupify
            soup_data = BeautifulSoup(await response.text(), features="html.parser")

            # set up variables
            descriptions, ce_ids = [], []

            # get all divs
            divs = soup_data.find_all('div')

            # iterate through them
            for item in divs :
                try :
                    CONSOLE_MESSAGES = False
                    if item['class'][0] == 'recommendation_readmore' :
                        if CONSOLE_MESSAGES : print('-- readmore --')
                        ce_ids.append(item.contents[0]['href'][-36:])
                        if CONSOLE_MESSAGES : print(ce_ids[-1])
                    if item['class'][0] == "recommendation_desc" :
                        if CONSOLE_MESSAGES : print('-- description --')
                        descriptions.append(item.string.replace('\t','').replace('\r','').replace('\n',''))
                        if CONSOLE_MESSAGES : print(descriptions[-1])
                except : continue
            return ce_ids, descriptions


#  _______   _    _   _____    ______              _____       _____              __  __   ______ 
# |__   __| | |  | | |  __ \  |  ____|     /\     |  __ \     / ____|     /\     |  \/  | |  ____|
#    | |    | |__| | | |__) | | |__       /  \    | |  | |   | |  __     /  \    | \  / | | |__   
#    | |    |  __  | |  _  /  |  __|     / /\ \   | |  | |   | | |_ |   / /\ \   | |\/| | |  __|  
#    | |    | |  | | | | \ \  | |____   / ____ \  | |__| |   | |__| |  / ____ \  | |  | | | |____ 
#    |_|    |_|  |_| |_|  \_\ |______| /_/    \_\ |_____/     \_____| /_/    \_\ |_|  |_| |______|


async def thread_single_game_update(old_game : CEGame | None, new_game : CEGame | None, driver) :
    "Threaded."
    return await Discord_Helper.game_addition_single_update(old_game, new_game, driver)



#  _______   _    _   _____    ______              _____      _    _    _____   ______   _____  
# |__   __| | |  | | |  __ \  |  ____|     /\     |  __ \    | |  | |  / ____| |  ____| |  __ \ 
#    | |    | |__| | | |__) | | |__       /  \    | |  | |   | |  | | | (___   | |__    | |__) |
#    | |    |  __  | |  _  /  |  __|     / /\ \   | |  | |   | |  | |  \___ \  |  __|   |  _  / 
#    | |    | |  | | | | \ \  | |____   / ____ \  | |__| |   | |__| |  ____) | | |____  | | \ \ 
#    |_|    |_|  |_| |_|  \_\ |______| /_/    \_\ |_____/     \____/  |_____/  |______| |_|  \_\


async def single_user_update_v2(user : CEUser, site_data : CEUser, old_database_name : list[CEGame],
                                    new_database_name : list[CEAPIGame]) -> list[UpdateMessage] :
    """Updates a user using the 'multiple documents' style of backend.
    The whole point of this is to no longer have a "database-user". However,
    this is only being used for reading, not for writing, so it's okay to pass it in here."""
    
    updates : list[UpdateMessage] = []

    original_points = user.get_total_points()
    # NOTE: we use old database name here for a specific reason. Say there was a T5,
    #       Celeste for example. if celeste goes from 250 points to 251 points,
    #       passing the new database would mark celeste as "incomplete" before
    #       and "complete" now, and thus every user who has completed celeste
    #       will get a message that says they've recompleted the game.
    #       by passing in the old database name, we can see that the game was complete
    #       before, and therefore a message won't be sent.
    original_completed_games = user.get_completed_games_2(old_database_name)
    original_rank = user.get_rank()
    original_games = user.owned_games

    user.owned_games = site_data.owned_games
    user._steam_id = site_data._steam_id

    new_points = user.get_total_points()
    new_completed_games = user.get_completed_games_2(new_database_name)
    new_rank = user.get_rank()
    new_games = user.owned_games

    # get the role messages
    updates += (check_category_roles(original_games, new_games, new_database_name, user))

    # search for newly completed games
    for game in new_completed_games :

        # if game is too low anyway, skip it
        TIER_MINIMUM = 4
        """int: The minimum tier for a game to be reported."""
        
        if not game.get_tier_num() >= TIER_MINIMUM : continue

        # check to see if it was completed before
        completed_before = False
        for old_game in original_completed_games :
            # it was completed before, so skip this
            if game.ce_id == old_game.ce_id : 
                completed_before = True
        if completed_before : continue
        
        #print(f"new completed game: {game.game_name}")
        if not user.on_mutelist():
            updates.append(UpdateMessage(
                location="userlog",
                message=(f"Wow {user.mention()} ({user.display_name})! You've completed {game.game_name}, " +
                        f"a {game.get_tier_emoji()} worth {game.get_total_points()} points {hm.get_emoji('Points')}!")
            ))
        else:
            updates.append(UpdateMessage(
            location="privatelog",
            message=f"🤫 Muted user {user.display_name_with_link()} completed {game.game_name}."))

    # rank update
    if new_rank != original_rank and new_points > original_points:
        if not user.on_mutelist():
            updates.append(UpdateMessage(
                location="userlog",
                message=(f"Congrats to {user.mention()} ({user.display_name}) for ranking up from Rank " +
                        f"{hm.get_emoji(original_rank)} to Rank {hm.get_emoji(new_rank)}!")
                ))
        else:
            updates.append(UpdateMessage(
                location="privatelog",
                message=f"🤫 Muted user {user.display_name_with_link()} ranked up from {original_rank} to {new_rank}."
            ))

    # check completion count
    COMPLETION_INCREMENT = 25
    if (int(len(original_completed_games) / COMPLETION_INCREMENT) 
        != int(len(new_completed_games) / COMPLETION_INCREMENT)):
        if not user.on_mutelist():
            updates.append(UpdateMessage(
                location="userlog",
                message=(f"Amazing! {user.mention()} ({user.display_name}) has passed the milestone of " +
                        f"{int(len(new_completed_games) / COMPLETION_INCREMENT) * COMPLETION_INCREMENT} completed games!")
            ))
        else:
            updates.append(UpdateMessage(
                location="privatelog",
                message=(f"🤫 Muted user {user.display_name_with_link()} has passed the milestone of" + 
                         f"{int(len(new_completed_games) / COMPLETION_INCREMENT) * COMPLETION_INCREMENT}")
            ))
    
    # check pendings
    for i, roll in enumerate(user.rolls[:]) :
        if roll.status == "pending" and roll.due_time <= hm.get_unix("now") :
            user.remove_pending(roll.roll_name)

    # check rolls
    for index, roll in enumerate(user.rolls) :
        # step 0: check multistage rolls
        # if the roll is multi stage AND its not in the final stage...
        # note: skip this if we're in the final stage because
        #       if it's in its final stage we can finish it out,
        #       this if statement just preps for the next one.
        if not roll.status == "current" : continue
        partner = None
        if roll.partner_ce_id is not None : partner = await Mongo_Reader.get_user(roll.partner_ce_id)
        if (roll.is_multi_stage() and not roll.in_final_stage() and 
            (roll.is_won(database_name=new_database_name, user=user, partner=partner))) :
            # if we've already hit this roll before, keep moving
            if roll.due_time == None : continue

            # add the update message
            updates.append(UpdateMessage(
                location="casino",
                message=(
                    f"{user.mention()}, you've finished your current stage in {roll.roll_name}. " +
                    f"To roll your next stage, type `/solo-roll {roll.roll_name}` in <#{hm.CASINO_ID}>."
                )
            ))

            # and kill the due time
            roll.due_time = None
            roll.set_status("waiting")
            user._rolls[index] = roll

        elif roll.is_won(database_name=new_database_name, user=user, partner=partner) :
            # add the update message
            updates.append(UpdateMessage(
                location="casinolog",
                message=(
                    roll.get_win_message(database_name=new_database_name, user=user, partner=partner)
                )
            ))
            # set the completed time to now
            roll.completed_time = hm.get_unix("now")

            # add the object to completed rolls, and
            # remove it from current
            roll.set_status("won")
            user._rolls[index] = roll

            """
            Let's talk about why this works.
            database-user is being constantly updated. Let's say we have two players, A and B.
            Since the last update, they have completed their requirements for their co-op roll.
            Player A joined the bot first, so their update is processed first. But since Player
            B hasn't been updated yet, the roll doesn't register as "won". So, we pass through
            Player A without removing the roll. But, when we get to Player B, both players have
            updated.
            """
            if roll.is_co_op() :
                # get the partner and their roll
                partner = await Mongo_Reader.get_user(roll.partner_ce_id)
                if partner.has_current_roll(roll.roll_name) :
                    partner_roll = partner.get_current_roll(roll.roll_name)

                    # update their current roll
                    if roll.is_pvp() and roll.status == "won" :
                        partner.fail_current_roll(partner_roll.roll_name)
                    elif roll.is_pvp() and roll.status == "failed" :
                        partner.win_current_roll(partner_roll.roll_name)
                    else :
                        partner.win_current_roll(partner_roll.roll_name)

                    # and append it to partners
                    await Mongo_Reader.dump_user(partner)

        
        elif roll.is_expired() :
            # add the update message
            updates.append(UpdateMessage(
                location="casino",
                message=(
                    roll.get_fail_message(database_name=new_database_name, user=user, partner=partner)
                )
            ))
            
            # remove this roll from current rolls
            user.fail_current_roll(roll.roll_name)
            if roll.is_co_op() :
                partner = await Mongo_Reader.get_user(roll.partner_ce_id)
                if partner.has_current_roll(roll.roll_name) :
                    partner.fail_current_roll(roll.roll_name)
                    await Mongo_Reader.dump_user(user)
    
    user.set_last_updated(hm.get_unix("now"))
    await Mongo_Reader.dump_user(user)

    return updates





#   _____   _    _   _____               _______    ____    _____       _____    ____    _    _   _   _   _______ 
#  / ____| | |  | | |  __ \      /\     |__   __|  / __ \  |  __ \     / ____|  / __ \  | |  | | | \ | | |__   __|
# | |      | |  | | | |__) |    /  \       | |    | |  | | | |__) |   | |      | |  | | | |  | | |  \| |    | |   
# | |      | |  | | |  _  /    / /\ \      | |    | |  | | |  _  /    | |      | |  | | | |  | | | . ` |    | |   
# | |____  | |__| | | | \ \   / ____ \     | |    | |__| | | | \ \    | |____  | |__| | | |__| | | |\  |    | |   
#  \_____|  \____/  |_|  \_\ /_/    \_\    |_|     \____/  |_|  \_\    \_____|  \____/   \____/  |_| \_|    |_|   

async def get_curator_count() -> int | None :
    "Returns the current curator count. Uses `requests` but I don't care!"

    # set the payload and pull from the curator
    payload = {"cc" : "us", "l" : "english"}
    data = requests.get("https://store.steampowered.com/curator/36185934", params=payload)

    # beautiful soupify
    soup_data = BeautifulSoup(data.text, features="html.parser")

    # get all spans
    spans = soup_data.find_all("span")

    # iterate through them
    for item in spans :
        try : 
            if item['id'] == "Recommendations_total" :
                return int(item.string)
        except :
            continue

    # return None if this fails.
    return None



#  _______   _    _   _____    ______              _____       _____   _    _   _____               _______    ____    _____  
# |__   __| | |  | | |  __ \  |  ____|     /\     |  __ \     / ____| | |  | | |  __ \      /\     |__   __|  / __ \  |  __ \ 
#    | |    | |__| | | |__) | | |__       /  \    | |  | |   | |      | |  | | | |__) |    /  \       | |    | |  | | | |__) |
#    | |    |  __  | |  _  /  |  __|     / /\ \   | |  | |   | |      | |  | | |  _  /    / /\ \      | |    | |  | | |  _  / 
#    | |    | |  | | | | \ \  | |____   / ____ \  | |__| |   | |____  | |__| | | | \ \   / ____ \     | |    | |__| | | | \ \ 
#    |_|    |_|  |_| |_|  \_\ |______| /_/    \_\ |_____/     \_____|  \____/  |_|  \_\ /_/    \_\    |_|     \____/  |_|  \_\


async def thread_curator(uncurated : list[str], database_name : list[CEGame], descriptions: list[str]) -> list[discord.Embed] :
    "Returns embed descriptions for the last `num_updates` curator posts. Max of 10."

    # adjust in case of max
    MAXIMUM_UPDATES = 10
    
    # and now return the embeds
    embeds : list[discord.Embed] = []
    for i in range(len(uncurated)) :
        embed = await Discord_Helper.get_game_embed(game_id=uncurated[i], database_name=database_name)
        #TODO: change header image to hex
        embed.title = f"New curator update: {embed.title}"
        embed.add_field(name="Curator Description", value=descriptions[i])
        embeds.append(embed)
    
    return embeds
