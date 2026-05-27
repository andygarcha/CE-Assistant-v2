import time
from typing import TYPE_CHECKING, Literal, NoReturn
from Modules import http_session
import requests
from Modules.Screenshot import Screenshot
import Modules.hm as hm
import logging

if TYPE_CHECKING:
    from Classes.CE_Game import CEGame


# selenium and beautiful soup stuff
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.common.by import By
import io
from PIL import Image

logger = logging.getLogger(__name__)

#   _____   ______   _______     _____   __  __               _____   ______
#  / ____| |  ____| |__   __|   |_   _| |  \/  |     /\      / ____| |  ____|
# | |  __  | |__       | |        | |   | \  / |    /  \    | |  __  | |__
# | | |_ | |  __|      | |        | |   | |\/| |   / /\ \   | | |_ | |  __|
# | |__| | | |____     | |       _| |_  | |  | |  / ____ \  | |__| | | |____
#  \_____| |______|    |_|      |_____| |_|  |_| /_/    \_\  \_____| |______|


def get_image(
    driver: webdriver.Chrome, 
    new_game: CEGame
) -> io.BytesIO | tuple[Literal["Assets/image_failed_v2.png"], str]:
    "Takes in the `driver` (webdriver) and the game's `ce_id` and returns an image to be screenshotted."

    # OBJECTIVE_LIMIT = 7
    # "The maximum amount of objectives to be screenshot before cropping."

    # initiate selenium
    logger.info("Attempting to screenshot game with Game ID %s", new_game.ce_id)
    try:
        url = f"https://cedb.me/game/{new_game.ce_id}/"
        driver.get(url)
    except Exception as e:
        logger.error("%s", e)
        return "Assets/image_failed_v2.png", str(e)
    logger.debug("Driver complete. Moving forward...")

    # set up variables
    start_time = hm.get_datetime("now")
    timeout = (hm.get_datetime("now") - start_time).total_seconds() > 5
    objective_list = []
    TIMEOUT_LIMIT = 8

    try:
        # give it five seconds to load the elements.
        logger.debug("Entering while...")
        while (
            len(objective_list) < 1 or not objective_list[0].is_displayed()
        ) and not timeout:
            # run this to just fully load the page...
            # html_page = driver.execute_script("return document.documentElement.innerHTML;")
            # ...and now get the list.
            logger.debug("Finding elements...")
            objective_list = driver.find_elements(
                By.CLASS_NAME, "bp4-html-table-striped"
            )
            logger.debug("find_elements() returned. Maybe looping again.")
            timeout = (
                hm.get_datetime("now") - start_time
            ).total_seconds() > TIMEOUT_LIMIT

        logger.debug("While exited!")

        # if it took longer than 5 seconds, just return the image failed image.
        if timeout:
            # TODO update this
            return ("Assets/image_failed_v2.png", "image timeout")
        logger.debug("Didn't timeout!")

        # i'm gonna let it sleep here just so that we are SURE the rest of the page loads in.

        SLEEP_LIMIT = 3
        logger.debug("sleeping for %d seconds...", SLEEP_LIMIT)
        time.sleep(SLEEP_LIMIT)
        logger.debug("sleep over.")

        logger.debug("finding elements...")
        primary_table = driver.find_element(By.CLASS_NAME, "css-c4zdq5")
        objective_list = primary_table.find_elements(
            By.CLASS_NAME, "bp4-html-table-striped"
        )
        title = driver.find_element(By.TAG_NAME, "h1")
        top_left = driver.find_element(By.CLASS_NAME, "GamePage-Header-Image").location
        title_size = title.size["width"]
        title_location = title.location["x"]

        bottom_right = objective_list[len(objective_list) - 2].location
        size = objective_list[len(objective_list) - 2].size

        header_elements = ["bp4-navbar", "tr-fadein", "css-1ugviwv"]

        BORDER_WIDTH = 15
        DISPLAY_FACTOR = 1

        top_left_x = (top_left["x"] - BORDER_WIDTH) * DISPLAY_FACTOR
        top_left_y = (top_left["y"] - BORDER_WIDTH) * DISPLAY_FACTOR
        bottom_right_y = (
            bottom_right["y"] + size["height"] + BORDER_WIDTH
        ) * DISPLAY_FACTOR

        if title_location + title_size > bottom_right["x"] + size["width"]:
            bottom_right_x = (
                title_location + title_size + BORDER_WIDTH
            ) * DISPLAY_FACTOR
        else:
            bottom_right_x = (
                bottom_right["x"] + size["width"] + BORDER_WIDTH
            ) * DISPLAY_FACTOR

        logger.debug("elements found")

        logger.debug("initializing Screenshot() object")
        ob = Screenshot(bottom_right_y)
        logger.debug("calling full_screenshot()")
        im = ob.full_screenshot(
            driver,
            save_path=r"Pictures/",
            image_name="ss.png",
            is_load_at_runtime=True,
            load_wait_time=10,
            hide_elements=header_elements,
        )
        logger.debug("screenshot returned!")
    except Exception as e:
        logger.error("%s", e)
        return ("Assets/image_failed_v2.png", f"{e}")

    logger.debug("passed try-except.")
    if isinstance(im, str):
        return ("Assets/image_failed_v2.png", "error")
    im = io.BytesIO(im)
    im_image = Image.open(im)

    SAVE_FULL_IMAGE_LOCALLY = False
    if SAVE_FULL_IMAGE_LOCALLY:
        logger.debug("saving image locally as ss.png")
        im_image.save("ss.png")

    logger.debug("cropping...")
    im_image = im_image.crop((top_left_x, top_left_y, bottom_right_x, bottom_right_y))
    logger.debug("cropping complete")

    logger.debug("bytesio ing...")
    imgByteArr = io.BytesIO()
    im_image.save(imgByteArr, format="PNG")
    final_im = imgByteArr.getvalue()
    ss = io.BytesIO(final_im)
    logger.debug("bytesio gotten.")

    SAVE_CROPPED_IMAGE_LOCALLY = False

    if SAVE_CROPPED_IMAGE_LOCALLY:
        logger.debug("saving *cropped* image locally as ss.png")
        im_image.save("ss.png")

    logger.info("Screenshot complete!")
    return ss


async def get_recent_curated() -> NoReturn:
    # set the payload and pull from the curator

    raise NotImplementedError

    payload = {"cc": "us", "l": "english"}
    session = await http_session.get_session()
    async with session.get(
        "https://store.steampowered.com/curator/36185934", params=payload
    ) as response:
        # beautiful soupify
        soup_data = BeautifulSoup(await response.text(), features="html.parser")

        # set up variables
        descriptions, ce_ids = [], []

        # get all divs
        divs = soup_data.find_all("div")

        # iterate through them
        for item in divs:
            if not isinstance(item, Tag):
                continue
            
            try:
                #classes = item.get("class", '')

                if item["class"][0] == "recommendation_readmore":
                    logger.debug("-- readmore --")
                    ce_ids.append(item.contents[0]["href"][-36:])
                    logger.debug("%s", ce_ids[-1])
                if item["class"][0] == "recommendation_desc":
                    logger.debug("-- description --")
                    descriptions.append(
                        item.string.replace("\t", "")
                        .replace("\r", "")
                        .replace("\n", "")
                    )
                    logger.debug("%s", descriptions[-1])
            except Exception as e:
                logger.exception(e)
                continue
        return ce_ids, descriptions


#   _____   _    _   _____               _______    ____    _____       _____    ____    _    _   _   _   _______
#  / ____| | |  | | |  __ \      /\     |__   __|  / __ \  |  __ \     / ____|  / __ \  | |  | | | \ | | |__   __|
# | |      | |  | | | |__) |    /  \       | |    | |  | | | |__) |   | |      | |  | | | |  | | |  \| |    | |
# | |      | |  | | |  _  /    / /\ \      | |    | |  | | |  _  /    | |      | |  | | | |  | | | . ` |    | |
# | |____  | |__| | | | \ \   / ____ \     | |    | |__| | | | \ \    | |____  | |__| | | |__| | | |\  |    | |
#  \_____|  \____/  |_|  \_\ /_/    \_\    |_|     \____/  |_|  \_\    \_____|  \____/   \____/  |_| \_|    |_|


async def get_curator_count() -> int | None:
    "Returns the current curator count. Uses `requests` but I don't care!"

    raise NotImplementedError

    # set the payload and pull from the curator
    payload = {"cc": "us", "l": "english"}
    data = requests.get(
        "https://store.steampowered.com/curator/36185934", params=payload
    )

    # beautiful soupify
    soup_data = BeautifulSoup(data.text, features="html.parser")

    # get all spans
    spans = soup_data.find_all("span")

    # iterate through them
    for item in spans:
        try:
            if item["id"] == "Recommendations_total":
                return int(item.string)
        except Exception as e:
            logger.exception(e)
            continue

    # return None if this fails.
    return None
