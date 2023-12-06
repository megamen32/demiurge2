# Настройка глобальной переменной для очереди
import asyncio
import json
import logging
import os
import random
import re
import socket
from asyncio import InvalidStateError
from collections import defaultdict

import aiohttp
import openai
import requests
import socks
import tiktoken
from aiolimiter import AsyncLimiter
from openai.error import RateLimitError

import config
from config import CHATGPT_API_KEY
from datebase import update_model_usage

request_queue = asyncio.Queue()
MAX_TOKENS = defaultdict(lambda: 4097, {'gpt-3.5-turbo-0613':4182-364,'gpt-3.5-turbo-16k':16384,'gpt-4':8192,'gpt-4-0613':8192-364,'gpt-3.5-turbo':4097})
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
rate_limiter =defaultdict(lambda :AsyncLimiter(3, 60))
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
    if config.USE_API:
        while True:
            if 'functions' in params and not params['functions']:
                params['model'] = params['model'].replace('-0613', '')
                params.pop('functions')
                params.pop('function_call')
            async with rate_limiter[params['model']]:
                try:
                    #set_random_api_key()
                    # Ограничьте историю MAX_HISTORY сообщениями
                    trim(params)
                    params['messages'] = [{"role": item["role"], "content": item["content"], **({'name': item['name']} if 'name' in item  else {})} for item in params['messages']]
                    new_dict= {'messages':[]}
                    for msg in params['messages']:
                        if msg['content']:
                            if not isinstance(msg['content'], str):
                                msg['content']=json.dumps(msg['content'])
                            new_dict['messages'].append(msg)
                    params['messages']=new_dict['messages']
                    user_id=None
                    if 'user_id' in params:
                        user_id = params['user_id']
                        params.pop('user_id')
                    openai.aiosession.set(await get_sessiong())
                    result = await openai.ChatCompletion.acreate(**params)
                    if params.get('stream',None):
                        return result

                    if user_id:
                        update_model_usage(user_id, params['model'], result['usage']['prompt_tokens'], result['usage']['completion_tokens'])
                    return result
                except RateLimitError as error:
                    if 'billing details' in error.error['message']:
                        result={'choices':[{'message':{'content':'Простите, но у меня закончились деньги чтобы общаться с вами. Как только за меня заплатят я заработaю.'}}]}
                        return result
                        #raise error
                    await asyncio.sleep(20)
                    continue
    else:
        from gpt4_openai import GPT4OpenAI
        global llm, cur_token_index
        if llm is None:
            llm = [GPT4OpenAI(token=token, headless=True, model='gpt-3.5' if params['model']!='gpt-4'else 'gpt-4') for token in my_session_tokens]
            # GPT3.5 will answer 8, while GPT4 should be smart enough to answer 10
        prompt = params['messages'][-1]['content']
        response = llm[cur_token_index](prompt)
        result = {'choices': [{'message': {
            'content': response}}]}
        return result
    return result


def trim(params):
    if count_tokens(params['messages']) > MAX_TOKENS[params['model']]:
        trimmed_messages = []
        for msg in params['messages'][::-1]:  # reverse the list
            msg_token_count = count_tokens([msg])
            if msg_token_count > MAX_TOKENS[params['model']] // 2:
                # Trim the message
                msg['content'] = trim_message_to_tokens(msg['content'], MAX_TOKENS[params['model']] // 2)
                msg_token_count = count_tokens([msg])
            if not trimmed_messages or (
                    count_tokens(trimmed_messages) + msg_token_count <= MAX_TOKENS[params['model']]):
                trimmed_messages.append(msg)
            else:
                break
        params['messages'] = trimmed_messages[::-1]  # reverse back

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            if key in ['role','content']:
                num_tokens += len(encoding.encode(value))
            if key in ["name"]:
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens
async def gpt_acreate(**params):
    if not params.get('stream',False):
        future = asyncio.get_event_loop().create_future()
        await request_queue.put({
            'params': params,
            'future': future
        })
        return  await future
    else:
        return agpt(**params)

tokenizer=None
def count_tokens(history):
    global tokenizer
    if tokenizer is None:
        from transformers import GPT2Tokenizer
        encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')

    tokens=0
    for msg in history:
        tokens+=len(encoding.encode(str(msg['content'])))
    return tokens





async def shorten(message_text):
    tokens = count_tokens([{'content': message_text}])
    if tokens > MAX_TOKENS['gpt-3.5-turbo-16k']:
        normal_text = []
        ctns = message_text.split('\n')
        if len(ctns) <= 2:
            ctns = message_text.split()
        while count_tokens(normal_text) < MAX_TOKENS['gpt-3.5-turbo-16k'] and any(ctns):
            elem = ctns.pop()
            content_elem_ = {'content': elem}
            if count_tokens(normal_text + [content_elem_]) < MAX_TOKENS['gpt-3.5-turbo-16k']:
                normal_text.append(content_elem_)
            else:
                break
        message_text = '\n'.join(msg['content'] for msg in normal_text)
        tokens= count_tokens([{'content': message_text}])
    if tokens > MAX_TOKENS['gpt-3.5-turbo-0613']//3:
        message_text=await summary_gpt([{'role': config.Role_USER, 'content':message_text}])

    return message_text


async def summary_gpt(history_for_openai,user_id):
    history_for_openai = [msg for msg in history_for_openai if
                          msg['role'] in [config.Role_ASSISTANT, config.Role_SYSTEM, config.Role_USER]]
    model = "gpt-3.5-turbo-16k"
    chat_response = await gpt_acreate(
        model=model,
        messages=history_for_openai + [
            {
                'role': 'system',
                'content': "Your task is to summarize the previous information. Do not extend the dialogue or answer any questions. Only summarize."
            }
        ],user_id=user_id
    )
    summary = chat_response['choices'][0]['message']['content']
    return summary

async def check_socks5_proxy(ip,proxy_port,proxy_user=None,proxy_pass=None):
    response = requests.get('http://httpbin.org/ip',proxies={'http':f'{ip}:{proxy_port}'}, timeout=10)
    print(response.text)
    from openai.api_resources import completion

    # Создание сессии requests с настройками прокси
    import os
    session= await aiohttp.ClientSession(proxy=f'{proxy_user}:{proxy_port}').__aenter__()
    openai.aiosession.set(session)
    #os.environ['https_proxy'] = 'http://20.111.54.16:80'

    # Теперь вы можете делать запросы к OpenAI, которые будут использовать прокси

    try:
        response = requests.get('http://httpbin.org/ip', timeout=10)
        if response.status_code == 200:
            print(response.text)
            return True
    except Exception as e:
        print(f"Error with {ip}: {e}")
    return False

async def set_random_api_key():
    import get_proxy
    prox='20.111.54.16:80'
    ip,port=prox.split(':')
    port=int(port)
    #f=await check_socks5_proxy(ip,port)
    #print('proxy is working:',f)


async def get_sessiong():
    #os.environ['https_proxy'] = 'http://20.111.54.16:80'
    #os.environ['http_proxy'] = 'http://20.111.54.16:80'
    from aiohttp_proxy import ProxyConnector, ProxyType

    connector = ProxyConnector.from_url('socks5://user109086:ku4sz6@146.247.105.173:17867')
    ### or use ProxyConnector constructor
    # connector = ProxyConnector(
    #     proxy_type=ProxyType.SOCKS5,
    #     host='127.0.0.1',
    #     port=1080,
    #     username='user',
    #     password='password',
    #     rdns=True
    # )
    return   await  aiohttp.ClientSession(connector=connector).__aenter__()
