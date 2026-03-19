#!/usr/bin/env python3
"""
市場情緒與資金流向數據收集模組
負責獲取：
1. CNN Fear & Greed Index
2. VIX (CBOE Volatility Index)
3. US 10Y Treasury Yield / DXY
4. 美林時鐘 (Investment Clock) 週期判斷
5. 全球資金流向 (CMF-based ETF money flow)
6. GICS 板塊資金流向
7. 債券市場資金流向
8. 新興市場指數
"""
import json
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


# ==================== ETF 定義 ====================

COUNTRY_ETFS = {
    'SPY': {'name': '美國', 'name_en': 'USA'},
    'VGK': {'name': '歐洲', 'name_en': 'Europe'},
    'EWJ': {'name': '日本', 'name_en': 'Japan'},
    'FXI': {'name': '中國/港股', 'name_en': 'China/HK'},
    'EWT': {'name': '台灣', 'name_en': 'Taiwan'},
    'EWY': {'name': '韓國', 'name_en': 'South Korea'},
    'INDA': {'name': '印度', 'name_en': 'India'},
    'VWO': {'name': '新興市場', 'name_en': 'Emerging Mkts'},
}

SECTOR_ETFS = {
    'XLK': {'name': '資訊科技', 'name_en': 'Info Tech'},
    'XLF': {'name': '金融', 'name_en': 'Financials'},
    'XLV': {'name': '醫療保健', 'name_en': 'Healthcare'},
    'XLY': {'name': '非必需消費', 'name_en': 'Cons. Disc.'},
    'XLP': {'name': '必需消費', 'name_en': 'Cons. Staples'},
    'XLI': {'name': '工業', 'name_en': 'Industrials'},
    'XLE': {'name': '能源', 'name_en': 'Energy'},
    'XLB': {'name': '原材料', 'name_en': 'Materials'},
    'XLU': {'name': '公用事業', 'name_en': 'Utilities'},
    'XLRE': {'name': '房地產', 'name_en': 'Real Estate'},
    'XLC': {'name': '通訊服務', 'name_en': 'Comm. Svcs'},
}

BOND_ETFS = {
    'SHY': {'name': '1-3年國債', 'name_en': '1-3Y Treasury'},
    'IEI': {'name': '3-7年國債', 'name_en': '3-7Y Treasury'},
    'IEF': {'name': '7-10年國債', 'name_en': '7-10Y Treasury'},
    'TLH': {'name': '10-20年國債', 'name_en': '10-20Y Treasury'},
    'TLT': {'name': '20年+國債', 'name_en': '20Y+ Treasury'},
    'LQD': {'name': '投資級債', 'name_en': 'Inv. Grade'},
    'HYG': {'name': '非投資等債', 'name_en': 'High Yield'},
    'EMB': {'name': '新興債', 'name_en': 'EM Bond'},
    'VWOB': {'name': '新興美元債', 'name_en': 'EM USD Bond'},
    'EMLC': {'name': '新興本地債', 'name_en': 'EM Local Bond'},
}

# 新興市場指數
EMERGING_INDICES = {
    '印度SENSEX': '^BSESN',
    '印度NIFTY50': '^NSEI',
    '印尼雅加達綜合': '^JKSE',
    '泰國SET': '^SET.BK',
    '馬來西亞KLCI': '^KLSE',
    '菲律賓PSEi': 'PSEI.PS',
}

# 補充 ETF（用於資金流向但不在主要國家 ETF 中）
EXTRA_ETFS = {
    'EIDO': {'name': '印尼', 'name_en': 'Indonesia'},
    'VNM': {'name': '越南', 'name_en': 'Vietnam'},
    'THD': {'name': '泰國', 'name_en': 'Thailand'},
    'EWM': {'name': '馬來西亞', 'name_en': 'Malaysia'},
    'EPHE': {'name': '菲律賓', 'name_en': 'Philippines'},
    'EWA': {'name': '澳洲', 'name_en': 'Australia'},
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ==================== 1. 市場情緒指標 ====================

def get_sentiment_data():
    """獲取市場情緒指標：CNN Fear & Greed、VIX、US10Y、DXY"""
    results = {}

    # 1. CNN Fear & Greed Index
    log("  獲取 CNN Fear & Greed Index...")
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            fg = data.get('fear_and_greed', {})
            results['fear_greed'] = {
                'score': fg.get('score', None),
                'rating': fg.get('rating', None),
                'previous_close': fg.get('previous_close', None),
                'previous_1_week': fg.get('previous_1_week', None),
                'previous_1_month': fg.get('previous_1_month', None),
                'previous_1_year': fg.get('previous_1_year', None),
            }
            log(f"    ✓ Fear & Greed: {fg.get('score', 'N/A'):.1f} ({fg.get('rating', 'N/A')})")
        else:
            results['fear_greed'] = {'error': f'HTTP {resp.status_code}'}
            log(f"    ✗ Fear & Greed: HTTP {resp.status_code}")
    except Exception as e:
        results['fear_greed'] = {'error': str(e)}
        log(f"    ✗ Fear & Greed: {e}")

    # 2. VIX
    log("  獲取 VIX...")
    try:
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="1mo")
        if not vix_hist.empty:
            latest_vix = vix_hist.iloc[-1]
            prev_vix = vix_hist.iloc[-2] if len(vix_hist) > 1 else None
            results['vix'] = {
                'value': float(latest_vix['Close']),
                'change': float(latest_vix['Close'] - prev_vix['Close']) if prev_vix is not None else 0,
                'change_pct': float((latest_vix['Close'] - prev_vix['Close']) / prev_vix['Close'] * 100) if prev_vix is not None else 0,
                'high_1m': float(vix_hist['High'].max()),
                'low_1m': float(vix_hist['Low'].min()),
            }
            log(f"    ✓ VIX: {results['vix']['value']:.2f} ({results['vix']['change_pct']:+.2f}%)")
    except Exception as e:
        results['vix'] = {'error': str(e)}
        log(f"    ✗ VIX: {e}")

    # 3. US 10Y Treasury Yield
    log("  獲取 US 10Y Yield...")
    try:
        tnx = yf.Ticker("^TNX")
        tnx_hist = tnx.history(period="1mo")
        if not tnx_hist.empty:
            latest_tnx = tnx_hist.iloc[-1]
            results['us10y'] = {
                'yield': float(latest_tnx['Close']),
                'change': float(latest_tnx['Close'] - tnx_hist.iloc[-2]['Close']) if len(tnx_hist) > 1 else 0,
            }
            log(f"    ✓ US 10Y: {results['us10y']['yield']:.3f}%")
    except Exception as e:
        results['us10y'] = {'error': str(e)}
        log(f"    ✗ US 10Y: {e}")

    # 4. US Dollar Index (DXY)
    log("  獲取 DXY...")
    try:
        dxy = yf.Ticker("DX-Y.NYB")
        dxy_hist = dxy.history(period="5d")
        if not dxy_hist.empty:
            latest_dxy = dxy_hist.iloc[-1]
            results['dxy'] = {
                'value': float(latest_dxy['Close']),
            }
            log(f"    ✓ DXY: {results['dxy']['value']:.2f}")
    except Exception as e:
        results['dxy'] = {'error': str(e)}
        log(f"    ✗ DXY: {e}")

    return results


# ==================== 2. 美林時鐘 ====================

def _calc_slope(series, window=10):
    """Calculate the linear regression slope over the last N days"""
    if len(series) < window:
        return 0
    recent = series.tail(window).values
    x = np.arange(window)
    if np.any(np.isnan(recent)):
        return 0
    slope = np.polyfit(x, recent, 1)[0]
    return slope


def get_investment_clock():
    """計算美林時鐘週期判斷"""
    log("  計算美林時鐘...")
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        tnx = yf.download("^TNX", start=start_date, end=end_date, progress=False)
        fvx = yf.download("^FVX", start=start_date, end=end_date, progress=False)
        tip = yf.download("TIP", start=start_date, end=end_date, progress=False)
        ief = yf.download("IEF", start=start_date, end=end_date, progress=False)
        shy = yf.download("SHY", start=start_date, end=end_date, progress=False)
        oil = yf.download("CL=F", start=start_date, end=end_date, progress=False)

        def get_close(df):
            if isinstance(df.columns, pd.MultiIndex):
                return df['Close'].iloc[:, 0] if df['Close'].shape[1] > 0 else df['Close']
            return df['Close']

        df = pd.DataFrame({
            'tnx_10y': get_close(tnx),
            'fvx_5y': get_close(fvx),
            'tip': get_close(tip),
            'ief': get_close(ief),
            'shy': get_close(shy),
            'oil': get_close(oil),
        }).dropna()

        # Breakeven inflation proxy: TIP/IEF ratio
        df['breakeven_proxy'] = df['tip'] / df['ief']
        # Yield curve slope: 10Y - 5Y
        df['yield_slope'] = df['tnx_10y'] - df['fvx_5y']

        # 20-day Moving Averages
        df['slope_ma20'] = df['yield_slope'].rolling(20).mean()
        df['breakeven_ma20'] = df['breakeven_proxy'].rolling(20).mean()

        # Direction signals
        growth_slope = _calc_slope(df['slope_ma20'], 10)
        inflation_slope = _calc_slope(df['breakeven_ma20'], 10)

        latest = df.iloc[-1]

        # Determine quadrant
        growth_up = growth_slope > 0
        inflation_up = inflation_slope > 0

        if growth_up and not inflation_up:
            phase, phase_cn, best_asset, phase_num = "Recovery", "復甦期", "股票", 2
        elif growth_up and inflation_up:
            phase, phase_cn, best_asset, phase_num = "Overheat", "過熱期", "商品", 3
        elif not growth_up and inflation_up:
            phase, phase_cn, best_asset, phase_num = "Stagflation", "滯脹期", "現金", 4
        else:
            phase, phase_cn, best_asset, phase_num = "Reflation", "衰退期", "債券", 1

        # Signal strength
        avg_strength = (abs(growth_slope) + abs(inflation_slope)) / 2
        strength_pct = min(100, avg_strength * 10000)
        if strength_pct > 60:
            confidence = "強"
        elif strength_pct > 30:
            confidence = "中"
        else:
            confidence = "弱"

        result = {
            "phase": phase,
            "phase_cn": phase_cn,
            "phase_num": phase_num,
            "best_asset": best_asset,
            "confidence": confidence,
            "confidence_pct": round(strength_pct, 1),
            "growth_direction": "up" if growth_up else "down",
            "inflation_direction": "up" if inflation_up else "down",
            "growth_slope": round(growth_slope, 8),
            "inflation_slope": round(inflation_slope, 8),
            "yield_10y": round(float(latest['tnx_10y']), 3),
            "yield_5y": round(float(latest['fvx_5y']), 3),
            "yield_slope": round(float(latest['yield_slope']), 3),
            "breakeven_proxy": round(float(latest['breakeven_proxy']), 4),
            "oil_price": round(float(latest['oil']), 2),
            "date": str(df.index[-1].date()),
            "description": "基於10Y-5Y殖利率曲線斜率趨勢（增長代理）和TIP/IEF比率趨勢（通脹預期代理）的20日移動平均方向判斷。",
            "growth_indicator": "10Y-5Y殖利率利差 20日MA斜率",
            "inflation_indicator": "TIP/IEF比率 20日MA斜率（隱含通脹預期）",
        }
        log(f"    ✓ 美林時鐘: {phase_cn} ({confidence})")
        return result

    except Exception as e:
        log(f"    ✗ 美林時鐘: {e}")
        return {"phase": "Unknown", "phase_cn": "未知", "phase_num": 0, "error": str(e)}


# ==================== 3. 資金流向 ====================

def _calculate_money_flow(df):
    """Calculate daily money flow using Chaikin Money Flow (CMF) logic."""
    high = df['High']
    low = df['Low']
    close = df['Close']
    volume = df['Volume']

    hl_range = high - low
    mfm = np.where(hl_range > 0, ((close - low) - (high - close)) / hl_range, 0)
    money_flow = mfm * volume * close

    return pd.Series(money_flow, index=df.index, name='MoneyFlow')


def _calculate_period_flows(all_data, etf_dict, periods):
    """Calculate money flow for different time periods."""
    results = {}
    for ticker, meta in etf_dict.items():
        if ticker not in all_data:
            continue
        df = all_data[ticker]
        mf = _calculate_money_flow(df)

        ticker_results = {'name': meta['name'], 'name_en': meta['name_en']}
        for period_name, n_days in periods.items():
            if n_days == 'ytd':
                ytd_start = datetime(datetime.now().year, 1, 1)
                period_mf = mf[mf.index >= pd.Timestamp(ytd_start, tz=mf.index.tz if mf.index.tz else None)]
                ticker_results[period_name] = float(period_mf.sum())
            elif n_days <= len(mf):
                ticker_results[period_name] = float(mf.iloc[-n_days:].sum())
            else:
                ticker_results[period_name] = float(mf.sum())

        latest = df.iloc[-1]
        ticker_results['close'] = float(latest['Close'])
        ticker_results['volume'] = float(latest['Volume'])
        ticker_results['change_pct'] = float(
            (latest['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close'] * 100
        ) if len(df) > 1 else 0

        results[ticker] = ticker_results
    return results


def get_fund_flows():
    """獲取全球資金流向數據（國家、板塊、債券）"""
    log("  獲取資金流向數據...")
    try:
        all_etfs = {}
        all_etfs.update(COUNTRY_ETFS)
        all_etfs.update(SECTOR_ETFS)
        all_etfs.update(BOND_ETFS)
        all_etfs.update(EXTRA_ETFS)

        ticker_list = list(all_etfs.keys())
        log(f"    下載 {len(ticker_list)} 個 ETF 數據...")
        data = yf.download(ticker_list, period='3mo', group_by='ticker', progress=False)

        all_data = {}
        for ticker in ticker_list:
            try:
                if len(ticker_list) == 1:
                    df = data.copy()
                else:
                    df = data[ticker].copy()
                df = df.dropna(subset=['Close'])
                all_data[ticker] = df
            except Exception:
                pass

        periods = {'1d': 1, '5d': 5, '1m': 21, 'ytd': 'ytd'}

        country_flows = _calculate_period_flows(all_data, COUNTRY_ETFS, periods)
        sector_flows = _calculate_period_flows(all_data, SECTOR_ETFS, periods)
        bond_flows = _calculate_period_flows(all_data, BOND_ETFS, periods)
        extra_flows = _calculate_period_flows(all_data, EXTRA_ETFS, periods)

        result = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'country': country_flows,
            'sector': sector_flows,
            'bond': bond_flows,
            'extra': extra_flows,
        }
        log(f"    ✓ 資金流向: {len(country_flows)} 國家, {len(sector_flows)} 板塊, {len(bond_flows)} 債券")
        return result

    except Exception as e:
        log(f"    ✗ 資金流向: {e}")
        return {'date': datetime.now().strftime('%Y-%m-%d'), 'country': {}, 'sector': {}, 'bond': {}, 'extra': {}}


# ==================== 4. 新興市場指數 ====================

def get_emerging_indices():
    """獲取新興市場指數數據"""
    log("  獲取新興市場指數...")
    results = []
    for name, symbol in EMERGING_INDICES.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if len(hist) >= 2:
                close = hist["Close"].iloc[-1]
                prev_close = hist["Close"].iloc[-2]
                change = close - prev_close
                change_pct = (change / prev_close) * 100
                results.append({
                    "name": name,
                    "symbol": symbol,
                    "price": round(float(close), 2),
                    "change": round(float(change), 2),
                    "changesPercentage": round(float(change_pct), 2),
                })
            elif len(hist) == 1:
                close = hist["Close"].iloc[-1]
                results.append({
                    "name": name,
                    "symbol": symbol,
                    "price": round(float(close), 2),
                    "change": 0,
                    "changesPercentage": 0,
                })
        except Exception as e:
            log(f"    ✗ {name}: {e}")

    log(f"    ✓ 新興市場指數: {len(results)} 項")
    return results


# ==================== 主函數 ====================

def collect_all_enhanced_data():
    """收集所有增強版數據"""
    log("開始收集增強版市場數據...")

    sentiment = get_sentiment_data()
    clock = get_investment_clock()
    fund_flows = get_fund_flows()
    emerging = get_emerging_indices()

    return {
        'sentiment': sentiment,
        'clock': clock,
        'fund_flows': fund_flows,
        'emerging_indices': emerging,
    }


if __name__ == '__main__':
    data = collect_all_enhanced_data()
    with open('/home/ubuntu/enhanced_data_test.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print("增強版數據收集完成")
