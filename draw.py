import traceback

from Imaginepy.imaginepy import Imagine, AsyncImagine

from Imaginepy.imaginepy import Imagine, Style, Ratio
import asyncio
import io
from aiogram import types

imagine = None
async def generate_image(prompt: str):
    global imagine
    if imagine is None:
        imagine = AsyncImagine()
    img_data = await imagine.sdprem(
        prompt=prompt,
        style=Style.ANIME_V2,
        ratio=Ratio.RATIO_16X9
    )

    if img_data is None:
        return None



    return img_data

async def upscale_image(img_data):
    global imagine
    if imagine is None:
        imagine = AsyncImagine()
    img_data = await imagine.upscale(image=img_data)
    return img_data

@dp.message_handler(commands=['draw'])
async def handle_draw(message: types.Message):
    prompt = message.get_args()
    if not prompt:
        await message.reply("Please provide a description for the image.")
        return

    msg = await message.reply("Creating image...")
    try:

        img_data = await generate_image(prompt)

        if img_data is None:
            await msg.edit_text("An error occurred while generating the image.")
            return

        img_file = io.BytesIO(img_data)
        img_file.name = f'{prompt}.jpeg'

        await msg.delete()
        photo=await message.answer_photo(photo=img_file,caption=prompt)

        img_data=await upscale_image(img_data)
        if img_data is None:
            await message.answer("An error occurred uppscaling  the image.")
            return

        img_file = io.BytesIO(img_data)
        img_file.name = f'{prompt}-upscale.jpeg'
        await photo.edit_media(media=img_file)
    except:
        traceback.print_exc()
        await msg.edit_text('An error occurred while generating the image.')

