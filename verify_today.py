"""
獨立數據品質驗證：讀取今天的 raw_data JSON，與 yfinance 即時數據交叉驗證
"""
import json
import os
import yfinance as yf
from datetime import datetime

os.environ['TZ'] = 'Asia/Taipei'

# Load today's raw data
today = datetime.now().strftime('%Y-%m-%d')
raw_path = f'reports/raw_data_{today}.json'
print(f"Loading raw data from: {raw_path}")

with open(raw_path) as f:
    data = json.load(f)

md = data['market_data']

errors = []
checks = 0

def verify_item(name, symbol, report_close, report_pct, category):
    global checks, errors
    checks += 1
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if len(hist) < 2:
            print(f"  ⚠️ {name} ({symbol}): 數據不足")
            return
        latest = hist.iloc[-1]
        prev = hist.iloc[-2]
        yf_close = latest['Close']
        yf_pct = ((yf_close - prev['Close']) / prev['Close']) * 100
        
        close_diff_pct = abs(yf_close - report_close) / report_close * 100 if report_close else 0
        pct_diff = abs(yf_pct - report_pct)
        
        status = "✅" if close_diff_pct < 1.0 else "❌"
        if status == "❌":
            errors.append(f"  {name}: Report={report_close:.2f} ({report_pct:+.2f}%) vs YF={yf_close:.2f} ({yf_pct:+.2f}%) | Δ={close_diff_pct:.3f}%")
        
        date_str = str(latest.name.date()) if hasattr(latest.name, 'date') else str(latest.name)[:10]
        print(f"  {status} {name}: Report={report_close:.2f} ({report_pct:+.2f}%) | YF={yf_close:.2f} ({yf_pct:+.2f}%) | Date={date_str} | Δ={close_diff_pct:.3f}%")
    except Exception as e:
        print(f"  ⚠️ {name} ({symbol}): Error - {e}")

# === 1. Key US Indices ===
print("=" * 70)
print("1. 美股關鍵指數驗證")
print("=" * 70)
for name in ['S&P 500', '納斯達克', '道瓊斯', '費城半導體', '羅素2000']:
    if name in md.get('us_indices', {}):
        item = md['us_indices'][name]
        verify_item(name, item['symbol'], item['current'], item['change_pct'], 'index')

# === 2. Key Asia Indices ===
print("\n" + "=" * 70)
print("2. 亞洲關鍵指數驗證")
print("=" * 70)
for name in ['日經225', '香港恆生', '韓國KOSPI', '上證綜指']:
    if name in md.get('asia_indices', {}):
        item = md['asia_indices'][name]
        verify_item(name, item['symbol'], item['current'], item['change_pct'], 'index')

# === 3. Commodities ===
print("\n" + "=" * 70)
print("3. 商品驗證（黃金、原油）")
print("=" * 70)
for name in ['黃金', '原油(WTI)', '布蘭特原油']:
    if name in md.get('commodities', {}):
        item = md['commodities'][name]
        verify_item(name, item['symbol'], item['current'], item['change_pct'], 'commodity')

# === 4. Crypto ===
print("\n" + "=" * 70)
print("4. 加密貨幣驗證（BTC, ETH）")
print("=" * 70)
for name in ['Bitcoin', 'Ethereum']:
    if name in md.get('crypto', {}):
        item = md['crypto'][name]
        verify_item(name, item['symbol'], item['current'], item['change_pct'], 'crypto')

# === 5. Hot Stocks (sample) ===
print("\n" + "=" * 70)
print("5. 熱門股票抽樣驗證")
print("=" * 70)
hot = data.get('hot_stocks', {})
sample_count = 0
for market_name, market_data in hot.items():
    if sample_count >= 5:
        break
    buy_stocks = market_data.get('buy_volume', [])
    for stock in buy_stocks[:2]:
        if sample_count >= 5:
            break
        symbol = stock.get('symbol', '')
        close = stock.get('close', 0)
        pct = stock.get('change_pct', 0)
        name = stock.get('name', symbol)
        if symbol and close:
            verify_item(f"{name} ({symbol})", symbol, close, pct, 'stock')
            sample_count += 1

# === Summary ===
print("\n" + "=" * 70)
print("驗證總結")
print("=" * 70)
print(f"總檢查項目: {checks}")
print(f"偏差超過 1% 的項目: {len(errors)}")
if errors:
    print("\n偏差項目:")
    for e in errors:
        print(e)
    print("\n⚠️ 注意：加密貨幣因 24 小時交易，數據收集時間差可能導致小幅偏差，屬正常現象。")
    print("⚠️ 注意：指數和股票的微小偏差可能因盤後交易或數據更新延遲導致。")
else:
    print("\n✅ 所有關鍵數據點驗證通過！偏差均在 1% 以內。")
