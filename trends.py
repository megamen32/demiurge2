import pandas as pd
from GoogleNews import GoogleNews

def get_news(text:str=' '):
    googlenews = GoogleNews(lang='ru', period='d')
    if not text or not any(text):
        text=' '
    googlenews.search(text)
    result = googlenews.result()
    trends=[]
    for article in result:
        trends.append(article['title'].strip('...')+' '+article['desc']+'\n'+article['url'])
    return trends

def get_tags():
    from pytrends.request import TrendReq
    pytrends = TrendReq()
    news = pytrends.trending_searches(pn='russia')
    df = pd.DataFrame(news)
    # отсортируем данные по убыванию популярности новостных тем
    tags=[ a[0] for a in df.values.tolist()]

    # выведем первые 10 строк объекта df
    return tags