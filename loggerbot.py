import traceback

import aiogram
from aiogram import Bot, Dispatcher




class LoggingBot(Bot):


    async def send_message(self, ignore=False,*args, **kwargs):
        # Здесь вы можете добавить предварительную обработку, если это необходимо
        kwargs['text']=kwargs['text'][:4000]
        try:
            result = await super().send_message(*args, **kwargs)
        except:
            traceback.print_exc()
            result= aiogram.types.Message(**kwargs)
        # Здесь мы добавим постобработку - заносим сообщение в память
        if not ignore:
            result.message_thread_id=None
            await self.log_sent_message(result)
        return result

    async def log_sent_message(self, message):
        from tgbot import dialog_append
        # Здесь вы можете реализовать свою логику по сохранению информации о сообщении

        if message.text and 'ing image...' not in message.text:
            print(f"Sent a message: {message.text}")
            await dialog_append(message,role='assistant')

    async def edit_message_text(self, text, chat_id, message_id, ignore=False, *args, **kwargs):
        from tgbot import dialog_edit
        # Здесь вы можете добавить предварительную обработку.
        text=text[:4096]
        result = await super().edit_message_text(text,chat_id,message_id, *args, **kwargs)
        if not ignore:
            try:
                await dialog_edit(chat_id=chat_id,message_id=message_id,text=text)
                # Здесь вы можете добавить постобработку, например, логирование.

            except:
                traceback.print_exc()
        return result
    async def delete_message(self,chat_id,message_id,**kwargs):
        from tgbot import dialog_delete
        result = await super().delete_message( chat_id, message_id)
        await dialog_delete(chat_id=chat_id, message_id=message_id)



