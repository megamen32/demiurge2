import random
import re
import traceback

import langdetect
import openai
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton

import config
from Imaginepy.imaginepy import Imagine, AsyncImagine

from Imaginepy.imaginepy import Imagine, Style, Ratio
import asyncio
import io
from aiogram import types

from config import dp, bot
from datebase import Prompt, ImageMidjourney
from gpt import gpt_acreate

MIDJOURNEY = 'MIDJOURNEY'

imagine = None


async def gen_img(prompt, ratio, style):
    if isinstance(style,Style) :
        global imagine
        if imagine is None:
            imagine = AsyncImagine()
        while True:
            img_data_task = asyncio.create_task( imagine.sdprem(
                prompt=prompt,
                style=style,
                ratio=ratio
            ))
            try:
                img_data=await asyncio.wait_for(img_data_task,timeout=10)
                if img_data is None:
                    continue
                break
            except:
                continue
        return img_data,None
    else:
         from imagine import generate_image_midjourney
         img_data,img_url=await generate_image_midjourney(prompt)

         return img_data,img_url


async def upscale_image(img_data):
    global imagine
    if imagine is None:
        imagine = AsyncImagine()
    img_data = await imagine.upscale(image=img_data)
    return img_data


async def improve_prompt(prompt, user_id,name):
    # Detect the language of the prompt
    try:
        lang = langdetect.detect(prompt)
    except langdetect.lang_detect_exception.LangDetectException:
        lang = 'en'

    # If the language is not English, translate and improve it
    if lang == 'ru' or lang =='uk' or lang=='mk':
        user_data = await dp.storage.get_data(chat=user_id)
        history = user_data.get('history', [])
        history_for_openai = [{"role": item["role"], "content": item["content"]} for item in user_data['history']]
        chat_response = await gpt_acreate(
            model="gpt-3.5-turbo",
            messages=  history_for_openai+[
                {"role": "system",
                 "content": '''Use the following info as a reference to create ideal Midjourney prompts.

•	Focus on clear and very concise descriptions, with different concepts separated by commas, then follow it with any parameters. Parameters are not separated by commas.
•	Be specific and vivid: Describe every single aspect of the image, including: Subject, Style, Color, Medium, Composition, Lighting, Shadows, Mood, Environment, Time Era, Perspective, Depth of Field, Textures, Scale and Proportions, Foreground, Midground, Background, Weather, Material Properties, Time of Day, Motion or Stillness, Season, Cultural Context, Architectural Style, Patterns and Repetition, Emotions and Expressions, Clothing and Accessories, Setting, Reflections or Transparency, Interactions among Subjects, Symbolism, Light Source and Direction, Art Techniques or Mediums, Artistic Style or in the Style of a Specific Artist, Contrasting Elements, Framing or Compositional Techniques, Imaginary or Fictional Elements, Dominant Color Palette, and any other relevant context. 

•	Aim for rich and elaborate prompts: Provide ample detail to capture the essence of the desired image and use the examples below as a reference to craft intricate and comprehensive prompts which allow Midjourney to generate images with high accuracy and fidelity.
•	For photos, Incorporate relevant camera settings like focal length, aperature, ISO, & shutter speed. Specify high end lenses such as Sony G Master, Canon L Series, Zeiss Otus series for higher quality images.
•	Select the aspect ratio by adding the --ar <value>:<value> parameter. Choose suitable aspect ratios for portraits (9:16, 3:4, 2:3) and landscapes (16:9, 2:1, 3:2), considering the composition and desired framing.
•	Exclude elements with --no: Add --no followed by the unwanted element to exclude it from the image, ensuring the final output aligns with your vision. Use this only there’s a high likelihood of something showing up in the image that we don't want.
•	Diversify your prompts: Explore various styles, moods, colors, art mediums, and aspect ratios to create a wide range of visually appealing and unique images.

Here are 2 example prompts. The first is artistic, the last is photo. Use these examples to determine desired length of each prompt.

•	Digital art of an enchanting piano recital set within a serene forest clearing, a grand piano as the centerpiece, the musician, a young woman with flowing locks and an elegant gown, gracefully playing amidst the vibrant green foliage and deep brown tree trunks, her fingers dancing across the keys with an air of passion and skill, soft pastel colors adding a touch of whimsy, warm, dappled sunlight filtering through the leaves, casting a dreamlike glow on the scene, a harmonious fusion of music and nature, eye-level perspective immersing the viewer in the tranquil woodland setting, a captivating blend of art and the natural world --ar 2:1•	Detailed charcoal drawing of a gentle elderly woman, with soft and intricate shading in her wrinkled face, capturing the weathered beauty of a long and fulfilling life. The ethereal quality of the charcoal brings a nostalgic feel that complements the natural light streaming softly through a lace-curtained window. In the background, the texture of the vintage furniture provides an intricate carpet of detail, with a monochromatic palette serving to emphasize the subject of the piece. This charcoal drawing imparts a sense of tranquillity and wisdom with an authenticity that captures the subject's essence.
•	Astounding astrophotography image of the Milky Way over Stonehenge, emphasizing the human connection to the cosmos across time. The enigmatic stone structure stands in stark silhouette with the awe-inspiring night sky, showcasing the complexity and beauty of our galaxy. The contrast accentuates the weathered surfaces of the stones, highlighting their intricate play of light and shadow. Sigma Art 14mm f/1.8, ISO 3200, f/1.8, 15s --ar 16:9 

You will receive a text prompt and then create one creative prompt for the Midjourney AI art generator using the best practices mentioned above. Do not include explanations in your response. List one prompt on English language with correct syntax without unnecessary words. Promt is: '''+prompt}
            ],
            max_tokens=200
        )

        # Extract the model's response
        improved_prompt = chat_response['choices'][0]['message']['content']
        # Удаление символов кавычек
        cleaned_text = improved_prompt.replace('"', '').replace("'", '').replace('translates to','')

        # Поиск английского текста с использованием регулярного выражения
        improved_prompt = ' '.join(re.findall(r'\b[A-Za-z]+\b', cleaned_text))


        # Remove the model's name from the response
        improved_prompt = re.sub(r'^.*?:', '', improved_prompt).strip()

        return improved_prompt

    # If the language is English, return the original prompt
    return prompt


def create_style_keyboard(prompt):
    styles = list(Style.__members__.keys())
    ratios = list(Ratio.__members__.keys())
    prompt_db,_=Prompt.get_or_create(text=prompt)
    kb = types.InlineKeyboardMarkup(resize_keyboard=True)
    width=5
    raws=6
    horizontal_styles = random.sample(styles, width*raws)
    for i in range(raws):
        # Добавление горизонтального ряда кнопок со случайными стилями

        buttons = [
            types.InlineKeyboardButton(style.lower(), callback_data=f'style_{prompt_db.id}_{style}')
            for style in horizontal_styles[i*width:(i+1)*width]
        ]
        kb.row(*buttons)

    buttons = [
        types.InlineKeyboardButton(ratio.lower().replace('ratio_',''), callback_data=f'ratio_{prompt_db.id}_{ratio}')
        for ratio in ratios
    ]
    buttons.append(types.InlineKeyboardButton(MIDJOURNEY, callback_data=(f'style_{prompt_db.id}_{MIDJOURNEY}')))
    kb.row(*buttons)

    return kb

@dp.callback_query_handler(lambda callback: callback.data.startswith('ratio') or callback.data.startswith('style'))
async def handle_ratio_callback(query: types.CallbackQuery):
    # Обработка callback для соотношений
    user_data = await dp.storage.get_data(chat=query.message.chat.id)
    _,id,text = query.data.split('_',2)
    prompt=Prompt.get_by_id(id).text
    if text in Style.__members__ or text in [MIDJOURNEY]:
        user_data['style'] = text
        await query.answer(f"Set style to {text}.")
    elif text in Ratio.__members__:
        user_data['ratio'] = text
        await query.answer(f"Set ratio to {text}.")
    else:
        await query.answer("Unknown option.")
    await dp.storage.set_data(chat=query.message.chat.id, data=user_data)
    await draw_and_answer(prompt,query.message.chat.id,query.from_user.full_name or query.from_user.username)

async def draw_and_answer(prompt,chat_id,name):
    user_data = await dp.storage.get_data(chat=chat_id)
    ratio = Ratio[user_data.get('ratio', 'RATIO_4X3')]
    try:
        style = Style[user_data.get('style', 'ANIME_V2')]
    except:
        style=user_data.get('style', 'ANIME_V2')
    msg=await bot.send_message(chat_id=chat_id,text= f"Creating image... {style}\n{ratio} \n{prompt}")
    try:
        prompt=await improve_prompt(prompt,chat_id,name)
        asyncio.create_task(msg.edit_text(prompt))

        img_file,url = await gen_img(prompt, ratio, style)
        if img_file is None:
            await msg.edit_text("An error occurred while generating the image.")
            return


        photo=None
        kb=create_style_keyboard(prompt)
        if isinstance(style,Style):
            photo = await bot.send_photo(chat_id=chat_id, photo=io.BytesIO(img_file), caption=f'{prompt}')
            img_file = await upscale_image(img_file)
        else:
            img_db = ImageMidjourney.create(prompt=prompt, url=url)

            btns = [InlineKeyboardButton(text=f"U {_ + 1}", callback_data=f"imagine_{_ + 1}_{img_db.id}") for _ in range(4)]
            kb.row(*btns)


        photo2 = await bot.send_photo(chat_id=chat_id,photo=io.BytesIO(img_file), caption=f'{prompt}\n{style}\n{ratio}', reply_markup=kb)
        if photo is not None:
            await photo.delete()
    except:
        traceback.print_exc()
        if msg is None:
            await bot.send_message(chat_id, "An error occurred while generating the image.")
        else:
            await msg.edit_text("An error occurred while generating the image.")

@dp.message_handler(commands=['draw'])
async def handle_draw(message: types.Message):
    prompt = message.get_args()
    if not prompt:
        await message.reply("Please provide a description for the image.")
        return
    await draw_and_answer(prompt,message.chat.id,message.from_user.full_name or message.from_user.username)


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
    user_data = await dp.storage.get_data(chat=message.chat.id)
    style = Style[user_data.get('style', 'ANIME_V2')]
    ratio = Ratio[user_data.get('ratio', 'RATIO_4X3')]

    await message.reply(f"Please choose style and ratio for your drawings.{style} {ratio}", reply_markup=keyboard)
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
    await state.finish()
    await dp.storage.set_data(chat=message.chat.id, data=user_data)
