from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Classes.CE_Game import CEGame
from Classes.OtherClasses import UpdateMessage
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
        for i, category in enumerate(hm.CATEGORIES) :
            if old_categories[i] < point_value and new_categories[i] >= point_value :
                updates.append(UpdateMessage(
                    location="log",
                    message=(f"Congratulations to <@{user.discord_id}>! " +
                             f"You have unlocked {category} {CATEGORY_ROLE_NAMES[point_index]} ({point_value}+ points)")
                ))
    # tiers
    for i in range(1, 6) : # 1, 2, 3, 4, 5
        #if    oldt1s       < 500   and    newt1s        >= 500
        if old_tiers[i - 1] < i*500 and new_tiers[i - 1] >= i * 500 :
            updates.append(UpdateMessage(
                location="log",
                message=(
                    f"Congratulations to <@{user.discord_id}>! " +
                    f"You have unlocked Tier {i} Enthusiast ({i * 500} points in Tier {i} completed games)."
                )
            ))

    return updates


async def user_update(user : CEUser, site_data : CEUser, database_name : list[CEGame]) -> tuple[list[UpdateMessage], CEUser] :
    """Takes in a user and updates it, and returns a list of things to send."""
    updates : list[UpdateMessage] = []

    original_points = user.get_total_points()
    original_completed_games = user.get_completed_games_2(database_name)
    original_rank = user.get_rank()
    original_games = user.owned_games

    user.owned_games = site_data.owned_games

    new_points = user.get_total_points()
    new_completed_games = user.get_completed_games_2(database_name)
    new_rank = user.get_rank()
    new_games = user.owned_games

    # get the role messages
    updates.append(check_category_roles(original_games, new_games, database_name, user))

    # search for newly completed games
    for game in new_completed_games :

        # if game is too low anyway, skip it
        TIER_MINIMUM = 4
        """int: The minimum tier for a game to be reported."""
        
        if not game.get_tier_num() >= TIER_MINIMUM : continue

        # check to see if it was completed before
        for old_game in original_completed_games :
            # it was completed before, so skip this
            if game.ce_id == old_game.ce_id : 
                continue
        
        updates.append(UpdateMessage(
            location="log",
            message=(f"Wow <@{user.discord_id}>! You've completed {game.game_name}, a {game.get_tier_emoji()} " + 
                     f"worth {game.get_total_points()} points {hm.get_emoji('Points')}!")
        ))

    # rank update
    if new_rank != original_rank and new_points > original_points :
        updates.append(UpdateMessage(
            location="log",
            message=(f"Congrats to <@{user.discord_id}> for ranking up from Rank {hm.get_emoji(original_rank)} " +
                     f"to Rank {hm.get_emoji(new_rank)}!")
        ))

    # check rolls
    for index, roll in enumerate(user.current_rolls) :
        # step 0: check multistage rolls
        # if the roll is multi stage AND its not in the final stage...
        # note: skip this if we're in the final stage because
        #       if it's in its final stage we can finish it out,
        #       this if statement just preps for the next one.
        if roll.is_multi_stage() and not roll.in_final_stage() and (await roll.is_won()) :
            # if we've already hit this roll before, keep moving
            if roll.due_time == None : continue

            # add the update message
            updates.append(UpdateMessage(
                location="casino",
                message=(
                    f"<@{user.discord_id}>, you've finished your current stage in {roll.roll_name}. " +
                    f"To roll your next stage, type `/solo-roll {roll.roll_name}` in <#{hm.CASINO_ID}>."
                )
            ))

            # and kill the due time
            roll.due_time = None

        elif roll.is_won() :
            # add the update message
            updates.append(UpdateMessage(
                location="log",
                message=(
                    await roll.get_win_message()
                )
            ))
            # set the completed time to now
            roll.completed_time = hm.get_unix("now")

            # add the object to completed rolls, and
            # remove it from current
            user.add_completed_roll(roll)
            del user.current_rolls[index]
        
        elif roll.is_expired() :
            # add the update message
            updates.append(UpdateMessage(
                location="casino",
                message=(
                    await roll.get_fail_message()
                )
            ))
            
            # remove this roll from current rolls
            del user.current_rolls[index]




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
    size = objective_list[len(objective_list)-2].size

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
    else:
        bottom_right_x = (bottom_right['x'] + size['width'])*2 + BORDER_WIDTH

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