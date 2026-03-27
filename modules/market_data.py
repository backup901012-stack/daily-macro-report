#!/usr/bin/env python3
"""
市場數據收集模組
負責獲取全球股市指數、大宗商品、外匯、債券殖利率、加密貨幣數據
"""
import json
import os
from datetime import datetime, timedelta
import yfinance as yf

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

# ==================== 新興市場指數定義 ====================

EMERGING_INDICES = {
    '印度SENSEX': '^BSESN',
    '印度NIFTY50': '^NSEI',
    '印尼雅加達綜合': '^JKSE',
    '泰國SET': '^SET.BK',
    '馬來西亞KLCI': '^KLSE',
    '菲律賓PSEi': 'PSEI.PS',
}


# ==================== YTD 年初價格快取 ====================

_ytd_cache = {}

def _get_ytd_close(symbol):
    """獲取該標的年初第一個交易日的收盤價（帶快取）"""
    if symbol in _ytd_cache:
        return _ytd_cache[symbol]
    try:
        year = datetime.now().year
        # 從 1/1 開始搜尋，取第一個交易日的收盤價
        start = f"{year}-01-01"
        end = f"{year}-01-15"  # 留足夠空間找到第一個交易日
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start, end=end)
        if not hist.empty:
            ytd_close = hist.iloc[0]['Close']
            _ytd_cache[symbol] = ytd_close
            return ytd_close
    except Exception as e:
        pass
    _ytd_cache[symbol] = None
    return None


def fetch_quote(symbol, name=None):
    """獲取單個標的的最新行情數據（純 yfinance 版本）"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='5d')

        if hist.empty or len(hist) < 2:
            return None

        # 取最近兩個交易日
        curr = hist.iloc[-1]
        prev = hist.iloc[-2]

        curr_close = float(curr['Close'])
        prev_close = float(prev['Close'])

        if curr_close <= 0 or prev_close <= 0:
            return None

        change = curr_close - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        # 計算 YTD 漲跌幅
        ytd_close = _get_ytd_close(symbol)
        ytd_pct = None
        if ytd_close is not None and ytd_close != 0:
            ytd_pct = round((curr_close - ytd_close) / ytd_close * 100, 2)

        return {
            'name': name or symbol,
            'symbol': symbol,
            'current': round(curr_close, 4),
            'previous': round(prev_close, 4),
            'change': round(change, 4),
            'change_pct': round(change_pct, 2),
            'ytd_pct': ytd_pct,
            'volume': int(curr['Volume']) if curr['Volume'] else 0,
            'high': round(float(curr['High']), 4) if curr['High'] else None,
            'low': round(float(curr['Low']), 4) if curr['Low'] else None,
            'timestamp': int(hist.index[-1].timestamp()),
        }
    except Exception as e:
        print(f"  [WARN] fetch_quote({symbol}, {name}) exception: {e}")
    return None


def fetch_batch(symbols_dict, max_retries=3):
    """批量獲取行情數據，失敗時自動重試"""
    import time
    results = {}
    for name, symbol in symbols_dict.items():
        data = None
        for attempt in range(1, max_retries + 1):
            data = fetch_quote(symbol, name)
            if data:
                break
            if attempt < max_retries:
                print(f"  [RETRY] {name}({symbol}) attempt {attempt}/{max_retries} failed, retrying in 2s...")
                time.sleep(2)
            else:
                print(f"  [FAIL] {name}({symbol}) failed after {max_retries} attempts, skipping")
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

def get_emerging_indices():
    return fetch_batch(EMERGING_INDICES)


def get_all_market_data():
    """獲取所有市場數據"""
    return {
        'asia_indices': get_asia_indices(),
        'europe_indices': get_europe_indices(),
        'us_indices': get_us_indices(),
        'emerging_indices': get_emerging_indices(),
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
