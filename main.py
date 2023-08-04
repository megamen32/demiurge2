import asyncio
import functools
import io
import json
import logging
import math
import operator
import pprint
import random
import subprocess
import tempfile
import traceback
from datetime import datetime, timedelta
from json import JSONDecodeError

from gtts import gTTS
import os
from aiogram import types, executor
import openai

# Установите ваши токены здесь
from aiogram.types import BotCommand
import speech_recognition as sr
from pydub import AudioSegment

import config
import gpt
import tgbot
from config import TELEGRAM_BOT_TOKEN, CHATGPT_API_KEY, dp, get_first_word, bot
from datebase import Prompt, ImageUnstability
from draw import  draw_and_answer, upscale_image_imagine

# Установите ваш ключ OpenAI
from gpt import process_queue, gpt_acreate, count_tokens, summary_gpt
from image_caption import image_caption_generator
from telegrambot.handlers import MessageLoggingMiddleware
from tgbot import dialog_append

openai.api_key = CHATGPT_API_KEY


@dp.message_handler(commands=['prompt'])
async def change_role(message: types.Message):
    # Получение настроек для этого чата
    data, chat_id = await get_chat_data(message)

    # Обновление настроек
    text = message.text.split(' ', 1)[-1]
    data['ASSISTANT_NAME'] = text
    data['ASSISTANT_NAME_SHORT'] = get_first_word(text)

    # Сохранение обновленных настроек
    await dp.storage.set_data(chat=chat_id, data=data)

    await message.reply(f'Now i am {data["ASSISTANT_NAME_SHORT"]}:\n' + text)


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('history'))
async def process_callback_history_button(callback_query: types.CallbackQuery):
    _, action, start, end = callback_query.data.split(";")
    start = int(start)
    end = int(end)

    if action == "next":
        start += 4090
        end += 4090
    elif action == "prev":
        start -= 4090
        end -= 4090

    text = await get_history(callback_query.message)



    text,kb=format_history(text,start, end)

    await bot.edit_message_text(text=text, chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id, reply_markup=kb)


def format_history(text, start=0, end=4090):
    # Форматируем историю
    formatted_text = ''
    text = text[start:end]

    # Проверяем, не обрезали ли мы предложение или абзац, и если обрезали, корректируем
    if len(text) == end:
        end = text.rfind('. ', 0, end) + 2

    text = text[:end]

    for line in text.split('\n'):
        if ": " in line:
            role, message = line.split(": ", 1)
            formatted_text += f"*{role.strip('*')}*: {message}\n\n"
        else:
            formatted_text += line + "\n"

    # Кнопки для навигации
    keyboard = InlineKeyboardMarkup()
    if len(text) > end:
        keyboard.add(InlineKeyboardButton("Вперёд", callback_data=f"history;next;{start};{end}"))
    if start != 0:
        keyboard.add(InlineKeyboardButton("Back", callback_data=f"history;prev;{start};{end}"))

    return formatted_text, keyboard


@dp.message_handler(commands=['history'])
async def show_history(message):
    text = await get_history(message)
    text,kb= format_history(text)
    # Отправляем сообщение

    try:
        await message.reply(text=text, reply_markup=kb, parse_mode='Markdown')
    except:
        try:
            await message.reply(text=text, reply_markup=kb)
        except:
            traceback.print_exc()
            await message.reply('Не удалось получить ответ от Демиурга')



async def get_history(message):
    user_data, chat_id = await get_chat_data(message)
    if 'history' in user_data:
        history = user_data['history']
        history_text = user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME) + '\n'
        for msg in history:
            if msg['role'] == config.Role_SYSTEM:
                role = 'Система: '
            elif msg['role'] == config.Role_ASSISTANT:
                role = user_data.get('ASSISTANT_NAME_SHORT', config.ASSISTANT_NAME_SHORT)
            else:
                role = ""
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
        user_data, chat_id = await get_chat_data(message)
        await do_short_dialog(chat_id, user_data,force=True)
        summary = await get_history(message)
        await msg.edit_text(text=f"История диалога была суммирована:\n{summary[:4096]}")
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось получить ответ от Демиурга')



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

        text = await recognize (file_id)
        message.text = text
        await dialog_append(message, message.text)
        asyncio.create_task(msg.edit_text(f'Вы сказали:\n{text[:4000]}'))
        await msg.edit_text(f'Вы сказали:\n{text[:4000]}')

        if len(text) > 4000:
            # Отправляем остальную часть длинного текста в отдельных сообщениях
            remaining_text = text[4000:]
            while remaining_text:
                chunk = remaining_text[:4000]
                remaining_text = remaining_text[4000:]
                await message.reply(chunk)
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
        destination = f"{file_id}.{ext}"
        await bot.download_file(file_path, destination=destination)

        if message.caption and message.caption.lower().replace('/','').startswith('u'):
            data=open(destination,'rb').read()
            img=await upscale_image_imagine(data)
            await message.answer_photo(io.BytesIO(img),caption='upscaled')
            os.remove(destination)
            await msg.delete()
            return

        text = await asyncio.get_running_loop().run_in_executor(None, image_caption_generator, destination)
        user = message.from_user
        content = f'User sent an image, which was recognized with the following caption: "{text}"'
        if message.caption:
            content += f'. User provided the following message with the image: "{message.caption}"'
        await dialog_append(message, content, config.Role_USER)
        asyncio.create_task(msg.edit_text(f'Вы send photo:\n{text}'))
        return await handle_message(message, role='system')
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
        ext = file_path.rsplit('.', 1)[-1]
        # Скачайте аудиофайл
        await bot.download_file(file_path, destination=f"{file_id}.{ext}")

        text = await recognize(file_id, f'.{ext}')

        await tgbot.dialog_append(message, text)
        asyncio.create_task(msg.edit_text(f'Вы сказали:\n{text}'))
        return await handle_message(message)
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось получить ответ от Демиурга')


speech_model = None
def split_audio(audio_file, chunk_duration):
    # Разбивает аудиофайл на чанки указанной длительности и возвращает список файлов чанков

    # Создание директории для временных файлов
    temp_dir = "temp_audio_chunks"
    os.makedirs(temp_dir, exist_ok=True)

    # Получение общей длительности аудиофайла
    audio_duration = get_audio_duration(audio_file)

    # Расчет количества чанков и длительности каждого чанка
    num_chunks = math.ceil(audio_duration / chunk_duration)
    chunk_duration_secs = chunk_duration * 1000  # Преобразование в миллисекунды

    chunk_files = []
    for i in range(num_chunks):
        # Вычисление времени начала и окончания текущего чанка
        start_time = i * chunk_duration_secs
        end_time = min((i + 1) * chunk_duration_secs, audio_duration)

        # Извлечение текущего чанка с использованием ffmpeg
        chunk_file = f"{temp_dir}/chunk_{i}.wav"
        os.system(f"ffmpeg -ss {start_time / 1000} -t {(end_time - start_time) / 1000} -i {audio_file} -c copy {chunk_file}")

        chunk_files.append(chunk_file)

    return chunk_files


def get_audio_duration(audio_file):
    # Получает длительность аудиофайла в миллисекундах

    duration_output = os.popen(f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {audio_file}").read()
    duration_secs = float(duration_output)
    duration_ms = duration_secs * 1000

    return duration_ms

async def recognize_chunk(file_id, chunk_index, chunk):
    chunk.export(f'{file_id}_chunk{chunk_index}.wav', format='wav')
    audio_file = open(f'{file_id}_chunk{chunk_index}.wav', "rb")
    response = await openai.Audio.atranscribe("whisper-1", audio_file)
    os.remove(f'{file_id}_chunk{chunk_index}.wav')
    return response['text']

async def recognize(file_id, ext='.ogg'):
    # Преобразование аудиофайла в формат WAV для распознавания речи
    # Используйте Whisper для преобразования аудио в текст
    os.system(f'ffmpeg -i {file_id}{ext} {file_id}.wav')

    if os.path.getsize(f'{file_id}.wav') <= 26214400:
        # Размер файла меньше или равен максимальному размеру для Whisper
        result = await openai.Audio.atranscribe('whisper-1', open(f"{file_id}.wav", 'rb'))
        text = result["text"]
    else:
        # Размер файла превышает максимальный размер для Whisper
        audio = AudioSegment.from_file(f'{file_id}.wav')
        chunk_size = 24000  # Размер каждого фрагмента аудио
        chunks = len(audio) // chunk_size + 1
        tasks = []
        for i in range(chunks):
            chunk = audio[i * chunk_size: (i + 1) * chunk_size]
            task = asyncio.create_task(recognize_chunk(file_id, i, chunk))
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        text = ''.join(results)

    os.remove(f'{file_id}{ext}')
    os.remove(f'{file_id}.wav')
    return text
def transcribe_chunk(chunk_file):
    # Отправляет чанк аудиофайла в API OpenAI для распознавания и возвращает полученный текст

    audio_file = open(chunk_file, "rb")
    result = openai.Audio.transcribe("whisper-1", audio_file)
    text = result['text']

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

@dp.message_handler(commands=['func','functions'])
async def switch_functions(message: types.Message):
    # Получение данных пользователя
    user_data, chat_id = await get_chat_data(message)

    # Получение текущего значения use_gpt_4 или получение значения по умолчанию, если оно ещё не установлено
    functions_on = user_data.get('functions', config.functions)
    function_names_on = list(map(operator.itemgetter('name'), functions_on))
    functions_all = config.functions

    names=[func['name'] for func in functions_all]
    btn=[InlineKeyboardButton(f'{name} {"V" if name in function_names_on else "X"}',callback_data=f'togglefunc_{name}') for name in names]
    kb=InlineKeyboardMarkup()
    kb.add(*btn)
    functions_info = "\n\n".join(
        [f'{func["name"]}: {func["description"]}' for func in functions_all])

    # Отправка сообщения пользователю об изменении режима
    await message.reply(functions_info[:4096],reply_markup=kb)
from aiogram import types

# Ваш код с предыдущим обработчиком команды

# Обработчик для нажатия на кнопку
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('togglefunc_'))
async def toggle_function_mode(callback_query: types.CallbackQuery):
    await callback_query.answer()
    # Получение имени функции из callback_data
    function_name = callback_query.data.split('_',maxsplit=1)[1]

    # Получение данных пользователя
    user_data, chat_id = await get_chat_data(callback_query.message)

    functions_on = user_data.get('functions', config.functions)

    # Получение списка имен функций из functions_on
    function_names_on = list(map(operator.itemgetter('name'), functions_on))

    # Обработка переключения функции вкл/выкл
    if function_name in function_names_on:
        functions_on = [func for func in functions_on if func["name"] != function_name]
    else:
        # Найти объект функции в functions_all по имени и добавить его в functions_on
        function = next((func for func in config.functions if func["name"] == function_name), None)
        if function:
            functions_on.append(function)
    function_names_on = list(map(operator.itemgetter('name'), functions_on))

    # Сохранение обновленного значения в данных пользователя
    user_data['functions'] = functions_on
    await dp.storage.set_data(chat=chat_id, data=user_data)

    # Отправка сообщения пользователю об изменении режима
    names = [func['name'] for func in config.functions]
    btn = [InlineKeyboardButton(f'{name} {"V" if name in function_names_on else "X"}', callback_data=f'togglefunc_{name}') for name in names]
    functions_info = "\n\n".join(
        [f'{func["name"]}: {func["description"]}' for func in config.functions])
    # Обновление клавиатуры с кнопками
    await bot.edit_message_text(
        functions_info,
        chat_id=chat_id,
        message_id=callback_query.message.message_id,
        reply_markup=InlineKeyboardMarkup().add(*btn)
    )


    # Ответить на callback_query, чтобы убрать кружок загрузки на кнопке


@dp.message_handler(commands=['gpt4'])
async def switch_gpt4_mode(message: types.Message):
    # Получение данных пользователя
    user_data, chat_id = await get_chat_data(message)

    # Получение текущего значения use_gpt_4 или получение значения по умолчанию, если оно ещё не установлено
    use_gpt_4 = user_data.get('gpt-4', config.useGPT4)

    # Переключение режима use_gpt_4
    use_gpt_4 = not use_gpt_4

    # Сохранение нового значения в данных пользователя
    user_data['gpt-4'] = use_gpt_4
    await dp.storage.set_data(chat=chat_id, data=user_data)

    # Отправка сообщения пользователю об изменении режима
    await message.reply(f"GPT-4 mode is now {'ON' if use_gpt_4 else 'OFF'}.")


from imagine import *


@dp.edited_message_handler(content_types=types.ContentType.TEXT)
async def handle_edited_message(message: types.Message):
    try:

        user_data, chat_id = await get_chat_data(message)

        if 'history' not in user_data:
            user_data['history'] = []
        try:
            # Находим и заменяем отредактированное сообщение в истории
            msg_id = None
            for msg in reversed(user_data['history']):
                if msg['role'] == 'user' and 'message_id' in msg and msg['message_id'] == message.message_id:
                    msg_id = user_data['history'].index(msg)
                    break
            user_data['history'] = user_data['history'][:msg_id]
            await dp.storage.set_data(chat=chat_id, data=user_data)
        except:
            traceback.print_exc()

        await dialog_append(message, message.text)
        await handle_message(message)


    except:
        traceback.print_exc()
        await message.answer('Не удалось получить ответ от Демиурга')


@dp.message_handler(commands=['count'])
async def show_memory_info(message: types.Message):
    user_data, _ = await get_chat_data(message)
    history = user_data['history']
    total_symbols = sum([len(message['content']) for message in history])
    total_tokens = count_tokens(history)
    await message.reply(f"В памяти находится {total_symbols} символов и {total_tokens} токенов.")


engine = None


def text_to_speech(text):
    global engine
    # Преобразование текста в речь и сохранение во временный файл
    with tempfile.NamedTemporaryFile(delete=True) as fp:
        filename = fp.name + ".mp3"

    if engine is None:
        import pyttsx3
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
    tts = await asyncio.get_running_loop().run_in_executor(None, functools.partial(gTTS, lang='ru'),
                                                           text)  # Указать язык текста
    await asyncio.get_running_loop().run_in_executor(None,
                                                     tts.save, (filename))
    return filename


from aiogram import types


@dp.message_handler(
    content_types=[types.ContentType.NEW_CHAT_MEMBERS, types.ContentType.LEFT_CHAT_MEMBER, types.ContentType.POLL,
                   types.ContentType.PINNED_MESSAGE, types.ContentType.DELETE_CHAT_PHOTO,
                   types.ContentType.NEW_CHAT_PHOTO, types.ContentType.NEW_CHAT_TITLE, types.ContentType.DICE,
                   types.ContentType.CONTACT, types.ContentType.STICKER])
async def handle_chat_update(message: types.Message):
    user = message.from_user

    user_data, chat_id = await get_chat_data(message)

    # Если история пользователя не существует, создайте новую
    if 'history' not in user_data:
        user_data['history'] = []

    # Добавьте сообщение пользователя в историю
    if message.content_type == types.ContentType.NEW_CHAT_MEMBERS:
        user_data['history'].append(
            {'role': 'system', 'content': f'{user.full_name or user.username} has joined the chat.'})
    elif message.content_type == types.ContentType.LEFT_CHAT_MEMBER:
        user_data['history'].append(
            {'role': 'system', 'content': f'{user.full_name or user.username} has left the chat.'})
    elif message.content_type == types.ContentType.PHOTO:
        user_data['history'].append(
            {'role': 'system', 'content': f'{user.full_name or user.username} has sent a photo.'})
    elif message.content_type == types.ContentType.VIDEO:
        user_data['history'].append(
            {"role": "system", "content": f'{user.full_name or user.username} has sent a video.', })
    elif message.content_type == types.ContentType.STICKER:
        user_data['history'].append({'role': 'system',
                                     'content': f'{user.full_name or user.username} has sent a sticker that represents "{message.sticker.emoji}" from sticker pack with name "{message.sticker.set_name}"'})
    else:
        user_data['history'].append({"role": "system",
                                     "content": f'{user.full_name or user.username} has created new chat event: {message.content_type}', })

    chat_response = await gpt_acreate(model='gpt-3.5-turbo-0613', messages=user_data['history'])
    response_text = chat_response['choices'][0]['message']['content']

    while ":" in response_text and len(response_text.split(":")[0].split()) < 5:
        response_text = response_text.split(":", 1)[1].strip()

    msg = await message.answer(response_text)
    ASSISTANT_NAME_SHORT = user_data.get('ASSISTANT_NAME_SHORT', config.ASSISTANT_NAME_SHORT)
    user_data['history'].append(
        {"role": "assistant", "content": f"{ASSISTANT_NAME_SHORT}:{response_text}", 'message_id': msg.message_id})


from asyncio import CancelledError

processing_tasks = {}


@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_message(message: types.Message, role='user'):
    user_data, chat_id = await get_chat_data(message)

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


def execute_python_code(code:str):
    # Добавляем return в конец кода
    code_with_return = "\n".join(code.split("\n")[:-1]) + "\nreturn " + \
                       code.split("\n")[-1]

    # Определяем функцию, которая будет исполнять код
    exec_function_str = f"def _exec_function():\n" + "\n".join("  " + line for line in code_with_return.split("\n"))

    # Исполняем код функции
    exec_globals = {}
    exec(exec_function_str, exec_globals)
    exec_function = exec_globals['_exec_function']

    # Вызываем функцию и возвращаем результат
    return exec_function()







# Создайте глобальную блокировку
dialog_locks = {}
async def process_function_call(function_name, function_args, message, step=0):
    process_next = False
    try:
        function_args = json.loads(function_args)
    except JSONDecodeError:
        function_args = {}

    if function_name == 'draw':
        image_description_ = function_args.get('image_description', '')
        ratio_ = function_args.get('ratio', None)
        style_ = function_args.get('style', None)
        message.text = f"/{function_name} {image_description_}"

        user_data, storage_id = await get_chat_data(message)

        # Сохранение ratio, style, и image_description в данных пользователя
        if ratio_ is not None:
            user_data['ratio'] = ratio_
        if style_ is not None:
            user_data['style'] = style_

        # Сохранение обновленных данных пользователя
        await dp.storage.set_data(chat=storage_id, data=user_data)

        asyncio.create_task( draw_and_answer(image_description_, message.chat.id, message.message_thread_id))
        response_text=None
        process_next = False

    elif function_name == 'web' or function_name=='extract_webpage_content' or function_name== 'open_link':
        url_ = function_args.get('url', '')
        message.text = f"/{function_name} {url_}"
        response_text, err = await function_web(url_)
        response_text = {"error": response_text} if err else {"content": response_text}
        if step==0:
            process_next = True
        else:
            process_next = not err

    elif function_name == 'search':
        query_ = function_args.get('query', '')
        message.text = f"/{function_name} {query_}"
        response_text = await function_search(query_)
        process_next = True

    elif function_name == 'execute_python_code' or function_name== 'python':
        code = function_args.get('code', '')
        res = execute_python_code(code)
        response_text = {'code':code,'result':res}
    else:
        raise Exception(f"There is no {function_name} funciton")
    if response_text is not None and not isinstance(response_text,str):
        response_text = json.dumps(response_text, ensure_ascii=False,default=str)
    return response_text, process_next


async def wait_and_process_messages(chat_id, message, user_data, role):
    global dialog_locks
    response_text=None
    cancel_event=asyncio.Event()
    while True:
        try:
            msg = await message.reply('...')


            break
        except RetryAfter as e:
            await asyncio.sleep(e.timeout)
            continue

    lock = dialog_locks.get(chat_id, asyncio.Lock())
    dialog_locks[chat_id] = lock
    try:
        async with lock:
            step=0
            while step<3:
                step+=1
                user_data, chat_id = await get_chat_data(message)
                functions=user_data.get('functions',config.functions)
                start_text =  get_start_text(user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME))
                gpt4 = user_data.get('gpt-4', config.useGPT4)

                asyncio.create_task(progress_bar('В процессе размышлений', msg, 60 if gpt4 else 15, cancel_event))
                chat_response = await gpt_acreate(
                    model="gpt-3.5-turbo-0613" if not gpt4 else 'gpt-4-0613',
                    messages=[
                                 {'role': 'system', 'content': start_text},
                             ] + user_data['history'],
                    functions=functions,
                    function_call="auto",
                )
                cancel_event.set()

                if 'function_call' in chat_response['choices'][0]['message']:
                    function_call = chat_response['choices'][0]['message']['function_call']
                    try:
                        response_text, process_next = await process_function_call(function_call['name'],
                                                                              function_call['arguments'], message)
                    except:
                        response_text=traceback.format_exc(0,False)
                        process_next=False


                    formatted_function_call =function_call["arguments"]
                    if process_next:
                        message.text = response_text
                        role = config.Role_ASSISTANT
                        user_data, chat_id = await dialog_append(message, text=response_text, role='function',
                                                                 name=function_call['name'])
                        ans=f'{function_call["name"]}:{formatted_function_call} => \n{response_text}'
                        await msg.edit_text(ans[:4096])
                        msg = await message.reply('...')
                        continue
                    response_text=f'{function_call["name"]}:{formatted_function_call}) => \n{response_text}'



                else:
                    response_text = chat_response['choices'][0]['message']['content']#.replace(f"{user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME)}:",'').replace(f"{user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME)} :",'').replace(f"{user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME)}",'')
                    user_data, chat_id = await dialog_append(message, response_text, role=config.Role_ASSISTANT)

                break

        asyncio.create_task(do_short_dialog(chat_id, user_data))
        if response_text:
            asyncio.create_task( send_response_text(msg, response_text))
    except CancelledError:await msg.delete()
    except:
        traceback.print_exc()
        await msg.edit_text(msg.text+'\n'+traceback.format_exc())


def get_start_text(character):
    start_text = f"You are a telegram bot responding in Markdown format. Your role is based on the following description: '{character}'. In any situation, you must act and respond strictly in accordance with the image of your character!"
    return start_text


async def send_response_text(msg, response_text):
    if response_text:
        parse_modes = ['Markdown', None]

        for mode in parse_modes:
            try:
                # Если parse_mode = None, параметр parse_mode не будет передан
                await msg.edit_text(response_text[:4096], parse_mode=mode)
                if config.TTS:
                    asyncio.create_task(send_tts(msg, response_text))
                break  # если сообщение было успешно отправлено, прекратить перебор
            except Exception as e:
                traceback.print_exc()
                continue
    else:
        await msg.delete()


async def do_short_dialog(chat_id, user_data,force=False):
    global dialog_locks

    # Получение текущего значения use_gpt_4 или получение значения по умолчанию, если оно ещё не установлено
    use_gpt_4 = user_data.get('gpt-4', config.useGPT4)
    model = gpt.MAX_TOKENS['gpt-3.5-turbo-0613'] if not use_gpt_4 else gpt.MAX_TOKENS['gpt-4-0613']
    MAX_MEMORY_SIZE = model * 0.95
    normal_MEMORY_SIZE = model * 0.3

    lock = dialog_locks.get(chat_id, asyncio.Lock())
    dialog_locks[chat_id] = lock

    # Memory management must be synchronized to prevent concurrent writing.
    async with lock:
        summary=None
        remaining_history=None
        if force:
            remaining_history=user_data['history']
            reduced_history = []
        elif count_tokens(user_data['history']) > MAX_MEMORY_SIZE:

            reversed_history = user_data['history'][::-1]

            reduced_history = []
            total_tokens = 0

            # We add messages to the reduced history until we reach the max memory size
            for message in reversed_history:
                message_tokens = count_tokens([message])  # ensure the message is in a list
                if total_tokens + message_tokens > normal_MEMORY_SIZE:
                    break
                reduced_history.append(message)
                total_tokens += message_tokens

            # We reverse the reduced history again to maintain the original order
            reduced_history = reduced_history[::-1]

            # Generate summary for remaining history
            remaining_history = [msg for msg in user_data['history'] if msg not in reduced_history]
        else:
            reduced_history=user_data['history']
        if remaining_history:
            summary = await summary_gpt(remaining_history)
            # Add the summary at the start of our history
            reduced_history = [{"role": config.Role_ASSISTANT, "content": summary}] + reduced_history

        # Update the user's history
        user_data['history'] = reduced_history

        # Save the updated history to the user's data
        await dp.storage.set_data(chat=chat_id, data=user_data)
        if summary:
            chat_id,thread_id=storage_to_chat_id(chat_id)
            try:
                await bot.send_message(chat_id=chat_id,text=f"Summary :{summary}"[:4096],reply_to_message_id=thread_id)
            except:
                traceback.print_exc()
        return summary


async def send_tts(message, msg, response_text):
    if False:
        voice_filename = await asyncio.get_running_loop().run_in_executor(None, text_to_speech, (response_text))
    else:
        voice_filename = await text_to_speech2(response_text)
    if os.path.exists(voice_filename):
        with open(voice_filename, 'rb') as audio:
            await message.reply_voice(voice=audio, caption=response_text[:1024])
        await msg.delete()


import redis

from aiogram.utils.exceptions import BotKicked, BotBlocked, RetryAfter


async def check_inactive_users():
    while True:
        # Ваш Redis сервер
        r = redis.Redis(host='localhost', port=6379, db=0)

        # Получите все ключи из Redis. Замените "your_prefix" на ваш префикс
        all_keys = r.keys("demiurge*")

        for key in all_keys:
            # Достаём chat_id из ключа
            storage_id = key.decode("utf-8").split(":")[1]

            # Получаем данные пользователя из aiogram storage
            user_data = await dp.storage.get_data(chat=storage_id)
            chat_id, thread_id =  storage_to_chat_id(storage_id)

            if 'last_message_time' not in user_data:
                continue
            last_message_time = datetime.fromtimestamp(user_data['last_message_time'])
            if datetime.now() - last_message_time > timedelta(hours=24):  # если прошло 24 часа
                # генерируем сообщение
                user_data['last_message_time'] = datetime.now().timestamp()
                await dp.storage.set_data(chat=storage_id, data=user_data)
                if random.random()>0.9:
                    ASSISTANT_NAME = user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME)

                    await tgbot.dialog_append_raw(storage_id,
                                                  f'Ваша следующая задача - мотивировать пользователя продолжить разговор. Пользователь не взаимодействовал с вами уже более {(datetime.now() - last_message_time).total_seconds()/60/60} часов.',None, 'system')
                    user_data = await dp.storage.get_data(chat=storage_id)

                    try:
                        msg = await dp.bot.send_message(chat_id=chat_id, text='hmm...', reply_to_message_id=thread_id)

                        history_for_openai = [{'role': 'system',
                                               'content': get_start_text(ASSISTANT_NAME)},
                                              ] + user_data['history']
                        chat_response = await gpt_acreate(
                            model="gpt-3.5-turbo-0613",
                            messages=history_for_openai
                        )
                        response_text = chat_response['choices'][0]['message']['content']

                        # отправляем сообщение

                        logging.info(f'sended {response_text} to {storage_id}')
                        msg = await msg.edit_text(text=response_text)
                        await tgbot.dialog_append(msg, response_text, config.Role_ASSISTANT)
                    except (BotKicked, BotBlocked):
                        # Бот был исключён из чата, удаляем данные о чате
                        await dp.storage.reset_data(chat=storage_id)
                    except:
                        traceback.print_exc()
        await asyncio.sleep(3600)  # ждём час перед следующей проверкой


def storage_to_chat_id(storage_id):
    thread_id = None
    if '&' in storage_id:
        chat_id, thread_id = storage_id.split('&', maxsplit=1)
    else:
        chat_id = storage_id
    return chat_id, thread_id
