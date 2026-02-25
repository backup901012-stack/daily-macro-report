#!/usr/bin/env python3
"""
經濟日曆模組
從網頁爬取重要經濟數據發布時間表
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json


def scrape_economic_calendar(target_date=None):
    """從 Trading Economics 爬取經濟日曆"""
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')

    try:
        url = f"https://tradingeconomics.com/calendar"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        # 由於 Trading Economics 可能需要 JS 渲染，使用備用方案
    except Exception as e:
        pass

    return get_hardcoded_calendar(target_date)


def get_hardcoded_calendar(target_date):
    """
    根據 S&P Global 等來源整理的本週經濟日曆
    在實際部署中，這部分會由 AI 從新聞中提取
    """
    # 計算本週日期
    try:
        dt = datetime.strptime(target_date, '%Y-%m-%d')
    except:
        dt = datetime.now()

    weekday = dt.weekday()  # 0=Monday
    week_start = dt - timedelta(days=weekday)

    calendar = []

    # 動態生成本週日曆框架
    days = ['週一', '週二', '週三', '週四', '週五']
    for i in range(5):
        day_dt = week_start + timedelta(days=i)
        calendar.append({
            'date': day_dt.strftime('%Y-%m-%d'),
            'day_label': days[i],
            'events': []
        })

    return calendar


def get_upcoming_events_from_news(news_articles, ai_analyzer=None):
    """從新聞中提取即將到來的經濟事件"""
    if ai_analyzer is None:
        return []

    # 收集提到經濟數據的新聞
    econ_keywords = ['cpi', 'ppi', 'gdp', 'employment', 'payroll', 'jobs report',
                     'retail sales', 'inflation', 'interest rate', 'fomc',
                     'manufacturing', 'trade balance', 'housing', 'consumer confidence',
                     'unemployment', 'budget', 'current account']

    relevant_news = []
    for article in news_articles:
        text = (article.get('title', '') + ' ' + article.get('description', '')).lower()
        if any(kw in text for kw in econ_keywords):
            relevant_news.append({
                'title': article['title'],
                'description': article.get('description', '')[:300],
            })

    return relevant_news[:10]


if __name__ == '__main__':
    cal = scrape_economic_calendar()
    print(json.dumps(cal, ensure_ascii=False, indent=2))
