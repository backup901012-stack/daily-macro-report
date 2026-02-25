#!/usr/bin/env python3
"""
熱門股票偵測模組
結合新聞提及頻率 + 成交量異常 + 漲跌幅異常來偵測市場熱點股票
"""
import sys
sys.path.append('/opt/.manus/.sandbox-runtime')

import json
from data_api import ApiClient
from datetime import datetime

client = ApiClient()


# 各市場的主要股票池（用於成交量異常偵測）
US_STOCK_POOL = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'AMD',
    'NFLX', 'CRM', 'ADBE', 'INTC', 'QCOM', 'MU', 'MRVL', 'AMAT', 'LRCX', 'KLAC',
    'JPM', 'V', 'MA', 'BAC', 'GS', 'MS', 'WFC', 'C', 'BLK', 'SCHW',
    'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY', 'BMY', 'AMGN',
    'XOM', 'CVX', 'COP', 'SLB', 'EOG',
    'KO', 'PEP', 'PG', 'WMT', 'COST', 'HD', 'MCD', 'DIS', 'NKE',
    'BA', 'CAT', 'GE', 'HON', 'UPS', 'RTX', 'LMT',
    'F', 'GM', 'RIVN', 'LCID',
    'COIN', 'MSTR', 'RIOT', 'MARA',
    'CLF', 'KR', 'MNDY',  # 當日特別活躍的
]

JP_STOCK_POOL = [
    '9984.T',   # SoftBank
    '6758.T',   # Sony
    '7203.T',   # Toyota
    '8306.T',   # Mitsubishi UFJ
    '6861.T',   # Keyence
    '9432.T',   # NTT
    '6501.T',   # Hitachi
    '8035.T',   # Tokyo Electron
    '6902.T',   # Denso
    '7741.T',   # HOYA
]

TW_STOCK_POOL = [
    '2330.TW',  # TSMC
    '2454.TW',  # MediaTek
    '2317.TW',  # Hon Hai
    '3034.TW',  # Novatek
    '2308.TW',  # Delta
    '2382.TW',  # Quanta
    '2303.TW',  # UMC
    '3711.TW',  # ASE
    '2881.TW',  # Fubon FHC
    '2891.TW',  # CTBC FHC
]

HK_STOCK_POOL = [
    '0700.HK',  # Tencent
    '9988.HK',  # Alibaba
    '9618.HK',  # JD.com
    '3690.HK',  # Meituan
    '1810.HK',  # Xiaomi
    '0941.HK',  # China Mobile
    '1398.HK',  # ICBC
    '2318.HK',  # Ping An
]


def detect_hot_stocks(stock_pool, market_name, top_n=5):
    """偵測熱門股票：基於漲跌幅絕對值和成交量"""
    results = []

    for symbol in stock_pool:
        try:
            response = client.call_api('YahooFinance/get_stock_chart', query={
                'symbol': symbol,
                'region': 'US',
                'interval': '1d',
                'range': '1mo'
            })

            if response and 'chart' in response and 'result' in response['chart']:
                result = response['chart']['result'][0]
                meta = result['meta']
                quotes = result['indicators']['quote'][0]
                timestamps = result.get('timestamp', [])

                if len(timestamps) < 5:
                    continue

                curr_close = quotes['close'][-1]
                prev_close = quotes['close'][-2]
                curr_volume = quotes['volume'][-1]

                if curr_close is None or prev_close is None or curr_volume is None:
                    continue

                change_pct = ((curr_close - prev_close) / prev_close * 100) if prev_close else 0

                # 計算過去20天的平均成交量
                valid_volumes = [v for v in quotes['volume'][:-1] if v is not None and v > 0]
                avg_volume = sum(valid_volumes) / len(valid_volumes) if valid_volumes else curr_volume
                volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1

                # 熱度分數 = |漲跌幅| * 成交量比率
                heat_score = abs(change_pct) * volume_ratio

                results.append({
                    'symbol': symbol,
                    'name': meta.get('longName', symbol),
                    'current': round(curr_close, 2),
                    'previous': round(prev_close, 2),
                    'change': round(curr_close - prev_close, 2),
                    'change_pct': round(change_pct, 2),
                    'volume': curr_volume,
                    'avg_volume': round(avg_volume),
                    'volume_ratio': round(volume_ratio, 2),
                    'heat_score': round(heat_score, 2),
                    'market': market_name,
                })

        except Exception as e:
            continue

    # 按熱度分數排序
    results.sort(key=lambda x: x['heat_score'], reverse=True)
    return results[:top_n]


def merge_with_news_tickers(hot_stocks, news_trending_tickers):
    """將新聞熱門 tickers 與成交量/漲跌幅熱門股票合併"""
    # 從新聞中提取的 tickers
    news_tickers = {t['ticker']: t for t in news_trending_tickers}

    # 為已有的熱門股票添加新聞提及信息
    for stock in hot_stocks:
        symbol_base = stock['symbol'].split('.')[0]
        if symbol_base in news_tickers:
            stock['news_mentions'] = news_tickers[symbol_base]['mention_count']
            stock['news_sentiment'] = news_tickers[symbol_base].get('sentiment', {})
        else:
            stock['news_mentions'] = 0
            stock['news_sentiment'] = {}

    return hot_stocks


def get_all_hot_stocks(news_trending_tickers=None):
    """獲取所有市場的熱門股票"""
    results = {
        '美股': detect_hot_stocks(US_STOCK_POOL, '美股', top_n=8),
        '日股': detect_hot_stocks(JP_STOCK_POOL, '日股', top_n=5),
        '台股': detect_hot_stocks(TW_STOCK_POOL, '台股', top_n=5),
        '港股': detect_hot_stocks(HK_STOCK_POOL, '港股', top_n=5),
    }

    if news_trending_tickers:
        for market, stocks in results.items():
            results[market] = merge_with_news_tickers(stocks, news_trending_tickers)

    return results


if __name__ == '__main__':
    # 測試美股熱門股票偵測
    print("偵測美股熱門股票...")
    us_hot = detect_hot_stocks(US_STOCK_POOL[:10], '美股', top_n=5)
    for s in us_hot:
        print(f"  {s['symbol']} ({s['name']}): {s['change_pct']:+.2f}% | Vol ratio: {s['volume_ratio']:.1f}x | Heat: {s['heat_score']:.1f}")
