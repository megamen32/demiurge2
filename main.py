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
import time
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from json import JSONDecodeError

import aiogram.utils.exceptions
import tiktoken
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
from config import TELEGRAM_BOT_TOKEN, CHATGPT_API_KEY, get_first_word, bot
from datebase import Prompt, ImageUnstability, User, get_user_balance, PaymentInfo, update_model_usage
from draw import  draw_and_answer, upscale_image_imagine

# Установите ваш ключ OpenAI
from gpt import process_queue, gpt_acreate, count_tokens, summary_gpt
from image_caption import image_caption_generator
from telegrambot.handlers import MessageLoggingMiddleware, create_user
from tgbot import dialog_append
from memory import dp
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
        start += end
        end += 4090
    elif action == "prev":
        start =max(0,start- 4090)
        end -= start

    text = await get_history(callback_query.message)



    text,kb=format_history(text,start, end)

    await bot.edit_message_text(text=text, chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id, reply_markup=kb,ignore=True)


def format_history(original_text, start=0, end=4090):
    # Форматируем историю
    formatted_text = ''
    text = original_text[start:end]


    for line in text.split('\n'):
        if ": " in line:
            role, message = line.split(": ", 1)
            formatted_text += f"*{role.strip('*')}*: {message}\n\n"
        else:
            formatted_text += line + "\n"

    # Кнопки для навигации
    keyboard = InlineKeyboardMarkup()
    formatted_text=formatted_text[:4096]
    last_known_world = formatted_text.rstrip('\n')[-1]
    try:
        end=original_text.rfind(last_known_world)
    except:
        logging.error(f"not found end in {last_known_world} {original_text[-15:]}")
    if len(original_text)-10 > end:
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
        await bot.send_message(chat_id=message.chat.id,reply_to_message_id=message.message_id,text=text, reply_markup=kb, parse_mode='Markdown',ignore=True)
    except:
        try:
            await bot.send_message(chat_id=message.chat.id,reply_to_message_id=message.message_id,text=text, reply_markup=kb,ignore=True)
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
                role = user_data.get('ASSISTANT_NAME_SHORT', config.ASSISTANT_NAME_SHORT)+': '
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
        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text='История диалога очищена.',ignore=True)
    except:
        traceback.print_exc()
        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text='Не удалось очистить историю диалога.')


@dp.message_handler(commands=['summarize'])
async def summarize_history(message: types.Message):
    msg = await message.reply('...')
    try:
        user_data, chat_id = await get_chat_data(message)
        await do_short_dialog(chat_id, user_data,force=True)
        summary = await get_history(message)
        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=f"История диалога была суммирована:\n{summary[:4096]}")
    except:
        traceback.print_exc()
        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text='Не удалось получить ответ от Демиурга')



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
        asyncio.create_task(bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=f'Вы сказали:\n{text[:4000]}'))


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
        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text='Не удалось получить ответ от Демиурга')


@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    msg = await message.reply('...')
    try:

        user_data, chat_id = await get_chat_data(message)
        if user_data.get('mute',False):
            return

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
            await bot.delete_message(msg.chat.id, msg.message_id,thread_id=msg.message_thread_id)
            return

        text = await asyncio.get_running_loop().run_in_executor(None, image_caption_generator, destination)
        user = message.from_user
        content = f'User sent an image, which was recognized with the following caption: "{text}"'
        if message.caption:
            content += f'. User provided the following message with the image: "{message.caption}"'
        await dialog_append(message, content, config.Role_USER)
        asyncio.create_task(bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=f'Вы send photo:\n{text}'))
        return await handle_message(message, role='system')
    except:
        traceback.print_exc()
        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text='Не удалось получить ответ от Демиурга')


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
        asyncio.create_task(bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=f'Вы сказали:\n{text}'))
        return await handle_message(message)
    except:
        traceback.print_exc()
        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text='Не удалось получить ответ от Демиурга')



lazy_model=None
@dp.message_handler(commands=['calc'])
async def handle_calc(message: types.Message):
    from gensim.models import KeyedVectors
    from tqdm import tqdm
    global lazy_model
    try:
        msg=await message.answer('...')
        cmd,txt = message.get_full_command()
        words=re.split('\+|-| ', message.get_args())
        result_words = []
        operators = {'+', '-'}
        current_op = '+'
        current_word = None
        if lazy_model is None:
            lazy_model =await asyncio.get_running_loop().run_in_executor(None,lambda :KeyedVectors.load_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True))

        pbar = tqdm(total=len(words), desc='Processing words', dynamic_ncols=True)

        for word in words:
            pbar.update()
            if word in operators:
                current_op = word
            elif current_word is None:
                current_word = word
            else:
                if current_op == '+':
                    similar_word = lazy_model.most_similar(positive=[current_word, word])[0]
                else:
                    similar_word = lazy_model.most_similar(positive=[current_word], negative=[word])[0]
                result_words.append(similar_word[0])
                current_word = None
        pbar.close()

        if current_word is not None:
            result_words.append(current_word)

        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text= ' '.join(result_words))
    except:
        traceback.print_exc()
        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=traceback.format_exc())
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
    await bot.edit_message_text(functions_info, chat_id=chat_id, message_id=callback_query.message.message_id,
                                reply_markup=InlineKeyboardMarkup().add(*btn))


    # Ответить на callback_query, чтобы убрать кружок загрузки на кнопке

@dp.message_handler(commands=['tts'])
async def switch_tts_mode(message: types.Message):
    # Получение данных пользователя
    user_data, chat_id = await get_chat_data(message)


    use_tts = user_data.get('tts', config.TTS )

    # Переключение режима use_gpt_4
    use_tts = not use_tts

    # Сохранение нового значения в данных пользователя
    user_data['tts'] = use_tts
    await dp.storage.set_data(chat=chat_id, data=user_data)

    # Отправка сообщения пользователю об изменении режима
    await message.reply(f"Text to speach mode is now {'ON' if use_tts else 'OFF'}.")
@dp.message_handler(commands=['mute'])
async def switch_mute_mode(message: types.Message):
    # Получение данных пользователя
    user_data, chat_id = await get_chat_data(message)


    use_tts = user_data.get('mute', False )

    # Переключение режима use_gpt_4
    use_tts = not use_tts

    # Сохранение нового значения в данных пользователя
    user_data['mute'] = use_tts
    await dp.storage.set_data(chat=chat_id, data=user_data)

    # Отправка сообщения пользователю об изменении режима
    await message.reply(f"Mute mode is now {'ON' if use_tts else 'OFF'}.")


@dp.message_handler(commands=['gpt4'])
async def switch_gpt4_mode(message: types.Message):
    # Получение данных пользователя
    user_data, chat_id = await get_chat_data(message)
    user,_=User.get_or_create(user_id=message.from_user.id)
    balance=await get_user_balance(message.from_id,message=message)

    # Получение текущего значения use_gpt_4 или получение значения по умолчанию, если оно ещё не установлено
    use_gpt_4 = user_data.get('gpt-4', config.useGPT4)
    if  balance['total_balance']<-5 and (not user.is_admin ) and use_gpt_4==False :
        return await message.reply(f"Im sorry but you need more money. Press /balance")

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
        if user_data.get('mute',False):
            return

        if 'history' not in user_data:
            user_data['history'] = []
        try:
            # Находим и заменяем отредактированное сообщение в истории
            msg_id = None
            for msg in reversed(user_data['history']):
                if  msg['message_id'] == message.message_id:
                    msg_id=j = user_data['history'].index(msg)
                    await tgbot.dialog_edit(message.chat.id, message.message_id, message.text, message.message_thread_id)
                    #await dp.storage.set_data(chat=chat_id,data=user_data)
                    while  j+1<len(user_data['history']) and  user_data['history'][j]['role']not in [config.Role_ASSISTANT] :
                        debug_msg=user_data['history'][j]
                        j+=1
                    old=user_data['history'][j]
                    break
            #user_data['history'] = user_data['history'][:msg_id]
            #await dp.storage.set_data(chat=chat_id, data=user_data)
            #tgbot.dialog_edit(chat_id=chat_id,message_id=message.message_id,)
        except:
            traceback.print_exc()


        nmsg=None
        try:
            if 'old' in locals():
                nmsg=await bot.edit_message_text(chat_id=chat_id,message_id=old['message_id'],text=f'Rethinking..\n{old["content"]}')
        except:traceback.print_exc()
        if nmsg is None:
            nmsg=message
            await dialog_append(message, message.text)
        await handle_message(nmsg,edit=True)


    except:
        traceback.print_exc()
        await message.answer('Не удалось получить ответ от Демиурга')

@dp.message_handler(commands=['send_all'])
async def send_all(message: types.Message):
    message_text = message.get_args()  # Получаем текст после команды /send_all
    if not message_text:
        # Если текста нет, отправляем сообщение об ошибке
        await bot.send_message(message.chat.id, "Пожалуйста, предоставьте текст сообщения после команды /send_all")
        return

    r = redis.Redis(host='localhost', port=6379, db=0)
    all_keys = r.keys("demiurge*")
    markdown=True
    for key in all_keys:
        storage_id = key.decode("utf-8").split(":")[1]
        chat_id, thread_id =  storage_to_chat_id(storage_id)
        try:
            if markdown:
                try:
                    await bot.send_message(chat_id=chat_id,reply_to_message_id=thread_id, text=message_text,parse_mode='Markdown')

                except aiogram.utils.exceptions.CantParseEntities:
                    markdown=False
            if not markdown:
                await bot.send_message(chat_id=chat_id, reply_to_message_id=thread_id,text=message_text)
        except (BotKicked, BotBlocked):
            # Бот был исключён из чата, удаляем данные о чате
            await dp.storage.reset_data(chat=storage_id)
        except Exception as e:
            # Обработка случая, если бот был исключен из чата или возникла другая ошибка
            await message.answer(f"Failed to send a message to chat {chat_id}. Error: {e}")

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

from yookassa import Payment
import uuid
@dp.message_handler(commands=['balance'])
async def send_balance(message: types.Message):
    user_id = message.from_id
    balance_data = await get_user_balance(user_id,message=message)

    if "error" in balance_data:
        await message.reply(f"🚫 Ошибка: {balance_data['error']}")
        return

    response_text = "📊 Ваш баланс и расходы по моделям:\n"

    for model_name, balance in balance_data["balances"].items():
        response_text += f"\n🤖 Модель: {model_name}\n"
        response_text += f"📥 Входящие символы: {balance['input_chars']}\n"
        response_text += f"📤 Исходящие символы: {balance['output_chars']}\n"
        response_text += f"💲 Стоимость: ${balance['total_cost']:.4f}\n"

    response_text += f"\n💰 Доходы: ${balance_data['total_payments']:.4f}"
    response_text += f"\n💰 Общий баланс: ${balance_data['total_balance']:.4f}"

    # Создаем inline-клавиатуру
    keyboard = InlineKeyboardMarkup()

    # Добавляем кнопки для пополнения баланса
    keyboard.add(InlineKeyboardButton("💳 Пополнить на 100 руб.", callback_data="buy_100"))
    keyboard.add(InlineKeyboardButton("💳 Пополнить на 500 руб.", callback_data="buy_500"))
    keyboard.add(InlineKeyboardButton("💳 Пополнить на 1000 руб.", callback_data="buy_1000"))

    # Отправляем сообщение с клавиатурой
    await message.reply(f"{response_text}\n\n💵 Выберите сумму для пополнения:", reply_markup=keyboard)
async def run_in_executor(func, *args):
    loop=asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, func, *args)


async def check_payment_status(payment_id,user_id):
    while True:
        payment :Payment= await run_in_executor(Payment.find_one, payment_id)
        if payment.status == 'succeeded':
            pay=PaymentInfo.create(amount=float(payment.amount.value),user=user_id,)
            # Платеж успешно завершен
            # Здесь ваш код для обработки успешного платежа
            return True
        elif payment.status == 'canceled':
            # Платеж был отменен
            # Здесь ваш код для обработки отмененного платежа
            return False
        await asyncio.sleep(30)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('buy_'))
async def process_callback_buy(callback_query: types.CallbackQuery):
    amount = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id

    message = await callback_query.message.edit_text('Пожалуйста, подождите...')

    try:
        payment = await run_in_executor(
            Payment.create, {
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/demiurge_space_bot"
                },
                "capture": True,
                "description": f"Пополнение баланса на {amount} руб."
            }, uuid.uuid4()
        )

        if payment.confirmation and payment.confirmation.confirmation_url:
            await message.edit_text(f"Пожалуйста, перейдите по [ссылке]({payment.confirmation.confirmation_url}) для завершения платежа.", parse_mode='Markdown')
            is_payd = asyncio.create_task(check_payment_status(payment.id, user_id=callback_query.from_user.id))
            text = 'Оплачено' if await is_payd else 'Отменено'
            await message.edit_text(text)
            await send_balance(callback_query.message)

        else:
            await message.edit_text("Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже.")

    except Exception as e:
        traceback.print_exc()
        await message.edit_text(f"Произошла ошибка: {str(e)}")

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

    chat_response = await gpt_acreate(model='gpt-3.5-turbo-0613', messages=user_data['history'],user_id=message.from_user.id)
    response_text = chat_response['choices'][0]['message']['content']

    while ":" in response_text and len(response_text.split(":")[0].split()) < 5:
        response_text = response_text.split(":", 1)[1].strip()

    msg = await message.answer(response_text)
    ASSISTANT_NAME_SHORT = user_data.get('ASSISTANT_NAME_SHORT', config.ASSISTANT_NAME_SHORT)
    user_data['history'].append(
        {"role": "assistant", "content": f"{ASSISTANT_NAME_SHORT}:{response_text}", 'message_id': msg.message_id})


from asyncio import CancelledError, Future

processing_tasks = {}

@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_message(message: types.Message, role='user',edit=False):
    global managing_dialog_locks
    global processing_tasks

    user_data, chat_id = await get_chat_data(message)
    if user_data.get('mute',False):
        return None
    async with managing_dialog_locks[chat_id]:

        # Получите текущую задачу обработки для этого пользователя (если есть)

        current_processing_task = processing_tasks.get(chat_id, None)

        # Если задача обработки уже запущена, отмените ее
        if current_processing_task:
            current_processing_task.cancel()
            try:
                await current_processing_task
            except CancelledError:
                pass
            user_data['history']=[msg for msg in user_data['history'] if msg['content'].strip()!='...']
            await dp.storage.set_data(chat=chat_id,data=user_data)

        # Запуск новой задачи обработки с задержкой
        processing_task = asyncio.create_task(wait_and_process_messages(chat_id, message, user_data, role,edit=edit))
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
dialog_locks = defaultdict(lambda :asyncio.Lock())
managing_dialog_locks = defaultdict(lambda :asyncio.Lock())
async def process_function_call(function_name, function_args, message, step=0):
    process_next = False
    try:
        function_args = json.loads(function_args)
    except JSONDecodeError:
        function_args = function_args

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

        asyncio.create_task( draw_and_answer(image_description_, message.chat.id, message.message_thread_id,message.from_user.id))
        response_text=None
        process_next = False

    elif function_name == 'web' or function_name=='extract_webpage_content' or function_name== 'open_link':
        url_ = function_args.get('url', '')
        question = function_args.get('question', '')
        user_data, storage_id = await get_chat_data(message)
        message.text = f"/{function_name} {url_}"
        model='gpt-3.5-turbo' if not  user_data.get('gpt-4',config.useGPT4) else 'gpt-4'
        response_text, err = await function_web(url_,question,model)
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
        if not isinstance(function_args,str):
            code = function_args.get('code', function_args)
        else:
            code=function_args
        res = execute_python_code(code)
        response_text = {'code':code,'result':res}
    else:
        raise Exception(f"There is no {function_name} funciton")
    if response_text is not None and not isinstance(response_text,str):
        response_text = json.dumps(response_text, ensure_ascii=False,default=str)
    return response_text, process_next



async def wait_and_process_messages(chat_id, message, user_data, role,edit=False):
    global dialog_locks
    user_data, chat_id = await get_chat_data(message)
    if user_data.get('mute',False):
        return
    response_text=None
    cancel_event=asyncio.Event()
    while True:
        try:
            msg = await message.reply('...') if not edit else message


            break
        except RetryAfter as e:
            await asyncio.sleep(e.timeout)
            continue

    lock = dialog_locks[chat_id]

    try:
        async with lock:
            step=0
            while step<3:
                step+=1
                user_data, chat_id = await get_chat_data(message)
                balance = await get_user_balance(message.from_id,message=message)

                # Получение текущего значения use_gpt_4 или получение значения по умолчанию, если оно ещё не установлено
                use_gpt_4 = user_data.get('gpt-4', config.useGPT4)
                user=create_user(message)
                if 'total_balance' in balance and balance['total_balance'] < -5 and (not user.is_admin) and use_gpt_4 == True:
                    user_data['gpt-4']=False
                    await dp.storage.set_data(chat=chat_id,data=user_data)
                    await message.reply(f"Im sorry but you run out off balance. And need more money. Press /balance. switching to gpt-3.5")



                functions=user_data.get('functions',config.functions)
                start_text =  get_start_text(user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME))
                gpt4 = user_data.get('gpt-4', config.useGPT4)
                phrases = [
                    "Будим питона 🐍…",
                    "Заводим мозги 💭…",
                    "Инициализируем креатив 🚀…",
                    "Оживляем байт-коды… 🧬",
                    "Перебираем 0 и 1… 💾",
                    "Производим магию с кодом 🎩🐇",
                    "Собираем пазлы байт-кодов 🧩...",
                    "Устраиваем байт-код вечеринку 🥳...",
                    "Соединяем квантовые состояния 🧲...",
                    "Читаем книгу по питону 📖...",
                    "Будим алгоритмы 💤…",
                    "Выдумываем новый код 💡...",
                    "Собираем данные в одну кучу🔍...",
                    "Уточняем векторное пространство📍...",
                    "Разогреваем нейроны🔥...",
                    "Запасаемся кофе для долгой ночи кодинга ☕️...",
                    "Разгоняем код до световой скорости🌠...",
                    "Будим код, он уснул на клавиатуре💤...",
                    "Связываем данные с помощью магии🔮...",
                    "Повышаем концентрацию кода... 🎯"
                ]
                choice = random.choice(phrases)
                stream=True
                if not stream:
                    asyncio.create_task(progress_bar(choice, msg, 120 if gpt4 else 15, cancel_event))
                gpt_model = "gpt-3.5-turbo-0613" if not gpt4 else 'gpt-4-0613'
                user_data_history_ = [{'role': 'system', 'content': start_text}, ] + user_data['history']
                if not stream:
                    chat_response = asyncio.create_task( gpt_acreate(
                        model=gpt_model,
                        messages=user_data_history_,
                        functions=functions,
                        function_call="auto",
                        user_id=message.from_user.id,
                        stream=stream
                    ))
                else:
                    chat_response = await gpt_acreate(
                        model=gpt_model,
                        messages=user_data_history_,
                        functions=functions,
                        function_call="auto",
                        user_id=message.from_user.id,
                        stream=stream
                    )

                if not stream:
                    chat_response=await asyncio.wait_for(chat_response,120)
                    cancel_event.set()
                else:

                        msg.text=''
                        chat_response=await chat_response
                        new_text=''
                        start_time=time.time()
                        func_call = {
                            "name": None,
                            "arguments": "",
                        }
                        async for chunk in chat_response:
                            delta = chunk['choices'][0]['delta']
                            if 'content' in chunk['choices'][0]['delta'] and chunk['choices'][0]['delta']['content']:
                                new_text+=chunk['choices'][0]['delta']['content']

                            elif "function_call" in delta:
                                if "name" in delta.function_call:
                                    func_call["name"] = delta.function_call["name"]
                                    new_text+=func_call["name"]
                                if "arguments" in delta.function_call:
                                    func_call["arguments"] += delta.function_call["arguments"]
                                    new_text+=delta.function_call["arguments"].replace(r'\n','\n\n')
                            if time.time() - start_time >= 5:
                                # cancel_event.set()
                                try:
                                    msg = await msg.edit_text(msg.text + new_text)
                                except RetryAfter as e:
                                    await asyncio.sleep(e.timeout)
                                new_text = ''
                                start_time = time.time()


                        chat_response=chunk
                        enc = tiktoken.encoding_for_model(gpt_model)

                        update_model_usage(message.from_user.id, gpt_model, gpt.num_tokens_from_messages(user_data_history_),len(enc.encode(msg.text+new_text)))
                        if not func_call['name']:
                            chat_response['choices'][0]['message']={'content':msg.text+new_text}
                        else:
                            chat_response['choices'][0]['message']={'function_call':func_call}


                if 'message' in chat_response['choices'][0] and 'function_call' in chat_response['choices'][0]['message'] :
                    function_call = chat_response['choices'][0]['message']['function_call']
                    try:
                        response_text, process_next = await process_function_call(function_call['name'],
                                                                              function_call['arguments'], message)
                    except:
                        response_text=traceback.format_exc(0,False)
                        process_next=False


                    formatted_function_call =function_call["arguments"].replace(r'\n','\n')
                    if process_next:
                        message.text = response_text
                        role = config.Role_ASSISTANT
                        user_data, chat_id = await dialog_append(message, text=response_text, role='function',
                                                                 name=function_call['name'])
                        ans=f'{function_call["name"]}(\n{formatted_function_call}\n) => \n{response_text if response_text else ""}'
                        if function_call["name"]  in ['python']:
                            await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=ans[:4096])
                            msg = await message.reply('...')
                        continue
                    response_text = f'{function_call["name"]}(\n{formatted_function_call}\n) => \n{response_text if response_text else ""}'
                    if function_call["name"] in ['draw']:
                        await bot.delete_message(msg.chat.id, msg.message_id,thread_id=msg.message_thread_id)



                else:#not a function
                    response_text = chat_response['choices'][0]['message']['content']#.replace(f"{user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME)}:",'').replace(f"{user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME)} :",'').replace(f"{user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME)}",'')


                break
        user_data, chat_id = await get_chat_data(message)
        asyncio.create_task(do_short_dialog(chat_id, user_data))
        if response_text:
            asyncio.create_task( send_response_text(msg, response_text))
    except CancelledError:
        cancel_event.set()
        await bot.delete_message(msg.chat.id, msg.message_id,thread_id=msg.message_thread_id)
    except aiogram.utils.exceptions.MessageNotModified:
        pass
    except:
        cancel_event.set()
        traceback.print_exc()
        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=msg.text+'\n'+traceback.format_exc())


def get_start_text(character):
    start_text = f"You are a telegram bot responding in Markdown format. Your role is based on the following description: '{character}'. In any situation, you must act and respond strictly in accordance with the image of your character!"
    return start_text


async def send_response_text(msg, response_text):
    if response_text:
        parse_modes = ['Markdown', None]

        sended=False
        for mode in parse_modes:
            try:
                # Если parse_mode = None, параметр parse_mode не будет передан
                await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=response_text[:4096], parse_mode=mode)
                sended=True
                data,chat_id=await get_chat_data(message=msg)
                if config.TTS or data.get('tts',config.TTS):
                    asyncio.create_task(send_tts(msg, response_text))
                break  # если сообщение было успешно отправлено, прекратить перебор
            except Exception as e:
                traceback.print_exc()
                continue
        if not sended:
            await msg.answer(response_text[:1000])
            await bot.delete_message(msg.chat.id, msg.message_id,thread_id=msg.message_thread_id)
    else:
        await bot.delete_message(msg.chat.id, msg.message_id,thread_id=msg.message_thread_id)


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
            summary = await summary_gpt(remaining_history,user_id=chat_id)
            # Add the summary at the start of our history
            reduced_history = [{"role": config.Role_ASSISTANT, "content": summary}] + reduced_history

        # Update the user's history
        user_data['history'] = reduced_history

        # Save the updated history to the user's data
        await dp.storage.set_data(chat=chat_id, data=user_data)
        send_summary_to_user=user_data.get('summary',False)
        if summary and send_summary_to_user:
            chat_id,thread_id=storage_to_chat_id(chat_id)
            try:
                await bot.send_message(chat_id=chat_id,text=f"Summary :{summary}"[:4096],reply_to_message_id=thread_id,ignore=True)
            except:
                traceback.print_exc()
        return summary


async def send_tts(message,  response_text):
    if False:
        voice_filename = await asyncio.get_running_loop().run_in_executor(None, text_to_speech, (response_text))
    else:
        voice_filename = await text_to_speech2(response_text)
    if os.path.exists(voice_filename):
        with open(voice_filename, 'rb') as audio:
            await message.reply_voice(voice=audio, caption=response_text[:1024])



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
            if datetime.now() - last_message_time > timedelta(hours=24+12):  # если прошло 24 часа
                # генерируем сообщение
                user_data['last_message_time'] = datetime.now().timestamp()
                await dp.storage.set_data(chat=storage_id, data=user_data)
                if random.random()>0.9:
                    ASSISTANT_NAME = user_data.get('ASSISTANT_NAME', config.ASSISTANT_NAME)

                    await tgbot.dialog_append_raw(storage_id,
                                                  f'Ваша следующая задача - мотивировать пользователя продолжить разговор. Пользователь не взаимодействовал с вами уже более {(datetime.now() - last_message_time).total_seconds()/60/60} часов.',None, 'system')
                    user_data = await dp.storage.get_data(chat=storage_id)

                    try:
                        msg = await bot.send_message(chat_id=chat_id, text='hmm...', reply_to_message_id=thread_id)

                        history_for_openai = [{'role': 'system',
                                               'content': get_start_text(ASSISTANT_NAME)},
                                              ] + user_data['history']
                        chat_response = await gpt_acreate(
                            model="gpt-3.5-turbo-0613",
                            messages=history_for_openai,
                            user_id=chat_id
                        )
                        response_text = chat_response['choices'][0]['message']['content']

                        # отправляем сообщение

                        logging.info(f'sended {response_text} to {storage_id}')
                        msg = await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=response_text)
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
