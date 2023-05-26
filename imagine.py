import asyncio
import io
import traceback
from aiogram import types

import aiohttp
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import dp
from datebase import ImageMidjourney
from draw import improve_prompt


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

    return io.BytesIO(response_bytes),url

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
                upscaled_url = response_json["upscaled_image_url"]
            else:
                print(f'Upscale error: {resp.status}')
                upscaled_url = None

    if upscaled_url:
        async with aiohttp.ClientSession() as session:
            async with session.get(upscaled_url) as resp:
                response_bytes = await resp.read()

        return io.BytesIO(response_bytes)

    return None

@dp.message_handler(commands=['imagine'])
async def handle_imagine(message: types.Message):
    prompt = message.get_args()
    if not prompt:
        await message.reply("Please provide a description for the image.")
        return

    msg = await message.reply("Creating image...")
    try:
        prompt=await improve_prompt(prompt,message.chat.id,message.from_user.full_name or message.from_user.username)
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

        kb = InlineKeyboardMarkup()
        for _ in range(4):
            btn = kb.add(InlineKeyboardButton(text=f"U {_ + 1}", callback_data=f"imagine_{_}_{img_db.id}"))
        photo=await message.answer_photo(photo=img_data,caption=prompt,reply_markup=kb)
        await msg.delete()
    except:
        traceback.print_exc()
        await message.answer('An error occurred while generating the image.')

@dp.callback_query_handler(lambda c:c.data.startswith("imagine_"))
async def handle_draw_callback(query: types.CallbackQuery):
    _,number,img_id = query.data.split("_")
    img_db = ImageMidjourney.get(id=img_id)
    await query.answer(f'... upscaling {img_db.prompt} {number}')
    msg=await query.message.reply(f'... upscaling {img_db.prompt} {number}')
    if img_db:
        img_data = await upscale_image(img_db.filename(), number)
        if img_data:
            await query.message.answer_photo(photo=img_data,caption=img_db.prompt)
            await msg.delete()
        else:
            await msg.edit_text("An error occurred while upscalling the image.")

    await query.message.edit_text(img_db.prompt)

