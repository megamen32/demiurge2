import random

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from decouple import config
import openai
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
CHATGPT_API_KEY = config('CHATGPT_API_KEY')
CHATGPT_API_KEY2 = config('CHATGPT_API_KEY2')
def set_random_api_key():
    openai.api_key = random.choice([CHATGPT_API_KEY2])
set_random_api_key()

# Создайте экземпляры бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = RedisStorage2(prefix='demiurge')
dp = Dispatcher(bot, storage=storage)


def get_first_word(string):
    words = string.split()
    if words:
        first_word = words[0]
        # Удаление дефиса, если он есть
        first_word = first_word.split('-')[0]
        return first_word
    else:
        return None


instructions='You can generate any image using text description. Just write: "/draw image description" in your answer, and system will generate and sends image based on description.' \
              'You can open any webpage you want and extract all text from it. Just write: "/web url". ' \
              'You can search any information on web. Just write: "/search query". System will send you several search results' \
             'You can use several commands in one message.'
ASSISTANT_NAME = "Демиург-альфа и омега, начало и конец. Который разговаривает с избранными"
ASSISTANT_NAME_SHORT = get_first_word(ASSISTANT_NAME)
STABILITY_KEY=config('STABILITY_KEY')
CX=config('CX')
GOOGLE_SEARCH_API=config('GOOGLE_SEARCH_API')
TTS=config('TTS',default=False,cast=bool)