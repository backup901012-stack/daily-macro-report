#!/usr/bin/env python3
"""
新聞收集模組
使用 Polygon.io API 獲取金融新聞，嚴格過濾日期，只保留目標日期的新聞
增加搜索工具抓取當日真正的重點財經新聞
"""
import os
import json
import requests
from datetime import datetime, timedelta
from collections import Counter

POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY', '')


def get_polygon_news(limit=100, ticker=None, published_after=None, published_before=None):
    """從 Polygon.io 獲取金融新聞，支持日期範圍過濾"""
    params = {
        'limit': limit,
        'apiKey': POLYGON_API_KEY,
        'order': 'desc',
        'sort': 'published_utc',
    }
    if ticker:
        params['ticker'] = ticker
    if published_after:
        params['published_utc.gte'] = published_after
    if published_before:
        params['published_utc.lte'] = published_before

    try:
        url = "https://api.polygon.io/v2/reference/news"
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        articles = data.get('results', [])

        processed = []
        for article in articles:
            pub_date = article.get('published_utc', '')
            processed.append({
                'title': article.get('title', ''),
                'description': article.get('description', ''),
                'publisher': article.get('publisher', {}).get('name', ''),
                'published_utc': pub_date,
                'tickers': article.get('tickers', []),
                'keywords': article.get('keywords', []),
                'insights': article.get('insights', []),
                'url': article.get('article_url', ''),
            })
        return processed
    except Exception as e:
        print(f"Polygon news error: {e}")
        return []


def filter_articles_by_date(articles, target_date_str):
    """嚴格過濾：只保留目標日期當天的新聞"""
    filtered = []
    for article in articles:
        pub_utc = article.get('published_utc', '')
        if pub_utc:
            # published_utc 格式: 2026-02-09T14:30:00Z
            article_date = pub_utc[:10]  # 取 YYYY-MM-DD
            if article_date == target_date_str:
                filtered.append(article)
    return filtered


def get_trending_tickers_from_news(articles):
    """從新聞中提取熱門股票（出現頻率最高的 tickers）"""
    ticker_counter = Counter()
    ticker_sentiment = {}

    for article in articles:
        for ticker in article.get('tickers', []):
            ticker_counter[ticker] += 1

        for insight in article.get('insights', []):
            t = insight.get('ticker', '')
            sentiment = insight.get('sentiment', 'neutral')
            reasoning = insight.get('sentiment_reasoning', '')
            if t:
                if t not in ticker_sentiment:
                    ticker_sentiment[t] = {'positive': 0, 'negative': 0, 'neutral': 0, 'reasons': []}
                ticker_sentiment[t][sentiment] = ticker_sentiment[t].get(sentiment, 0) + 1
                if reasoning:
                    ticker_sentiment[t]['reasons'].append(reasoning)

    # 取出現次數最多的前20個 tickers
    top_tickers = ticker_counter.most_common(20)

    results = []
    for ticker, count in top_tickers:
        sentiment_info = ticker_sentiment.get(ticker, {})
        results.append({
            'ticker': ticker,
            'mention_count': count,
            'sentiment': sentiment_info,
        })

    return results


def categorize_news(articles):
    """將新聞分類為宏觀事件類別"""
    categories = {
        'central_bank': [],      # 央行政策
        'economic_data': [],     # 經濟數據
        'geopolitics': [],       # 地緣政治
        'tech_industry': [],     # 科技產業
        'commodities': [],       # 大宗商品
        'crypto': [],            # 加密貨幣
        'earnings': [],          # 財報
        'other': [],             # 其他
    }

    # 關鍵詞分類規則
    rules = {
        'central_bank': ['fed', 'federal reserve', 'ecb', 'boj', 'pboc', 'rate cut', 'rate hike',
                         'interest rate', 'monetary policy', 'inflation target', 'quantitative',
                         'central bank', 'fomc', 'powell', 'lagarde'],
        'economic_data': ['gdp', 'cpi', 'ppi', 'employment', 'payroll', 'jobs report', 'retail sales',
                          'unemployment', 'inflation', 'consumer price', 'producer price',
                          'manufacturing', 'pmi', 'trade balance', 'housing'],
        'geopolitics': ['tariff', 'sanction', 'trade war', 'geopolitical', 'war', 'conflict',
                        'nuclear', 'iran', 'china', 'russia', 'ukraine', 'middle east', 'trump',
                        'election', 'government shutdown', 'executive order', 'policy'],
        'tech_industry': ['ai', 'artificial intelligence', 'semiconductor', 'chip', 'nvidia',
                          'openai', 'tech', 'software', 'data center', 'cloud'],
        'commodities': ['gold', 'oil', 'crude', 'silver', 'copper', 'commodity', 'opec',
                        'precious metal', 'natural gas', 'energy'],
        'crypto': ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'token', 'defi', 'btc', 'eth'],
        'earnings': ['earnings', 'revenue', 'profit', 'quarterly', 'fiscal', 'guidance',
                     'beat expectations', 'miss expectations', 'financial results'],
    }

    for article in articles:
        text = (article.get('title', '') + ' ' + article.get('description', '')).lower()
        categorized = False

        for category, keywords in rules.items():
            if any(kw in text for kw in keywords):
                categories[category].append(article)
                categorized = True
                break

        if not categorized:
            categories['other'].append(article)

    return categories


def get_news_for_date(target_date=None):
    """
    獲取指定日期的新聞
    嚴格只返回 target_date 當天的新聞
    如果當天是週末/假日新聞較少，會擴展到前一個交易日
    """
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # 設定嚴格的日期範圍：目標日期 00:00:00 到 23:59:59 UTC
    published_after = f"{target_date}T00:00:00Z"
    published_before = f"{target_date}T23:59:59Z"

    print(f"  抓取新聞日期範圍: {published_after} ~ {published_before}")

    # 第一次抓取：嚴格目標日期
    articles = get_polygon_news(
        limit=100,
        published_after=published_after,
        published_before=published_before
    )

    # 嚴格過濾確保日期正確
    articles = filter_articles_by_date(articles, target_date)
    print(f"  目標日期 {target_date} 新聞數: {len(articles)}")

    # 如果是週末或假日，新聞可能很少，擴展到前一天
    if len(articles) < 10:
        prev_date = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        prev_after = f"{prev_date}T00:00:00Z"
        prev_before = f"{prev_date}T23:59:59Z"
        extra_articles = get_polygon_news(
            limit=50,
            published_after=prev_after,
            published_before=prev_before
        )
        extra_articles = filter_articles_by_date(extra_articles, prev_date)
        print(f"  補充前一日 {prev_date} 新聞數: {len(extra_articles)}")
        articles.extend(extra_articles)

    # 去重（根據標題）
    seen_titles = set()
    unique_articles = []
    for article in articles:
        title = article.get('title', '')
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_articles.append(article)

    articles = unique_articles
    print(f"  去重後總新聞數: {len(articles)}")

    return {
        'articles': articles,
        'categorized': categorize_news(articles),
        'trending_tickers': get_trending_tickers_from_news(articles),
        'date': target_date,
    }


if __name__ == '__main__':
    data = get_news_for_date()
    with open('/home/ubuntu/daily-macro-report/reports/news_test.json', 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n新聞收集完成 - {data['date']}")
    print(f"總新聞數: {len(data['articles'])}")

    # 顯示每篇新聞的日期，驗證過濾
    print(f"\n新聞日期驗證:")
    for a in data['articles'][:5]:
        print(f"  [{a['published_utc'][:10]}] {a['title'][:80]}")

    for cat, articles in data['categorized'].items():
        if articles:
            print(f"  {cat}: {len(articles)} articles")
    print(f"\n熱門股票:")
    for t in data['trending_tickers'][:10]:
        print(f"  {t['ticker']}: {t['mention_count']} mentions")
