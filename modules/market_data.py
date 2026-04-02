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


# 交易所日曆映射（用於判斷休市）
_EXCHANGE_MAP = {
    # 亞洲
    '000001.SS': 'XSHG',   # 上證
    '399001.SZ': 'XSHG',   # 深證（用上證日曆，兩所同步）
    '^N225': 'XTKS', '^TOPX': 'XTKS',  # 東京
    '^HSI': 'XHKG',        # 香港
    '^TWII': 'XTAI',       # 台灣
    '^KS11': 'XKRX',       # 韓國
    '^AXJO': 'XASX',       # 澳洲
    # 歐洲
    '^GDAXI': 'XFRA', '^FTSE': 'XLON', '^FCHI': 'XPAR',
    '^STOXX50E': 'XAMS', '^SSMI': 'XSWX',
    # 美國
    '^GSPC': 'XNYS', '^IXIC': 'XNYS', '^DJI': 'XNYS',
    '^RUT': 'XNYS', '^SOX': 'XNYS',
}


def _is_market_closed_today(symbol):
    """用 exchange_calendars 判斷今天是否休市"""
    exchange_code = _EXCHANGE_MAP.get(symbol)
    if not exchange_code:
        return False  # 找不到映射，預設非休市
    try:
        import exchange_calendars as xcals
        cal = xcals.get_calendar(exchange_code)
        today = datetime.now().strftime('%Y-%m-%d')
        return not cal.is_session(today)
    except Exception:
        return False  # 判斷失敗，預設非休市


def _fetch_quote_yahoo_direct(symbol, name=None):
    """備用數據源：直接用 Yahoo Finance HTTP API（繞過 yfinance 套件）"""
    import requests as _req
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d'
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = _req.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        result = data.get('chart', {}).get('result', [])
        if not result:
            return None
        quotes = result[0].get('indicators', {}).get('quote', [{}])[0]
        closes = quotes.get('close', [])
        volumes = quotes.get('volume', [])
        highs = quotes.get('high', [])
        lows = quotes.get('low', [])
        timestamps = result[0].get('timestamp', [])

        # 過濾 None 值
        valid = [(c, v, h, l, t) for c, v, h, l, t in zip(closes, volumes, highs, lows, timestamps) if c is not None]
        if len(valid) < 2:
            return None

        curr_close, curr_vol, curr_high, curr_low, curr_ts = valid[-1]
        prev_close = valid[-2][0]

        import math
        if math.isnan(curr_close) or math.isnan(prev_close) or curr_close <= 0 or prev_close <= 0:
            return None

        change = curr_close - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

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
            'volume': int(curr_vol) if curr_vol else 0,
            'high': round(float(curr_high), 4) if curr_high else None,
            'low': round(float(curr_low), 4) if curr_low else None,
            'timestamp': int(curr_ts),
        }
    except Exception as e:
        print(f"  [WARN] yahoo_direct({symbol}) failed: {e}")
    return None


def fetch_quote(symbol, name=None):
    """獲取單個標的的最新行情數據（yfinance 主要 + Yahoo HTTP 備用）"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='5d')

        if hist.empty or len(hist) < 2:
            return None

        # 取最近兩個交易日
        curr = hist.iloc[-1]
        prev = hist.iloc[-2]

        import math
        curr_close = float(curr['Close'])
        prev_close = float(prev['Close'])

        if math.isnan(curr_close) or math.isnan(prev_close) or curr_close <= 0 or prev_close <= 0:
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


def fetch_batch(symbols_dict, max_retries=5):
    """批量獲取行情數據

    三層防護：
    1. yfinance 重試 5 次（間隔 5 秒）
    2. 全失敗 → Yahoo Finance HTTP API 備用
    3. 仍失敗 → 用 exchange_calendars 判斷：休市→標記休市，非休市→不顯示
    """
    import time
    results = {}
    for name, symbol in symbols_dict.items():
        data = None
        # 第一層：yfinance 重試
        for attempt in range(1, max_retries + 1):
            data = fetch_quote(symbol, name)
            if data:
                break
            if attempt < max_retries:
                print(f"  [RETRY] {name}({symbol}) attempt {attempt}/{max_retries}, waiting 5s...")
                time.sleep(5)

        # 第二層：Yahoo HTTP API 備用
        if not data:
            print(f"  [FALLBACK] {name}({symbol}) trying Yahoo HTTP API...")
            data = _fetch_quote_yahoo_direct(symbol, name)
            if data:
                print(f"  [FALLBACK] {name}({symbol}) ✅ Yahoo HTTP succeeded")

        # 第三層：判斷休市 vs 抓取失敗
        if data:
            results[name] = data
        else:
            if _is_market_closed_today(symbol):
                # 確認休市 → 標記休市
                results[name] = {'name': name, 'symbol': symbol, 'market_closed': True}
                print(f"  [CLOSED] {name}({symbol}) 今日休市")
            else:
                # 非休市但抓取失敗 → 不顯示（避免顯示錯誤數據）
                print(f"  [FAIL] {name}({symbol}) 抓取失敗且非休市，不顯示")
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
