import asyncio
import datetime
import functools
import time
import typing
from discord.ext import tasks
import discord
import requests
from Classes.CE_Cooldown import CECooldown
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Classes.CE_Game import CEAPIGame, CEGame
from Classes.OtherClasses import EmbedMessage, UpdateMessage
from Exceptions.FailedScrapeException import FailedScrapeException
from Modules import CEAPIReader, Discord_Helper, Mongo_Reader
from Modules.Screenshot import Screenshot
import Modules.hm as hm


# selenium and beautiful soup stuff
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
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
                updates.append(UpdateMessage(
                    location="userlog",
                    message=(f"Congratulations to <@{user.discord_id}>! " +
                             f"You have unlocked {category} {CATEGORY_ROLE_NAMES[point_index]} ({point_value}+ points)")
                ))
    # tiers
    for i in range(1, 6) : # 1, 2, 3, 4, 5
        #if    oldt1s       < 500   and    newt1s        >= 500
        if old_tiers[i - 1] < i*500 and new_tiers[i - 1] >= i * 500 :
            updates.append(UpdateMessage(
                location="userlog",
                message=(
                    f"Congratulations to <@{user.discord_id}>! " +
                    f"You have unlocked Tier {i} Enthusiast ({i * 500} points in Tier {i} completed games)."
                )
            ))

    return updates



#  _    _    _____   ______   _____      _    _   _____    _____               _______   ______ 
# | |  | |  / ____| |  ____| |  __ \    | |  | | |  __ \  |  __ \      /\     |__   __| |  ____|
# | |  | | | (___   | |__    | |__) |   | |  | | | |__) | | |  | |    /  \       | |    | |__   
# | |  | |  \___ \  |  __|   |  _  /    | |  | | |  ___/  | |  | |   / /\ \      | |    |  __|  
# | |__| |  ____) | | |____  | | \ \    | |__| | | |      | |__| |  / ____ \     | |    | |____ 
#  \____/  |_____/  |______| |_|  \_\    \____/  |_|      |_____/  /_/    \_\    |_|    |______|


def user_update(user : CEUser, site_data : CEUser, old_database_name : list[CEGame], 
                new_database_name : list[CEAPIGame], database_user : list[CEUser],
                guild : discord.Guild) -> tuple[list[UpdateMessage], CEUser, list[CEUser]] :
    """Takes in a user and updates it, and returns a list of things to send."""
    updates : list[UpdateMessage] = []
    # if a partner needs to be returned, it'll be placed here
    partners : list[CEUser] = []

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

    new_points = user.get_total_points()
    new_completed_games = user.get_completed_games_2(new_database_name)
    new_rank = user.get_rank()
    new_games = user.owned_games

    NEW_MESSAGES = False

    # get the role messages
    updates += (check_category_roles(original_games, new_games, new_database_name, user))

    # discord user
    if NEW_MESSAGES : discord_user = guild.get_member(user.discord_id)

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
        
        if NEW_MESSAGES : 
            updates.append(UpdateMessage(
                location="userlog",
                message=(f"Wow {discord_user.global_name} ({user.mention()})! You've completed {game.game_name}, " + 
                        f"a {game.get_tier_emoji()} worth {game.get_total_points()} points {hm.get_emoji('Points')}!")
            ))
        else : 
            updates.append(UpdateMessage(
                location="userlog",
                message=(f"Wow {user.mention()}! You've completed {game.game_name}, " +
                        f"a {game.get_tier_emoji()} worth {game.get_total_points()} points {hm.get_emoji('Points')}!")
            ))

    # rank update
    if new_rank != original_rank and new_points > original_points :
        if NEW_MESSAGES : updates.append(UpdateMessage(
            location="userlog",
            message=(f"Congrats to {discord_user.global_name} {user.mention()} for ranking up from Rank " +
                     f"{hm.get_emoji(original_rank)} to Rank {hm.get_emoji(new_rank)}!")
            ))
        else : updates.append(UpdateMessage(
            location="userlog",
            message=(f"Congrats to {user.mention()} for ranking up from Rank " +
                     f"{hm.get_emoji(original_rank)} to Rank {hm.get_emoji(new_rank)}!")
            ))

    # check completion count
    COMPLETION_INCREMENT = 25
    if int(len(original_completed_games) / COMPLETION_INCREMENT) != int(len(new_completed_games) / COMPLETION_INCREMENT) :
        if NEW_MESSAGES : 
            updates.append(UpdateMessage(
                location="userlog",
                message=(f"Amazing! {discord_user} ({user.mention()}) has passed the milestone of " +
                        f"{int(len(new_completed_games) / COMPLETION_INCREMENT) * COMPLETION_INCREMENT} completed games!")
            ))
        else : 
            updates.append(UpdateMessage(
                location="userlog",
                message=(f"Amazing! {user.mention()} has passed the milestone of " +
                        f"{int(len(new_completed_games) / COMPLETION_INCREMENT) * COMPLETION_INCREMENT} completed games!")
            ))

    # check cooldowns
    for i, cooldown in enumerate(user.cooldowns) :
        if cooldown.end_time is None or cooldown.end_time <= hm.get_unix('now') :
            updates.append(UpdateMessage(
                location="casino",
                message=f"{user.mention()}, your {cooldown.roll_name} cooldown has ended."
            ))
            del user.cooldowns[i]
    
    # check pendings
    for i, pending in enumerate(user.pending_rolls) :
        if pending.end_time <= hm.get_unix('now') :
            del user.pending_rolls[i]

    # check rolls
    for index, roll in enumerate(user.current_rolls) :
        # step 0: check multistage rolls
        # if the roll is multi stage AND its not in the final stage...
        # note: skip this if we're in the final stage because
        #       if it's in its final stage we can finish it out,
        #       this if statement just preps for the next one.
        if (roll.is_multi_stage() and not roll.in_final_stage() and 
            (roll.is_won(database_name=new_database_name, database_user=database_user))) :
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

        elif roll.is_won(database_name=new_database_name, database_user=database_user) :
            # add the update message
            updates.append(UpdateMessage(
                location="casinolog",
                message=(
                    roll.get_win_message(database_name=new_database_name, database_user=database_user)
                )
            ))
            # set the completed time to now
            roll.completed_time = hm.get_unix("now")

            # add the object to completed rolls, and
            # remove it from current
            user.add_completed_roll(roll)
            del user.current_rolls[index]

            if roll.is_co_op() :
                # get the partner and their roll
                partner = hm.get_item_from_list(roll.partner_ce_id, database_user)
                partner_roll = partner.get_current_roll(roll.roll_name)

                # set the partner roll's winner tag
                if roll.is_pvp() : partner_roll.winner = not roll.winner

                # remove their current roll
                partner.remove_current_roll(partner_roll.roll_name)

                # set the completion time and add it to the completed rolls
                partner_roll.completed_time = hm.get_unix('now')
                partner.add_completed_roll(partner_roll)

                # and append it to partners
                partners.append(partner)

        
        elif roll.is_expired() :
            # add the update message
            updates.append(UpdateMessage(
                location="casino",
                message=(
                    roll.get_fail_message(database_name=new_database_name, database_user=database_user)
                )
            ))
            
            # remove this roll from current rolls
            del user.current_rolls[index]
            if roll.is_co_op() :
                partner = hm.get_item_from_list(roll.partner_ce_id, database_user)
                partner.remove_current_roll(roll.roll_name)
                partners.append(partner)


            # and add a cooldown
            user.add_cooldown(CECooldown(
                roll_name=roll.roll_name,
                end_time=roll.calculate_cooldown_date(database_name=new_database_name)
            ))
    
    return (updates, user, partners)


#   _____   ______   _______     _____   __  __               _____   ______ 
#  / ____| |  ____| |__   __|   |_   _| |  \/  |     /\      / ____| |  ____|
# | |  __  | |__       | |        | |   | \  / |    /  \    | |  __  | |__   
# | | |_ | |  __|      | |        | |   | |\/| |   / /\ \   | | |_ | |  __|  
# | |__| | | |____     | |       _| |_  | |  | |  / ____ \  | |__| | | |____ 
#  \_____| |______|    |_|      |_____| |_|  |_| /_/    \_\  \_____| |______|




def get_image(driver : webdriver.Chrome, new_game) -> io.BytesIO | tuple[typing.Literal['Assets/image_failed_v2.png'], str] :
    "Takes in the `driver` (webdriver) and the game's `ce_id` and returns an image to be screenshotted."

    # set type hinting
    from Classes.CE_Game import CEGame, CEAPIGame
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
        database_name = await Mongo_Reader.get_mongo_games()
        try :
            new_games = await CEAPIReader.get_api_games_full()
            # get the embeds
            game_returns : tuple[list[EmbedMessage], list[UpdateMessage]] = await thread_game_update(
                old_games=database_name, new_games=new_games
            )
            if game_returns == "No valid machine option available." :
                await private_log_channel.send("No valid machine option available for selenium.")
                return
            embeds = game_returns[0]
            exceptions = game_returns[1]

            # send embeds
            for embed in embeds :
                if embed.file is not None :
                    await game_additions_channel.send(embed=embed.embed, file=embed.file)
                else :
                    await game_additions_channel.send(embed=embed.embed)
            
            # send exceptions
            for exc in exceptions :
                await private_log_channel.send(f"{exc.message} \n<@413427677522034727>")

            # dump the games
            await Mongo_Reader.dump_games(new_games)
        
        except FailedScrapeException as e :
            await private_log_channel.send(f":warning: {e.get_message()}")
            print('fetching games failed.')
            return
    
    

    # ---- users ----
    SKIP_USER_SCRAPE = False
    if not SKIP_USER_SCRAPE :
        if SKIP_GAME_SCRAPE : return
        database_user = await Mongo_Reader.get_mongo_users()
        try :
            new_users = await CEAPIReader.get_api_users_all(database_user=database_user)

            # guild
            guild = await client.fetch_guild(guild_id)

            # get the updates
            print('starting returns')
            user_returns : tuple[list[UpdateMessage], list[CEUser]] = await thread_user_update(
                database_user, new_users, database_name, new_games, guild
            )

            # send update messages
            for update_message in user_returns[0] :
                match(update_message.location) :
                    case "userlog" : await user_log_channel.send(update_message.message)
                    case "casinolog" : await casino_log_channel.send(update_message.message)
                    case "gameadditions" : await game_additions_channel.send(update_message.message)
                    case "casino" : await casino_channel.send(update_message.message)
                    case "privatelog" : await private_log_channel.send(update_message.message)
                    
            # and dump updated users
            await Mongo_Reader.dump_users(user_returns[1])
        except FailedScrapeException as e :
            await private_log_channel.send(f":warning: {e.get_message()}")
            print('fetching users failed.')
            return
    
    # ---- curator ----

    # pull the data
    print("checking curator")
    mongo_curator_count = await Mongo_Reader.get_mongo_curator_count()
    steam_curator_count = get_curator_count()
    database_name = await Mongo_Reader.get_mongo_games()

    # if steam didn't fail and the numbers are different
    if steam_curator_count is not None and mongo_curator_count != steam_curator_count :
        print(f"curating {steam_curator_count - mongo_curator_count} update(s)")
        curator_embeds = await thread_curator(steam_curator_count - mongo_curator_count, database_name)
        for embed in curator_embeds :
            await game_additions_channel.send(embed=embed)
        
        await Mongo_Reader.dump_curator_count(steam_curator_count)
    
    else : print('no new curator updates.')
    
    print('---- loop complete. ----')
    return await private_log_channel.send(f":white_check_mark: loop complete at <t:{hm.get_unix('now')}>.")


#  _______   _    _   _____    ______              _____       _____              __  __   ______ 
# |__   __| | |  | | |  __ \  |  ____|     /\     |  __ \     / ____|     /\     |  \/  | |  ____|
#    | |    | |__| | | |__) | | |__       /  \    | |  | |   | |  __     /  \    | \  / | | |__   
#    | |    |  __  | |  _  /  |  __|     / /\ \   | |  | |   | | |_ |   / /\ \   | |\/| | |  __|  
#    | |    | |  | | | | \ \  | |____   / ____ \  | |__| |   | |__| |  / ____ \  | |  | | | |____ 
#    |_|    |_|  |_| |_|  \_\ |______| /_/    \_\ |_____/     \_____| /_/    \_\ |_|  |_| |______|

@to_thread
def thread_game_update(old_games : list[CEGame], new_games : list[CEAPIGame]) :
    "Threaded."
    return Discord_Helper.game_additions_updates(old_games=old_games, new_games=new_games)



#  _______   _    _   _____    ______              _____      _    _    _____   ______   _____  
# |__   __| | |  | | |  __ \  |  ____|     /\     |  __ \    | |  | |  / ____| |  ____| |  __ \ 
#    | |    | |__| | | |__) | | |__       /  \    | |  | |   | |  | | | (___   | |__    | |__) |
#    | |    |  __  | |  _  /  |  __|     / /\ \   | |  | |   | |  | |  \___ \  |  __|   |  _  / 
#    | |    | |  | | | | \ \  | |____   / ____ \  | |__| |   | |__| |  ____) | | |____  | | \ \ 
#    |_|    |_|  |_| |_|  \_\ |______| /_/    \_\ |_____/     \____/  |_____/  |______| |_|  \_\


@to_thread
def thread_user_update(old_data : list[CEUser], new_data : list[CEUser], old_database_name : list[CEGame],
                       new_database_name : list[CEAPIGame], guild : discord.Guild
                       ) -> tuple[list[UpdateMessage], list[CEUser]] :
    """Update the users."""
    CONSOLE_UPDATES = False
    if CONSOLE_UPDATES : print('thread began')
    messages : list[UpdateMessage] = []
    users : list[CEUser] = []
    for old_user in old_data :
        if CONSOLE_UPDATES : print('before grabbing user')
        new_user = hm.get_item_from_list(old_user.ce_id, new_data)
        if CONSOLE_UPDATES : print(f'updating user {old_user.ce_id}')

        # if the old user isn't on the site, alert someone!
        if new_user == None : 
            messages.append(UpdateMessage(
                location="privatelog",
                message=f"user not found in scrape: {old_user}"
            ))
            continue
        
        if CONSOLE_UPDATES : print('update beginning...')
        user_updates = user_update(
            user=old_user,
            site_data=new_user,
            old_database_name=old_database_name,
            new_database_name=new_database_name,
            database_user=old_data,
            guild=guild
        )
        if CONSOLE_UPDATES : print('update gotten')

        messages += user_updates[0]
        users.append(user_updates[1])
        partners : list[CEUser] = user_updates[2]

        # if some partners were sent back up, replace them!
        for partner in partners :
            index = hm.get_index_from_list(partner.ce_id, old_data)
            old_data[index] = partner

    return (messages, users)
    """
    how the fuck does this work?
    andy and brooks enter winner takes all
    andy wins
    andy's code runs, a message is sent that his thing is completed, moves from current to completed
    keep iterating...
    get to brooks
    sees he loses
    """



#   _____   _    _   _____               _______    ____    _____       _____    ____    _    _   _   _   _______ 
#  / ____| | |  | | |  __ \      /\     |__   __|  / __ \  |  __ \     / ____|  / __ \  | |  | | | \ | | |__   __|
# | |      | |  | | | |__) |    /  \       | |    | |  | | | |__) |   | |      | |  | | | |  | | |  \| |    | |   
# | |      | |  | | |  _  /    / /\ \      | |    | |  | | |  _  /    | |      | |  | | | |  | | | . ` |    | |   
# | |____  | |__| | | | \ \   / ____ \     | |    | |__| | | | \ \    | |____  | |__| | | |__| | | |\  |    | |   
#  \_____|  \____/  |_|  \_\ /_/    \_\    |_|     \____/  |_|  \_\    \_____|  \____/   \____/  |_| \_|    |_|   

def get_curator_count() -> int | None :
    "Returns the current curator count."

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


@to_thread
def thread_curator(num_updates : int, database_name : list[CEGame]) -> list[discord.Embed] :
    "Returns embed descriptions for the last `num_updates` curator posts. Max of 10."

    # adjust in case of max
    MAXIMUM_UPDATES = 10
    if num_updates > MAXIMUM_UPDATES : num_updates = MAXIMUM_UPDATES

    # set the payload and pull from the curator
    payload = {'cc' : 'us', 'l' : 'english'}
    data = requests.get('https://store.steampowered.com/curator/36185934', params=payload)

    # beautiful soupify
    soup_data = BeautifulSoup(data.text, features="html.parser")

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
    
    # and now return the embeds
    embeds : list[discord.Embed] = []
    for i in range(num_updates) :
        embed = Discord_Helper.get_game_embed(game_id=ce_ids[i], database_name=database_name)
        #TODO: change header image to hex
        embed.title = f"New curator update: {embed.title}"
        embed.add_field(name="Curator Description", value=descriptions[i])
        embeds.append(embed)
    
    return embeds
