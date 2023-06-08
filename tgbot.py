from aiogram import types

from config import dp

async def get_chat_data_raw(chat_id,thread_id=None):
    if thread_id is not None:
        storage_id = f"{chat_id}-{thread_id}"
    else:
        storage_id = f"{chat_id}"
    # Получение данных для определенного потока из хранилища
    user_data  = await dp.storage.get_data(chat=storage_id)
    return user_data, storage_id
async def get_chat_data(message:types.Message):
    thread_id = message.message_thread_id
    user_id = message.chat.id

    return await get_chat_data_raw(user_id, thread_id)
