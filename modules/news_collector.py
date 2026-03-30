#!/usr/bin/env python3
"""
新聞收集模組 v4
四來源架構（按品質排序）：
  1. 頂級財經媒體 RSS（Bloomberg, Reuters, FT, WSJ, CNN Business）— via Google News RSS
  2. CNBC RSS（直接 RSS feed）— 即時性最強
  3. NewsAPI.org — 廣泛覆蓋主流財經媒體
  4. Polygon.io — 補充 ticker 關聯度和市場情緒數據

品質控制：
  - 來源分級：Tier-1（Bloomberg/Reuters/FT/WSJ）> Tier-2（CNBC/CNN）> Tier-3（NewsAPI/Polygon）
  - 過濾律師事務所集體訴訟廣告
  - 嚴格日期過濾，只保留目標日期的新聞
  - 智慧去重合併
"""
import os
import re
import json
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import Counter
from email.utils import parsedate_to_datetime

POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY', '')
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY', '919b1fdb80a340f2b3080464664d7178')
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', 'd6nsik9r01qse5qmtl4gd6nsik9r01qse5qmtl50')
MARKETAUX_API_KEY = os.environ.get('MARKETAUX_API_KEY', 'V8xTWZIiaj2dtxt2ULUyS6Z7gQKARSygVRoYXQg6')

# ─── 來源品質分級 ─────────────────────────────────────────────────
SOURCE_TIERS = {
    # Tier 1: 頂級財經媒體
    'Bloomberg': 1, 'Reuters': 1, 'Financial Times': 1,
    'The Wall Street Journal': 1, 'Wall Street Journal': 1, 'WSJ': 1,
    # Tier 2: 優質財經媒體
    'CNBC': 2, 'CNN': 2, 'CNN Business': 2, 'MarketWatch': 2,
    'Barron\'s': 2, 'The Economist': 2, 'Forbes': 2,
    'Nikkei Asia': 2, 'Nikkei': 2, 'SCMP': 2,
    'South China Morning Post': 2,
    # Tier 3: 一般來源
}

def _get_source_tier(publisher):
    """取得來源的品質等級（1=最高, 3=一般）"""
    pub_lower = publisher.lower()
    for name, tier in SOURCE_TIERS.items():
        if name.lower() in pub_lower:
            return tier
    return 3


# ─── 垃圾新聞過濾規則 ─────────────────────────────────────────────
JUNK_TITLE_PATTERNS = [
    r'class action',
    r'securities fraud',
    r'shareholder alert',
    r'investor alert',
    r'reminds investors',
    r'encourages.*investors.*to\s+(inquire|contact)',
    r'announces.*class action',
    r'announces.*lawsuit',
    r'investigating.*securities',
    r'lead plaintiff deadline',
    r'securities litigation',
    r'loss recovery',
    r'investors with.*losses',
]

JUNK_PUBLISHERS = {
    'halper sadeh', 'bragar eagel', 'rosen law', 'robbins llp',
    'bernstein liebhard', 'pomerantz', 'levi & korsinsky',
    'kessler topaz', 'schall law', 'faruqi & faruqi',
    'bronstein, gewirtz', 'rigrodsky & long', 'johnson fistel',
    'kirby mcinerney', 'glancy prongay', 'block & leviton',
    'scott+scott', 'labaton sucharow',
}

_JUNK_RE = re.compile('|'.join(JUNK_TITLE_PATTERNS), re.IGNORECASE)


def _is_junk_article(article):
    """判斷是否為垃圾新聞（律師事務所廣告、訴訟招攬等）"""
    title = article.get('title', '')
    desc = article.get('description', '') or ''
    publisher = article.get('publisher', '').lower()

    for junk_pub in JUNK_PUBLISHERS:
        if junk_pub in publisher:
            return True

    combined = title + " " + desc
    if _JUNK_RE.search(combined):
        return True

    return False


# ─── 來源 1：頂級財經媒體 via Google News RSS ─────────────────────

# Google News RSS 查詢配置：site:domain + 財經關鍵詞
PREMIUM_RSS_SOURCES = {
    'Bloomberg': 'https://news.google.com/rss/search?q=site:bloomberg.com+when:1d&hl=en-US&gl=US&ceid=US:en',
    'Reuters': 'https://news.google.com/rss/search?q=site:reuters.com+business+when:1d&hl=en-US&gl=US&ceid=US:en',
    'Financial Times': 'https://news.google.com/rss/search?q=site:ft.com+when:1d&hl=en-US&gl=US&ceid=US:en',
    'WSJ': 'https://news.google.com/rss/search?q=site:wsj.com+when:1d&hl=en-US&gl=US&ceid=US:en',
    'CNN Business': 'https://news.google.com/rss/search?q=site:cnn.com+business+when:1d&hl=en-US&gl=US&ceid=US:en',
    # 亞洲媒體
    'Nikkei Asia': 'https://news.google.com/rss/search?q=site:asia.nikkei.com+when:1d&hl=en-US&gl=US&ceid=US:en',
    'SCMP': 'https://news.google.com/rss/search?q=site:scmp.com+business+when:1d&hl=en-US&gl=US&ceid=US:en',
}


def get_premium_rss_news():
    """從 Google News RSS 抓取頂級財經媒體新聞"""
    all_articles = []

    for source_name, rss_url in PREMIUM_RSS_SOURCES.items():
        try:
            resp = requests.get(rss_url, timeout=15,
                                headers={'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'})
            if resp.status_code != 200:
                print(f"    {source_name}: HTTP {resp.status_code}")
                continue

            root = ET.fromstring(resp.text)
            items = root.findall('.//item')

            count = 0
            for item in items:
                title_el = item.find('title')
                pubdate_el = item.find('pubDate')
                link_el = item.find('link')
                source_el = item.find('source')

                title = title_el.text if title_el is not None else ''
                pubdate = pubdate_el.text if pubdate_el is not None else ''
                link = link_el.text if link_el is not None else ''
                src = source_el.text if source_el is not None else source_name

                # 清理標題（移除 " - Bloomberg" 等後綴）
                clean_title = re.sub(r'\s*-\s*(Bloomberg|Reuters|Financial Times|WSJ|CNN)$', '', title).strip()

                # 解析日期
                published_utc = ''
                if pubdate:
                    try:
                        dt = parsedate_to_datetime(pubdate)
                        published_utc = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                    except Exception:
                        published_utc = pubdate

                all_articles.append({
                    'title': clean_title if clean_title else title,
                    'description': '',
                    'publisher': src,
                    'published_utc': published_utc,
                    'tickers': [],
                    'keywords': [],
                    'insights': [],
                    'url': link,
                    'source': 'premium_rss',
                    'source_tier': _get_source_tier(src),
                })
                count += 1

            print(f"    {source_name}: {count} 篇")

        except Exception as e:
            print(f"    {source_name}: Error - {e}")

    return all_articles


# ─── 來源 2：CNBC RSS（直接 feed） ───────────────────────────────

CNBC_RSS_FEEDS = {
    'Top News': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114',
    'World': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362',
    'Business': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147',
    'Technology': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910',
    'Finance': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664',
}


def get_cnbc_rss_news():
    """從 CNBC RSS 直接抓取新聞"""
    all_articles = []
    seen_titles = set()

    for feed_name, rss_url in CNBC_RSS_FEEDS.items():
        try:
            resp = requests.get(rss_url, timeout=10)
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.text)
            items = root.findall('.//item')

            count = 0
            for item in items:
                title_el = item.find('title')
                pubdate_el = item.find('pubDate')
                link_el = item.find('link')

                title = title_el.text if title_el is not None else ''
                pubdate = pubdate_el.text if pubdate_el is not None else ''
                link = link_el.text if link_el is not None else ''

                # CNBC feed 內去重
                title_key = title.lower()[:80]
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                # 解析日期
                published_utc = ''
                if pubdate:
                    try:
                        dt = parsedate_to_datetime(pubdate)
                        published_utc = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                    except Exception:
                        published_utc = pubdate

                all_articles.append({
                    'title': title,
                    'description': '',
                    'publisher': 'CNBC',
                    'published_utc': published_utc,
                    'tickers': [],
                    'keywords': [],
                    'insights': [],
                    'url': link,
                    'source': 'cnbc_rss',
                    'source_tier': 2,
                })
                count += 1

            print(f"    CNBC {feed_name}: {count} 篇")

        except Exception as e:
            print(f"    CNBC {feed_name}: Error - {e}")

    return all_articles


# ─── 來源 3：NewsAPI.org ──────────────────────────────────────────

def get_newsapi_headlines(category='business', country='us', page_size=50):
    """從 NewsAPI 獲取頭條新聞"""
    try:
        resp = requests.get('https://newsapi.org/v2/top-headlines', params={
            'category': category,
            'country': country,
            'pageSize': page_size,
            'apiKey': NEWSAPI_KEY,
        }, timeout=15)
        data = resp.json()
        if data.get('status') != 'ok':
            print(f"    NewsAPI headlines error: {data.get('message', 'unknown')}")
            return []
        return _process_newsapi_articles(data.get('articles', []))
    except Exception as e:
        print(f"    NewsAPI headlines error: {e}")
        return []


def get_newsapi_everything(query, from_date, to_date, sort_by='relevancy', page_size=30):
    """從 NewsAPI 搜尋特定主題的新聞"""
    try:
        resp = requests.get('https://newsapi.org/v2/everything', params={
            'q': query,
            'language': 'en',
            'sortBy': sort_by,
            'from': from_date,
            'to': to_date,
            'pageSize': page_size,
            'apiKey': NEWSAPI_KEY,
        }, timeout=15)
        data = resp.json()
        if data.get('status') != 'ok':
            print(f"    NewsAPI everything error: {data.get('message', 'unknown')}")
            return []
        return _process_newsapi_articles(data.get('articles', []))
    except Exception as e:
        print(f"    NewsAPI everything error: {e}")
        return []


def _process_newsapi_articles(raw_articles):
    """處理 NewsAPI 返回的文章，轉換為統一格式"""
    processed = []
    for article in raw_articles:
        if article.get('title') == '[Removed]':
            continue

        publisher = article.get('source', {}).get('name', '')
        processed.append({
            'title': article.get('title', ''),
            'description': article.get('description', '') or '',
            'publisher': publisher,
            'published_utc': article.get('publishedAt', ''),
            'tickers': [],
            'keywords': [],
            'insights': [],
            'url': article.get('url', ''),
            'source': 'newsapi',
            'source_tier': _get_source_tier(publisher),
        })
    return processed


# ─── 來源 4：Polygon.io（補充 ticker 關聯） ──────────────────────

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
            publisher = article.get('publisher', {}).get('name', '')
            processed.append({
                'title': article.get('title', ''),
                'description': article.get('description', ''),
                'publisher': publisher,
                'published_utc': pub_date,
                'tickers': article.get('tickers', []),
                'keywords': article.get('keywords', []),
                'insights': article.get('insights', []),
                'url': article.get('article_url', ''),
                'source': 'polygon',
                'source_tier': _get_source_tier(publisher),
            })
        return processed
    except Exception as e:
        print(f"    Polygon news error: {e}")
        return []


# ─── 日期過濾 ─────────────────────────────────────────────────────

def filter_articles_by_date(articles, target_date_str):
    """嚴格過濾：只保留目標日期當天的新聞"""
    filtered = []
    for article in articles:
        pub_utc = article.get('published_utc', '')
        if pub_utc:
            article_date = pub_utc[:10]  # 取 YYYY-MM-DD
            if article_date == target_date_str:
                filtered.append(article)
    return filtered


# ─── Ticker 關聯度提取 ────────────────────────────────────────────

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


# ─── 新聞分類 ─────────────────────────────────────────────────────

def categorize_news(articles):
    """將新聞分類為宏觀事件類別"""
    categories = {
        'central_bank': [],
        'economic_data': [],
        'geopolitics': [],
        'tech_industry': [],
        'commodities': [],
        'crypto': [],
        'earnings': [],
        'other': [],
    }

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


# ─── 主入口：四來源新聞收集 ───────────────────────────────────────

def get_news_for_date(target_date=None):
    """
    獲取指定日期的新聞（四來源架構）

    1. 頂級財經媒體 RSS（Bloomberg, Reuters, FT, WSJ, CNN Business）
    2. CNBC RSS（直接 feed）
    3. NewsAPI（廣泛覆蓋）
    4. Polygon（ticker 關聯）
    5. 品質過濾 + 來源分級排序 + 去重
    """
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"  新聞目標日期: {target_date}")
    all_articles = []

    # ── 來源 1：頂級財經媒體 via Google News RSS ──
    print(f"  [Premium RSS] 抓取 Bloomberg, Reuters, FT, WSJ, CNN Business...")
    premium_articles = get_premium_rss_news()
    premium_articles = filter_articles_by_date(premium_articles, target_date)
    print(f"    Premium RSS 當日新聞: {len(premium_articles)} 篇")
    all_articles.extend(premium_articles)

    # ── 來源 2：CNBC RSS ──
    print(f"  [CNBC RSS] 抓取 CNBC 新聞...")
    cnbc_articles = get_cnbc_rss_news()
    cnbc_articles = filter_articles_by_date(cnbc_articles, target_date)
    print(f"    CNBC 當日新聞: {len(cnbc_articles)} 篇")
    all_articles.extend(cnbc_articles)

    # ── 來源 3：NewsAPI Top Headlines ──
    print(f"  [NewsAPI] 抓取 Top Headlines...")
    headlines = get_newsapi_headlines(category='business', page_size=50)
    headlines = filter_articles_by_date(headlines, target_date)
    print(f"    Top Headlines (當日): {len(headlines)} 篇")
    all_articles.extend(headlines)

    # ── 來源 3b：NewsAPI Everything（多主題搜尋） ──
    search_queries = [
        ('stock market OR Wall Street OR S&P 500 OR Dow Jones OR NASDAQ', '股市'),
        ('Fed OR interest rate OR central bank OR monetary policy', '央行'),
        ('NVIDIA OR semiconductor OR AI chip OR data center', 'AI/科技'),
        ('oil price OR gold price OR commodity OR OPEC', '大宗商品'),
        ('tariff OR trade war OR geopolitics OR sanctions', '地緣政治'),
        ('earnings OR quarterly results OR revenue guidance', '財報'),
        ('bitcoin OR crypto OR ethereum', '加密貨幣'),
        ('merger OR acquisition OR IPO OR buyout', '併購/IPO'),
    ]

    for query, label in search_queries:
        print(f"  [NewsAPI] 搜尋 {label}...")
        articles = get_newsapi_everything(
            query=query,
            from_date=target_date,
            to_date=target_date,
            sort_by='relevancy',
            page_size=15
        )
        articles = filter_articles_by_date(articles, target_date)
        print(f"    {label}: {len(articles)} 篇")
        all_articles.extend(articles)

    # ── 來源 4：Polygon（補充 ticker 關聯） ──
    published_after = target_date + "T00:00:00Z"
    published_before = target_date + "T23:59:59Z"
    print(f"  [Polygon] 抓取新聞（ticker 關聯）...")
    polygon_articles = get_polygon_news(
        limit=100,
        published_after=published_after,
        published_before=published_before
    )
    polygon_articles = filter_articles_by_date(polygon_articles, target_date)
    print(f"    Polygon 新聞: {len(polygon_articles)} 篇")
    all_articles.extend(polygon_articles)

    # ── 來源 5-7：爬蟲（帶文章描述，不做日期過濾因為爬到的都是最新的） ──
    print(f"  [CNBC Scraper] 抓取 CNBC 文章描述...")
    cnbc_scraped = _scrape_cnbc_articles()
    print(f"    CNBC Scraper: {len(cnbc_scraped)} 篇（帶描述）")
    all_articles.extend(cnbc_scraped)

    print(f"  [BBC Scraper] 抓取 BBC Business...")
    bbc_scraped = _scrape_bbc_business()
    print(f"    BBC Scraper: {len(bbc_scraped)} 篇（帶描述）")
    all_articles.extend(bbc_scraped)

    print(f"  [Al Jazeera Scraper] 抓取 Al Jazeera Economy...")
    aj_scraped = _scrape_aljazeera_economy()
    print(f"    Al Jazeera Scraper: {len(aj_scraped)} 篇（帶描述）")
    all_articles.extend(aj_scraped)

    # ── 來源 8：Finnhub（帶新聞摘要） ──
    print(f"  [Finnhub] 抓取市場新聞...")
    finnhub_articles = _get_finnhub_news(target_date)
    print(f"    Finnhub 新聞: {len(finnhub_articles)} 篇")
    all_articles.extend(finnhub_articles)

    # ── 來源 6：MarketAux（帶完整描述+情緒） ──
    print(f"  [MarketAux] 抓取全球新聞...")
    marketaux_articles = _get_marketaux_news(target_date)
    print(f"    MarketAux 新聞: {len(marketaux_articles)} 篇")
    all_articles.extend(marketaux_articles)

    # ── 品質過濾：移除垃圾新聞 ──
    before_filter = len(all_articles)
    all_articles = [a for a in all_articles if not _is_junk_article(a)]
    junk_removed = before_filter - len(all_articles)
    print(f"  垃圾新聞過濾: 移除 {junk_removed} 篇（律師事務所廣告等）")

    # ── 智慧去重（根據標題相似度） ──
    seen_titles = set()
    unique_articles = []
    for article in all_articles:
        title = article.get('title', '').strip()
        if not title:
            continue
        # 標準化標題用於去重
        title_key = re.sub(r'[^a-zA-Z0-9\s]', '', title.lower())[:80]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_articles.append(article)

    all_articles = unique_articles
    print(f"  去重後總新聞數: {len(all_articles)}")

    # ── 按來源品質分級排序 ──
    def _article_priority(a):
        # 來源等級（Tier 1 最高）
        tier = a.get('source_tier', 3)
        # 來源類型排序：premium_rss > cnbc_rss > newsapi > polygon
        source_order = {
            'premium_rss': 0,
            'cnbc_rss': 1,
            'cnbc_scraper': 1,
            'bbc_scraper': 1,
            'aj_scraper': 2,
            'finnhub': 2,
            'marketaux': 2,
            'newsapi': 3,
            'polygon': 4,
        }
        src = source_order.get(a.get('source', ''), 4)
        # 有 ticker 關聯的排前面
        ticker_score = 0 if a.get('tickers') else 1
        return (tier, src, ticker_score)

    all_articles.sort(key=_article_priority)

    # ── 統計來源分布 ──
    source_stats = Counter()
    tier_stats = Counter()
    for a in all_articles:
        source_stats[a.get('publisher', 'Unknown')] += 1
        tier_stats[a.get('source_tier', 3)] += 1

    print(f"\n  === 新聞來源品質分布 ===")
    print(f"    Tier-1 (Bloomberg/Reuters/FT/WSJ): {tier_stats.get(1, 0)} 篇")
    print(f"    Tier-2 (CNBC/CNN/MarketWatch): {tier_stats.get(2, 0)} 篇")
    print(f"    Tier-3 (其他): {tier_stats.get(3, 0)} 篇")
    print(f"    Top 來源: {source_stats.most_common(10)}")

    return {
        'articles': all_articles,
        'categorized': categorize_news(all_articles),
        'trending_tickers': get_trending_tickers_from_news(all_articles),
        'date': target_date,
        'source_stats': {
            'tier_1': tier_stats.get(1, 0),
            'tier_2': tier_stats.get(2, 0),
            'tier_3': tier_stats.get(3, 0),
            'top_publishers': dict(source_stats.most_common(10)),
        },
    }


def _scrape_cnbc_articles():
    """爬取 CNBC 文章列表，抓取每篇的 meta description 作為描述"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        r = requests.get('https://www.cnbc.com/world/?region=world', headers=headers, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, 'html.parser')

        articles = []
        seen = set()
        for card in soup.select('.Card-titleContainer a, .Card-title a'):
            title = card.get_text(strip=True)
            href = card.get('href', '')
            if not title or len(title) < 15 or title in seen:
                continue
            seen.add(title)
            if not href.startswith('http'):
                href = 'https://www.cnbc.com' + href

            # 抓單篇的 meta description
            desc = ''
            try:
                r2 = requests.get(href, headers=headers, timeout=8)
                if r2.status_code == 200:
                    soup2 = BeautifulSoup(r2.text, 'html.parser')
                    og = soup2.find('meta', attrs={'property': 'og:description'})
                    if og and og.get('content'):
                        desc = og['content'][:300]
                    # 也抓發布時間
                    time_tag = soup2.find('time')
                    pub_time = time_tag.get('datetime', '') if time_tag else ''
            except Exception:
                pass

            articles.append({
                'title': title,
                'description': desc,
                'publisher': 'CNBC',
                'published_utc': pub_time if 'pub_time' in dir() else '',
                'tickers': [], 'keywords': [], 'insights': [],
                'url': href, 'source': 'cnbc_scraper',
                'source_tier': 2,
            })

            if len(articles) >= 15:  # 限制請求數量
                break

        return articles
    except Exception as e:
        print(f"    CNBC Scraper 錯誤: {e}")
        return []


def _scrape_bbc_business():
    """爬取 BBC Business 新聞列表（標題+描述）"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        r = requests.get('https://www.bbc.com/news/business', headers=headers, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, 'html.parser')

        articles = []
        seen = set()
        for card in soup.select('[data-testid="card-text-wrapper"]'):
            title_el = card.find('h2')
            desc_el = card.find('p')
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 10 or title in seen:
                continue
            seen.add(title)
            desc = desc_el.get_text(strip=True) if desc_el else ''

            # 找連結
            link = card.find_parent('a') or card.find('a')
            href = ''
            if link:
                href = link.get('href', '')
                if href and not href.startswith('http'):
                    href = 'https://www.bbc.com' + href

            articles.append({
                'title': title,
                'description': desc,
                'publisher': 'BBC News',
                'published_utc': '',
                'tickers': [], 'keywords': [], 'insights': [],
                'url': href, 'source': 'bbc_scraper',
                'source_tier': 2,
            })

        return articles
    except Exception as e:
        print(f"    BBC Scraper 錯誤: {e}")
        return []


def _scrape_aljazeera_economy():
    """爬取 Al Jazeera Economy 新聞"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        r = requests.get('https://www.aljazeera.com/economy/', headers=headers, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, 'html.parser')

        articles = []
        seen = set()
        for article in soup.select('article'):
            title_el = article.find('h3') or article.find('h2')
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 10 or title in seen:
                continue
            seen.add(title)

            # 找描述
            desc_el = article.find('p')
            desc = desc_el.get_text(strip=True) if desc_el else ''

            # 找連結
            link = article.find('a')
            href = ''
            if link:
                href = link.get('href', '')
                if href and not href.startswith('http'):
                    href = 'https://www.aljazeera.com' + href

            articles.append({
                'title': title,
                'description': desc,
                'publisher': 'Al Jazeera English',
                'published_utc': '',
                'tickers': [], 'keywords': [], 'insights': [],
                'url': href, 'source': 'aj_scraper',
                'source_tier': 2,
            })

        return articles
    except Exception as e:
        print(f"    Al Jazeera Scraper 錯誤: {e}")
        return []


def _get_finnhub_news(target_date):
    """從 Finnhub 獲取市場新聞（帶摘要）"""
    if not FINNHUB_API_KEY:
        return []
    try:
        r = requests.get(
            f'https://finnhub.io/api/v1/news?category=general&token={FINNHUB_API_KEY}',
            timeout=15
        )
        if r.status_code != 200:
            return []
        articles = []
        for item in r.json()[:80]:
            headline = item.get('headline', '')
            summary = item.get('summary', '')
            source = item.get('source', '')
            # Finnhub summary 常常跟 headline 一樣，只取真正有內容的
            if summary and summary != headline and len(summary) > len(headline) + 20:
                desc = summary[:500]
            else:
                desc = ''
            articles.append({
                'title': headline,
                'description': desc,
                'publisher': source,
                'published_utc': datetime.fromtimestamp(item.get('datetime', 0)).isoformat() if item.get('datetime') else '',
                'tickers': [],
                'keywords': [],
                'insights': [],
                'url': item.get('url', ''),
                'source': 'finnhub',
                'source_tier': _get_source_tier(source),
            })
        return articles
    except Exception as e:
        print(f"    Finnhub 錯誤: {e}")
        return []


def _get_marketaux_news(target_date):
    """從 MarketAux 獲取全球新聞（帶完整描述）"""
    if not MARKETAUX_API_KEY:
        return []
    try:
        r = requests.get(
            f'https://api.marketaux.com/v1/news/all',
            params={
                'language': 'en',
                'filter_entities': 'true',
                'published_on': target_date,
                'limit': 50,
                'api_token': MARKETAUX_API_KEY,
            },
            timeout=15
        )
        if r.status_code != 200:
            return []
        data = r.json()
        articles = []
        for item in data.get('data', []):
            articles.append({
                'title': item.get('title', ''),
                'description': item.get('description', '') or item.get('snippet', ''),
                'publisher': item.get('source', ''),
                'published_utc': item.get('published_at', ''),
                'tickers': [e.get('symbol', '') for e in item.get('entities', []) if e.get('symbol')],
                'keywords': [],
                'insights': [],
                'url': item.get('url', ''),
                'source': 'marketaux',
                'source_tier': _get_source_tier(item.get('source', '')),
            })
        return articles
    except Exception as e:
        print(f"    MarketAux 錯誤: {e}")
        return []


if __name__ == '__main__':
    data = get_news_for_date()
    with open('/home/ubuntu/daily-macro-report/reports/news_test.json', 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n新聞收集完成 - {data['date']}")
    print(f"總新聞數: {len(data['articles'])}")

    print(f"\n前 15 篇新聞（按品質排序）:")
    for a in data['articles'][:15]:
        tier = a.get('source_tier', 3)
        pub = a.get('publisher', '')
        title = a.get('title', '')[:80]
        print(f"  [T{tier}|{pub}] {title}")
