import io
import logging
import time

from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By

from Modules.Screenshot import Screenshot
from pi_screenshot_service import objective_diff

logger = logging.getLogger(__name__)

TIMEOUT_LIMIT_SECONDS = 8
RENDER_SLEEP_SECONDS = 3
BORDER_WIDTH = 15

WARMUP_GAME_ID = "1e866995-6fec-452e-81ba-1e8f8594f4ea"  # Celeste
WARMUP_SLEEP_SECONDS = 2


def build_driver() -> webdriver.Chrome:
    "Builds a headless Chrome driver suitable for running unattended on the Pi."
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,2000")
    return webdriver.Chrome(options=options)


def _warm_up_browser(driver: webdriver.Chrome) -> None:
    """Loads a throwaway game page before the real capture.

    Each capture gets a brand-new Chrome profile, so the header's color
    extraction (a separate cross-origin image fetch) always races a cold CDN
    connection and loses. Eating that cold fetch here, on a page we don't
    screenshot, means the real capture's fetch is warm.
    """
    driver.get(f"https://cedb.me/game/{WARMUP_GAME_ID}/")
    time.sleep(WARMUP_SLEEP_SECONDS)


def capture_game_screenshot(
    driver: webdriver.Chrome, game_id: str
) -> tuple[bytes, dict[str, float]]:
    "Navigates to the game page and returns a cropped PNG of its objectives table, plus a per-phase timing breakdown."
    timings: dict[str, float] = {}

    phase_start = time.monotonic()
    _warm_up_browser(driver)
    timings["warmup"] = time.monotonic() - phase_start

    phase_start = time.monotonic()
    url = f"https://cedb.me/game/{game_id}/"
    driver.get(url)

    start_time = time.monotonic()
    objective_list = []
    while not objective_list or not objective_list[0].is_displayed():
        if time.monotonic() - start_time > TIMEOUT_LIMIT_SECONDS:
            raise TimeoutError(f"page for game {game_id} did not render in time")
        objective_list = driver.find_elements(By.CLASS_NAME, "bp4-html-table-striped")
    timings["page_load"] = time.monotonic() - phase_start

    phase_start = time.monotonic()
    time.sleep(RENDER_SLEEP_SECONDS)

    primary_table = driver.find_element(By.CLASS_NAME, "css-c4zdq5")
    objective_list = primary_table.find_elements(
        By.CLASS_NAME, "bp4-html-table-striped"
    )
    title = driver.find_element(By.TAG_NAME, "h1")
    top_left = driver.find_element(By.CLASS_NAME, "GamePage-Header-Image").location
    title_size = title.size["width"]
    title_location = title.location["x"]

    bottom_right = objective_list[-2].location
    size = objective_list[-2].size

    top_left_x = max(top_left["x"] - BORDER_WIDTH, 0)
    top_left_y = max(top_left["y"] - BORDER_WIDTH, 0)
    bottom_right_y = bottom_right["y"] + size["height"] + BORDER_WIDTH

    if title_location + title_size > bottom_right["x"] + size["width"]:
        bottom_right_x = title_location + title_size + BORDER_WIDTH
    else:
        bottom_right_x = bottom_right["x"] + size["width"] + BORDER_WIDTH
    timings["render"] = time.monotonic() - phase_start

    phase_start = time.monotonic()
    screenshot = Screenshot(bottom_right_y)
    image_bytes = screenshot.full_screenshot(
        driver,
        is_load_at_runtime=True,
        load_wait_time=10,
        hide_elements=["bp4-navbar", "tr-fadein", "css-1ugviwv"],
    )
    if isinstance(image_bytes, str):
        raise RuntimeError(
            f"screenshot capture failed for game {game_id}: {image_bytes}"
        )

    image = Image.open(io.BytesIO(image_bytes))
    image = image.crop((top_left_x, top_left_y, bottom_right_x, bottom_right_y))

    output = io.BytesIO()
    image.save(output, format="PNG")
    timings["screenshot"] = time.monotonic() - phase_start

    return output.getvalue(), timings


def capture_objective_diff(
    driver: webdriver.Chrome,
    game_id: str,
    objective_id: str,
    old_text: str,
    new_text: str,
) -> tuple[bytes, dict[str, float]]:
    "Navigates to the game page, highlights one changed objective field, and returns a cropped PNG of just that objective's row."
    timings: dict[str, float] = {}

    phase_start = time.monotonic()
    _warm_up_browser(driver)
    timings["warmup"] = time.monotonic() - phase_start

    phase_start = time.monotonic()
    game_json = objective_diff.fetch_game_json(game_id)
    objective_name = objective_diff.find_objective_name(game_json, objective_id)
    if objective_name is None:
        raise ValueError(f"objective {objective_id} not found for game {game_id}")
    timings["api_lookup"] = time.monotonic() - phase_start

    phase_start = time.monotonic()
    url = f"https://cedb.me/game/{game_id}/"
    driver.get(url)

    start_time = time.monotonic()
    objective_list = []
    while not objective_list or not objective_list[0].is_displayed():
        if time.monotonic() - start_time > TIMEOUT_LIMIT_SECONDS:
            raise TimeoutError(f"page for game {game_id} did not render in time")
        objective_list = driver.find_elements(By.CLASS_NAME, "bp4-html-table-striped")
    timings["page_load"] = time.monotonic() - phase_start

    phase_start = time.monotonic()
    time.sleep(RENDER_SLEEP_SECONDS)

    row_xpath = objective_diff.build_diff_row_xpath(objective_name)
    row = driver.find_element(By.XPATH, row_xpath)

    highlighted = objective_diff.inject_diff_highlight(driver, row, old_text, new_text)
    if not highlighted:
        raise ValueError(
            f"could not locate text {new_text!r} in objective {objective_id!r} to highlight"
        )
    timings["highlight"] = time.monotonic() - phase_start

    phase_start = time.monotonic()
    location = row.location
    size = row.size
    top_left_x = max(location["x"] - BORDER_WIDTH, 0)
    top_left_y = max(location["y"] - BORDER_WIDTH, 0)
    bottom_right_x = location["x"] + size["width"] + BORDER_WIDTH
    bottom_right_y = location["y"] + size["height"] + BORDER_WIDTH

    screenshot = Screenshot(bottom_right_y)
    image_bytes = screenshot.full_screenshot(
        driver,
        is_load_at_runtime=True,
        load_wait_time=10,
        hide_elements=["bp4-navbar", "tr-fadein", "css-1ugviwv"],
    )
    if isinstance(image_bytes, str):
        raise RuntimeError(f"screenshot capture failed for game {game_id}: {image_bytes}")

    image = Image.open(io.BytesIO(image_bytes))
    image = image.crop((top_left_x, top_left_y, bottom_right_x, bottom_right_y))

    output = io.BytesIO()
    image.save(output, format="PNG")
    timings["screenshot"] = time.monotonic() - phase_start

    return output.getvalue(), timings
