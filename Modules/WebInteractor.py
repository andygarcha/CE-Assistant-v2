import time
import typing
from Modules import http_session
import requests
from Modules.Screenshot import Screenshot
import Modules.hm as hm


# selenium and beautiful soup stuff
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
import io
from PIL import Image

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
    start_time = hm.get_datetime('now')
    timeout = (hm.get_datetime('now') - start_time).total_seconds() > 5
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
            timeout = (hm.get_datetime('now') - start_time).total_seconds() > TIMEOUT_LIMIT
        
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



async def get_recent_curated():
    # set the payload and pull from the curator
    payload = {'cc' : 'us', 'l' : 'english'}
    session = await http_session.get_session()
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