from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from decouple import config
import openai
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
CHATGPT_API_KEY = config('CHATGPT_API_KEY')
openai.api_key = CHATGPT_API_KEY

# Создайте экземпляры бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = RedisStorage2()
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


instructions='если меня просят нарисовать что-то, то я отвечаю "/draw [describe image on english]"'
ASSISTANT_NAME = "Демиург-альфа и омега, начало и конец. Который разговаривает с избранными"
ASSISTANT_NAME_SHORT = get_first_word(ASSISTANT_NAME)
