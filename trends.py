import pandas as pd
from GoogleNews import GoogleNews

def get_news2(text:str=' '):
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
def get_news(query=' '):
    from googlesearch import search
    search_results = []
    for result in search(query,advanced=True, num_results=10):
        search_results.append(result.title.strip('...')+' '+result.description+'\n'+result.url)
    return search_results

def get_tags():
    from pytrends.request import TrendReq
    pytrends = TrendReq()
    news = pytrends.trending_searches(pn='russia')
    df = pd.DataFrame(news)
    # отсортируем данные по убыванию популярности новостных тем
    tags=[ a[0] for a in df.values.tolist()]

    # выведем первые 10 строк объекта df
    return tags