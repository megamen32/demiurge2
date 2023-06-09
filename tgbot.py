from aiogram import types

from config import dp, Role_SYSTEM, Role_USER


async def get_storage_from_chat(chat_id, thread_id=None):
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
    return await get_storage_from_chat(user_id, thread_id)


async def dialog_append(message:types.Message, text:str=None,role='user', **params):
    content=text
    if content is None:
        content=message.text
    if role==Role_USER:
        content = f'{message.from_user.full_name or message.from_user.username}:{content}'

    return await dialog_append_raw(message.chat.id, content,message.message_thread_id,role ,message_id=message.message_id, **params)


async def dialog_append_raw(chat_id, response_text_, thread_id=None, role='user', **params):
    user_data, storage_id = await get_storage_from_chat(chat_id, thread_id)
    if 'history' not in user_data:
        user_data['history'] =[]
    user_data['history'].append(
        {"role": role, "content": response_text_, **params})
    await dp.storage.set_data(chat=storage_id, data=user_data)
    return user_data, storage_id
