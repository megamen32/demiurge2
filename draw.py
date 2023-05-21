import re
import traceback

import langdetect
import openai
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


async def improve_prompt(prompt, user_id):
    # Detect the language of the prompt
    try:
        lang = langdetect.detect(prompt)
    except langdetect.lang_detect_exception.LangDetectException:
        lang = 'en'

    # If the language is not English, translate and improve it
    if lang != 'en':
        user_data = await dp.storage.get_data(user=user_id)
        history = user_data.get('history', [])
        history_for_openai = [{"role": item["role"], "content": item["content"]} for item in user_data['history']]

        chat_response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=history_for_openai + [
                {"role": "user",
                 "content": f'translate this prompt from {lang} to English: "{prompt}"'}
            ],
            max_tokens=100
        )

        # Extract the model's response
        improved_prompt = chat_response['choices'][0]['message']['content'].replace('"',''),("'",'')

        # Add translation and improvement to history
        if 'history' in user_data:
            user_data['history'].extend([
                {"role": "user",
                 "content": f'translate this text from {lang} to English: "{prompt}"'},
                {"role": "assistant", "content": f"{improved_prompt}"},
                {"role": "system", "content": f"нарисовал и отправил в чат нарисованную по описанию картинку"},
            ])
        await dp.storage.set_data(user=user_id, data=user_data)

        # Remove the model's name from the response
        improved_prompt = re.sub(r'^.*?:', '', improved_prompt).strip()

        return improved_prompt

    # If the language is English, return the original prompt
    return prompt


@dp.message_handler(commands=['draw'])
async def handle_draw(message: types.Message):
    prompt = message.get_args()
    if not prompt:
        await message.reply("Please provide a description for the image.")
        return

    msg = await message.reply("Creating image...")
    try:
        prompt=await improve_prompt(prompt,message.chat.id)
        img_data = await generate_image(prompt,message.from_user.id)

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
    styles = list(Style.__members__.keys())
    ratios = list(Ratio.__members__.keys())
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Add ratio buttons
    ratio_buttons = [types.KeyboardButton(ratio) for ratio in ratios]
    keyboard.row(*ratio_buttons)

    # Add a separator
    keyboard.row(types.KeyboardButton("-" * 10))

    # Add style buttons in groups of 5
    for i in range(0, len(styles), 5):
        style_buttons = [types.KeyboardButton(style) for style in styles[i:i + 5]]
        keyboard.row(*style_buttons)

    return keyboard


class DrawingSettings(StatesGroup):
    settings=State()
@dp.message_handler(commands=['draw_settings'])
async def handle_draw_settings(message: types.Message,state:FSMContext):
    keyboard = create_settings_keyboard()
    await DrawingSettings.settings.set()
    user_data = await dp.storage.get_data(chat=message.from_user.id)
    style = Style[user_data.get('style', 'ANIME_V2')]
    ratio = Ratio[user_data.get('ratio', 'RATIO_4X3')]

    await message.reply(f"Please choose style and ratio for your drawings.{style} {ratio}", reply_markup=keyboard)
@dp.message_handler(state=DrawingSettings.settings.state)
async def handle_style_and_ratio(message: types.Message,state:FSMContext):
    user_data = await dp.storage.get_data(chat=message.from_user.id)
    text = message.text
    if text in Style.__members__:
        user_data['style'] = text
        await message.reply(f"Set style to {text}.")
    elif text in Ratio.__members__:
        user_data['ratio'] = text
        await message.reply(f"Set ratio to {text}.")
    else:
        await message.reply("Unknown option.")
    await state.finish()
    await dp.storage.set_data(chat=message.from_user.id, data=user_data)
