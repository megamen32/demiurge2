import asyncio
import os
import traceback

from aiogram import Bot, types, Dispatcher, executor
import os
from aiogram import Bot, types, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import openai


# Установите ваши токены здесь
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.types import BotCommand
import speech_recognition as sr
from config import TELEGRAM_BOT_TOKEN, CHATGPT_API_KEY, dp, bot

# Установите ваш ключ OpenAI
openai.api_key=CHATGPT_API_KEY

# Максимальное количество сообщений для сохранения
MAX_HISTORY = 4

def get_first_word(string):
    words = string.split()
    if words:
        first_word = words[0]
        # Удаление дефиса, если он есть
        first_word = first_word.split('-')[0]
        return first_word
    else:
        return None

ASSISTANT_NAME = "Демиург-альфа и омега, начало и конец. Который разговаривает с избранными"
ASSISTANT_NAME_SHORT = get_first_word(ASSISTANT_NAME)
@dp.message_handler(commands=['promt'])
async def change_role(message: types.Message):
    global ASSISTANT_NAME
    global ASSISTANT_NAME_SHORT
    text=message.text.split(' ',1)[-1]
    ASSISTANT_NAME=text
    ASSISTANT_NAME_SHORT = get_first_word(ASSISTANT_NAME)
    await message.reply(f'Now i am {ASSISTANT_NAME_SHORT}:\n'+text)

@dp.message_handler(commands=['history'])
async def show_history(message: types.Message):
    m = await message.reply('...')
    try:
        user_id = message.chat.id
        text = await get_history(user_id)
        if text is None:
            text = 'История пуста'
        await m.edit_text(text=text)
    except:
        traceback.print_exc()
        await m.edit_text('Не удалось получить ответ от Демиурга')


async def get_history(user_id):
    user_data = await dp.storage.get_data(chat=user_id)
    if 'history' in user_data:
        history = user_data['history']
        history_text = ''
        for msg in history:
            role = 'Пользователь' if msg['role'] == 'user' else ASSISTANT_NAME_SHORT
            history_text += f'{role}: {msg["content"]}\n'
        text = history_text
    else:
        text = None
    return text


@dp.message_handler(commands=['clear'])
async def clear_history(message: types.Message):
    msg = await message.reply('...')
    try:
        user_id = message.chat.id
        user_data = await dp.storage.get_data(chat=user_id)

        if 'history' in user_data and user_data['history']:
            user_data['history'] = []
            await dp.storage.set_data(chat=user_id, data=user_data)
        await msg.edit_text('История диалога очищена.')
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось очистить историю диалога.')

@dp.message_handler(commands=['summarize'])
async def summarize_history(message: types.Message):
    msg = await message.reply('...')
    try:

        user_id = message.chat.id
        summary = await get_summary( user_id)
        if summary is not None:
            user_data = await dp.storage.get_data(chat=user_id)
            # Замените историю диалога суммарным представлением
            user_data['history'] = [{"role": "assistant", "content": summary}]
            await dp.storage.set_data(chat=user_id, data=user_data)

            await msg.edit_text( text=f"История диалога была суммирована:\n{summary}")
        else:
            await msg.edit_text( text="История диалога пуста.")
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось получить ответ от Демиурга')


async def get_summary( user_id):
    history_text = await get_history(user_id)
    if history_text is not None:
        # Сформируйте запрос на суммирование к GPT-3.5
        chat_response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{'role': 'system', 'content': f"Пожалуйста, суммируйте следующий текст:\n{history_text}"}]
        )
        summary = chat_response['choices'][0]['message']['content']
    return summary


@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    msg = await message.reply('...')
    try:
        user_id = message.chat.id
        user_data = await dp.storage.get_data(chat=user_id)

        # Получите файл голосового сообщения
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

        # Скачайте аудиофайл
        await bot.download_file(file_path, destination=f"{file_id}.ogg")

        text = await asyncio.get_running_loop().run_in_executor(None, recognize,(file_id))
        message.text=text
        asyncio.create_task( msg.edit_text(f'Вы сказали:\n{text}'))
        return await handle_message(message)
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось получить ответ от Демиурга')


def recognize(file_id):
    # Преобразование аудиофайла в формат WAV для распознавания речи
    os.system(f"ffmpeg -i {file_id}.ogg {file_id}.wav")
    # Используйте SpeechRecognition для преобразования аудио в текст
    recognizer = sr.Recognizer()
    with sr.AudioFile(f"{file_id}.wav") as source:
        audio = recognizer.record(source)
    text = recognizer.recognize_google(audio, language='ru-RU')
    os.remove(f'{file_id}.ogg')
    os.remove(f'{file_id}.wav')
    return text


@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_message(message: types.Message):

    msg=await message.reply('...')
    try:
        user_id = message.chat.id
        user_data = await dp.storage.get_data(chat=user_id)

        # Если история пользователя не существует, создайте новую
        if 'history' not in user_data:
            user_data['history'] = []

        # Добавьте сообщение пользователя в историю
        user_data['history'].append({"role": "user", "content": f'{message.from_user.full_name or message.from_user.username}:{message.text}'})

        # Сформируйте ответ от GPT-3.5
        chat_response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{'role': 'system', 'content': ASSISTANT_NAME}] + user_data['history']
        )

        # Добавьте ответ бота в историю
        user_data['history'].append({"role": "assistant", "content": f"{ASSISTANT_NAME_SHORT}:{chat_response['choices'][0]['message']['content']}"})

        # Отправьте ответ пользователю
        await msg.edit_text(chat_response['choices'][0]['message']['content'])

        # Ограничьте историю MAX_HISTORY сообщениями
        if len(user_data['history']) > MAX_HISTORY:
            summary = await get_summary(user_id)
            asyncio.create_task(message.answer('Короче:\n' + summary))
            # Замените историю диалога суммарным представлением
            user_data['history'] = [{"role": "assistant", "content": summary}]

        await dp.storage.set_data(chat=user_id, data=user_data)
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось получить ответ от Демиурга')

async def on_startup(dp):
    # Установите здесь ваши команды
    await bot.set_my_commands([
        BotCommand("history", "Показать историю диалога"),
        BotCommand("summarize", "Суммировать историю диалога"),
        BotCommand("clear", "Clear историю диалога"),
        BotCommand("promt", "Edit gpt start promt"),
        # Добавьте здесь любые дополнительные команды
    ])

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)