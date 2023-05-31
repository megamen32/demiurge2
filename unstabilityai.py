import re
import time
import traceback
import random

from selenium import webdriver
from selenium.common import StaleElementReferenceException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import json
import requests

from chromedriver_py_auto import binary_path

from datebase import ImageUnstability


def extract_url(style_string):
    match = re.search(r'url\("(.+?)"\)', style_string)
    return match.group(1) if match else None
def fetch_image(promtp='котик фури',style='photo'):
    # Настройка пути до драйвера
    driver_path = binary_path
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1080,1080")
    manual = True

    # Загрузка куки из файла
    cookie__json = random.choice(['cookie2.json','cookie.json'])
    with open(cookie__json, 'r') as f:
        cookies = json.load(f)

    # Открытие веб-страницы




    try:
        param_sets = {
            "photo": {'genre': 'realistic', 'style': 'realistic-photo'},
            "art": {'genre': 'digital-art', 'style': 'digital-art'}
        }

        # Выбор набора параметров
        param_choice = "photo" if style=='photo' else 'art' # или "art"

        # Общие параметры для запроса
        base_params = {
            "admin": False,
            "prompt": promtp,
            "negative_prompt": "",
            "aspect_ratio": "2:3",
            "width": 512,
            "height": 768,
            "count": 1,
            "lighting_filter": "dynamic-contrast",
            "lighting_filter_strength": 20,
            "lighting_filter_color": "#242424",
            "lighting_filter_negative_color": "#ebebeb",
            "alternate_mode": False,
            "detail_pass_strength": 50,
            "saturation": 50,
            "fast": False
        }

        # Обновление общих параметров выбранным набором параметров
        base_params.update(param_sets[param_choice])

        respoce.raise_for_status()
        manual=False
    except:
        traceback.print_exc()
    new_images=set()
    if manual:
        driver = webdriver.Chrome(executable_path=driver_path, chrome_options=chrome_options)
        try:
            driver.get('https://www.unstability.ai/robots.txt')

            for cookie in cookies:
                if 'sameSite' in cookie:
                    if cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                        cookie['sameSite'] = 'None'

                # Только определенные ключи должны быть добавлены
                cookie_dict = {key: cookie[key] for key in ['name', 'value']
                               if key in cookie}
                driver.add_cookie(cookie_dict)

            driver.get('https://www.unstability.ai/')
            time.sleep(3)

            # Ввод текста
            textarea = driver.find_element(By.CSS_SELECTOR,
                                           'textarea.mantine-Input-input.mantine-Textarea-input')
            textarea.send_keys(promtp)

            # Нажатие кнопки
            try:
              select_input = driver.find_element(By.CSS_SELECTOR,
                                               'div.mantine-Input-wrapper.mantine-Select-wrapper.mantine-7c7vou input')
              driver.execute_script("arguments[0].scrollIntoView(true);", select_input);
              select_input.click()

            # Подождать пока выпадающий список не станет видимым
              wait = WebDriverWait(driver, 10)
              wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.mantine-Select-item')))


                # Найти элемент "Photo" в выпадающем списке и кликнуть по нему
              photo_option = driver.find_element(By.XPATH, '//div[contains(text(), "Photo")]')
              ActionChains(driver).move_to_element(photo_option).click().perform()
            except:
                traceback.print_exc()
            try:
                one_photo=driver.find_element(By.XPATH,'//div[@class="mantine-Group-root mantine-1dyf7sd"]//button//span[contains(text(), "1")]')
                driver.execute_script("arguments[0].scrollIntoView(true);", one_photo);
                one_photo.click()
            except:
                traceback.print_exc()
            button = driver.find_element(By.XPATH,
                                         "//div[@class='mantine-7o6j5m']")

            existing_images = set()
            for el in driver.find_elements(By.CSS_SELECTOR, 'div.mantine-AspectRatio-root > div > div > div'):
                try:
                    existing_images.add(extract_url(el.get_attribute('style')))
                except StaleElementReferenceException:
                    continue
            driver.execute_script("arguments[0].scrollIntoView(true);", button);
            button.click()

            # Получение текущих изображений

            # Ожидание появления нового изображения
            time.sleep(20)
            i = 0
            while i < 10:
                i+=1
                images = set()
                for el in driver.find_elements(By.CSS_SELECTOR, 'div.mantine-AspectRatio-root > div > div > div'):
                    try:
                        images.add(extract_url(el.get_attribute('style')))
                        driver.execute_script("arguments[0].scrollIntoView(true);", el);
                    except StaleElementReferenceException:
                        continue
                new_images = images.difference(existing_images)
                if any(new_images):
                    break
                sleep(2)
        finally:
            driver.quit()
    else:time.sleep(20)

    if not new_images:
        headers = {
            'cookie': '__Host-next-auth.csrf-token=a4f9c18bceec877af13f20c7de614b6db156f06e0550634d325e0b2098f9f0bb%7C33364ae3ff4c006cf766dc96cea162a1bd91194dff0e0488ef0a580b7c05efbf; __Secure-next-auth.callback-url=https%3A%2F%2Fwww.unstability.ai%2F; __Secure-next-auth.session-token=35b9984e-03a6-4c2d-94e5-704cf5277f53',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
        }
        data = {'items': 250}
        response = requests.post('https://www.unstability.ai/api/image_history', headers=headers, json=data)
        images = response.json()['results']

        # Получаем URL всех загруженных изображений
        new_urls = {image['images'][0]['original'] for image in images}

        # Получаем URL всех старых изображений
        old_urls = set(ImageUnstability.select(ImageUnstability.url))

        # Находим разницу между новыми и старыми URL, чтобы получить только новые изображения
        new_images = new_urls.difference(old_urls)

    # Добавляем новые изображения в базу данных
    for image_url in new_images:
        ImageUnstability.create(url=image_url, prompt=promtp)

    # Прокрутка до элемента
    files=[]
    for i,new_image in enumerate(new_images):
        try:
            # Прокрутка до элемента
            image_url = new_image

            # Загрузка изображения
            response=requests.get(new_image)
            files.append(response.content)
        except:
            traceback.print_exc()
            continue
    return files




