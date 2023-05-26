import asyncio
import io
import traceback
from aiogram import types

import aiohttp

from config import dp
from draw import improve_prompt


async def generate_image(prompt):
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

    return io.BytesIO(response_bytes)



@dp.message_handler(commands=['imagine'])
async def handle_draw(message: types.Message):
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
            img_data = await generate_image(prompt)
        except:
            traceback.print_exc()

        if img_data is None:
            await msg.edit_text("An error occurred while generating the image.")
            return



        photo=await message.answer_photo(photo=img_data,caption=prompt)
        await msg.delete()
    except:
        traceback.print_exc()
        await message.answer('An error occurred while generating the image.')