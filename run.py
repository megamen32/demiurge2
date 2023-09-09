import asyncio
import subprocess

from aiogram.types import BotCommand
from aiogram.utils import executor

from config import dp, bot
from datebase import ImageUnstability, ImageMidjourney, Prompt, User, ModelUsage, PaymentInfo
from gpt import process_queue
from main import  check_inactive_users
from memory import mem_init
from telegrambot.handlers import MessageLoggingMiddleware

async def on_startup_disp(dp):
    asyncio.create_task(process_queue())
    asyncio.create_task(check_inactive_users())
    asyncio.create_task(mem_init())
    await bot.set_my_commands([
        BotCommand("history", "Показать историю диалога"),
        BotCommand("gpt4", "turn gpt4 on or off"),
        BotCommand("balance", "See you balance"),
        BotCommand("functions", "change plugins that turned on or off"),
        BotCommand("summarize", "Суммировать историю диалога"),
        BotCommand("clear", "Clear историю диалога"),
        BotCommand("prompt", "Edit gpt start prompt"),
        BotCommand("draw_settings", "draw settings"),
        BotCommand("draw", "{prompt} draws an image"),
        BotCommand("count", "show history length"),
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
    if not User.table_exists(): User.create_table()
    if not ModelUsage.table_exists(): ModelUsage.create_table()
    if not PaymentInfo.table_exists(): PaymentInfo.create_table()
    #start Midjourney-Web-API/app.py
    subprocess.Popen(["python", "Midjourney-Web-API/app.py"])

    dp.middleware.setup(MessageLoggingMiddleware())
    executor.start_polling(dp, on_startup=on_startup_disp)
