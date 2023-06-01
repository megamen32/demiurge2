# Настройка глобальной переменной для очереди
import asyncio
import re

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
                # Ограничьте историю MAX_HISTORY сообщениями
                if count_tokens(params['messages']) > MAX_TOKENS:
                    normal_text = []
                    ctns = list(reversed((params['messages'])))
                    while count_tokens(normal_text) < MAX_TOKENS and any(ctns):
                        elem = ctns.pop()
                        if count_tokens(normal_text + [elem]) < MAX_TOKENS:
                            normal_text.append(elem)
                        else:
                            break
                    params['messages']=list(reversed(normal_text))


                result = await openai.ChatCompletion.acreate(**params)
                return result
            except RateLimitError as error:
                if error.error['message']=='You exceeded your current quota, please check your plan and billing details.':
                    result={'choices':[{'message':{'content':'Простите, но у меня закончились деньги чтобы общаться с вами. Как только за меня заплатят я заработaю.'}}]}
                    return result
                    #raise error
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


def count_tokens(history):
    regex_russian = re.compile(r'[а-яА-ЯёЁ]+')
    regex_other = re.compile(r'\b\w+\b')
    c_russian = c_other = 0
    for msg in history:
        russian_tokens = regex_russian.findall(msg['content'])
        c_russian += len(russian_tokens)

        other_tokens = regex_other.findall(msg['content'])
        other_tokens = [t for t in other_tokens if not regex_russian.search(t)]
        c_other += len(other_tokens)
    return c_russian*3.5+c_other


MAX_TOKENS = 2700


async def shorten(message_text):
    if count_tokens([{'content': message_text}]) > MAX_TOKENS:
        normal_text = []
        ctns = message_text.split('\n')
        if len(ctns) <= 2:
            ctns = message_text.split()
        while count_tokens(normal_text) < MAX_TOKENS and any(ctns):
            elem = ctns.pop()
            content_elem_ = {'content': elem}
            if count_tokens(normal_text + [content_elem_]) < MAX_TOKENS:
                normal_text.append(content_elem_)
            else:
                break
        message_text = '\n'.join(msg['content'] for msg in normal_text)
    return message_text


async def summary_gpt(history_for_openai):
    chat_response = await gpt_acreate(
        model="gpt-3.5-turbo",
        messages=history_for_openai + [{'role': 'system',
                                        'content': f"Your memory is full, you need to summarize it. Your need to write down summarized information as it would stay in memory of character that you pretending to be. Stay in the Image. Your next answer will replace all previus chat history with it. So it must include all important information. Do not write any extra text: don't continue dialog or answer questions. User will not see your answer. You need only to summirize"}]
    )
    summary = chat_response['choices'][0]['message']['content']
    return summary
