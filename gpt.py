# Настройка глобальной переменной для очереди
import asyncio
import logging
import re
from asyncio import InvalidStateError

import openai
from aiolimiter import AsyncLimiter
from openai.error import RateLimitError


import config
request_queue = asyncio.Queue()
MAX_TOKENS = 4097
async def process_queue():
    while True:
        task = await request_queue.get()
        try:
            result = await agpt(**task['params'])
            task['future'].set_result(result)
        except InvalidStateError:pass
        except Exception as e:
            task['future'].set_exception(e)
        finally:
            request_queue.task_done()




# Create a rate limiter that allows 3 operations per minute
rate_limiter = AsyncLimiter(3, 60)
llm=None
cur_token_index=0
my_session_tokens = ['eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik1UaEVOVUpHTkVNMVFURTRNMEZCTWpkQ05UZzVNRFUxUlRVd1FVSkRNRU13UmtGRVFrRXpSZyJ9.eyJodHRwczovL2FwaS5vcGVuYWkuY29tL3Byb2ZpbGUiOnsiZW1haWwiOiJoZGhmYTEyNEByYW1ibGVyLnJ1IiwiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJodHRwczovL2FwaS5vcGVuYWkuY29tL2F1dGgiOnsidXNlcl9pZCI6InVzZXIta3ZrNzRJWGxzWkZxRVZzR3FhMnFwR0hYIn0sImlzcyI6Imh0dHBzOi8vYXV0aDAub3BlbmFpLmNvbS8iLCJzdWIiOiJhdXRoMHw2M2Y1MmYyOWY4M2JkODE2ZTg4NzQ2OGIiLCJhdWQiOlsiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSIsImh0dHBzOi8vb3BlbmFpLm9wZW5haS5hdXRoMGFwcC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNjg2MzEyODQ2LCJleHAiOjE2ODc1MjI0NDYsImF6cCI6IlRkSkljYmUxNldvVEh0Tjk1bnl5d2g1RTR5T282SXRHIiwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCBtb2RlbC5yZWFkIG1vZGVsLnJlcXVlc3Qgb3JnYW5pemF0aW9uLnJlYWQgb3JnYW5pemF0aW9uLndyaXRlIn0.Rmwv55D2gNG--Kmm433y7mbJuVm2V2LNz0nU9bgs_6_JmBNvzZk_PBh7bCPBBrDQIGhlaxf1nqr_PhTKsCYqe7w2CJaSaFdK7_HEpLGIKSetrn4Bpl2BAholzd2dXtLq9B1vacgEwGoTjVyYOZyqLcV3poCXVq5wt8Pii9awDILRnJM3yEdeGys9r7vGOxQEFTlMGOBkpMwwC6hL7l5FQMLimK2ZMDadyyCNeFAOrhIM9Jk99toO_GaDoRPbkRkfEJeacDQ9mt3_ldYsr7VopkIDOjB_aLMdr-bpJzqSVu9cbRRmywr4lbk1YB-rvN3jZzTcQD97npc-088ROE98Aw']
def trim_message_to_tokens(message, max_tokens):
    global tokenizer
    if tokenizer is None:
        from transformers import GPT2Tokenizer
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    tokens = tokenizer.encode(message)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return tokenizer.decode(tokens)

async def agpt(**params):
    # Wait for permission from the rate limiter before proceeding
    if config.USE_API and params['model']!='gpt-4':
        while True:
            async with rate_limiter:
                try:
                    config.set_random_api_key()
                    # Ограничьте историю MAX_HISTORY сообщениями
                    if count_tokens(params['messages']) > MAX_TOKENS:
                        trimmed_messages = []
                        for msg in params['messages'][::-1]:  # reverse the list
                            msg_token_count = count_tokens([msg])
                            if msg_token_count > MAX_TOKENS // 2:
                                # Trim the message
                                msg['content'] = trim_message_to_tokens(msg['content'], MAX_TOKENS // 2)
                                msg_token_count = count_tokens([msg])
                            if not trimmed_messages or (count_tokens(trimmed_messages) + msg_token_count <= MAX_TOKENS):
                                trimmed_messages.append(msg)
                            else:
                                break
                        params['messages'] = trimmed_messages[::-1]  # reverse back
                    params['messages'] = [{"role": item["role"], "content": item["content"], **({'name': item['name']} if 'name' in item else {})} for item in params['messages']]
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
        from transformers import GPT2Tokenizer
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

    tokens=0
    for msg in history:
        tokens+=len(tokenizer.encode(msg['content']))
    return tokens





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
        model="gpt-3.5-turbo-0613",
        messages=history_for_openai + [
            {
                'role': 'system',
                'content': "Ты помощник, которому нужно суммировать всю предыдущую информацию. Твой следующий ответ заменит всю предыдущую историю чата, поэтому он должен содержать всю важную информацию. Следуй изображению персонажа, которым ты притворяешься. Не пиши лишний текст: не продолжай диалог или не отвечай на вопросы. Пользователь не увидит твой ответ. Тебе нужно только суммировать."
            }
        ]
    )
    summary = chat_response['choices'][0]['message']['content']
    return summary
