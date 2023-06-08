import pandas as pd
import requests


import config


def get_news2(text:str=' '):
    from GoogleNews import GoogleNews
    googlenews = GoogleNews(lang='ru')
    if not text or not any(text):
        text=' '
        googlenews = GoogleNews(lang='ru',period='d')
    googlenews.search(text)
    result = googlenews.result()
    trends=[]
    for article in result:
        trends.append(article['title'].strip('...')+' '+article['desc']+'\n'+article['link'])
    return trends
def get_news_google(query=' '):
    from googlesearch import search
    search_results = []
    generator = search(query, advanced=True, num_results=10)
    for result in generator:
        search_results.append(result.title.strip('...')+' '+result.description+'\n'+result.url)
    return search_results
def get_news_old(query=' '):
    from search_web import google_search
    search_results = []
    generator = google_search(query)
    for result in generator:
        search_results.append(result.title.strip('...')+' '+result.description+'\n'+result.url)
    return search_results
def get_news(search_term=' '):
    cx=config.CX
    api_key=config.GOOGLE_SEARCH_API
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': search_term,
        'key': api_key,
        'cx': cx,
        'num':5,
    }
    response = requests.get(base_url, params=params)
    items= response.json()['items']
    text=[f"Title: {result['title']}\nLink: {result['link']}\nSnippet: {result['snippet']}\n" for result in items]
    return text
def get_tags():
    from pytrends.request import TrendReq
    pytrends = TrendReq()
    news = pytrends.trending_searches(pn='russia')
    df = pd.DataFrame(news)
    # отсортируем данные по убыванию популярности новостных тем
    tags=[ a[0] for a in df.values.tolist()]

    # выведем первые 10 строк объекта df
    return tags