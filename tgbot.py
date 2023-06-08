from aiogram import types

from config import dp

async def get_chat_data_raw(chat_id,thread_id=None):
    if thread_id is not None:
        storage_id = f"{chat_id}&{thread_id}"
    else:
        storage_id = f"{chat_id}"
    # Получение данных для определенного потока из хранилища
    user_data  = await dp.storage.get_data(chat=storage_id)
    if 'history' not in user_data:
        user_data['history'] =[]
    return user_data, storage_id
async def get_chat_data(message:types.Message):
    thread_id = message.message_thread_id
    user_id = message.chat.id
    return await get_chat_data_raw(user_id, thread_id)


async def dialog_append(message, content,role='user', **params):
    return await dialog_append_raw(message.chat.id, content,message.message_thread_id,role ,message_id=message.message_id, **params)


async def dialog_append_raw(chat_id, response_text_, thread_id=None, role='user', **params):
    user_data, chat_id = await get_chat_data_raw(chat_id,thread_id)
    if 'history' not in user_data:
        user_data['history'] =[]
    user_data['history'].append(
        {"role": role, "content": response_text_, **params})
    await dp.storage.set_data(chat=chat_id, data=user_data)
    return user_data, chat_id
