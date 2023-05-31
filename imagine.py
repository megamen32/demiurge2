import asyncio
import io
import re
import traceback

import requests
from aiogram import types

import aiohttp
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bs4 import BeautifulSoup

import config
import trends
from config import dp
from datebase import ImageMidjourney
from draw import improve_prompt
from gpt import shorten


async def generate_image_midjourney(prompt):
    payload = {
        "prompt": prompt
    }
    url = "http://localhost:5000/api/send_and_receive"
    headers = {
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            response_json = await resp.json()
            url = response_json["latest_image_url"]

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            response_bytes = await resp.read()

    return response_bytes,url

async def upscale_image(file_name, number):
    url = f"http://localhost:5000/upscale"
    params = {
        "file_name": file_name,
        "number": number
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                print('Upscale successful!')
                response_json = await resp.json()
                upscaled_url = response_json["latest_image_url"]
            else:
                print(f'Upscale error: {resp.status}')
                upscaled_url = None

    if upscaled_url:
        async with aiohttp.ClientSession() as session:
            async with session.get(upscaled_url) as resp:
                response_bytes = await resp.read()

        return io.BytesIO(response_bytes)

    return None

@dp.message_handler(commands=['imagine','i'])
async def handle_imagine(message: types.Message):
    old=prompt = message.get_args()
    if not prompt:
        await message.reply("Please provide a description for the image.")
        return

    msg = await message.reply("Creating image...")
    try:
        chat_id=message.chat.id


        user_data = await dp.storage.get_data(chat=chat_id)
        user_data['history'].extend([
            {'role': 'user', 'content': f'{message.from_user.full_name or message.from_user.username}: /draw {old}'}])
        await dp.storage.set_data(chat=chat_id,data=user_data)
        prompt = await improve_prompt(prompt,chat_id)
        asyncio.create_task( msg.edit_text(prompt))
        img_data=None
        try:
            img_data, image_url = await generate_image_midjourney(prompt)
            # Extract file name from the URL

            img_db=ImageMidjourney.create(prompt=prompt,url=image_url)

        except:
            traceback.print_exc()

        if img_data is None:
            await msg.edit_text("An error occurred while generating the image.")
            return

        kb = InlineKeyboardMarkup(resize_keyboard=True)

        btns = [InlineKeyboardButton(text=f"U {_ + 1}", callback_data=f"imagine_{_+1}_{img_db.id}") for _ in range(4)]
        kb.row(*btns)
        photo=await message.answer_photo(photo=io.BytesIO(img_data),caption=prompt,reply_markup=kb)
        await msg.delete()
    except:
        traceback.print_exc()
        await message.answer('An error occurred while generating the image.')

@dp.callback_query_handler(lambda c:c.data.startswith("imagine_"))
async def handle_draw_callback(query: types.CallbackQuery):
    _,number,img_id = query.data.split("_")
    number=int(number)
    img_db = ImageMidjourney.get(id=img_id)
    await query.answer(f'... upscaling {number}')
    msg=await query.message.reply(f'... upscaling {img_db.prompt} {number}')
    if img_db:
        img_data=None
        try:
            img_data = await upscale_image(img_db.filename(), number)
        except:
            traceback.print_exc()
        if img_data:
            await query.message.answer_photo(photo=img_data,caption=img_db.prompt)
            await msg.delete()
        else:
            await msg.edit_text("An error occurred while upscalling the image.")

@dp.message_handler(commands=['web'])
@dp.message_handler(regexp=r'https?://[^\s]+')
async def handle_web(message: types.Message):

    try:
        promt=None
        try:
            promt=message.get_args()
        except:
            pass
        if promt is None or not any(promt):
            promt=message.text
        msg = await message.reply(f'opening link... {promt}')
        url = promt
        text = await asyncio.get_event_loop().run_in_executor(None,open_url,(url))
        message.text=text
        await msg.edit_text(message.text[:4096])

        message_text = message.text
        message.text=await shorten(message_text)

        from main import handle_message
        return await handle_message(message,role='system')
    except:
        traceback.print_exc()
        await msg.edit_text('Не удалось скачать сайт')


def open_url(url):
    from newspaper import Article
    article = Article(url)
    article.download()
    article.parse()
    if article.text:
        text = f'Скинул сайт {url}, дата публикации {article.publish_date}, Авторы :{", ".join(article.authors)} вот содержимое: {article.text}'
    else:
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        # извлекаем все элементы <p>
        paragraphs = '\n'.join([ p.text for p in soup.findAll('p')])
        # возвращаем все абзацы в виде строки
        text = f'Скинул сайт {url}, вот содержимое: {paragraphs}'
    return text


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
    loop=asyncio.get_running_loop()
    #tags=loop.run_in_executor(None,trends.get_tags)
    news=await loop.run_in_executor(None,trends.get_news,promt)
    text='\n'.join(news)
    #text+='\n'.join([f'{n}' for n in tags])

    await msg.edit_text(text)
    message.text=f'Search results for "{promt}":\n {text}'
    from main import handle_message
    return await handle_message(message,role='system')

def process_search_commands(response_text,message, pattern='/search (.+)\/?',coroutine=handle_search):
    while True:
        prompts = re.findall(pattern, response_text)
        if not prompts:
            break
        for prompt in prompts:

            message.text=prompt
            asyncio.create_task(coroutine(message))
        response_text = re.sub(pattern, '', response_text)
    return response_text


def generate_image_stability(prompt):
    from unstabilityai import fetch_image
    files=fetch_image(prompt)
    return files


@dp.message_handler(commands=['stable','s'])
async def handle_imagine(message: types.Message):
    old=prompt = message.get_args()
    if not prompt:
        await message.reply("Please provide a description for the image.")
        return

    msg = await message.reply("Creating image...")
    try:
        chat_id=message.chat.id


        user_data = await dp.storage.get_data(chat=chat_id)
        user_data['history'].extend([
            {'role': 'user', 'content': f'{message.from_user.full_name or message.from_user.username}: /draw {old}'}])
        await dp.storage.set_data(chat=chat_id,data=user_data)
        prompt = await improve_prompt(prompt,chat_id)
        asyncio.create_task( msg.edit_text(prompt))
        img_data=None
        try:
            img_data = await asyncio.get_running_loop().run_in_executor(None, generate_image_stability,(prompt))
            # Extract file name from the URL



        except:
            traceback.print_exc()

        if img_data is None:
            await msg.edit_text("An error occurred while generating the image.")
            return

        kb = InlineKeyboardMarkup(resize_keyboard=True)
        for photo in img_data:
            asyncio.create_task( message.answer_photo(photo=types.InputFile(photo),caption=prompt,reply_markup=kb))
        await msg.delete()
    except:
        traceback.print_exc()
        await message.answer('An error occurred while generating the image.')