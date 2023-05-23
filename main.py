import functools
import tempfile

from gtts import gTTS
import os
from aiogram import types, executor
import openai


# Установите ваши токены здесь
from aiogram.types import BotCommand
import speech_recognition as sr

import config
from config import TELEGRAM_BOT_TOKEN, CHATGPT_API_KEY, dp, get_first_word, ASSISTANT_NAME, ASSISTANT_NAME_SHORT

# Установите ваш ключ OpenAI
openai.api_key=CHATGPT_API_KEY

# Максимальное количество сообщений для сохранения
MAX_HISTORY = 2048


@dp.message_handler(commands=['promt'])
async def change_role(message: types.Message):
    text=message.text.split(' ',1)[-1]
    config.ASSISTANT_NAME =text
    config.ASSISTANT_NAME_SHORT = get_first_word(config.ASSISTANT_NAME)
    await message.reply(f'Now i am {config.ASSISTANT_NAME_SHORT}:\n' + text)

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
            role = 'Система: ' if msg['role'] == 'system' else ""
            history_text += f'{role}{msg["content"]}\n'
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
            messages=[{'role': 'system', 'content': f"Your memory is full, you need to summarize most important information from dialogue:\n{history_text}"}]
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


async def handle_text_message(user_id: int, user_name: str, text: str, message_id: int = None):
    user_data = await dp.storage.get_data(chat=user_id)

    # Если история пользователя не существует, создайте новую
    if 'history' not in user_data:
        user_data['history'] = []

    # Добавьте сообщение пользователя в историю
    user_data['history'].append({"role": "user", "content": f'{user_name}:{text}', 'message_id': message_id})

    # Создаем новую историю, содержащую только необходимые поля
    history_for_openai = [{"role": item["role"], "content": item["content"]} for item in user_data['history']]

    # Сформируйте ответ от GPT-3.5
    chat_response = await openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{'role': 'system', 'content': ASSISTANT_NAME}] + history_for_openai
    )

    # Добавьте ответ бота в историю
    user_data['history'].append(
        {"role": "assistant", "content": f"{ASSISTANT_NAME_SHORT}:{chat_response['choices'][0]['message']['content']}"})

    # Ограничьте историю MAX_TOKENS_COUNT токенами
    while count_tokens(user_data['history']) > MAX_HISTORY:
        await shorten_history(user_data, user_id)

    await dp.storage.set_data(chat=user_id, data=user_data)

    return chat_response['choices'][0]['message']['content']
from draw import *
@dp.edited_message_handler(content_types=types.ContentType.TEXT)
async def handle_edited_message(message: types.Message):
    try:
        user_id = message.chat.id
        user_data = await dp.storage.get_data(chat=user_id)

        if 'history' not in user_data:
            user_data['history'] = []

        # Находим и заменяем отредактированное сообщение в истории

        for msg in reversed(user_data['history']):
            if msg['role'] == 'user' and 'message_id' in msg and msg['message_id'] == message.message_id:
                msg['content'] = f"{message.from_user.full_name or message.from_user.username}:{message.text}"
                break
        history_for_openai = [{"role": item["role"], "content": item["content"]} for item in user_data['history']]
        # Запрос к модели GPT-3.5 Turbo
        chat_response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{'role': 'system', 'content': ASSISTANT_NAME}] + history_for_openai
        )

        response_text = chat_response['choices'][0]['message']['content']

        if ":" in response_text and len(response_text.split(":")[0].split()) < 5:
            response_text = response_text.split(":", 1)[1].strip()

        # Заменяем последний ответ модели на новый
        msg_id=None
        for msg in reversed(user_data['history']):
            if msg['role'] == 'assistant':
                msg['content'] = response_text
                msg_id=msg['message_id']
                break

        await bot.edit_message_text(response_text,message.chat.id,msg_id)

        if count_tokens(user_data['history']) > MAX_HISTORY:
            await shorten_history( user_data, user_id)

        await dp.storage.set_data(chat=user_id, data=user_data)
    except:
        traceback.print_exc()
        await message.answer('Не удалось получить ответ от Демиурга')


async def shorten_history( user_data, user_id):
    summary = await get_summary(user_id)
    asyncio.create_task(bot.send_message(chat_id=user_id,text='Короче:\n' + summary))
    last_msg = user_data['history'][-2:]
    user_data['history'] = [{"role": "assistant", "content": summary}]
    user_data['history'].extend(last_msg)


import pyttsx3
engine=None
def text_to_speech(text):
    global engine
    # Преобразование текста в речь и сохранение во временный файл
    with tempfile.NamedTemporaryFile(delete=True) as fp:
        filename = fp.name + ".mp3"

    if engine is None:
        engine = pyttsx3.init()
        # Открывайте и просматривайте доступные голоса, чтобы выбрать мужской голос
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'ru' in voice.name and 'male' in voice.gender:
                engine.setProperty('voice', voice.id)

    engine.save_to_file(text, filename)
    engine.runAndWait()

    return filename
async def text_to_speech2(text):
    # Преобразование текста в речь и сохранение во временный файл
    with tempfile.NamedTemporaryFile(delete=True) as fp:
        filename = fp.name + ".mp3"
    tts = await asyncio.get_running_loop().run_in_executor(None, functools.partial(gTTS,lang='ru'),text)  # Указать язык текста
    await asyncio.get_running_loop().run_in_executor(None,
                                                     tts.save,(filename))
    return filename
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
        user_data['history'].append({"role": "user", "content": f'{message.from_user.full_name or message.from_user.username}:{message.text}','message_id': message.message_id})
        history_for_openai = [{"role": item["role"], "content": item["content"]} for item in user_data['history']]
        # Сформируйте ответ от GPT-3.5
        chat_response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                         {'role': 'system', 'content': f'You are pretending to answer like a character from the following description: {ASSISTANT_NAME}'},
                         {'role': 'system', 'content': f'{config.instructions}'}
                     ] + history_for_openai
        )

        # Добавьте ответ бота в историю
        response_text = chat_response['choices'][0]['message']['content']

        while ":" in response_text and len(response_text.split(":")[0].split()) < 5:
            response_text = response_text.split(":", 1)[1].strip()

        if '/draw' in response_text:
            promt=response_text.split('/draw ',1)[-1]
            promt=promt.split('\n',1)[0]
            promt=promt.replace('[','').replace(']','')
            asyncio.create_task(draw_and_answer(promt,user_id,message.from_user.full_name or message.from_user.username))
        user_data['history'].append({"role": "assistant", "content": f"{ASSISTANT_NAME_SHORT}:{response_text}", 'message_id': msg.message_id})


        # Отправьте ответ пользователю
        await msg.edit_text(response_text)
        try:
            if False:
                voice_filename=await asyncio.get_running_loop().run_in_executor(None, text_to_speech,(response_text))
            else:
                voice_filename=await text_to_speech2(response_text)
            if os.path.exists(voice_filename):
                with open(voice_filename, 'rb') as audio:
                    await message.reply_voice(voice= audio,caption=response_text[:1024])
                await msg.delete()
        except:traceback.print_exc()
        #await dp.storage.set_data(chat=user_id, data=user_data)

        # Ограничьте историю MAX_HISTORY сообщениями
        if count_tokens(user_data['history']) > MAX_HISTORY:
            summary = await get_summary(user_id)
            asyncio.create_task(message.answer('Короче:\n' + summary))
            # Замените историю диалога суммарным представлением
            last_msg=user_data['history'][-2:]
            user_data['history'] = [{"role": "assistant", "content": summary}]
            user_data['history'].extend(last_msg)

        await dp.storage.set_data(chat=user_id, data=user_data)
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось получить ответ от Демиурга')
def count_tokens(history):
    c = 0
    for msg in history:
        if re.search("[а-яА-Я]", msg['content']):  # Если содержит русские буквы
            c += len(msg['content'].split()) * 3  # Оценка количества токенов
        else:  # Для английского и других языков
            c += len(msg['content'].split())
    return c

async def on_startup(dp):
    # Установите здесь ваши команды
    await bot.set_my_commands([
        BotCommand("history", "Показать историю диалога"),
        BotCommand("summarize", "Суммировать историю диалога"),
        BotCommand("clear", "Clear историю диалога"),
        BotCommand("promt", "Edit gpt start promt"),
        BotCommand("draw_settings", "draw settings"),
        BotCommand("draw", "{prompt} draws an image"),
        # Добавьте здесь любые дополнительные команды
    ])

if __name__ == '__main__':
    if not Prompt.table_exists(): Prompt.create_table()
    executor.start_polling(dp, on_startup=on_startup)