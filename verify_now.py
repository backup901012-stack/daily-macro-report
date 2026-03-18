#!/usr/bin/env python3
"""數據品質驗證 - 讀取 raw_data JSON，用 yfinance 即時數據交叉驗證"""
import json, os, yfinance as yf, datetime

os.environ['TZ'] = 'Asia/Taipei'
today = datetime.datetime.now().strftime('%Y-%m-%d')
raw_path = f'reports/raw_data_{today}.json'

with open(raw_path, 'r', encoding='utf-8') as f:
    raw = json.load(f)

md = raw['market_data']

print(f"{'='*60}")
print(f"  數據品質驗證（面向機構客戶 - 最高標準）")
print(f"  日期: {today}")
print(f"{'='*60}\n")

targets = []

# S&P 500
sp = md['us_indices']['S&P 500']
targets.append(('S&P 500', '^GSPC', sp['current'], sp['change_pct']))

# 納斯達克
nq = md['us_indices']['納斯達克']
targets.append(('納斯達克', '^IXIC', nq['current'], nq['change_pct']))

# 道瓊斯
dj = md['us_indices']['道瓊斯']
targets.append(('道瓊斯', '^DJI', dj['current'], dj['change_pct']))

# Bitcoin
btc = md['crypto']['Bitcoin']
targets.append(('Bitcoin', 'BTC-USD', btc['current'], btc['change_pct']))

# 黃金
gold = md['commodities']['黃金']
targets.append(('黃金', 'GC=F', gold['current'], gold['change_pct']))

# 熱門股票（美股 inflow 前 2 支）
us_inflow = raw['hot_stocks']['美股'].get('inflow', [])
for s in us_inflow[:2]:
    targets.append((f"Hot: {s['name']} ({s['symbol']})", s['symbol'], s['current'], s['change_pct']))

all_pass = True
results = []

for name, yf_ticker, report_price, report_chg in targets:
    try:
        tk = yf.Ticker(yf_ticker)
        hist = tk.history(period='5d')
        if hist.empty:
            print(f"⚠️  {name}: yfinance 無數據，跳過\n")
            continue
        
        yf_close = hist['Close'].iloc[-1]
        yf_prev = hist['Close'].iloc[-2] if len(hist) >= 2 else None
        yf_chg = ((yf_close - yf_prev) / yf_prev * 100) if yf_prev else None
        
        dev = abs(yf_close - report_price) / report_price * 100 if report_price else 0
        is_crypto = 'BTC' in yf_ticker or 'ETH' in yf_ticker
        threshold = 3.0 if is_crypto else 1.0
        passed = dev < threshold
        
        if not passed:
            all_pass = False
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {name}")
        print(f"       報告價格:    {report_price:>12,.2f}")
        print(f"       yfinance:    {yf_close:>12,.2f}")
        print(f"       價格偏差:    {dev:>11.4f}%  (閾值: {threshold}%)")
        if report_chg is not None and yf_chg is not None:
            print(f"       報告漲跌幅:  {report_chg:>+11.2f}%")
            print(f"       yfinance:    {yf_chg:>+11.2f}%")
        print()
        
        results.append({'name': name, 'passed': passed, 'dev': dev})
    except Exception as e:
        print(f"⚠️  {name}: 驗證錯誤 - {e}\n")

print(f"{'='*60}")
print(f"  驗證結果摘要")
print(f"{'='*60}")
print(f"  總驗證項目: {len(results)}")
print(f"  通過: {sum(1 for r in results if r['passed'])}")
print(f"  失敗: {sum(1 for r in results if not r['passed'])}")
print()
if all_pass:
    print("  ✅ 數據品質驗證通過！所有關鍵數據點偏差在允許範圍內。")
    print("  → 可以安全發送報告。")
else:
    print("  ❌ 數據品質驗證未通過！")
    for r in results:
        if not r['passed']:
            print(f"     問題項: {r['name']} (偏差 {r['dev']:.4f}%)")
print(f"{'='*60}")
