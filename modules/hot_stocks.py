#!/usr/bin/env python3
"""
熱門股票偵測模組（v4 — yfinance 統一版）

數據來源：
  - 美股：yfinance 批量下載（yf.download，一次最多 90 支，分批）
  - 日股/台股/港股：yfinance 批量下載（同上）

候選池：
  - 美股：道瓊30 + S&P 500 + NASDAQ 100（~519 支）
  - 日股：日經 225（~226 支）
  - 台股：台灣 50 + 中型 100（~150 支）
  - 港股：恆生指數（~85 支）

分層漏斗篩選：
  第一層（硬門檻）：量比 ≥ 1.5x + 上漲 → 資金追捧
                     量比 ≥ 2.5x + 下跌 → 資金出清
  第二層（排序）：  按漲跌幅絕對值排序
  第三層（加分）：  有新聞提及的優先（tiebreaker）

顯示上限：每市場最多 10 支買入 + 10 支賣出

v4 變更：
  - 美股從 Polygon Grouped Daily Bars 改為 yfinance 批量下載
  - 解決 Polygon 免費方案無法取得當天數據的問題
  - 所有市場統一使用 yfinance，數據即時且穩定
"""
import json
import os
import time
import datetime
import io
from contextlib import redirect_stderr

# ==================== 量比門檻設定 ====================
MIN_VOLUME_RATIO_BUY = 1.5    # 買入放量：量比 ≥ 1.5x + 上漲
MIN_VOLUME_RATIO_SELL = 2.5   # 賣出放量：量比 ≥ 2.5x + 下跌

# ==================== 資金流向分類 ====================
FLOW_BUY = 'inflow'           # 資金追捧（買入放量上漲）
FLOW_SELL = 'outflow'         # 資金出清（賣出放量下跌）

# ==================== 顯示上限 ====================
MAX_PER_FLOW = 10             # 每市場每方向最多顯示 10 支

# ==================== yfinance 批量下載設定 ====================
YF_BATCH_SIZE = 90            # 每批下載股票數（yf.download 批量）
YF_BATCH_DELAY = 3            # 批次間休息秒數
YF_DOWNLOAD_PERIOD = '1mo'    # 下載期間（1 個月，用於計算平均成交量）

# ==================== 成分股快取路徑 ====================
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
COMPONENTS_FILE = os.path.join(DATA_DIR, 'index_components.json')


# ================================================================
#  通用函數
# ================================================================

def load_stock_pool(market_code):
    """從本地快取載入指定市場的成分股清單"""
    if not os.path.exists(COMPONENTS_FILE):
        print(f"  [警告] 成分股快取不存在: {COMPONENTS_FILE}")
        print(f"  請先執行 fetch_index_components.py 建立快取")
        return []

    with open(COMPONENTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    market = data.get('markets', {}).get(market_code, {})
    stocks = market.get('stocks', [])
    symbols = [s['symbol'] for s in stocks]
    print(f"  [{market.get('name', market_code)}] 載入 {len(symbols)} 支成分股（{market.get('indices', '')}）")
    return symbols


def _enrich_names(stocks, market_code):
    """從成分股快取補充公司名稱"""
    try:
        with open(COMPONENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        market = data.get('markets', {}).get(market_code, {})
        name_map = {s['symbol']: s.get('name', s['symbol']) for s in market.get('stocks', [])}
        for stock in stocks:
            if stock['symbol'] in name_map:
                stock['name'] = name_map[stock['symbol']]
    except Exception:
        pass


# ================================================================
#  yfinance 批量下載（所有市場統一使用）
# ================================================================

def yfinance_batch_scan(symbols, market_name, market_code='US'):
    """
    用 yfinance 批量下載掃描一個市場的所有成分股

    策略：
    1. 用 yf.download() 批量下載 1 個月日線數據
    2. 每批最多 YF_BATCH_SIZE 支，批次間休息
    3. 從下載的數據計算量比和漲跌幅
    4. 自動過濾無效 ticker

    Args:
        symbols: 成分股代碼列表
        market_name: 市場名稱（用於日誌）
        market_code: 市場代碼（用於補充名稱）

    Returns:
        list of stock dicts
    """
    import yfinance as yf

    results = []
    total_success = 0
    total_failed = 0
    start_time = time.time()
    total_batches = (len(symbols) + YF_BATCH_SIZE - 1) // YF_BATCH_SIZE

    print(f"  [{market_name}-yfinance] 開始批量下載 {len(symbols)} 支（{total_batches} 批 x {YF_BATCH_SIZE} 支）...")

    for batch_idx in range(0, len(symbols), YF_BATCH_SIZE):
        batch = symbols[batch_idx:batch_idx + YF_BATCH_SIZE]
        batch_num = batch_idx // YF_BATCH_SIZE + 1

        try:
            # 靜默下載，抑制 yfinance 的錯誤輸出
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                df = yf.download(
                    batch,
                    period=YF_DOWNLOAD_PERIOD,
                    interval='1d',
                    group_by='ticker',
                    progress=False,
                    threads=True
                )

            if df.empty:
                total_failed += len(batch)
                elapsed = time.time() - start_time
                print(f"    批次 {batch_num}/{total_batches}: 0 成功, {len(batch)} 失敗 ({elapsed:.0f}s)")
                continue

            batch_success = 0
            batch_failed = 0

            # 處理單支 vs 多支的不同 DataFrame 結構
            is_single = len(batch) == 1

            for symbol in batch:
                try:
                    if is_single:
                        stock_df = df
                    else:
                        if symbol not in df.columns.get_level_values(0).unique():
                            batch_failed += 1
                            continue
                        stock_df = df[symbol]

                    # 去除 NaN 行
                    stock_df = stock_df.dropna(subset=['Close', 'Volume'])

                    if len(stock_df) < 5:
                        batch_failed += 1
                        continue

                    curr_close = float(stock_df['Close'].iloc[-1])
                    prev_close = float(stock_df['Close'].iloc[-2])
                    curr_volume = float(stock_df['Volume'].iloc[-1])

                    if curr_close <= 0 or prev_close <= 0 or curr_volume <= 0:
                        batch_failed += 1
                        continue

                    change_pct = ((curr_close - prev_close) / prev_close) * 100

                    # 計算平均成交量（排除最近一天）
                    hist_volumes = stock_df['Volume'].iloc[:-1]
                    valid_volumes = hist_volumes[hist_volumes > 0]
                    avg_volume = float(valid_volumes.mean()) if len(valid_volumes) > 0 else curr_volume
                    volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1

                    results.append({
                        'symbol': symbol,
                        'name': symbol,
                        'current': round(curr_close, 2),
                        'previous': round(prev_close, 2),
                        'change': round(curr_close - prev_close, 2),
                        'change_pct': round(change_pct, 2),
                        'volume': int(curr_volume),
                        'avg_volume': round(avg_volume),
                        'volume_ratio': round(volume_ratio, 2),
                        'market': market_name,
                    })
                    batch_success += 1

                except Exception:
                    batch_failed += 1

            total_success += batch_success
            total_failed += batch_failed
            elapsed = time.time() - start_time
            print(f"    批次 {batch_num}/{total_batches}: {batch_success} 成功, {batch_failed} 失敗 ({elapsed:.0f}s)")

        except Exception as e:
            total_failed += len(batch)
            elapsed = time.time() - start_time
            print(f"    批次 {batch_num}/{total_batches}: 錯誤 - {e} ({elapsed:.0f}s)")

        # 批次間休息
        if batch_idx + YF_BATCH_SIZE < len(symbols):
            time.sleep(YF_BATCH_DELAY)

    elapsed = time.time() - start_time
    rate = total_success / len(symbols) * 100 if symbols else 0
    print(f"  [{market_name}-yfinance] 掃描完成: {total_success}/{len(symbols)} 成功 ({rate:.0f}%), 耗時 {elapsed:.1f}s")

    # 補充公司名稱
    _enrich_names(results, market_code)

    return results


# ================================================================
#  分層漏斗篩選
# ================================================================

def apply_funnel_filter(stocks, market_name):
    """
    分層漏斗篩選

    第一層（硬門檻）：
      - 買入放量：量比 ≥ 1.5x + 上漲 → inflow
      - 賣出放量：量比 ≥ 2.5x + 下跌 → outflow
      - 其餘淘汰

    第二層（排序）：
      - 按漲跌幅絕對值排序（大→小）

    Returns:
        (inflow_list, outflow_list) — 各最多 MAX_PER_FLOW 支
    """
    inflow = []
    outflow = []
    skipped = 0

    for stock in stocks:
        change_pct = stock['change_pct']
        volume_ratio = stock['volume_ratio']

        if change_pct > 0 and volume_ratio >= MIN_VOLUME_RATIO_BUY:
            stock['flow'] = FLOW_BUY
            inflow.append(stock)
        elif change_pct < 0 and volume_ratio >= MIN_VOLUME_RATIO_SELL:
            stock['flow'] = FLOW_SELL
            outflow.append(stock)
        else:
            skipped += 1

    # 第二層：按漲跌幅絕對值排序
    inflow.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    outflow.sort(key=lambda x: abs(x['change_pct']), reverse=True)

    # 動態門檻回退：如果任一方向篩選結果不足，使用寬鬆門檻補充
    if (len(inflow) < 3 or len(outflow) < 3) and len(stocks) > 50:
        RELAXED_VOL_BUY = 1.1
        RELAXED_VOL_SELL = 1.3
        RELAXED_CHG_BUY = 0.3
        RELAXED_CHG_SELL = -0.3
        existing_symbols = {s['symbol'] for s in inflow + outflow}
        for stock in stocks:
            if stock['symbol'] in existing_symbols:
                continue
            cp = stock['change_pct']
            vr = stock['volume_ratio']
            if len(inflow) < MAX_PER_FLOW and cp >= RELAXED_CHG_BUY and vr >= RELAXED_VOL_BUY:
                stock['flow'] = FLOW_BUY
                inflow.append(stock)
            elif len(outflow) < MAX_PER_FLOW and cp <= RELAXED_CHG_SELL and vr >= RELAXED_VOL_SELL:
                stock['flow'] = FLOW_SELL
                outflow.append(stock)
        inflow.sort(key=lambda x: abs(x['change_pct']), reverse=True)
        outflow.sort(key=lambda x: abs(x['change_pct']), reverse=True)
        added = len(inflow) + len(outflow) - len(existing_symbols)
        if added > 0:
            print(f"  [{market_name}] 寬鬆門檻補充 {added} 支 (vol≥{RELAXED_VOL_BUY}x/漲≥{RELAXED_CHG_BUY}%, vol≥{RELAXED_VOL_SELL}x/跌≤{RELAXED_CHG_SELL}%)")

    # ��三層回退：最活躍��股（量加權��量排序）
    if (len(inflow) < 3 or len(outflow) < 3) and len(stocks) > 50:
        existing_symbols2 = {s['symbol'] for s in inflow + outflow}
        candidates = [
            s for s in stocks
            if s['volume_ratio'] >= 1.0 and s['change_pct'] != 0 and s['symbol'] not in existing_symbols2
        ]
        # 按 abs(change_pct) * volume_ratio 排序
        candidates.sort(key=lambda x: abs(x['change_pct']) * x['volume_ratio'], reverse=True)
        for s in candidates:
            if s['change_pct'] > 0 and len(inflow) < 5:
                s['flow'] = FLOW_BUY
                inflow.append(s)
            elif s['change_pct'] < 0 and len(outflow) < 5:
                s['flow'] = FLOW_SELL
                outflow.append(s)
            if len(inflow) >= 5 and len(outflow) >= 5:
                break
        if inflow or outflow:
            print(f"  [{market_name}] 最活躍個股 fallback 啟用 (vol≥1.0x, 按量加權動量排序)")

    print(f"  [{market_name}] 篩選結果: 買入放量 {len(inflow)} 支, 賣出放量 {len(outflow)} 支, 淘汰 {skipped} 支")

    return inflow[:MAX_PER_FLOW], outflow[:MAX_PER_FLOW]


def apply_news_tiebreaker(stocks, news_trending_tickers):
    """
    第三層：新聞提及作為 tiebreaker
    同漲跌幅時，有新聞提及的排前面
    """
    if not news_trending_tickers:
        for s in stocks:
            s['news_mentions'] = 0
            s['news_sentiment'] = {}
        return stocks

    news_tickers = {t['ticker']: t for t in news_trending_tickers}

    for stock in stocks:
        symbol_base = stock['symbol'].split('.')[0]
        if symbol_base in news_tickers:
            stock['news_mentions'] = news_tickers[symbol_base]['mention_count']
            stock['news_sentiment'] = news_tickers[symbol_base].get('sentiment', {})
        else:
            stock['news_mentions'] = 0
            stock['news_sentiment'] = {}

    # 穩定排序：先按漲跌幅絕對值，再按新聞提及數
    stocks.sort(key=lambda x: (abs(x['change_pct']), x['news_mentions']), reverse=True)
    return stocks


# ================================================================
#  主入口
# ================================================================

MARKET_CONFIG = {
    'US': {'name': '美股', 'code': 'US'},
    'JP': {'name': '日股', 'code': 'JP'},
    'TW': {'name': '台股', 'code': 'TW'},
    'HK': {'name': '港股', 'code': 'HK'},
}


def detect_hot_stocks_v2(market_code, market_name, news_trending_tickers=None):
    """
    完整流程：載入成分股 → 掃描 → 分層篩選 → 新聞加分

    Returns:
        dict with 'inflow' and 'outflow' lists
    """
    symbols = load_stock_pool(market_code)
    if not symbols:
        return {'inflow': [], 'outflow': []}

    # 所有市場統一使用 yfinance 批量下載
    raw_data = yfinance_batch_scan(symbols, market_name, market_code)

    # 分層漏斗篩選
    inflow, outflow = apply_funnel_filter(raw_data, market_name)

    # 新聞 tiebreaker
    inflow = apply_news_tiebreaker(inflow, news_trending_tickers)
    outflow = apply_news_tiebreaker(outflow, news_trending_tickers)

    return {'inflow': inflow, 'outflow': outflow}


def get_all_hot_stocks(news_trending_tickers=None):
    """
    獲取所有市場的熱門股票

    Returns:
        dict: {
            '美股': {'inflow': [...], 'outflow': [...]},
            '日股': {'inflow': [...], 'outflow': [...]},
            '台股': {'inflow': [...], 'outflow': [...]},
            '港股': {'inflow': [...], 'outflow': [...]},
        }
    """
    markets = [
        ('US', '美股'),
        ('JP', '日股'),
        ('TW', '台股'),
        ('HK', '港股'),
    ]

    results = {}
    total_start = time.time()

    for market_code, market_name in markets:
        print(f"\n{'='*50}")
        print(f"掃描 {market_name}...")
        results[market_name] = detect_hot_stocks_v2(
            market_code, market_name, news_trending_tickers
        )

    total_elapsed = time.time() - total_start
    print(f"\n{'='*50}")
    print(f"全部掃描完成，總耗時: {total_elapsed:.1f}s")

    for market_name, data in results.items():
        in_count = len(data['inflow'])
        out_count = len(data['outflow'])
        print(f"  {market_name}: 買入放量 {in_count} 支, 賣出放量 {out_count} 支")

    return results


# ==================== 向後兼容函數 ====================
def split_by_flow(stocks):
    """將舊格式的股票列表按資金流向分成兩組"""
    inflow = [s for s in stocks if s.get('flow') == FLOW_BUY]
    outflow = [s for s in stocks if s.get('flow') == FLOW_SELL]
    return inflow, outflow


def merge_with_news_tickers(hot_stocks, news_trending_tickers):
    """向後兼容：合併新聞數據"""
    return apply_news_tiebreaker(hot_stocks, news_trending_tickers)


if __name__ == '__main__':
    print(f"買入放量門檻：{MIN_VOLUME_RATIO_BUY}x（量比 + 上漲）")
    print(f"賣出放量門檻：{MIN_VOLUME_RATIO_SELL}x（量比 + 下跌）")
    print(f"每市場上限：買入 {MAX_PER_FLOW} 支 + 賣出 {MAX_PER_FLOW} 支")
    print()

    # 測試美股
    print("=" * 50)
    print("測試美股（yfinance 批量下載）...")
    us_symbols = load_stock_pool('US')
    if us_symbols:
        us_data = yfinance_batch_scan(us_symbols[:20], '美股', 'US')
        print(f"測試結果: {len(us_data)} 支")
        for s in us_data[:5]:
            print(f"  {s['symbol']:8s} {s['change_pct']:+6.2f}% | Vol {s['volume_ratio']:.1f}x | Close {s['current']}")
