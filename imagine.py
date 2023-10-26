import asyncio
import io
import logging
import re
import traceback

import requests
from aiogram import types

import aiohttp
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import BadRequest
from bs4 import BeautifulSoup



import tgbot
import trends
from config import dp,bot
from datebase import ImageMidjourney
from draw import improve_prompt, progress_bar
from gpt import shorten
from tgbot import get_chat_data


async def generate_image_midjourney(prompt):
    payload = {
        "prompt": prompt
    }
    url = "http://localhost:5001/api/send_and_receive"
    headers = {
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            response_json = await resp.json()
            print(resp.status,resp.content)
            url = response_json["latest_image_url"]

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            response_bytes = await resp.read()

    return response_bytes, url


async def upscale_image(file_name, number):
    url = f"http://localhost:5001/upscale"
    params = {
        "file_name": file_name,
        "number": number
    }
    steps = 0
    async with aiohttp.ClientSession() as session:
        while steps < 6:
            try:
                steps += 1
                if steps != 1:
                    await asyncio.sleep(30)
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:

                        response_json = await resp.json()
                        if 'error' in response_json:
                            logging.error(response_json)
                            continue
                        upscaled_url = response_json["latest_image_url"]
                        print('Upscale successful!')
                        break
                    else:
                        print(f'Upscale error: {resp.status}')
                        upscaled_url = None
            except:
                traceback.print_exc()

    if upscaled_url:
        async with aiohttp.ClientSession() as session:
            async with session.get(upscaled_url) as resp:
                response_bytes = await resp.read()

        return io.BytesIO(response_bytes)

    return None


@dp.message_handler(commands=['imagine', 'i'])
async def handle_imagine(message: types.Message):
    old = prompt = message.get_args()
    if not prompt:
        await message.reply("Please provide a description for the image.")
        return

    msg = await message.reply("Creating image...")
    try:
        chat_id = message.chat.id

        prompt = await improve_prompt(prompt, chat_id, message.from_user.id)
        asyncio.create_task(bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text=prompt))
        img_data = None
        try:
            img_data, image_url = await generate_image_midjourney(prompt)
            # Extract file name from the URL

            img_db = ImageMidjourney.create(prompt=prompt, url=image_url)

        except:
            traceback.print_exc()

        if img_data is None:
            await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text="An error occurred while generating the image.")
            return

        kb = InlineKeyboardMarkup(resize_keyboard=True)

        btns = [InlineKeyboardButton(text=f"U {_ + 1}", callback_data=f"imagine_{_ + 1}_{img_db.id}") for _ in range(4)]
        kb.row(*btns)
        photo = await message.answer_photo(photo=io.BytesIO(img_data), caption=prompt, reply_markup=kb)
    except:
        traceback.print_exc()
        await message.answer('An error occurred while generating the image.')
    finally:
        await bot.delete_message(msg.chat.id, msg.message_id,thread_id=msg.message_thread_id)


@dp.callback_query_handler(lambda c: c.data.startswith("imagine_"))
async def handle_draw_callback(query: types.CallbackQuery):
    _, number, img_id = query.data.split("_")
    number = int(number)
    img_db = ImageMidjourney.get(id=img_id)
    await query.answer(f'... upscaling {number}')
    msg = await query.message.reply(f'... upscaling {img_db.prompt} {number}')
    asyncio.create_task(progress_bar(f'Upscaling #{number} {img_db.prompt}', msg))
    if img_db:
        img_data = None
        try:
            img_data = await upscale_image(img_db.filename(), number)
        except:
            traceback.print_exc()
        if img_data:
            await query.message.answer_photo(photo=img_data, caption=img_db.prompt)
            await bot.delete_message(msg.chat.id, msg.message_id,thread_id=msg.message_thread_id)
            return
    await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text="An error occurred while upscalling the image.")


@dp.message_handler(commands=['web'])
# @dp.message_handler(regexp=r'https?://[^\s]+')
async def handle_web(message: types.Message):
    try:
        promt = None
        try:
            promt = message.get_args()
        except:
            pass
        if promt is None or not any(promt):
            promt = message.text
        msg = await message.reply(f'opening link... {promt}')
        text, _ = await function_web(promt, None)
        message.text = text
        try:
            await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=text[:4000])
        except BadRequest:
            await msg.reply(text[:4000])

        message_text = message.text
        message.text = await shorten(message_text)
        await tgbot.dialog_append(message, message.text, role='function', name='open_link')

        from main import handle_message
        return await handle_message(message, role='function')
    except:
        traceback.print_exc()
        await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text='Не удалось скачать сайт')


async def function_web(url, question=None,model='gpt-3.5-turbo'):
    from llama_index import Response
    url = url
    err = False
    text = None
    try:
        text = await asyncio.get_event_loop().run_in_executor(None, find_relevant_section, url, question,model)
        if type(text) is Response:
            text=text.response
    except Exception as e:
        text = str(e)
        err = True

    return text, err


def open_url(url):

    smart = True
    if smart:
        from goose3 import Goose

        try:
            g = Goose()
            article = g.extract(url=url)
            if len(article.cleaned_text) > 500:
                return article.cleaned_text
            from newspaper import Article
            article = Article(url)
            article.download()
            article.parse()
            if article.text:
                text = f'{article.text}'
            smart = len(article.text) > 500
        except:
            smart = False
    if not smart:
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')

        # Создаем пустую строку для хранения текста
        text = ""

        # Добавляем заголовки и абзацы с соответствующим форматированием
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'li', 'a']):
            if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text += '\n' + tag.text.strip().upper() + '\n'  # Заголовки в верхнем регистре
            elif tag.name == 'p':
                text += '\n' + tag.text.strip() + '\n'  # Абзацы с переносами строк
            elif tag.name == 'li':
                text += '  - ' + tag.text.strip() + '\n'  # Элементы списка с тире
            else:
                text += tag.text.strip() + ' '  # Остальные элементы без дополнительного форматирования

    return text


from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


def find_relevant_section(url, question=None,model='gpt-3.5-turbo'):
    if not question and ' ' in url:
        url, question = url.split(' ', maxsplit=1)
    if 'youtube.com/' in url:

        from memory import smart_youtube_reader
        return smart_youtube_reader(url,question,model)
    text = open_url(url)
    if not question:
        if type(text) is list:
            text=' '.join(text)
        return text
    # Разбиваем текст на абзацы
    if type(text) == str:
        paragraphs = text.split('\n')
    else:
        paragraphs=text

    # noinspection PyUnreachableCode
    if True:
        # Используем TF-IDF для векторизации абзацев и вопроса
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(paragraphs + [question])

        # Вычисляем косинусное сходство между вопросом и каждым абзацем
        cosine_similarities = np.dot(tfidf_matrix[-1], tfidf_matrix[:-1].T).toarray()[0]

        # Находим индекс наиболее релевантного абзаца
        relevant_index = np.argmax(cosine_similarities)

        # Возвращаем наиболее релевантный абзац
        return paragraphs[relevant_index]
    #await query_index(None, text, [file_path.name])


@dp.message_handler(commands=['search'])
async def handle_search(message: types.Message):
    promt = None
    try:
        promt = message.get_args()
    except:
        pass
    if promt is None or not any(promt):
        promt = message.text
    msg = await message.reply(f'searching for... {promt}')

    news = await function_search(promt)

    text = '\n'.join(news)
    # text+='\n'.join([f'{n}' for n in tags])

    await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=text)
    await tgbot.dialog_append(message, news, 'function', name='search')
    from main import handle_message
    return await handle_message(message, role='system')


async def function_search(promt):
    loop = asyncio.get_running_loop()
    # tags=loop.run_in_executor(None,trends.get_tags)
    news = await loop.run_in_executor(None, trends.get_news, promt)
    news = [{'Title': result['title'], 'url': result['link'], 'Snippet': result['snippet']} for result in news]
    return news


def process_search_commands(response_text, message, pattern='/search (.+)\/?', coroutine=handle_search):
    while True:
        prompts = re.findall(pattern, response_text)
        if not prompts:
            break
        for prompt in prompts:
            message.text = prompt
            asyncio.create_task(coroutine(message))
        response_text = re.sub(pattern, '', response_text)
    return response_text


def generate_image_stability(prompt, style='photo'):
    from unstabilityai import fetch_image
    files = fetch_image(prompt, style)
    return files


async def agenerate_image_stability(prompt, style='photo'):
    return await asyncio.get_running_loop().run_in_executor(None, generate_image_stability, prompt, style)


@dp.message_handler(commands=['stable', 's'])
async def handle_imagine(message: types.Message):
    old = prompt = message.get_args()
    if not prompt:
        await message.reply("Please provide a description for the image.")
        return

    msg = await message.reply("Creating image...")
    try:
        chat_id = message.chat.id

        user_data, user_id = await get_chat_data(message)
        user_data['history'].extend([
            {'role': 'user', 'content': f'{message.from_user.full_name or message.from_user.username}: /draw {old}'}])
        await dp.storage.set_data(chat=chat_id, data=user_data)
        prompt = await improve_prompt(prompt, chat_id, message.from_user.id)
        asyncio.create_task(bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text=prompt))
        img_data = None
        try:
            img_data = await asyncio.get_running_loop().run_in_executor(None, generate_image_stability, (prompt))
            # Extract file name from the URL



        except:
            traceback.print_exc()

        if img_data is None:
            await bot.edit_message_text(chat_id=msg.chat.id,message_id=msg.message_id,text="An error occurred while generating the image.")
            return

        kb = InlineKeyboardMarkup(resize_keyboard=True)
        for photo in img_data:
            asyncio.create_task(message.answer_photo(photo=io.BytesIO(photo), caption=prompt, reply_markup=kb))
        await bot.delete_message(msg.chat.id, msg.message_id,thread_id=msg.message_thread_id)
    except:
        traceback.print_exc()
        await message.answer('An error occurred while generating the image.')
