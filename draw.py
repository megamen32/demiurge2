import traceback

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from Imaginepy.imaginepy import Imagine, AsyncImagine

from Imaginepy.imaginepy import Imagine, Style, Ratio
import asyncio
import io
from aiogram import types

from config import dp

imagine = None
async def generate_image(prompt: str, user_id):
    user_data = await dp.storage.get_data(chat=user_id)
    style = Style[user_data.get('style', 'ANIME_V2')]
    ratio = Ratio[user_data.get('ratio', 'RATIO_4X3')]

    global imagine
    if imagine is None:
        imagine = AsyncImagine()
    img_data = await imagine.sdprem(
        prompt=prompt,
        style=style,
        ratio=ratio
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

        img_data = await generate_image(prompt,message.chat.id)

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
        photo2 = await message.answer_photo(photo=img_file, caption=prompt)
        await photo.delete()
    except:
        traceback.print_exc()
        await message.answer('An error occurred while generating the image.')
def create_settings_keyboard():
    styles = Style.__members__
    ratios = Ratio.__members__
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for style in styles:
        keyboard.add(types.KeyboardButton(style))
    for ratio in ratios:
        keyboard.add(types.KeyboardButton(ratio))
    return keyboard

class DrawingSettings(StatesGroup):
    settings=State()
@dp.message_handler(commands=['draw_settings'])
async def handle_draw_settings(message: types.Message,state:FSMContext):
    keyboard = create_settings_keyboard()
    await DrawingSettings.settings.set()
    await message.reply("Please choose style and ratio for your drawings.", reply_markup=keyboard)
@dp.message_handler(state=DrawingSettings.settings.state)
async def handle_style_and_ratio(message: types.Message,state:FSMContext):
    user_data = await dp.storage.get_data(chat=message.chat.id)
    text = message.text
    if text in Style.__members__:
        user_data['style'] = text
        await message.reply(f"Set style to {text}.")
    elif text in Ratio.__members__:
        user_data['ratio'] = text
        await message.reply(f"Set ratio to {text}.")
    else:
        await message.reply("Unknown option.")
    await dp.storage.set_data(chat=message.chat.id, data=user_data)
    await state.finish()
