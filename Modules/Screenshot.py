import io
import os
import time

from PIL import Image
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

import logging

logger = logging.getLogger(__name__)


class Screenshot:
    """
    #================================================================================================================#
    #                                          Class: Screenshot                                                     #
    #                                    Purpose: Capture full and element screenshot using Selenium                #
    #                                    a) Capture full webpage as image                                            #
    #                                    b) Capture element screenshots                                              #
    #================================================================================================================#
    """

    def __init__(self, final_page_height):
        """
        Usage:
            N/A
        Args:
            N/A
        Returns:
            N/A
        Raises:
            N/A
        """
        self.fph = final_page_height
        pass

    def full_screenshot(
        self,
        driver: WebDriver,
        save_path: str = "",
        image_name: str = "selenium_full_screenshot.png",
        hide_elements: list | None = None,
        is_load_at_runtime: bool = False,
        load_wait_time: int = 5,
    ) -> bytes | str:
        """
        Take full screenshot of web page
        Args:
            driver: Web driver instance
            save_path: Path where to save image
            image_name: The name of the image
            hide_elements: List of Xpath elements to hide from web page
            is_load_at_runtime: Page loads at runtime
            load_wait_time: The wait time while loading full screen

        Returns:
            str: The image path
        """
        # image_name = os.path.abspath(save_path + '/' + image_name)
        logger.debug("1")
        logger.debug("save_path=%s", save_path)
        logger.debug("image_name=%s", image_name)

        # final_page_height = 0
        original_size = driver.get_window_size()
        logger.debug("2")

        # if is_load_at_runtime:
        #     while True:
        #         page_height = driver.execute_script("return document.body.scrollHeight")
        #         print(page_height)
        #         if page_height != final_page_height and final_page_height <= 10000:
        #             driver.execute_script("window.scrollTo(0, {})".format(page_height))
        #             time.sleep(load_wait_time)
        #             final_page_height = page_height
        #         else:
        #             break

        if hide_elements is not None:
            self.hide_elements(driver, hide_elements)
            logger.debug("3")

        if isinstance(driver, webdriver.Ie):
            required_width = driver.execute_script(
                "return document.body.parentNode.scrollWidth"
            )
            logger.debug("4")
            driver.set_window_size(required_width, self.fph)
            logger.debug("5")
            driver.save_screenshot(image_name)
            logger.debug("6")
            driver.set_window_size(original_size["width"], original_size["height"])
            logger.debug("7")
            return image_name

        else:
            total_width = driver.execute_script("return document.body.offsetWidth")
            total_height = driver.execute_script(
                "return document.body.parentNode.scrollHeight"
            )
            viewport_width = driver.execute_script("return document.body.clientWidth")
            viewport_height = driver.execute_script("return window.innerHeight")
            # Already at scroll position 0 from the page load the caller already
            # waited on, so there's nothing new to settle here.
            driver.execute_script("window.scrollTo(0, 0)")
            rectangles = []

            i = 0
            while i < total_height:
                logger.debug("while")
                ii = 0
                top_height = i + viewport_height
                if top_height > total_height:
                    top_height = total_height
                while ii < total_width:
                    top_width = ii + viewport_width
                    if top_width > total_width:
                        top_width = total_width
                    rectangles.append((ii, i, top_width, top_height))
                    ii = ii + viewport_width
                i = i + viewport_height
            stitched_image = Image.new("RGB", (total_width, total_height))
            logger.debug("while broken")
            previous = None
            part = 0

            for rectangle in rectangles:
                if previous is not None:
                    driver.execute_script(
                        "window.scrollTo({0}, {1})".format(rectangle[0], rectangle[1])
                    )
                    time.sleep(2)

                if hide_elements is not None:
                    self.hide_elements(driver, hide_elements)

                tile_bytes = driver.get_screenshot_as_png()
                tile = Image.open(io.BytesIO(tile_bytes))

                if rectangle[1] + viewport_height > total_height:
                    offset = (rectangle[0], total_height - viewport_height)
                else:
                    offset = (rectangle[0], rectangle[1])

                stitched_image.paste(tile, offset)
                del tile
                part = part + 1
                previous = rectangle
            logger.debug("finished capturing %d tiles", part)

            output = io.BytesIO()
            stitched_image.save(output, format="PNG")
            return output.getvalue()

    def get_element(
        self,
        driver: WebDriver,
        element: WebElement,
        save_path: str,
        image_name: str = "cropped_screenshot.png",
        hide_elements: list | None = None,
    ) -> str:
        """
        Usage:
            Capture element screenshot as an image
        Args:
            driver: Web driver instance
            element: The element on the web page to be captured
            save_path: Path where to save image
            image_name: The name of the image
            hide_elements: List of Xpath elements to hide from web page
        Returns:
            img_url(str): The image path
        Raises:
            N/A
        """
        image = self.full_screenshot(
            driver,
            save_path=save_path,
            image_name="clipping_shot.png",
            hide_elements=hide_elements,
        )
        # Need to scroll to top, to get absolute coordinates
        driver.execute_script("window.scrollTo(0, 0)")
        location = element.location
        size = element.size
        x = location["x"]
        y = location["y"]
        w = size["width"]
        h = size["height"]
        width = x + w
        height = y + h

        image_object = Image.open(io.BytesIO(image))
        image_object = image_object.crop((int(x), int(y), int(width), int(height)))
        img_url = os.path.abspath(os.path.join(save_path, image_name))
        image_object.save(img_url)

        image_object.close()

        return img_url

    @staticmethod
    def hide_elements(driver: WebDriver, elements: list) -> None:
        if elements is not None:
            try:
                for e in elements:
                    js_script = """
                        element1 = document.getElementsByClassName('{}');
                        element1[0].style.display = 'none';
                        """.format(e)
                    driver.execute_script(js_script)
            except Exception as Error:
                logger.error("Error : %s", str(Error))
