# Настройка глобальной переменной для очереди
import asyncio
import re

import openai
from aiolimiter import AsyncLimiter
from openai.error import RateLimitError
from transformers import GPT2Tokenizer

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
llm=None
cur_token_index=0
my_session_tokens = ['eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik1UaEVOVUpHTkVNMVFURTRNMEZCTWpkQ05UZzVNRFUxUlRVd1FVSkRNRU13UmtGRVFrRXpSZyJ9.eyJodHRwczovL2FwaS5vcGVuYWkuY29tL3Byb2ZpbGUiOnsiZW1haWwiOiJoZGhmYTEyNEByYW1ibGVyLnJ1IiwiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJodHRwczovL2FwaS5vcGVuYWkuY29tL2F1dGgiOnsidXNlcl9pZCI6InVzZXIta3ZrNzRJWGxzWkZxRVZzR3FhMnFwR0hYIn0sImlzcyI6Imh0dHBzOi8vYXV0aDAub3BlbmFpLmNvbS8iLCJzdWIiOiJhdXRoMHw2M2Y1MmYyOWY4M2JkODE2ZTg4NzQ2OGIiLCJhdWQiOlsiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSIsImh0dHBzOi8vb3BlbmFpLm9wZW5haS5hdXRoMGFwcC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNjg1MTAyMjc1LCJleHAiOjE2ODYzMTE4NzUsImF6cCI6IlRkSkljYmUxNldvVEh0Tjk1bnl5d2g1RTR5T282SXRHIiwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCBtb2RlbC5yZWFkIG1vZGVsLnJlcXVlc3Qgb3JnYW5pemF0aW9uLnJlYWQgb3JnYW5pemF0aW9uLndyaXRlIn0.J586tB92Sd9W6A9DQGD6BcwoKAaQQlEzR9c8IsUnXwYbezh5mCS2lTtFtiBf1vKt2t1GPg0k-WaS5zkqbrob4A0IngaNpHqZsIh04D-0pGz9pyEjkwwJvNhi7uQ9WdkTGwLsPKdx-oBto23OjcGgnv-OyWG2Vsm5nukgGe3escVikAZtzWO0visHiV_3p-97JIh5OCYF_R4Zfip5vGyWi16YuIDV1UssBCk1nF30-C-_-uyohSyGZZZ0HAE47YgiKXkqhnNrqbUKVcMhGndpaQ2eTDTcOFegZ2ASkpsvqPpceJnwhYaja5XGXga-ZsDITNMw0H4jDWOsnHYzNYPdVw']

async def agpt(**params):
    # Wait for permission from the rate limiter before proceeding
    if config.USE_API:
        while True:
            async with rate_limiter:
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
    else:
        from gpt4_openai import GPT4OpenAI
        global llm, cur_token_index
        if llm is None:
            llm = [GPT4OpenAI(token=token, headless=True, model='gpt-3.5' if params['model']!='gpt=4'else 'gpt-4') for token in my_session_tokens]
            # GPT3.5 will answer 8, while GPT4 should be smart enough to answer 10
        prompt = params['messages'][-1]['content']
        response = llm[cur_token_index](prompt)
        result = {'choices': [{'message': {
            'content': response}}]}
        return result
    return result



async def gpt_acreate(**params):
    future = asyncio.get_event_loop().create_future()
    await request_queue.put({
        'params': params,
        'future': future
    })
    return await future

tokenizer=None
def count_tokens(history):
    global tokenizer
    if tokenizer is None:
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

    tokens=0
    for msg in history:
        tokens+=len(tokenizer.encode(msg['content']))
    return tokens


MAX_TOKENS = 4000


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
        messages=history_for_openai + [
            {
                'role': 'system',
                'content': "Ты помощник, которому нужно суммировать всю предыдущую информацию. Твой следующий ответ заменит всю предыдущую историю чата, поэтому он должен содержать всю важную информацию. Следуй изображению персонажа, которым ты притворяешься. Не пиши лишний текст: не продолжай диалог или не отвечай на вопросы. Пользователь не увидит твой ответ. Тебе нужно только суммировать."
            }
        ]
    )
    summary = chat_response['choices'][0]['message']['content']
    return summary
