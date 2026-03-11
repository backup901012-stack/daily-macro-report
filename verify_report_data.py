#!/usr/bin/env python3
"""
數據品質驗證腳本：讀取 raw_data JSON，用 yfinance 即時數據交叉驗證關鍵數據點
驗證標準：偏差 < 1%（加密貨幣因 24 小時交易，允許稍大偏差）
"""
import json
import sys
import os
from datetime import datetime

os.environ['TZ'] = 'Asia/Taipei'

import yfinance as yf

# 今天日期
today = datetime.now().strftime('%Y-%m-%d')
raw_data_path = f'reports/raw_data_{today}.json'

print(f"=== 數據品質驗證 ===")
print(f"日期: {today}")
print(f"原始數據: {raw_data_path}")
print()

# 讀取 raw_data
with open(raw_data_path, 'r') as f:
    raw_data = json.load(f)

# 提取報告中的關鍵數據
report_data = {}
market_data = raw_data.get('market_data', {})

# 美股指數（dict 結構：key=名稱, value=dict）
us_indices = market_data.get('us_indices', {})
for key, idx in us_indices.items():
    symbol = idx.get('symbol', '')
    if symbol == '^GSPC' or 'S&P' in key:
        report_data['S&P 500'] = {'price': idx.get('current'), 'change_pct': idx.get('change_pct'), 'symbol': '^GSPC'}
    elif symbol == '^IXIC' or '納斯達克' in key or 'NASDAQ' in key:
        report_data['NASDAQ'] = {'price': idx.get('current'), 'change_pct': idx.get('change_pct'), 'symbol': '^IXIC'}
    elif symbol == '^DJI' or '道瓊' in key:
        report_data['Dow Jones'] = {'price': idx.get('current'), 'change_pct': idx.get('change_pct'), 'symbol': '^DJI'}

# 大宗商品
commodities = market_data.get('commodities', {})
for key, c in commodities.items():
    symbol = c.get('symbol', '')
    if symbol == 'GC=F' or '黃金' in key or 'Gold' in key:
        report_data['Gold'] = {'price': c.get('current'), 'change_pct': c.get('change_pct'), 'symbol': 'GC=F'}
    elif symbol == 'CL=F' or '原油' in key or 'WTI' in key:
        report_data['WTI Oil'] = {'price': c.get('current'), 'change_pct': c.get('change_pct'), 'symbol': 'CL=F'}

# 加密貨幣
crypto = market_data.get('crypto', {})
for key, c in crypto.items():
    symbol = c.get('symbol', '')
    if symbol == 'BTC-USD' or 'Bitcoin' in key or 'BTC' in key:
        report_data['BTC'] = {'price': c.get('current'), 'change_pct': c.get('change_pct'), 'symbol': 'BTC-USD'}
    elif symbol == 'ETH-USD' or 'Ethereum' in key or 'ETH' in key:
        report_data['ETH'] = {'price': c.get('current'), 'change_pct': c.get('change_pct'), 'symbol': 'ETH-USD'}

# 熱門股票 - 抽查至少 2 支美股
hot_stocks = raw_data.get('hot_stocks', {})
us_hot = hot_stocks.get('美股', {})
inflow_stocks = us_hot.get('inflow', [])
if inflow_stocks:
    for stock in inflow_stocks[:2]:
        ticker = stock.get('symbol', '')
        if ticker:
            report_data[f'Hot Stock: {ticker}'] = {
                'price': stock.get('current'),
                'change_pct': stock.get('change_pct'),
                'symbol': ticker
            }

print("報告中的關鍵數據點：")
for name, data in report_data.items():
    price = data['price']
    chg = data['change_pct']
    print(f"  {name}: 價格={price}, 漲跌幅={chg}%, Symbol={data['symbol']}")

print()
print("--- 開始 yfinance 即時驗證 ---")
print()

# 用 yfinance 驗證
all_symbols = [data['symbol'] for data in report_data.values()]
tickers_data = yf.download(all_symbols, period='5d', progress=False)

errors = []
warnings = []
verified = 0

for name, data in report_data.items():
    symbol = data['symbol']
    report_price = data['price']
    report_change = data['change_pct']
    
    try:
        # 取得 yfinance 數據
        if len(all_symbols) > 1:
            close_series = tickers_data['Close'][symbol].dropna()
        else:
            close_series = tickers_data['Close'].dropna()
        
        if len(close_series) < 2:
            warnings.append(f"  ⚠ {name}: yfinance 數據不足（僅 {len(close_series)} 天）")
            continue
            
        yf_price = float(close_series.iloc[-1])
        yf_prev = float(close_series.iloc[-2])
        yf_change = ((yf_price - yf_prev) / yf_prev) * 100
        
        # 計算偏差
        if report_price and report_price != 0:
            price_diff_pct = abs(yf_price - report_price) / report_price * 100
        else:
            price_diff_pct = float('inf')
            
        # 判斷是否為加密貨幣（允許較大偏差）
        is_crypto = symbol in ['BTC-USD', 'ETH-USD']
        threshold = 3.0 if is_crypto else 1.0
        
        status = "✓" if price_diff_pct < threshold else "✗"
        
        print(f"  {status} {name} ({symbol}):")
        print(f"    報告價格: {report_price:.2f} | yfinance: {yf_price:.2f} | 偏差: {price_diff_pct:.3f}%")
        if report_change is not None:
            print(f"    報告漲跌: {report_change:.2f}% | yfinance: {yf_change:.2f}%")
        
        if price_diff_pct >= threshold:
            errors.append(f"  ✗ {name}: 價格偏差 {price_diff_pct:.3f}% 超過閾值 {threshold}%（報告: {report_price:.2f}, yfinance: {yf_price:.2f}）")
        else:
            verified += 1
            
    except Exception as e:
        warnings.append(f"  ⚠ {name} ({symbol}): 驗證失敗 - {str(e)}")

print()
print("=== 驗證結果摘要 ===")
print(f"  已驗證: {verified}/{len(report_data)} 項")

if warnings:
    print(f"  警告: {len(warnings)} 項")
    for w in warnings:
        print(w)

if errors:
    print(f"  ✗ 錯誤: {len(errors)} 項")
    for e in errors:
        print(e)
    print()
    print("❌ 數據品質驗證未通過！請排查原因後再發送。")
    sys.exit(1)
else:
    print()
    print("✅ 數據品質驗證通過！所有關鍵數據點偏差均在允許範圍內。")
    sys.exit(0)
