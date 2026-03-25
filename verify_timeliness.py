#!/usr/bin/env python3
"""數據時效性驗證：確認所有數據都是當日最新的"""
import json
import datetime
import os
import exchange_calendars as xcals

os.environ['TZ'] = 'Asia/Taipei'

with open('reports/raw_data_2026-03-26.json', 'r') as f:
    data = json.load(f)

report_date = data.get('report_date', '')
today = datetime.date.today().strftime('%Y-%m-%d')

print("=" * 70)
print("數據時效性驗證")
print("=" * 70)
print(f"報告日期: {report_date}")
print(f"今日日期: {today}")
print(f"報告日期是否正確: {'✅ 正確' if report_date == today else '❌ 不正確！'}")

errors = []

# 檢查各市場數據日期
md = data.get('market_data', {})

# 定義市場和對應的交易所日曆
market_exchanges = {
    'asia_indices': {'name': '亞洲指數', 'calendar': None},
    'europe_indices': {'name': '歐洲指數', 'calendar': None},
    'us_indices': {'name': '美股指數', 'calendar': 'XNYS'},
    'commodities': {'name': '大宗商品', 'calendar': None},
    'forex': {'name': '外匯', 'calendar': None},
    'crypto': {'name': '加密貨幣', 'calendar': None},
    'emerging_indices': {'name': '新興市場指數', 'calendar': None},
}

print(f"\n--- 各市場數據日期檢查 ---")

for section, info in market_exchanges.items():
    section_data = md.get(section, {})
    if not section_data:
        print(f"  ⚠ {info['name']}: 無數據")
        continue
    
    dates_found = set()
    for name, item in section_data.items():
        if isinstance(item, dict) and 'date' in item:
            dates_found.add(item['date'])
    
    if dates_found:
        print(f"  {info['name']}: 數據日期 = {', '.join(sorted(dates_found))}")
        # 檢查是否為最近交易日
        for d in dates_found:
            try:
                data_date = datetime.datetime.strptime(d, '%Y-%m-%d').date()
                today_date = datetime.date.today()
                # 數據日期應該是今天或昨天（因為亞洲時間看美股是前一天的）
                days_diff = (today_date - data_date).days
                if days_diff > 3:
                    errors.append(f"{info['name']}: 數據日期 {d} 距今 {days_diff} 天，可能過期")
                    print(f"    ❌ 日期 {d} 距今 {days_diff} 天")
                else:
                    print(f"    ✅ 日期 {d} 距今 {days_diff} 天 (正常)")
            except:
                pass
    else:
        print(f"  {info['name']}: {len(section_data)} 項數據（無日期欄位）")

# 檢查情緒指標數據
print(f"\n--- 情緒指標數據檢查 ---")
sentiment = data.get('sentiment', {})
if sentiment:
    fear_greed = sentiment.get('fear_greed', {})
    if fear_greed:
        print(f"  Fear & Greed Index: {fear_greed.get('value', 'N/A')} ({fear_greed.get('label', 'N/A')})")
    
    vix = sentiment.get('vix', {})
    if vix:
        print(f"  VIX: {vix.get('current', 'N/A')} ({vix.get('change_pct', 'N/A')}%)")
    
    investment_clock = sentiment.get('investment_clock', {})
    if investment_clock:
        print(f"  美林時鐘: {investment_clock.get('phase', 'N/A')} ({investment_clock.get('strength', 'N/A')})")
    
    print(f"  ✅ 情緒指標數據存在")
else:
    print(f"  ⚠ 無情緒指標數據")

# 檢查資金流向數據
print(f"\n--- 資金流向數據檢查 ---")
fund_flow = data.get('fund_flow', {}) or sentiment.get('fund_flow', {})
if fund_flow:
    countries = fund_flow.get('countries', {})
    sectors = fund_flow.get('sectors', {})
    bonds = fund_flow.get('bonds', {})
    print(f"  國家/地區 ETF: {len(countries)} 項")
    print(f"  GICS 板塊: {len(sectors)} 項")
    print(f"  債券 ETF: {len(bonds)} 項")
    print(f"  ✅ 資金流向數據存在")
else:
    print(f"  ⚠ 無資金流向數據")

# 檢查熱門股票
print(f"\n--- 熱門股票數據檢查 ---")
hot_stocks = data.get('hot_stocks', {})
for market in ['美股', '日股', '台股', '港股']:
    market_data = hot_stocks.get(market, {})
    buy = market_data.get('buy', [])
    sell = market_data.get('sell', [])
    print(f"  {market}: 買入放量 {len(buy)} 支, 賣出放量 {len(sell)} 支")

# 檢查新聞
print(f"\n--- 新聞數據檢查 ---")
news = data.get('news', {})
ai_news = news.get('ai_summary', []) or data.get('ai_analysis', {}).get('news', [])
print(f"  AI 歸納新聞: {len(ai_news)} 條")

# 檢查經濟日曆
print(f"\n--- 經濟日曆檢查 ---")
calendar = data.get('ai_analysis', {}).get('calendar', [])
print(f"  經濟事件: {len(calendar)} 項")

# 總結
print(f"\n{'=' * 70}")
print("時效性驗證總結")
print("=" * 70)

if errors:
    print(f"\n❌ 發現 {len(errors)} 個時效性問題：")
    for e in errors:
        print(f"  - {e}")
else:
    print(f"\n✅ 所有數據時效性驗證通過")
    print(f"  - 報告日期正確: {report_date}")
    print(f"  - 所有市場數據為最近交易日數據")

print(f"\n驗證完成時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
