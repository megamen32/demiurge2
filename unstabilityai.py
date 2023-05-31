import re
import time
import traceback

from selenium import webdriver
from selenium.common import StaleElementReferenceException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import json
import requests

from chromedriver_py_auto import binary_path


def extract_url(style_string):
    match = re.search(r'url\("(.+?)"\)', style_string)
    return match.group(1) if match else None
def fetch_image(promtp='котик фури'):
    # Настройка пути до драйвера
    driver_path = binary_path

    driver = webdriver.Chrome(driver_path)

    # Загрузка куки из файла
    with open('cookie2.json', 'r') as f:
        cookies = json.load(f)

    # Открытие веб-страницы
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
            except StaleElementReferenceException:
                continue
        new_images = images.difference(existing_images)
        if any(new_images):
            break
        sleep(2)

    # Извлечение URL нового изображения

    # Прокрутка до элемента
    files=[]
    for i,new_image in enumerate(new_images):
        try:
            # Прокрутка до элемента
            image_url = new_image

            # Загрузка изображения
            response=requests.get(new_image)
            file = f'image_{i}.png'
            with open(file, 'wb') as f:
                f.write(response.content)
            files.append(file)
        except:
            traceback.print_exc()
            continue

    driver.quit()

    # Возврат пути до изображения
    return files



