import logging
import pprint
from datetime import datetime

from aiogram import types, Bot, Dispatcher
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

import config
import tgbot
from config import dp, bot,ASSISTANT_NAME_SHORT
from datebase import User


class MessageLoggingMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        user_data,user_id=await tgbot.get_chat_data(message)
        user_data['last_message_time'] = datetime.now().timestamp()

        create_user(message)
        await dp.storage.set_data(chat=user_id,data=user_data)
        if message.reply_to_message and message.reply_to_message.text:
            user = message.reply_to_message.from_user
            from_ = user.full_name or user.username if not user.id == bot.id else user_data.get('ASSISTANT_NAME_SHORT',
                                                                                                ASSISTANT_NAME_SHORT)
            message.text = f'{message.text} (this message is in response to "{from_}" who said: {message.reply_to_message.text or message.reply_to_message.caption})'


        if  message.text:
            if message.get_command(True) not in ['history']:
                await tgbot.dialog_append(message,message.text)
        print(message.text or message.caption,user_id)
        if user_data.get('mute',None) and (not message.text or '/mute' not in message.text):
            raise CancelHandler()
        # Продолжаем обработку следующими middleware и обработчиками

def create_user( message):
    user, _ = User.get_or_create(user_id=message.from_user.id)
    if _:
        user.username = message.from_user.username or message.from_user.full_name
        user.save()
    return user




