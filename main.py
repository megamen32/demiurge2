import functools
import subprocess
import tempfile
from datetime import datetime, timedelta

from gtts import gTTS
import os
from aiogram import types, executor
import openai


# Установите ваши токены здесь
from aiogram.types import BotCommand
import speech_recognition as sr

import gpt
from config import TELEGRAM_BOT_TOKEN, CHATGPT_API_KEY, dp, get_first_word, bot
from datebase import Prompt, ImageUnstability
from draw import process_draw_commands

# Установите ваш ключ OpenAI
from gpt import process_queue, gpt_acreate, count_tokens, summary_gpt
from image_caption import image_caption_generator
from tgbot import get_chat_data

openai.api_key=CHATGPT_API_KEY





@dp.message_handler(commands=['promt'])
async def change_role(message: types.Message):
    # Получение настроек для этого чата
    data , chat_id = await get_chat_data(message)

    # Обновление настроек
    text = message.text.split(' ', 1)[-1]
    data['ASSISTANT_NAME'] = text
    data['ASSISTANT_NAME_SHORT'] = get_first_word(text)

    # Сохранение обновленных настроек
    await dp.storage.set_data(chat=chat_id,data=data)

    await message.reply(f'Now i am {data["ASSISTANT_NAME_SHORT"]}:\n' + text)

@dp.message_handler(commands=['history'])
async def show_history(message: types.Message):
    m = await message.reply('...')
    try:

        text = await get_history(message)
        if text is None:
            text = 'История пуста'
        await m.edit_text(text=text[-4090:])
    except:
        traceback.print_exc()
        await m.edit_text('Не удалось получить ответ от Демиурга')


async def get_history(message):
    user_data, chat_id = await get_chat_data(message)
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

        user_data, chat_id = await get_chat_data(message)

        if 'history' in user_data and user_data['history']:
            user_data['history'] = []
            await dp.storage.set_data(chat=chat_id, data=user_data)
        await msg.edit_text('История диалога очищена.')
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось очистить историю диалога.')

@dp.message_handler(commands=['summarize'])
async def summarize_history(message: types.Message):
    msg = await message.reply('...')
    try:


        summary = await get_summary( message)
        if summary is not None:
            user_data, chat_id = await get_chat_data(message)
            # Замените историю диалога суммарным представлением
            user_data['history'] = [{"role": "assistant", "content": summary}]
            await dp.storage.set_data(chat=chat_id, data=user_data)

            await msg.edit_text( text=f"История диалога была суммирована:\n{summary}")
        else:
            await msg.edit_text( text="История диалога пуста.")
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось получить ответ от Демиурга')


async def get_summary( message):
    user_data, chat_id = await get_chat_data(message)
    ASSISTANT_NAME=user_data.get('ASSISTANT_NAME',config.ASSISTANT_NAME)

    if user_data.get('history',None) is not None:
        history_for_openai = [{'role': 'system',
                               'content': f'You are pretending to answer like a character from the following description: {ASSISTANT_NAME}'},
                              ] + [{"role": item["role"], "content": item["content"]} for item in user_data['history']]
        # Сформируйте запрос на суммирование к GPT-3.5
        summary = await summary_gpt(history_for_openai)
    return summary


@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    msg = await message.reply('...')
    try:

        user_data, chat_id = await get_chat_data(message)

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
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    msg = await message.reply('...')
    try:

        user_data, chat_id = await get_chat_data(message)

        # Получите файл голосового сообщения
        file_id = message.photo[-1].file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        ext = file_path.rsplit('.', 1)[-1]
        # Скачайте аудиофайл
        await bot.download_file(file_path, destination=f"{file_id}.{ext}")

        text = await asyncio.get_running_loop().run_in_executor(None, image_caption_generator, f'{file_id}.{ext}')
        message.text = f'User sends your photo, that ai recognized as "{text}"'
        if message.caption:
            user=message.from_user
            user_data['history'].append(
                {'role': 'system', 'content': f'User {user.full_name or user.username} sended image,  Ai recognized image as "{text}"'})
            await dp.storage.set_data(chat=chat_id)
            message.text=f'{message.caption}'
        asyncio.create_task(msg.edit_text(f'Вы send photo:\n{text}'))
        return await handle_message(message,role='system')
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось получить ответ от Демиурга')
@dp.message_handler(content_types=types.ContentType.VIDEO)
async def handle_video(message: types.Message):
    msg = await message.reply('...')
    try:

        user_data, chat_id = await get_chat_data(message)

        # Получите файл голосового сообщения
        file_id = message.video.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        ext=file_path.rsplit('.',1)[-1]
        # Скачайте аудиофайл
        await bot.download_file(file_path, destination=f"{file_id}.{ext}")

        text = await asyncio.get_running_loop().run_in_executor(None, recognize,file_id,f'.{ext}')
        message.text=text
        asyncio.create_task( msg.edit_text(f'Вы сказали:\n{text}'))
        return await handle_message(message)
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось получить ответ от Демиурга')

import whisper
speech_model=None
def recognize(file_id,ext='.ogg'):
    # Преобразование аудиофайла в формат WAV для распознавания речи
    # Используйте SpeechRecognition для преобразования аудио в текст
    if False:
        global speech_model
        if speech_model is None:
            speech_model = whisper.load_model("small")
        result = speech_model.transcribe(f"{file_id}{ext}")
        text=(result["text"])
    else:
        os.system(f'ffmpeg -i {file_id}{ext} {file_id}.wav')
        audio_file = open(f'{file_id}.wav', "rb")
        text=openai.Audio.transcribe("whisper-1", audio_file)['text']
        os.remove(f'{file_id}.wav')

    os.remove(f'{file_id}{ext}')
    return text
def recognize_old(file_id):
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



from imagine import *
@dp.edited_message_handler(content_types=types.ContentType.TEXT)
async def handle_edited_message(message: types.Message):
    try:

        user_data, chat_id = await get_chat_data(message)

        if 'history' not in user_data:
            user_data['history'] = []
        try:
            # Находим и заменяем отредактированное сообщение в истории
            msg_id=None
            for msg in reversed(user_data['history']):
                if msg['role'] == 'user' and 'message_id' in msg and msg['message_id'] == message.message_id:
                    msg_id=user_data['history'].index(msg)
                    break
            user_data['history']=user_data['history'][:msg_id]
            await dp.storage.set_data(chat=chat_id, data=user_data)
        except:
            traceback.print_exc()

        await handle_message(message)


    except:
        traceback.print_exc()
        await message.answer('Не удалось получить ответ от Демиурга')


async def shorten_history( user_data, chat_id):
    summary = await get_summary(chat_id)
    asyncio.create_task(bot.send_message(chat_id=chat_id,text='Короче:\n' + summary))
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

from aiogram import types

@dp.message_handler(content_types=[types.ContentType.NEW_CHAT_MEMBERS, types.ContentType.LEFT_CHAT_MEMBER,types.ContentType.POLL,types.ContentType.PINNED_MESSAGE,types.ContentType.DELETE_CHAT_PHOTO,types.ContentType.NEW_CHAT_PHOTO,types.ContentType.NEW_CHAT_TITLE,types.ContentType.DICE,types.ContentType.CONTACT,types.ContentType.STICKER])
async def handle_chat_update(message: types.Message):

    user = message.from_user

    user_data, chat_id = await get_chat_data(message)

    # Если история пользователя не существует, создайте новую
    if 'history' not in user_data:
        user_data['history'] = []

    # Добавьте сообщение пользователя в историю
    if message.content_type == types.ContentType.NEW_CHAT_MEMBERS:
        user_data['history'].append({'role': 'system', 'content': f'{user.full_name or user.username} has joined the chat.'})
    elif message.content_type == types.ContentType.LEFT_CHAT_MEMBER:
        user_data['history'].append({'role': 'system', 'content': f'{user.full_name or user.username} has left the chat.'})
    elif message.content_type == types.ContentType.PHOTO:
        user_data['history'].append({'role': 'system', 'content': f'{user.full_name or user.username} has sent a photo.'})
    elif message.content_type == types.ContentType.VIDEO:
        user_data['history'].append({"role": "system", "content": f'{user.full_name or user.username} has sent a video.',})
    elif message.content_type == types.ContentType.STICKER:
        user_data['history'].append({'role': 'system', 'content': f'{user.full_name or user.username} has sent a sticker that represents "{message.sticker.emoji}" from sticker pack with name "{message.sticker.set_name}"'})
    else:
        user_data['history'].append({"role": "system", "content": f'{user.full_name or user.username} has created new chat event: {message.content_type}',})
    history_for_openai = [{"role": item["role"], "content": item["content"]} for item in user_data['history']]
    chat_response = await gpt_acreate(model='gpt-3.5-turbo', messages=history_for_openai)
    response_text = chat_response['choices'][0]['message']['content']

    while ":" in response_text and len(response_text.split(":")[0].split()) < 5:
        response_text = response_text.split(":", 1)[1].strip()

    msg = await message.answer(response_text)
    ASSISTANT_NAME_SHORT=user_data.get('ASSISTANT_NAME_SHORT',config.ASSISTANT_NAME_SHORT)
    user_data['history'].append({"role": "assistant", "content": f"{ASSISTANT_NAME_SHORT}:{response_text}", 'message_id': msg.message_id})





from asyncio import CancelledError

processing_tasks = {}

@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_message(message: types.Message,role='user'):
    user_data, chat_id = await get_chat_data(message)
    user_data['last_message_time'] = datetime.now().timestamp()

    # Если история пользователя не существует, создайте новую
    if 'history' not in user_data:
        user_data['history'] = []

    # Добавьте сообщение пользователя в историю
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        from_ = user.full_name or user.username if not user.id == bot.id else user_data.get('ASSISTANT_NAME_SHORT',
                                                                                            config.ASSISTANT_NAME_SHORT)
        message.text = f'{message.text} (this message is in response to "{from_}" who said: {message.reply_to_message.text or message.reply_to_message.caption})'
    if role == 'user':
        text_ = f'{message.from_user.full_name or message.from_user.username}:{message.text}'
        user_data['history'].append({"role": "user", "content": text_, 'message_id': message.message_id})
    else:
        user_data['history'].append({"role": "system", "content": f'{message.text}', 'message_id': message.message_id})
    await dp.storage.set_data(chat=chat_id, data=user_data)

    # Получите текущую задачу обработки для этого пользователя (если есть)
    current_processing_task = processing_tasks.get(chat_id, None)

    # Если задача обработки уже запущена, отмените ее
    if current_processing_task:
        current_processing_task.cancel()
        try:
            await current_processing_task
        except CancelledError:
            pass

    # Запуск новой задачи обработки с задержкой
    processing_task = asyncio.create_task(wait_and_process_messages(chat_id, message, user_data, role))
    processing_tasks[chat_id] = processing_task

    await dp.storage.set_data(chat=chat_id, data=user_data)


async def wait_and_process_messages(chat_id, message, user_data, role):
    msg=await message.reply('...')
    try:
        await asyncio.sleep(3)  # ждем 3 секунды
        user_data, chat_id = await get_chat_data(message)
        # Сформируйте ответ от GPT-3.5
        history_for_openai = [{"role": item["role"], "content": item["content"]} for item in user_data['history']]
        ASSISTANT_NAME = user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME)
        chat_response = await gpt_acreate(
            model="gpt-3.5-turbo" if not config.useGPT4 else 'gpt-4',
            messages=[
                         {'role': 'system',
                          'content': f'You are pretending to answer like a character from the following description: {ASSISTANT_NAME}'},
                         {'role': 'system', 'content': f'{config.instructions}'}
                     ] + history_for_openai
        )

        # Добавьте ответ бота в историю
        response_text = chat_response['choices'][0]['message']['content']

        while ":" in response_text and len(response_text.split(":")[0].split()) < 5:
            response_text = response_text.split(":", 1)[1].strip()

        ASSISTANT_NAME_SHORT = user_data.get('ASSISTANT_NAME_SHORT', config.ASSISTANT_NAME_SHORT)
        user_data, chat_id = await get_chat_data(message)
        user_data['history'].append(
            {"role": "assistant", "content": f"{ASSISTANT_NAME_SHORT}:{response_text}", 'message_id': msg.message_id})
        await dp.storage.set_data(chat=chat_id, data=user_data)
        response_text = process_draw_commands(response_text, r'draw\("(.+?)"\)', message.chat.id, message.message_id)
        response_text = process_draw_commands(response_text, r'\/draw (.+)\/?', message.chat.id, message.message_id)
        response_text = process_search_commands(response_text, message, r'\/search (.+)\/?')
        response_text = process_search_commands(response_text, message, r'\/web (.+)\/?', coroutine=handle_web)

        # Отправьте ответ пользователю
        if response_text:

            try:
                await msg.edit_text(response_text[:4096])
                if config.TTS:
                    asyncio.create_task(send_tts(message, msg, response_text))
            except:
                traceback.print_exc()
            # await dp.storage.set_data(chat=chat_id, data=user_data)
        else:
            await msg.delete()

        if count_tokens([{'role': 'system',
                          'content': f'You are pretending to answer like a character from the following description: {ASSISTANT_NAME}'},
                         ] + user_data['history']) > gpt.MAX_TOKENS:
            history_for_openai = [{'role': 'system',
                                   'content': f'You are pretending to answer like a character from the following description: {ASSISTANT_NAME}'},
                                  ] + [{"role": item["role"], "content": item["content"]} for item in
                                       user_data['history'][:-2]]
            summary = await summary_gpt(history_for_openai)
            asyncio.create_task(message.answer('Короче:\n' + summary))
            # Замените историю диалога суммарным представлением
            last_msg = user_data['history'][-2:]
            user_data['history'] = [{"role": "assistant", "content": summary}]
            user_data['history'].extend(last_msg)

        await dp.storage.set_data(chat=chat_id, data=user_data)
    except CancelledError:
        await msg.delete()
    except:
        traceback.print_exc()
        await msg.edit_text(f'Error in getting answer {traceback.format_exc()}')





async def send_tts(message, msg, response_text):
    if False:
        voice_filename = await asyncio.get_running_loop().run_in_executor(None, text_to_speech, (response_text))
    else:
        voice_filename = await text_to_speech2(response_text)
    if os.path.exists(voice_filename):
        with open(voice_filename, 'rb') as audio:
            await message.reply_voice(voice=audio, caption=response_text[:1024])
        await msg.delete()


async def on_startup(dp):
    # Установите здесь ваши команды
    asyncio.create_task(process_queue())
    await bot.set_my_commands([
        BotCommand("history", "Показать историю диалога"),
        BotCommand("summarize", "Суммировать историю диалога"),
        BotCommand("clear", "Clear историю диалога"),
        BotCommand("promt", "Edit gpt start promt"),
        BotCommand("draw_settings", "draw settings"),
        BotCommand("draw", "{prompt} draws an image"),
        BotCommand("imagine", "{prompt} draws an image"),
        BotCommand("trends", "get all news and trends"),
        # Добавьте здесь любые дополнительные команды
    ])
import redis

async def check_inactive_users():
    while True:
        # Ваш Redis сервер
        r = redis.Redis(host='localhost', port=6379, db=0)

        # Получите все ключи из Redis. Замените "your_prefix" на ваш префикс
        all_keys = r.keys("demiurge*")

        for key in all_keys:
            # Достаём chat_id из ключа
            chat_id = key.decode("utf-8").split(":")[1]
            # Получаем данные пользователя из aiogram storage
            user_data = await dp.storage.get_data(chat=chat_id)

            if 'last_message_time' not in user_data:
                continue
            last_message_time = datetime.fromtimestamp(user_data['last_message_time'])
            if datetime.now() - last_message_time > timedelta(seconds=30):  # если прошло 24 часа
                # генерируем сообщение
                ASSISTANT_NAME = user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME)
                history_for_openai = [{'role': 'system',
                                       'content': f'You are pretending to answer like a character from the following description: {ASSISTANT_NAME}'},
                                      ] + [{"role": item["role"], "content": item["content"]} for item in
                                           user_data['history']]
                chat_response = await gpt_acreate(
                    model="gpt-3.5-turbo",
                    messages=history_for_openai+[
                        {'role': 'system', 'content': 'Пользователь не взаимодействовал в течение 24 часов.'},
                        {'role': 'system', 'content': 'Вы должны напомнить о себе.'}
                    ]
                )
                response_text = chat_response['choices'][0]['message']['content']
                # отправляем сообщение
                await dp.bot.send_message(chat_id=chat_id, text=response_text)
        await asyncio.sleep(3600)  # ждём час перед следующей проверкой



if __name__ == '__main__':
    if not Prompt.table_exists(): Prompt.create_table()
    if not ImageMidjourney.table_exists(): ImageMidjourney.create_table()
    if not ImageUnstability.table_exists(): ImageUnstability.create_table()
    #start Midjourney-Web-API/app.py
    subprocess.Popen(["python", "Midjourney-Web-API/app.py"])
    loop = asyncio.new_event_loop()
    loop.create_task(check_inactive_users())
    loop.create_task(loop.run_in_executor(None,executor.start_polling(dp, on_startup=on_startup)))
    loop.run_forever()