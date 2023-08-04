

from aiogram import Bot, Dispatcher

class LoggingBot(Bot):


    async def send_message(self, ignore=False,*args, **kwargs):
        # Здесь вы можете добавить предварительную обработку, если это необходимо
        result = await super().send_message(*args, **kwargs)
        # Здесь мы добавим постобработку - заносим сообщение в память
        await self.log_sent_message(result)
        return result

    async def log_sent_message(self, message):
        from tgbot import dialog_append
        # Здесь вы можете реализовать свою логику по сохранению информации о сообщении
        print(f"Sent a message: {message.text}")
        if message.text and message.text!='...':
            await dialog_append(message,role='assistant')