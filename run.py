import asyncio
import subprocess

from aiogram.types import BotCommand
from aiogram.utils import executor

from config import dp, bot
from datebase import ImageUnstability, ImageMidjourney, Prompt
from gpt import process_queue
from main import  check_inactive_users
from telegrambot.handlers import MessageLoggingMiddleware

async def on_startup_disp(dp):
    asyncio.create_task(process_queue())
    asyncio.create_task(check_inactive_users())
    await bot.set_my_commands([
        BotCommand("history", "Показать историю диалога"),
        BotCommand("summarize", "Суммировать историю диалога"),
        BotCommand("clear", "Clear историю диалога"),
        BotCommand("prompt", "Edit gpt start prompt"),
        BotCommand("draw_settings", "draw settings"),
        BotCommand("draw", "{prompt} draws an image"),
        BotCommand("imagine", "{prompt} draws an image"),
        BotCommand("i", "{prompt} draws an image"),
        BotCommand("search", "search{prompt} for news and trends"),
        BotCommand("s", "{prompt} draw uncensroed images"),
        # Добавьте здесь любые дополнительные команды
    ])


if __name__ == '__main__':
    if not Prompt.table_exists(): Prompt.create_table()
    if not ImageMidjourney.table_exists(): ImageMidjourney.create_table()
    if not ImageUnstability.table_exists(): ImageUnstability.create_table()
    #start Midjourney-Web-API/app.py
    subprocess.Popen(["python", "Midjourney-Web-API/app.py"])

    dp.middleware.setup(MessageLoggingMiddleware())
    executor.start_polling(dp, on_startup=on_startup_disp)
