import os
from pathlib import Path
import time

from PIL import Image
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement



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

    def full_screenshot(self, driver: WebDriver, save_path: str = '', image_name: str = 'selenium_full_screenshot.png',
                        hide_elements: list = None, is_load_at_runtime: bool = False, load_wait_time: int = 5) -> str:
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
        #image_name = os.path.abspath(save_path + '/' + image_name)
        SHOW_CONSOLE_UPDATES = False
        if SHOW_CONSOLE_UPDATES : print('1')
        if SHOW_CONSOLE_UPDATES : print(save_path)
        if SHOW_CONSOLE_UPDATES : print('image')
        if SHOW_CONSOLE_UPDATES : print(image_name)

        # final_page_height = 0
        original_size = driver.get_window_size()
        if SHOW_CONSOLE_UPDATES : print('2')

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

        self.hide_elements(driver, hide_elements)
        if SHOW_CONSOLE_UPDATES : print('3')

        if isinstance(driver, webdriver.Ie):
            required_width = driver.execute_script('return document.body.parentNode.scrollWidth')
            if SHOW_CONSOLE_UPDATES : print('4')
            driver.set_window_size(required_width, self.fph)
            if SHOW_CONSOLE_UPDATES : print('5')
            driver.save_screenshot(image_name)
            if SHOW_CONSOLE_UPDATES : print('6')
            driver.set_window_size(original_size['width'], original_size['height'])
            if SHOW_CONSOLE_UPDATES : print('7')
            return image_name

        else:
            if SHOW_CONSOLE_UPDATES : print('8')
            total_width = driver.execute_script("return document.body.offsetWidth")
            if SHOW_CONSOLE_UPDATES : print('9')
            total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
            if SHOW_CONSOLE_UPDATES : print('10')
            viewport_width = driver.execute_script("return document.body.clientWidth")
            if SHOW_CONSOLE_UPDATES : print('11')
            viewport_height = driver.execute_script("return window.innerHeight")
            if SHOW_CONSOLE_UPDATES : print('12')
            driver.execute_script("window.scrollTo(0, 0)")
            if SHOW_CONSOLE_UPDATES : print('13')
            time.sleep(3)
            if SHOW_CONSOLE_UPDATES : print('14')
            rectangles = []

            i = 0
            while i < total_height:
                if SHOW_CONSOLE_UPDATES : print('while')
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
            stitched_image = Image.new('RGB', (total_width, total_height))
            if SHOW_CONSOLE_UPDATES : print('while broken')
            previous = None
            part = 0

            for rectangle in rectangles:
                if SHOW_CONSOLE_UPDATES : print('for')
                if previous is not None:
                    if SHOW_CONSOLE_UPDATES : print('prev not none')
                    driver.execute_script("window.scrollTo({0}, {1})".format(rectangle[0], rectangle[1]))
                    time.sleep(10)
                if SHOW_CONSOLE_UPDATES : print('broke if 1')

                self.hide_elements(driver, hide_elements)
                if SHOW_CONSOLE_UPDATES : print('15')

                file_name = "part{0}.png".format(part)
                path = Path("/CE-Assistant/part{0}.png".format(part))
                if SHOW_CONSOLE_UPDATES : print('16')
                if SHOW_CONSOLE_UPDATES : print(file_name)
                if SHOW_CONSOLE_UPDATES : print(str(path))

                ss = driver.get_screenshot_as_png()
                if SHOW_CONSOLE_UPDATES : print('gotcha >:)')
                return ss
                print("ss")
                path.parent.mkdir(parents=True, exist_ok=True)
                print('makedirs')
                with open(path, "wb") as ss_file:
                    print('with open')
                    ss_file.write(ss)
                    print("Svreenshot saved")
                #print('directory: ' + str(os.listdir('/home/andrewgarcha/CE-Assistant')))
                print('17')
                screenshot = Image.open(path)
                print('18')

                if rectangle[1] + viewport_height > total_height:
                    print('if2')
                    offset = (rectangle[0], total_height - viewport_height)
                else:
                    print('else2')
                    offset = (rectangle[0], rectangle[1])
                print('broke if 2') 

                stitched_image.paste(screenshot, offset)
                print('19')
                del screenshot
                print('20')
                os.remove(path)
                print('21')
                part = part + 1
                print('22')
                previous = rectangle
                print('23')
            if SHOW_CONSOLE_UPDATES : print('for loop broken')
            save_path = Path("/CE-Assistant/Pictures/" + image_name)
            if SHOW_CONSOLE_UPDATES : print('24')
            if SHOW_CONSOLE_UPDATES : print(save_path)
            stitched_image.save(save_path)
            if SHOW_CONSOLE_UPDATES : print('25')
            return save_path

    def get_element(self, driver: WebDriver, element: WebElement, save_path: str, image_name: str = 'cropped_screenshot.png', hide_elements: list = None) -> str:
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
        image = self.full_screenshot(driver, save_path=save_path, image_name='clipping_shot.png', hide_elements=hide_elements)
        # Need to scroll to top, to get absolute coordinates
        driver.execute_script("window.scrollTo(0, 0)")
        location = element.location
        size = element.size
        x = location['x']
        y = location['y']
        w = size['width']
        h = size['height']
        width = x + w
        height = y + h

        image_object = Image.open(image)
        image_object = image_object.crop((int(x), int(y), int(width), int(height)))
        img_url = os.path.abspath(os.path.join(save_path, image_name))
        image_object.save(img_url)

        image_object.close()
        os.remove(image)

        return img_url

    @staticmethod
    def hide_elements(driver: WebDriver, elements: list) -> None:
        if elements is not None:
            try:
                for e in elements:
                    js_script = '''
                        element1 = document.getElementsByClassName('{}');
                        element1[0].style.display = 'none';
                        '''.format(e)
                    driver.execute_script(js_script)
            except Exception as Error:
                print('Error : ', str(Error))
