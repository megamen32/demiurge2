import logging

from aiogram import types

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
    thread_id = message.message_thread_id
    user_id = message.chat.id
    return await get_storage_from_chat(user_id, thread_id)


from aiogram import types

@dp.message_handler(commands=['balance'])
async def send_balance(message: types.Message):
    user_id = message.from_user.id
    balance_data = await get_user_balance(user_id)

    if "error" in balance_data:
        await message.reply(f"Ошибка: {balance_data['error']}")
        return

    response_text = "Ваш баланс и стоимость использованных символов для каждой модели:\n"
    for model_name, balance in balance_data["balances"].items():
        response_text += f"\n🤖 Модель: {model_name}\n"
        response_text += f"📥 Входящих символов: {balance['input_chars']}\n"
        response_text += f"📤 Исходящих символов: {balance['output_chars']}\n"
        response_text += f"💲 Общая стоимость: ${balance['total_cost']:.4f}\n"

    response_text += f"\n💰 Общий баланс: ${balance_data['total_balance']:.4f}"
    await message.reply(response_text)

async def dialog_append(message:types.Message, text:str=None,role='user', **params):
    content=text
    
    if content is None:
        content=message.text
    if role==Role_USER:
        content = f'{message.from_user.full_name or message.from_user.username}: {content}'
    #if role==Role_ASSISTANT:
        #user_data, storage_id = await get_storage_from_chat(message.chat.id,message.message_thread_id)
        #content = f"{user_data.get('ASSISTANT_NAME_SHORT', ASSISTANT_NAME_SHORT)}:{content}"

    return await dialog_append_raw(message.chat.id, content,message.message_thread_id,role ,message_id=message.message_id, **params)

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
            dialog_message['content'] = text
            # Обновить историю диалога
            user_data['history'][i] = dialog_message
            # Обновить хранилище данных пользователя
            await dp.storage.set_data(chat=storage_id, data=user_data)
            print(f"Edited a message to: {text}")
            break

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
