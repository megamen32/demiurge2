import time
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import json
import requests

from chromedriver_py_auto import binary_path
def fetch_image(promtp='котик фури'):
    # Настройка пути до драйвера
    driver_path = binary_path

    driver = webdriver.Chrome(driver_path)

    # Загрузка куки из файла
    with open('cookie.json', 'r') as f:
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
    button = driver.find_element(By.XPATH,
                                 "//div[@class='mantine-7o6j5m']")
    button.click()

    # Получение текущих изображений
    existing_images = driver.find_elements(By.CSS_SELECTOR, 'div.mantine-AspectRatio-root.mantine-1ii1w80')

    # Ожидание появления нового изображения
    time.sleep(70)
    while True:
        images = driver.find_elements(By.CSS_SELECTOR, 'div.mantine-AspectRatio-root')
        if len(images) > len(existing_images):
            break
        sleep(1)

    # Извлечение URL нового изображения
    new_images = set(images).difference(existing_images)
    # Прокрутка до элемента
    files=[]
    for i,new_image in enumerate(new_images):
        try:
            # Прокрутка до элемента
            driver.execute_script("arguments[0].scrollIntoView();", new_image)
            image_url = new_image.screenshot_as_png

            # Загрузка изображения

            file = f'image_{i}.png'
            with open(file, 'wb') as f:
                f.write(image_url)
            files.append(file)
        except:
            traceback.print_exc()
            continue

    driver.quit()

    # Возврат пути до изображения
    return files



