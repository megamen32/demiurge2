import glob
import os
import traceback

import aiogram.types
import aioredis

from config import bot, dp
from llama_index import VectorStoreIndex, SimpleDirectoryReader

from read_all_files import read_file



import pickle
redis=None
async def mem_init():
    global redis
    redis = await aioredis.from_url("redis://localhost")
    if not os.path.exists('data/'):
        os.mkdir('data')





def get_index(chat_id,files=None):
    documents = SimpleDirectoryReader(input_files=files).load_data()
    index = VectorStoreIndex.from_documents(documents)
    return index



async def query_index(chat_id, query_text,files):



    index=get_index(chat_id,files)
    query_engine = index.as_query_engine()
    results = query_engine.query(query_text)

    return results
from aiogram import types
@dp.message_handler(lambda m:m.caption or m.text,content_types=aiogram.types.ContentTypes.DOCUMENT)
async def handle_doc_query(message: types.Message):
    try:
        chat_id = message.chat.id
        text = message.caption or message.text

        # Если прикреплен файл, сделаем из него индекс (пример)

        file_path = await bot.download_file_by_id(message.document.file_id, destination_dir=f"data/{chat_id}")
        # Здесь загрузите файл в индекс



        results = await query_index(chat_id, text,[file_path.name])
        if results:
            await message.reply( f"Found results: {results}")
        else:
            await message.reply( "No results found.")
    except:
        traceback.print_exc()
        await message.reply(traceback.format_exc())
