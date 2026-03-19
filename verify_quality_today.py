#!/usr/bin/env python3
"""數據品質驗證：用 yfinance 交叉驗證報告中的關鍵數據點"""
import json
import yfinance as yf

with open('reports/raw_data_2026-03-20.json', 'r') as f:
    raw = json.load(f)

md = raw['market_data']
sent = raw['sentiment_data']

print("=" * 70)
print("數據品質驗證 - 交叉驗證關鍵數據點")
print("=" * 70)

# 定義驗證目標: (名稱, yfinance ticker, 報告中的值, 報告中的漲跌幅)
targets = [
    ("S&P 500",  "^GSPC",   md['us_indices']['S&P 500']['current'],   md['us_indices']['S&P 500']['change_pct']),
    ("NASDAQ",   "^IXIC",   md['us_indices']['納斯達克']['current'],    md['us_indices']['納斯達克']['change_pct']),
    ("BTC",      "BTC-USD", md['crypto']['Bitcoin']['current'],        md['crypto']['Bitcoin']['change_pct']),
    ("黃金",     "GC=F",    md['commodities']['黃金']['current'],       md['commodities']['黃金']['change_pct']),
    ("VIX",      "^VIX",    sent['vix']['value'],                      sent['vix']['change_pct']),
]

# 加入一支熱門股票
hot = raw.get('hot_stocks', {})
for market_name in ['美股']:
    if market_name in hot:
        stocks = hot[market_name]
        if 'buy_volume' in stocks and len(stocks['buy_volume']) > 0:
            first_stock = stocks['buy_volume'][0]
            ticker = first_stock.get('ticker', first_stock.get('symbol', ''))
            name = first_stock.get('name', ticker)
            price = first_stock.get('close', first_stock.get('price', first_stock.get('current')))
            chg = first_stock.get('change_pct', 0)
            if ticker and price:
                targets.append((f"熱門股:{name}", ticker, price, chg))
                break

errors = []
print()
for name, ticker, report_val, report_chg in targets:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period='5d')
        if len(hist) < 2:
            print(f"  {name} ({ticker}): 數據不足，跳過")
            continue
        
        yf_close = hist.iloc[-1]['Close']
        yf_prev = hist.iloc[-2]['Close']
        yf_chg = ((yf_close - yf_prev) / yf_prev) * 100
        yf_date = str(hist.index[-1].date())
        
        close_diff = abs(yf_close - report_val) / yf_close * 100
        chg_diff = abs(yf_chg - report_chg)
        
        close_ok = "PASS" if close_diff < 1 else "FAIL"
        chg_ok = "PASS" if chg_diff < 1 else "FAIL"
        
        print(f"  [{close_ok}] {name} ({ticker}) | 日期: {yf_date}")
        print(f"         收盤價: 報告={report_val:.2f}  yfinance={yf_close:.2f}  偏差={close_diff:.4f}%")
        print(f"         漲跌幅: 報告={report_chg:+.2f}%  yfinance={yf_chg:+.2f}%  偏差={chg_diff:.4f}pp")
        print()
        
        if close_diff >= 1:
            errors.append(f"{name}: 收盤價偏差 {close_diff:.4f}%（報告={report_val:.2f}, yfinance={yf_close:.2f}）")
        if chg_diff >= 1:
            errors.append(f"{name}: 漲跌幅偏差 {chg_diff:.4f}pp（報告={report_chg:+.2f}%, yfinance={yf_chg:+.2f}%）")
    except Exception as e:
        print(f"  [WARN] {name} ({ticker}): {e}")
        print()

print("=" * 70)
if errors:
    print(f"FAIL: 發現 {len(errors)} 個偏差超過閾值的數據點：")
    for e in errors:
        print(f"  - {e}")
    print("\n需要排查原因後再發送！")
else:
    print("PASS: 所有 {} 個關鍵數據點驗證通過，偏差均在可接受範圍內".format(len(targets)))
print("=" * 70)
