# Настройка глобальной переменной для очереди
import asyncio

import openai
from aiolimiter import AsyncLimiter
from openai.error import RateLimitError

import config
request_queue = asyncio.Queue()

async def process_queue():
    while True:
        task = await request_queue.get()
        try:
            result = await agpt(**task['params'])
            task['future'].set_result(result)
        except Exception as e:
            task['future'].set_exception(e)
        finally:
            request_queue.task_done()




# Create a rate limiter that allows 3 operations per minute
rate_limiter = AsyncLimiter(3, 60)

async def agpt(**params):
    # Wait for permission from the rate limiter before proceeding
    async with rate_limiter:
        while True:
            try:
                config.set_random_api_key()
                result = await openai.ChatCompletion.acreate(**params)
                return result
            except RateLimitError:
                await asyncio.sleep(20)
                continue

    return result



async def gpt_acreate(**params):
    future = asyncio.get_event_loop().create_future()
    await request_queue.put({
        'params': params,
        'future': future
    })
    return await future
