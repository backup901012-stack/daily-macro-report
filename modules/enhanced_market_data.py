#!/usr/bin/env python3
"""
增強版市場數據模組
新增：陸港通資金流向代理、信用利差、技術面關鍵位、財報日曆、歷史情境
"""
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ==================== 1. 陸港通資金流向代理 ====================

NORTHBOUND_ETFS = {
    'FXI': {'name': '中國大型股', 'name_en': 'China Large-Cap'},
    'KWEB': {'name': '中國科技', 'name_en': 'China Internet'},
    'MCHI': {'name': '中國MSCI', 'name_en': 'MSCI China'},
}
SOUTHBOUND_ETFS = {
    'EWH': {'name': '香港', 'name_en': 'Hong Kong'},
    '2800.HK': {'name': '盈富基金', 'name_en': 'Tracker Fund HK'},
}


def _cmf_flow(df):
    """Calculate Chaikin Money Flow series"""
    h, l, c, v = df['High'], df['Low'], df['Close'], df['Volume']
    hl = h - l
    mfm = np.where(hl > 0, ((c - l) - (h - c)) / hl, 0)
    return pd.Series(mfm * v * c, index=df.index)


def get_northbound_southbound_flows():
    """獲取陸港通資金流向代理數據"""
    log("  獲取陸港通資金流向代理...")
    results = {'northbound': {}, 'southbound': {}}

    for direction, etf_dict in [('northbound', NORTHBOUND_ETFS), ('southbound', SOUTHBOUND_ETFS)]:
        for ticker, meta in etf_dict.items():
            try:
                df = yf.download(ticker, period='3mo', progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.dropna(subset=['Close'])
                if len(df) < 5:
                    continue
                mf = _cmf_flow(df)
                close = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[-2]) if len(df) > 1 else close
                chg = (close - prev) / prev * 100 if prev else 0
                results[direction][ticker] = {
                    'name': meta['name'],
                    'name_en': meta['name_en'],
                    'close': round(close, 2),
                    'change_pct': round(chg, 2),
                    '1d': float(mf.iloc[-1]) if len(mf) >= 1 else 0,
                    '5d': float(mf.iloc[-5:].sum()) if len(mf) >= 5 else 0,
                    '20d': float(mf.iloc[-20:].sum()) if len(mf) >= 20 else 0,
                }
            except Exception as e:
                log(f"    ✗ {ticker}: {e}")

    log(f"    ✓ 陸港通代理: 北向 {len(results['northbound'])} + 南向 {len(results['southbound'])}")
    return results


# ==================== 2. 信用利差 ====================

def get_credit_spreads():
    """獲取信用利差數據（IG/HY vs Treasury）"""
    log("  獲取信用利差...")
    try:
        tickers = ['LQD', 'HYG', 'IEF']
        data = yf.download(tickers, period='3mo', group_by='ticker', progress=False)

        result = {}
        for name, ticker in [('IG', 'LQD'), ('HY', 'HYG')]:
            try:
                etf = data[ticker].dropna(subset=['Close'])
                tsy = data['IEF'].dropna(subset=['Close'])
                # 合併日期
                merged = pd.DataFrame({
                    'etf': etf['Close'], 'tsy': tsy['Close']
                }).dropna()
                if len(merged) < 20:
                    continue
                # 用相對表現作為利差代理
                spread = (merged['tsy'] / merged['tsy'].iloc[0]) - (merged['etf'] / merged['etf'].iloc[0])
                result[name] = {
                    'current': round(float(spread.iloc[-1]) * 100, 2),
                    '1w_ago': round(float(spread.iloc[-5]) * 100, 2) if len(spread) >= 5 else None,
                    '1m_ago': round(float(spread.iloc[-20]) * 100, 2) if len(spread) >= 20 else None,
                    '1w_change': round(float(spread.iloc[-1] - spread.iloc[-5]) * 100, 3) if len(spread) >= 5 else 0,
                    '1m_change': round(float(spread.iloc[-1] - spread.iloc[-20]) * 100, 3) if len(spread) >= 20 else 0,
                    'direction': '擴大' if float(spread.iloc[-1]) > float(spread.iloc[-5]) else '收窄' if len(spread) >= 5 else '持平',
                }
            except Exception:
                pass

        log(f"    ✓ 信用利差: {list(result.keys())}")
        return result
    except Exception as e:
        log(f"    ✗ 信用利差: {e}")
        return {}


# ==================== 3. 技術面關鍵位 ====================

MAJOR_INDICES = {
    'S&P 500': '^GSPC',
    '納斯達克': '^IXIC',
    '道瓊斯': '^DJI',
    '香港恆生': '^HSI',
    '台灣加權': '^TWII',
    '日經225': '^N225',
    '德國DAX': '^GDAXI',
}


def _calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def get_technical_levels():
    """獲取主要指數的技術面關鍵位"""
    log("  計算技術面關鍵位...")
    results = {}

    for name, symbol in MAJOR_INDICES.items():
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna(subset=['Close'])
            if len(df) < 50:
                continue

            close = df['Close']
            current = float(close.iloc[-1])
            ma50 = float(close.rolling(50).mean().iloc[-1])
            ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
            rsi = float(_calc_rsi(close).iloc[-1])
            high_52w = float(close.max())
            low_52w = float(close.min())
            pct_from_high = round((current - high_52w) / high_52w * 100, 2)
            pct_from_low = round((current - low_52w) / low_52w * 100, 2)

            # Golden cross / Death cross
            cross = None
            if ma200 is not None:
                if ma50 > ma200:
                    cross = '黃金交叉'
                else:
                    cross = '死亡交叉'

            # 近20日支撐/阻力
            recent = close.iloc[-20:]
            support = float(recent.min())
            resistance = float(recent.max())

            results[name] = {
                'symbol': symbol,
                'current': round(current, 2),
                'ma50': round(ma50, 2),
                'ma200': round(ma200, 2) if ma200 else None,
                'rsi': round(rsi, 1),
                'high_52w': round(high_52w, 2),
                'low_52w': round(low_52w, 2),
                'pct_from_high': pct_from_high,
                'pct_from_low': pct_from_low,
                'cross': cross,
                'support_20d': round(support, 2),
                'resistance_20d': round(resistance, 2),
                'above_ma50': current > ma50,
                'above_ma200': current > ma200 if ma200 else None,
            }
        except Exception as e:
            log(f"    ✗ {name}: {e}")

    log(f"    ✓ 技術面: {len(results)} 指數")
    return results


# ==================== 4. 財報日曆 ====================

EARNINGS_WATCHLIST = {
    'AAPL': 'Apple', 'MSFT': 'Microsoft', 'GOOGL': 'Alphabet',
    'AMZN': 'Amazon', 'NVDA': 'NVIDIA', 'META': 'Meta',
    'TSLA': 'Tesla', 'TSM': 'TSMC', 'BABA': 'Alibaba',
    'NFLX': 'Netflix', 'JPM': 'JPMorgan', 'BAC': 'Bank of America',
    'XOM': 'ExxonMobil', 'CVX': 'Chevron', 'WMT': 'Walmart',
    'JNJ': 'Johnson & Johnson', 'V': 'Visa', 'MA': 'Mastercard',
    'DIS': 'Disney', 'NKE': 'Nike', 'INTC': 'Intel', 'AMD': 'AMD',
}


def get_upcoming_earnings(days_ahead=14):
    """獲取未來重要財報發布日期"""
    log("  檢查重要財報日曆...")
    results = []
    today = datetime.now().date()
    cutoff = today + timedelta(days=days_ahead)

    for symbol, name in EARNINGS_WATCHLIST.items():
        try:
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar
            if cal is not None and not cal.empty:
                # yfinance calendar format varies
                if 'Earnings Date' in cal.index:
                    dates = cal.loc['Earnings Date']
                    for d in dates:
                        if hasattr(d, 'date'):
                            d = d.date()
                        if isinstance(d, str):
                            d = datetime.strptime(d, '%Y-%m-%d').date()
                        if today <= d <= cutoff:
                            results.append({
                                'symbol': symbol,
                                'name': name,
                                'earnings_date': str(d),
                            })
                            break
        except Exception:
            pass

    results.sort(key=lambda x: x['earnings_date'])
    log(f"    ✓ 未來{days_ahead}天財報: {len(results)} 家")
    return results


# ==================== 5. 歷史情境比較 ====================

def get_historical_sentiment_context(fg_score, vix_value=None):
    """根據當前情緒指標提供歷史情境參考"""
    context = {}

    if fg_score is not None:
        if fg_score <= 10:
            context['fear_greed'] = (
                f"CNN 恐懼與貪婪指數 {fg_score:.0f} 處於極度恐懼區間（≤10），"
                f"歷史上類似水平出現在 2020年3月（COVID崩盤）、2022年9月（Fed激進升息）、2024年8月（日圓套利平倉）。"
                f"每次極度恐懼之後，市場在3-6個月內均出現顯著反彈，但短期內仍可能進一步下跌。"
            )
        elif fg_score <= 20:
            context['fear_greed'] = (
                f"CNN 恐懼與貪婪指數 {fg_score:.0f} 處於極度恐懼區間（10-20），"
                f"通常反映市場已大幅回調但恐慌尚未見頂。歷史上此水平往往伴隨高波動性，"
                f"聰明資金可能開始分批佈局，但建議等待 VIX 從高位回落作為確認信號。"
            )
        elif fg_score <= 40:
            context['fear_greed'] = (
                f"CNN 恐懼與貪婪指數 {fg_score:.0f} 處於恐懼區間（20-40），"
                f"市場情緒偏悲觀但尚未極端。歷史上此區間是逐步增加風險敞口的時機，"
                f"但需配合基本面判斷是否為結構性轉弱。"
            )
        elif fg_score <= 60:
            context['fear_greed'] = (
                f"CNN 恐懼與貪婪指數 {fg_score:.0f} 處於中性區間（40-60），"
                f"市場情緒平衡，無明確方向信號。"
            )
        elif fg_score <= 80:
            context['fear_greed'] = (
                f"CNN 恐懼與貪婪指數 {fg_score:.0f} 處於貪婪區間（60-80），"
                f"市場情緒偏樂觀，需警惕追高風險。"
            )
        else:
            context['fear_greed'] = (
                f"CNN 恐懼與貪婪指數 {fg_score:.0f} 處於極度貪婪區間（>80），"
                f"歷史上此水平是減倉信號，市場通常在數週內出現回調。"
            )

    if vix_value is not None:
        if vix_value >= 35:
            context['vix'] = f"VIX {vix_value:.1f} 處於恐慌水平（≥35），歷史上此水平通常意味著市場接近短期底部，但波動性可能持續數週。"
        elif vix_value >= 25:
            context['vix'] = f"VIX {vix_value:.1f} 處於高波動區間（25-35），反映市場不確定性顯著上升，期權避險成本高企。"
        elif vix_value >= 20:
            context['vix'] = f"VIX {vix_value:.1f} 處於偏高水平（20-25），市場存在一定壓力但尚未恐慌。"
        else:
            context['vix'] = f"VIX {vix_value:.1f} 處於正常水平（<20），市場波動性溫和。"

    return context


# ==================== 6. 殖利率曲線分析 ====================

def get_yield_curve_analysis():
    """分析殖利率曲線狀態"""
    log("  分析殖利率曲線...")
    try:
        tickers = {'^IRX': '3M', '^FVX': '5Y', '^TNX': '10Y', '^TYX': '30Y'}
        data = {}
        for symbol, label in tickers.items():
            t = yf.Ticker(symbol)
            hist = t.history(period='5d')
            if not hist.empty:
                data[label] = float(hist['Close'].iloc[-1])

        if '3M' in data and '10Y' in data:
            spread_3m10y = data['10Y'] - data['3M']
        else:
            spread_3m10y = None

        if '5Y' in data and '10Y' in data:
            spread_5y10y = data['10Y'] - data['5Y']
        else:
            spread_5y10y = None

        # 判斷曲線形態
        if spread_3m10y is not None:
            if spread_3m10y < -0.1:
                shape = '倒掛'
                interpretation = '殖利率曲線倒掛，歷史上是經濟衰退的可靠前瞻指標。短端利率高於長端，反映市場預期未來經濟走弱和央行被迫降息。'
            elif spread_3m10y < 0.2:
                shape = '平坦'
                interpretation = '殖利率曲線接近平坦，反映市場對經濟前景存在分歧。需密切關注是否進一步倒掛。'
            elif spread_3m10y < 1.0:
                shape = '正常偏平'
                interpretation = '殖利率曲線正常但偏平坦，長期利率溫和高於短期，反映市場對經濟增長持謹慎樂觀態度。'
            else:
                shape = '陡峭'
                interpretation = '殖利率曲線陡峭，長端利率明顯高於短端，通常出現在經濟復甦初期或通脹預期上升時期。'
        else:
            shape = '未知'
            interpretation = ''

        result = {
            'yields': data,
            'spread_3m10y': round(spread_3m10y, 3) if spread_3m10y else None,
            'spread_5y10y': round(spread_5y10y, 3) if spread_5y10y else None,
            'shape': shape,
            'interpretation': interpretation,
        }
        log(f"    ✓ 殖利率曲線: {shape} (3M-10Y spread: {spread_3m10y:.3f}%)" if spread_3m10y else "    ✓ 殖利率曲線: 部分數據")
        return result
    except Exception as e:
        log(f"    ✗ 殖利率曲線: {e}")
        return {}


# ==================== 主函數 ====================

def collect_all_enhanced_v2():
    """收集所有增強版 v2 數據"""
    log("開始收集增強版 v2 數據...")

    ns_flows = get_northbound_southbound_flows()
    credit = get_credit_spreads()
    tech = get_technical_levels()
    earnings = get_upcoming_earnings()
    yield_curve = get_yield_curve_analysis()

    return {
        'northbound_southbound': ns_flows,
        'credit_spreads': credit,
        'technical_levels': tech,
        'earnings_calendar': earnings,
        'yield_curve': yield_curve,
    }


if __name__ == '__main__':
    import json
    data = collect_all_enhanced_v2()
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
