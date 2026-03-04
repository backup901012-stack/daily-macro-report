#!/usr/bin/env python3
"""
數據品質驗證腳本 v3
讀取 raw_data JSON（嵌套字典結構），用 yfinance 即時數據交叉驗證關鍵數據點
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
print(f"讀取: {raw_data_path}")
print()

with open(raw_data_path, 'r') as f:
    raw_data = json.load(f)

market_data = raw_data.get('market_data', {})

# 建立 symbol -> item 的扁平映射（market_data 是嵌套字典：category -> name -> {data}）
symbol_map = {}
for category, items in market_data.items():
    if isinstance(items, dict):
        for item_name, item_data in items.items():
            if isinstance(item_data, dict):
                sym = item_data.get('symbol', '')
                if sym:
                    symbol_map[sym] = item_data

print(f"已載入 {len(symbol_map)} 個市場數據項目")
print()

# 定義要驗證的數據點
verify_targets = [
    {'name': 'S&P 500', 'symbol': '^GSPC'},
    {'name': 'NASDAQ Composite', 'symbol': '^IXIC'},
    {'name': 'Dow Jones', 'symbol': '^DJI'},
    {'name': 'Bitcoin', 'symbol': 'BTC-USD'},
    {'name': 'Gold (Futures)', 'symbol': 'GC=F'},
]

all_errors = []
all_results = []

print("--- 主要指數/商品/加密貨幣驗證 ---")
for target in verify_targets:
    name = target['name']
    symbol = target['symbol']
    
    raw_item = symbol_map.get(symbol)
    if not raw_item:
        print(f"  ⚠ {name} ({symbol}): 報告中未找到")
        continue
    
    report_price = raw_item.get('current')
    report_change = raw_item.get('change_pct')
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='5d')
        if len(hist) == 0:
            print(f"  ⚠ {name} ({symbol}): yfinance 無歷史數據")
            continue
        
        yf_price = float(hist['Close'].iloc[-1])
        yf_prev = float(hist['Close'].iloc[-2]) if len(hist) > 1 else None
        yf_change = ((yf_price - yf_prev) / yf_prev * 100) if yf_prev else None
        
        if report_price is not None:
            rp = float(report_price)
            deviation = abs(rp - yf_price) / yf_price * 100
            is_crypto = 'BTC' in symbol or 'ETH' in symbol
            threshold = 3.0 if is_crypto else 1.0
            status = "✓ PASS" if deviation < threshold else "✗ FAIL"
            
            change_info = ""
            if report_change is not None and yf_change is not None:
                change_dev = abs(float(report_change) - yf_change)
                change_info = f" | 漲跌幅: 報告={report_change}% vs yf={yf_change:.2f}% (差={change_dev:.2f}pp)"
            
            result = {
                'name': name,
                'symbol': symbol,
                'report_price': rp,
                'yf_price': round(yf_price, 2),
                'deviation_pct': round(deviation, 4),
                'status': status,
            }
            all_results.append(result)
            
            if status == "✗ FAIL":
                all_errors.append(f"{name}: 偏差 {deviation:.2f}% (報告: {rp:.2f}, yfinance: {yf_price:.2f})")
            
            print(f"  {status} {name} ({symbol}): 報告={rp:.2f}, yfinance={yf_price:.2f}, 偏差={deviation:.4f}%{change_info}")
        else:
            print(f"  ⚠ {name} ({symbol}): 報告中無價格數據")
    except Exception as e:
        print(f"  ✗ {name} ({symbol}): 驗證失敗 - {e}")

# 驗證熱門股票
print()
print("--- 熱門股票驗證 ---")
hot_stocks_data = raw_data.get('hot_stocks', {})
verified_hot = 0

for market_name in ['美股', '日股', '台股', '港股']:
    market_hs = hot_stocks_data.get(market_name, {})
    if not isinstance(market_hs, dict):
        continue
    for direction in ['inflow', 'outflow']:
        stock_list = market_hs.get(direction, [])
        if not isinstance(stock_list, list):
            continue
        for stock in stock_list[:1]:  # 每個方向取第一支
            if verified_hot >= 5:
                break
            ticker_str = stock.get('symbol', stock.get('ticker', ''))
            stock_name = stock.get('name', ticker_str)
            report_price = stock.get('current', stock.get('close', stock.get('price', None)))
            
            if not ticker_str or report_price is None:
                continue
            
            try:
                ticker = yf.Ticker(ticker_str)
                hist = ticker.history(period='5d')
                if len(hist) == 0:
                    print(f"  ⚠ {stock_name} ({ticker_str}): yfinance 無數據")
                    continue
                
                yf_price = float(hist['Close'].iloc[-1])
                rp = float(report_price)
                deviation = abs(rp - yf_price) / yf_price * 100
                status = "✓ PASS" if deviation < 1.0 else "✗ FAIL"
                
                result = {
                    'name': f"{stock_name} ({ticker_str})",
                    'report_price': rp,
                    'yf_price': round(yf_price, 2),
                    'deviation_pct': round(deviation, 4),
                    'status': status,
                }
                all_results.append(result)
                verified_hot += 1
                
                if status == "✗ FAIL":
                    all_errors.append(f"{stock_name} ({ticker_str}): 偏差 {deviation:.2f}%")
                
                print(f"  {status} [{market_name}] {stock_name} ({ticker_str}): 報告={rp:.2f}, yfinance={yf_price:.2f}, 偏差={deviation:.4f}%")
            except Exception as e:
                print(f"  ✗ {stock_name} ({ticker_str}): 驗證失敗 - {e}")

# 總結
print()
print("=" * 60)
print(f"驗證結果總結:")
print(f"  總驗證項目: {len(all_results)}")
passed = sum(1 for r in all_results if '✓' in r['status'])
failed = sum(1 for r in all_results if '✗' in r['status'])
print(f"  通過: {passed}")
print(f"  失敗: {failed}")

if all_errors:
    print()
    print("⚠ 發現以下數據偏差超過閾值:")
    for err in all_errors:
        print(f"  - {err}")
    print()
    print("建議：請排查原因後再發送報告")
    sys.exit(1)
else:
    print()
    print("✓ 所有關鍵數據點驗證通過")
    print("可以安全發送報告")
    sys.exit(0)
