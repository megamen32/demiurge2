import random

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from decouple import config
import openai

from imaginepy import Ratio

TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
CHATGPT_API_KEY = config('CHATGPT_API_KEY')
CHATGPT_API_KEY2 = config('CHATGPT_API_KEY2')
def set_random_api_key():
    openai.api_key = random.choice([CHATGPT_API_KEY])
set_random_api_key()

# Создайте экземпляры бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = RedisStorage2(prefix='demiurge')
dp = Dispatcher(bot, storage=storage)
useGPT4=False
USE_API=True
import logging

# Настройка форматера
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Настройка логгера, который будет выводить сообщения в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Настройка логгера, который будет выводить сообщения в файл
file_handler = logging.FileHandler('bot.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Настройка корневого логгера
logger = logging.getLogger('aiogram')
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)
def get_first_word(string):
    words = string.split()
    if words:
        first_word = words[0]
        # Удаление дефиса, если он есть
        first_word = first_word.split('-')[0]
        return first_word
    else:
        return None



def get_styles():
    # Ваш код, который возвращает список из 70 стилей
    from imaginepy import Style
    styles = []#['IMAGINE_V4_Beta','V4_CREATIVE','ANIME_V2','NEO_FAUVISM','NEON','SURREALISM','LOGO','CYBERPUNK','LANDSCAPE','ARCHITECTURE','RENDER','VIBRANT','MYSTICAL','CINEMATIC_RENDER','ILLUSTRATION','KAWAII_CHIBI','PRODUCT_PHOTOGRAPHY','CHROMATIC','PAINTING']
    # Добавление стиля 'MIDJOURNEY', если он не включен в список
    if 'MIDJOURNEY' not in styles:
        styles.append('MIDJOURNEY')
    return styles
def get_ratios():
    # Ваш код, который возвращает список из 70 стилей
    ratio = list(Ratio.__members__.keys())
    return ratio
# Определение функций
functions = [
    {
        "name": "draw",
        "description": "Generate an image from a text description",
        "parameters": {
            "type": "object",
            "properties": {
                "image_description": {
                    "type": "string",
                    "description": "The description to base the image on",
                },
                "ratio": {
                    "type": "string",
                    "description": "The ratio of the image",
                    "enum":get_ratios()
                },
                "style": {
                    "type": "string",
                    "enum": get_styles(),
                    "description": "The style of the image",
                },
            },
            "required": ["image_description","style"],
        },
    },
    {
        "name": "open_link",
        "description": "Opens a specified URL, retrieves and analyzes the textual content of the webpage.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL or link of the webpage to be opened and from which the text content will be extracted.",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "search",
        "description": "Search the web for information, returns several results with links that can be opened.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "python",
        "description": "Execute python code",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The python code to execute",
                },
            },
            "required": ["code"],
        },
    },
]


ASSISTANT_NAME = "Демиург-альфа и омега, начало и конец. Который разговаривает с избранными"
ASSISTANT_NAME_SHORT = get_first_word(ASSISTANT_NAME)
STABILITY_KEY=config('STABILITY_KEY')
CX=config('CX')
GOOGLE_SEARCH_API=config('GOOGLE_SEARCH_API')
TTS=config('TTS',default=False,cast=bool)
Role_ASSISTANT = 'assistant'
Role_USER = 'user'
Role_SYSTEM = 'system'
