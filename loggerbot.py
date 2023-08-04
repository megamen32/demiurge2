import traceback

from aiogram import Bot, Dispatcher




class LoggingBot(Bot):


    async def send_message(self, ignore=False,*args, **kwargs):
        # Здесь вы можете добавить предварительную обработку, если это необходимо
        result = await super().send_message(*args, **kwargs)
        # Здесь мы добавим постобработку - заносим сообщение в память
        if not ignore:
            await self.log_sent_message(result)
        return result

    async def log_sent_message(self, message):
        from tgbot import dialog_append
        # Здесь вы можете реализовать свою логику по сохранению информации о сообщении

        if message.text:
            print(f"Sent a message: {message.text}")
            await dialog_append(message,role='assistant')

    async def edit_message_text(self, text, chat_id, message_id, ignore=False, *args, **kwargs):
        from tgbot import dialog_edit
        # Здесь вы можете добавить предварительную обработку.
        result = await super().edit_message_text(text,chat_id,message_id, *args, **kwargs)
        if not ignore:
            try:
                await dialog_edit(chat_id=chat_id,thread_id=result.message_thread_id,message_id=message_id,text=text)
                # Здесь вы можете добавить постобработку, например, логирование.

            except:
                traceback.print_exc()
        return result

