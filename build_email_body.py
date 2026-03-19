#!/usr/bin/env python3
"""Generate email body text from raw_data JSON."""
import json
import sys

def build_email_body(raw_data_path):
    with open(raw_data_path) as f:
        data = json.load(f)

    md = data.get('market_data', {})
    news = data.get('news_events', [])
    cal = data.get('calendar_events', [])
    holidays = data.get('holiday_alerts', {})
    idx_analysis = data.get('index_analysis', {})
    
    asia = md.get('asia_indices', {})
    europe = md.get('europe_indices', {})
    us = md.get('us_indices', {})
    crypto = md.get('crypto', {})

    lines = []

    # Holiday alerts
    if holidays.get('has_alerts'):
        tomorrow = holidays.get('tomorrow_closed', [])
        if tomorrow:
            lines.append('📅 明日休市提醒：')
            upcoming = holidays.get('upcoming_holidays', [])
            for h in upcoming:
                date_str = h.get('date', '')
                weekday = h.get('weekday', '')
                markets = '、'.join(h.get('markets', []))
                lines.append(f'- {date_str}（週{weekday}）{markets} 休市')
            lines.append('')

    # Market summary
    summary_text = idx_analysis.get('summary', '')
    if summary_text:
        lines.append('【市場總覽】')
        lines.append(summary_text)
        lines.append('')

    # News
    if news:
        lines.append('【宏觀重點新聞】')
        for i, n in enumerate(news, 1):
            title = n['title'] if isinstance(n, dict) else str(n)
            lines.append(f'{i}. {title}')
        lines.append('')

    # Index performance
    lines.append('【指數表現亮點】')
    
    # Asia
    asia_items = []
    for name, d in asia.items():
        if isinstance(d, dict):
            pct = d.get('change_pct', d.get('change_percent', 0))
            if pct:
                asia_items.append(f'{name} {pct:+.2f}%')
    if asia_items:
        lines.append(f'- 亞洲：{"、".join(asia_items[:4])}')

    # Europe
    eu_items = []
    for name, d in europe.items():
        if isinstance(d, dict):
            pct = d.get('change_pct', d.get('change_percent', 0))
            if pct:
                eu_items.append(f'{name} {pct:+.2f}%')
    if eu_items:
        lines.append(f'- 歐洲：{"、".join(eu_items[:3])}')

    # US
    us_items = []
    for name, d in us.items():
        if isinstance(d, dict):
            pct = d.get('change_pct', d.get('change_percent', 0))
            if pct:
                us_items.append(f'{name} {pct:+.2f}%')
    if us_items:
        lines.append(f'- 美國：{"、".join(us_items[:3])}')
    lines.append('')

    # Crypto
    lines.append('【加密貨幣】')
    crypto_items = []
    for name, d in crypto.items():
        if isinstance(d, dict):
            pct = d.get('change_pct', d.get('change_percent', 0))
            if pct:
                crypto_items.append(f'{name} {pct:+.2f}%')
    if crypto_items:
        lines.append(f'- {"、".join(crypto_items[:5])}')
    lines.append('')

    # Calendar
    if cal:
        lines.append('【本週經濟日曆重點】')
        for c in cal:
            if isinstance(c, dict):
                lines.append(f'- {c.get("date","")} {c.get("event","")}')
        lines.append('')

    lines.append('完整報告請見附件 PDF。')
    lines.append('')
    lines.append('資料來源：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com')

    return '\n'.join(lines)

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'reports/raw_data_2026-03-19.json'
    print(build_email_body(path))
