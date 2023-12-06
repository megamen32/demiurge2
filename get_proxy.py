import traceback

import redis
import random
import requests
import time
import json

# Настройки Redis
from config import SERVER_URL, AUTH

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# Подключение к Redis
redis_conn = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
PROXY_CACHE_KEY = 'proxy_cache'
PROXY_CACHE_TIME = 60  # Время кеширования в секундах


def get_proxy():
    try:
        while True:
            # Проверка кеша и времени последнего запроса
            cached_proxies = redis_conn.get(PROXY_CACHE_KEY)
            proxy_list=None
            if cached_proxies and time.time() - json.loads(cached_proxies)['timestamp'] < PROXY_CACHE_TIME:
                proxy_list = json.loads(cached_proxies)['proxies']
            if not proxy_list:
                if False:
                    with open('data/proxy.txt', 'r') as f:
                        proxies = f.read()
                        _proxy_list = proxies.split('\n')
                        proxy_list=[]
                        for pr in _proxy_list:
                            proxy_list.append({'proxy':pr})
                else:
                    for i in range(2):
                        t = requests.get(f'{SERVER_URL}/proxy/', params={'count': 50, 'priority': i == 0}, auth=AUTH, timeout=15)
                        if t.status_code == 500:
                            break
                        try:
                            proxy_list = t.json()
                        except:
                            proxy_list = [{'proxy': t.text}]
                        if len(proxy_list)>0:
                            break
                    # Сохранение прокси в кеше Redis
                    redis_conn.set(PROXY_CACHE_KEY, json.dumps({'proxies': proxy_list, 'timestamp': time.time()}))

            proxy = random.choice(proxy_list)['proxy']



            return proxy
    except:
        traceback.print_exc()



def check_http_proxy(ip, proxy_port, proxy_user=None, proxy_pass=None):
    proxies = {
        'http': (f'http://{proxy_user}:{proxy_pass}@{ip}:{proxy_port}' if proxy_user else f'http://{ip}:{proxy_port}'),
        'https': (f'http://{proxy_user}:{proxy_pass}@{ip}:{proxy_port}' if proxy_user else f'http://{ip}:{proxy_port}'),
    }
    try:
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
        if response.status_code == 200:
            return True
    except Exception as e:
        print(f"Error with {ip}: {e}")
    return False

if __name__ == '__main__':
    proxies = ['109.254.114.51:9090',
'198.49.68.80:80',
'138.68.60.8:8080',
'159.65.77.168:8585',
'62.33.207.202:3128',
'31.148.207.153:80',
'178.54.21.203:8081',
'88.99.249.96:8188',
'185.217.143.125:80',
'94.45.74.60:8080',
'93.20.25.100:80',
'157.245.46.100:31280',
'83.243.92.154:8080',
'167.71.41.76:8080',
'43.157.105.92:8888',
'43.157.8.79:8888',
'129.150.39.9:80',
'51.210.216.54:80',
'109.194.22.61:8080',
'88.99.249.96:8110',
'79.137.206.147:80',
'166.109.239.42:8080',
'43.133.136.208:8800',
'43.157.67.116:8888',
'47.91.104.88:3128',
'20.219.137.240:3000',
'103.117.192.10:80',
'117.160.250.134:80',
'208.193.6.170:3131',
'117.160.250.132:80',
'164.92.105.75:2083',
'144.217.180.238:8888',
'188.87.137.45:3128',
'5.2.180.169:8080',
'159.203.61.169:8080',
'20.42.119.47:80',
'103.120.6.46:80',
'204.188.255.68:4128',
'176.98.81.85:8080',
'103.123.8.46:80',
'46.47.197.210:3128',
'91.241.217.58:9090',
'191.96.100.33:3128',
'45.88.138.176:3128',
'144.202.9.97:3467',
'84.39.112.144:3128',
'153.19.91.77:80',
'88.99.249.96:8250',
'43.156.0.125:8888',
'62.33.207.202:80',
'164.132.170.100:80',
'132.145.162.109:3128',
'103.23.37.138:80',
'5.180.254.9:80',
'103.105.196.130:3128',
'85.214.251.15:3128',
'5.161.111.42:3128',
'103.231.78.36:80',
'185.221.237.219:80',
'103.178.94.107:80',
'31.210.172.11:3128',
'143.47.121.145:3128',
'109.254.81.159:9090',
'177.200.239.40:999',
'95.216.164.36:80',
'194.182.187.78:3128',
'188.215.245.235:80',
'94.130.54.171:7293',
'94.130.54.171:7095',
'190.110.35.224:999',
'179.1.129.37:999',
'142.93.218.24:3128',
'65.21.232.59:8786',
'5.161.82.73:3128',
'179.53.239.155:3128',
'103.83.232.122:80',
'103.218.188.2:80',
'88.99.249.96:8283',
'129.213.118.148:3128',
'179.53.250.19:3128',
'92.63.168.248:80',
'5.161.207.168:3128',
'45.5.118.43:999',
'2.83.198.171:80',
'78.47.186.43:6666',
'162.212.157.35:8080',
'162.212.157.238:8080',
'162.212.153.95:8080',
'103.127.1.130:80',
'34.86.252.79:8585',
'34.162.24.17:8585',
'34.86.196.77:8585',
'34.162.183.32:8585',
'34.162.76.11:8585',
'35.193.158.6:8585',
'34.162.63.141:8585',
'34.162.67.130:8585',
'34.162.171.228:8585',
'34.86.138.63:8585',
'34.162.135.2:8585',
'34.162.156.215:8585',
'34.85.155.119:8585',
'34.162.53.144:8585',
'34.162.22.200:8585',
'35.245.31.182:8585',
'66.29.154.103:3128',
'46.160.209.155:8088',
'87.123.56.163:80',
'181.225.107.227:999',
'200.82.188.28:999',
'103.146.17.241:80',
'43.251.118.153:45787',
'37.32.12.216:4006',
'158.101.113.18:80',
'188.127.249.9:20255',
'165.225.206.248:10007',
'174.138.184.82:38661',
'188.235.0.207:8282',
'103.118.78.194:80',
'95.217.210.191:8080',
]
    for i in range(5):
        ip, port = random.choice(proxies).split(':')
        good = check_http_proxy(ip, int(port))
        if good:
            print('succ',ip,port)
            break

        print('failed')
