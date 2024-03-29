import httpx
import openai.version
from aiogram import Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from decouple import config

from imaginepy import Ratio
from requests.auth import HTTPBasicAuth


from loggerbot import LoggingBot

TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
CHATGPT_API_KEY = config('CHATGPT_API_KEY')
CHATGPT_API_KEY2 = config('CHATGPT_API_KEY2')


# Создайте экземпляры бота и диспетчера
bot = LoggingBot(token=TELEGRAM_BOT_TOKEN)
storage = RedisStorage2(prefix='demiurge')
dp = Dispatcher(bot, storage=storage)
admins_ids=[540308572]
useGPT4=False
USE_API=True
from yookassa import Configuration
Configuration.configure( config('YOOMONEY_ACCOUNT_ID'), config('YOOMONEY_SECRET_KEY'))
proxy='http://168.80.203.204:8000'
if int(openai.version.VERSION[0])>0:
    from openai import AsyncOpenAI
    openai_client=AsyncOpenAI(api_key=CHATGPT_API_KEY,http_client=httpx.AsyncClient(proxies={'http://':proxy,'https://':proxy}))

SERVER_URL=config('SERVER_URL')
AUTH=HTTPBasicAuth(config("USERNAME"),config("PASSWORD"))

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
    styles = ['CREATIVE','ANIME','NEO FAUVISM','SURREALISM','LOGO','CYBERPUNK','LANDSCAPE','ARCHITECTURE','RENDER','VIBRANT','MYSTICAL','CINEMATIC RENDER','ILLUSTRATION','KAWAII CHIBI','PRODUCT PHOTOGRAPHY','CHROMATIC','PAINTING','REALISTIC']
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
                    #"enum": get_styles(),
                    "description": "The textual name of style to draw picture",
                },
            },
            "required": ["image_description","style"],
        },
    },
    {
        "name": "open_link",
        "description": "Opens a specified URL, retrieves and analyzes the textual content of the webpage. Also working for youtube video urls",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the webpage to be opened and from which the text content will be extracted.",
                },
                "question": {
                    "type": "string",
                    "description": "The question to extract from page. must be in webpage langauge",
                },
            },
            "required": ["url",'question'],
        },
    },
    {
        "name": "search",
        "description": "Search the google with query, return list of urls,that can be opened to gain more info.",
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
Role_FUNCTION = 'function'
