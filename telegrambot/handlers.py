import logging
import pprint
from datetime import datetime

from aiogram import types, Bot, Dispatcher
from aiogram.dispatcher.middlewares import BaseMiddleware

import tgbot
from config import dp, bot,ASSISTANT_NAME_SHORT


class MessageLoggingMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        user_data,user_id=await tgbot.get_chat_data(message)
        user_data['last_message_time'] = datetime.now().timestamp()
        await dp.storage.set_data(chat=user_id,data=user_data)
        if message.reply_to_message and message.reply_to_message.text:
            user = message.reply_to_message.from_user
            from_ = user.full_name or user.username if not user.id == bot.id else user_data.get('ASSISTANT_NAME_SHORT',
                                                                                                ASSISTANT_NAME_SHORT)
            message.text = f'{message.text} (this message is in response to "{from_}" who said: {message.reply_to_message.text or message.reply_to_message.caption})'



        await tgbot.dialog_append(message,message.text)
        print(pprint.pprint(message))
        # Продолжаем обработку следующими middleware и обработчиками




