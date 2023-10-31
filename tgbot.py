import logging

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import dp, Role_SYSTEM, Role_USER, Role_ASSISTANT, ASSISTANT_NAME_SHORT
from datebase import get_user_balance


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
    thread_id = message.message_thread_id if message.is_topic_message else None
    user_id = message.chat.id
    return await get_storage_from_chat(user_id, thread_id)


from aiogram import types


async def dialog_append(message:types.Message, text:str=None,role='user', **params):
    content=text
    
    if content is None:
        content=message.text
    if role==Role_USER:
        content = f'{message.from_user.full_name or message.from_user.username}: {content}'
    #if role==Role_ASSISTANT:
        #user_data, storage_id = await get_storage_from_chat(message.chat.id,message.message_thread_id)
        #content = f"{user_data.get('ASSISTANT_NAME_SHORT', ASSISTANT_NAME_SHORT)}:{content}"

    return await dialog_append_raw(chat_id=message.chat.id,response_text_= content,thread_id=message.message_thread_id,role=role ,message_id=message.message_id, **params)

async def dialog_edit(chat_id,message_id ,text,thread_id=None, **params):
    if text is None:
        logging.error('why changing to none?')
        return None,None
    # Получить соответствующее хранилище данных пользователя
    user_data, storage_id = await get_storage_from_chat(chat_id,thread_id)

    # Получить историю диалога
    dialog_history = user_data.get('history', [])

    # Найти сообщение для редактирования
    for i, dialog_message in enumerate(dialog_history):
        if dialog_message.get('message_id') == message_id:
            # Обновить содержимое сообщения
            old=dialog_message['content']

            dialog_message['content'] = text if dialog_message['role']!=Role_USER else dialog_message['content'].split(': ',1)[0]+': '+text
            # Обновить историю диалога
            user_data['history'][i] = dialog_message
            # Обновить хранилище данных пользователя
            await dp.storage.set_data(chat=storage_id, data=user_data)
            print(f"Edited a message from {old} to: {text} in {storage_id}")
            break

    return user_data, storage_id


async def dialog_delete(chat_id, message_id, thread_id=None, **params):
    # Получить хранилище данных и историю диалога
    user_data, storage_id = await get_storage_from_chat(chat_id, thread_id)
    dialog_history = user_data.get('history', [])

    # Найти и удалить сообщение
    message_to_remove = next((m for m in dialog_history if m.get('message_id') == message_id), None)

    if message_to_remove:
        dialog_history.remove(message_to_remove)
        print(f'removing {message_to_remove["content"]}')
    else:
        logging.error(f'message_not_found! {chat_id} {message_id} {thread_id or params}')

    return user_data, storage_id
async def dialog_append_raw(chat_id, response_text_, thread_id=None, role='user', **params):
    user_data, storage_id = await get_storage_from_chat(chat_id, thread_id)
    if thread_id is not None:
        # Делайте что-то с thread_id, например, добавить его в словарь params
        params['thread_id'] = thread_id
    if 'history' not in user_data:
        user_data['history'] =[]
    user_data['history'].append(
        {"role": role, "content": response_text_, **params})
    await dp.storage.set_data(chat=storage_id, data=user_data)
    return user_data, storage_id


