#!/usr/bin/env python3
"""
市場數據收集模組
負責獲取全球股市指數、大宗商品、外匯、債券殖利率、加密貨幣數據
"""
import sys
sys.path.append('/opt/.manus/.sandbox-runtime')

import json
import os
from datetime import datetime, timedelta
from data_api import ApiClient

client = ApiClient()

# ==================== 全球股市指數定義 ====================

ASIA_INDICES = {
    '日經225': '^N225',
    '東證指數': '^TOPX',
    '台灣加權': '^TWII',
    '香港恆生': '^HSI',
    '上證綜指': '000001.SS',
    '深證成指': '399001.SZ',
    '韓國KOSPI': '^KS11',
    '澳洲ASX200': '^AXJO',
}

EUROPE_INDICES = {
    '德國DAX': '^GDAXI',
    '英國FTSE100': '^FTSE',
    '法國CAC40': '^FCHI',
    '歐洲STOXX50': '^STOXX50E',
    '瑞士SMI': '^SSMI',
}

US_INDICES = {
    'S&P 500': '^GSPC',
    '納斯達克': '^IXIC',
    '道瓊斯': '^DJI',
    '羅素2000': '^RUT',
    '費城半導體': '^SOX',
}

# ==================== 大宗商品定義 ====================

COMMODITIES = {
    '黃金': 'GC=F',
    '白銀': 'SI=F',
    '原油(WTI)': 'CL=F',
    '布蘭特原油': 'BZ=F',
    '銅': 'HG=F',
    '天然氣': 'NG=F',
}

# ==================== 外匯定義 ====================

FOREX = {
    '美元指數': 'DX-Y.NYB',
    'EUR/USD': 'EURUSD=X',
    'USD/JPY': 'JPY=X',
    'GBP/USD': 'GBPUSD=X',
    'USD/CNY': 'CNY=X',
    'USD/TWD': 'TWD=X',
}

# ==================== 債券殖利率定義 ====================

BONDS = {
    '美國2年期': '^IRX',
    '美國10年期': '^TNX',
    '美國30年期': '^TYX',
}

# ==================== 加密貨幣定義 ====================

CRYPTO = {
    'Bitcoin': 'BTC-USD',
    'Ethereum': 'ETH-USD',
    'BNB': 'BNB-USD',
    'Solana': 'SOL-USD',
    'XRP': 'XRP-USD',
    'Cardano': 'ADA-USD',
    'Dogecoin': 'DOGE-USD',
}


def fetch_quote(symbol, name=None):
    """獲取單個標的的最新行情數據"""
    try:
        response = client.call_api('YahooFinance/get_stock_chart', query={
            'symbol': symbol,
            'region': 'US',
            'interval': '1d',
            'range': '5d'
        })

        if response and 'chart' in response and 'result' in response['chart']:
            result = response['chart']['result'][0]
            meta = result['meta']
            timestamps = result.get('timestamp', [])
            quotes = result['indicators']['quote'][0]

            if len(timestamps) >= 2:
                # 找到最新的有效 close 和前一個有效 close
                curr_close = None
                prev_close = None
                closes = quotes['close']
                
                # 從後往前找最新的有效數據
                for i in range(len(closes) - 1, -1, -1):
                    if closes[i] is not None:
                        if curr_close is None:
                            curr_close = closes[i]
                        elif prev_close is None:
                            prev_close = closes[i]
                            break
                
                if curr_close is not None and prev_close is not None:
                    change = curr_close - prev_close
                    change_pct = (change / prev_close * 100) if prev_close else 0

                    return {
                        'name': name or meta.get('longName', symbol),
                        'symbol': symbol,
                        'current': round(curr_close, 4),
                        'previous': round(prev_close, 4),
                        'change': round(change, 4),
                        'change_pct': round(change_pct, 2),
                        'volume': quotes['volume'][-1] if quotes['volume'][-1] else 0,
                        'high': round(quotes['high'][-1], 4) if quotes['high'][-1] else None,
                        'low': round(quotes['low'][-1], 4) if quotes['low'][-1] else None,
                        'timestamp': timestamps[-1],
                    }
    except Exception as e:
        pass
    return None


def fetch_batch(symbols_dict):
    """批量獲取行情數據"""
    results = {}
    for name, symbol in symbols_dict.items():
        data = fetch_quote(symbol, name)
        if data:
            results[name] = data
    return results


def get_asia_indices():
    return fetch_batch(ASIA_INDICES)

def get_europe_indices():
    return fetch_batch(EUROPE_INDICES)

def get_us_indices():
    return fetch_batch(US_INDICES)

def get_commodities():
    return fetch_batch(COMMODITIES)

def get_forex():
    return fetch_batch(FOREX)

def get_bonds():
    return fetch_batch(BONDS)

def get_crypto():
    return fetch_batch(CRYPTO)


def get_all_market_data():
    """獲取所有市場數據"""
    return {
        'asia_indices': get_asia_indices(),
        'europe_indices': get_europe_indices(),
        'us_indices': get_us_indices(),
        'commodities': get_commodities(),
        'forex': get_forex(),
        'bonds': get_bonds(),
        'crypto': get_crypto(),
    }


if __name__ == '__main__':
    data = get_all_market_data()
    with open('/home/ubuntu/daily-macro-report/reports/market_data_test.json', 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("市場數據獲取完成")
    for category, items in data.items():
        print(f"\n{category}: {len(items)} items")
        for name, d in items.items():
            print(f"  {name}: {d['current']} ({d['change_pct']:+.2f}%)")
