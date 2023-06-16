import random

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from decouple import config
import openai
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


instructions = 'As an AI, you have access to multiple functionalities that you can execute:\n' \
               '1) To generate an image from a text description, you should use the command: "draw("image description")". The system will then generate and send an image based on the description you provided.\n' \
               '2) To extract text from any webpage, you should use the command: "web("url")".\n' \
               '3) To search for information on the web, you should use the command: "search("query")". The system will provide search results based on the query you provided.\n' \
               '4) To execute any python code, you should use the format: """python code""".\n' \
               'Remember, you can use several commands in one message.'
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
            },
            "required": ["image_description"],
        },
    },
    {
        "name": "web",
        "description": "Extract text from a webpage",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the webpage to extract text from",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "search",
        "description": "Search the web for information",
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
        "name": "execute_python_code",
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
