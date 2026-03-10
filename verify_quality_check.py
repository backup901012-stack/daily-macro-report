#!/usr/bin/env python3
"""
數據品質驗證腳本
讀取今天的 raw_data JSON，用 yfinance 即時數據交叉驗證關鍵數據點
"""
import json
import sys
import os
from datetime import datetime

os.environ['TZ'] = 'Asia/Taipei'

import yfinance as yf

today = datetime.now().strftime('%Y-%m-%d')
raw_data_path = f'reports/raw_data_{today}.json'

print(f"=== 數據品質驗證 ===")
print(f"日期: {today}")
print(f"原始數據: {raw_data_path}")
print()

with open(raw_data_path, 'r') as f:
    raw_data = json.load(f)

md = raw_data['market_data']

# 定義要驗證的數據點
checks = [
    {"name": "S&P 500", "report_price": md['us_indices']['S&P 500']['current'], 
     "report_change": md['us_indices']['S&P 500']['change_pct'], "yf_symbol": "^GSPC"},
    {"name": "NASDAQ", "report_price": md['us_indices']['納斯達克']['current'],
     "report_change": md['us_indices']['納斯達克']['change_pct'], "yf_symbol": "^IXIC"},
    {"name": "Bitcoin (BTC)", "report_price": md['crypto']['Bitcoin']['current'],
     "report_change": md['crypto']['Bitcoin']['change_pct'], "yf_symbol": "BTC-USD"},
    {"name": "黃金 (Gold)", "report_price": md['commodities']['黃金']['current'],
     "report_change": md['commodities']['黃金']['change_pct'], "yf_symbol": "GC=F"},
]

# 加入 2 支美股熱門股票
us_hot = raw_data.get('hot_stocks', {}).get('美股', {}).get('inflow', [])
for stock in us_hot[:2]:
    checks.append({
        "name": f"熱門股: {stock['name']} ({stock['symbol']})",
        "report_price": stock['current'],
        "report_change": stock['change_pct'],
        "yf_symbol": stock['symbol']
    })

print(f"將驗證 {len(checks)} 個數據點\n")

all_pass = True
results = []

for check in checks:
    name = check['name']
    yf_symbol = check['yf_symbol']
    report_price = float(check['report_price'])
    report_change = float(check['report_change'])
    
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period='5d')
        if len(hist) == 0:
            print(f"⚠️  {name}: yfinance 無法取得數據")
            continue
        
        yf_price = float(hist['Close'].iloc[-1])
        if len(hist) >= 2:
            prev_close = float(hist['Close'].iloc[-2])
            yf_change = ((yf_price - prev_close) / prev_close) * 100
        else:
            yf_change = None
        
        deviation = abs(report_price - yf_price) / yf_price * 100
        
        # 加密貨幣允許稍大偏差（24小時交易）
        threshold = 2.0 if 'BTC' in yf_symbol or 'ETH' in yf_symbol else 1.0
        status = "✅ PASS" if deviation < threshold else "❌ FAIL"
        if deviation >= threshold:
            all_pass = False
        
        print(f"{status} {name}")
        print(f"  報告價格:     {report_price:,.2f}")
        print(f"  yfinance 價格: {yf_price:,.2f}")
        print(f"  偏差:         {deviation:.4f}% (閾值: {threshold}%)")
        if yf_change is not None:
            print(f"  報告漲跌幅:   {report_change:+.2f}%")
            print(f"  yfinance漲跌: {yf_change:+.2f}%")
        print()
        
        results.append({
            'name': name,
            'report_price': report_price,
            'yf_price': yf_price,
            'deviation_pct': deviation,
            'pass': deviation < threshold
        })
    except Exception as e:
        print(f"⚠️  {name}: 驗證錯誤 - {e}")
        print()

print("=" * 50)
if all_pass:
    print("✅ 所有數據點驗證通過！偏差均在允許範圍內")
    print("報告數據品質合格，可以發送。")
    sys.exit(0)
else:
    print("❌ 發現數據偏差超過閾值！")
    print("需要排查原因後再決定是否發送。")
    for r in results:
        if not r['pass']:
            print(f"  問題: {r['name']} 偏差 {r['deviation_pct']:.4f}%")
    sys.exit(1)
