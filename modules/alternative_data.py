#!/usr/bin/env python3
"""
替代數據源模組
新增補充指標以豐富每日宏觀日報：
1. SPY 看跌/看漲比率 (Put/Call Ratio)
2. 板塊輪動分析 (Sector Rotation)
3. 波動率期限結構 (VIX vs VIX3M)
4. 新興市場貨幣壓力 (EM Currency Stress)
5. 市場寬度指標 (Market Breadth)
"""
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


# ==================== 常量定義 ====================

SECTOR_ETFS = {
    'XLK': {'name': '資訊科技', 'name_en': 'Info Tech'},
    'XLF': {'name': '金融', 'name_en': 'Financials'},
    'XLV': {'name': '醫療保健', 'name_en': 'Healthcare'},
    'XLE': {'name': '能源', 'name_en': 'Energy'},
    'XLI': {'name': '工業', 'name_en': 'Industrials'},
    'XLY': {'name': '非必需消費', 'name_en': 'Cons. Disc.'},
    'XLP': {'name': '必需消費', 'name_en': 'Cons. Staples'},
    'XLU': {'name': '公用事業', 'name_en': 'Utilities'},
    'XLRE': {'name': '房地產', 'name_en': 'Real Estate'},
    'XLB': {'name': '原材料', 'name_en': 'Materials'},
    'XLC': {'name': '通訊服務', 'name_en': 'Comm. Svcs'},
}

# Risk-on sectors: Tech, Discretionary, Industrials, Financials, Comm Svcs
# Risk-off sectors: Utilities, Staples, Healthcare, Real Estate
RISK_ON_SECTORS = ['XLK', 'XLY', 'XLI', 'XLF', 'XLC']
RISK_OFF_SECTORS = ['XLU', 'XLP', 'XLV', 'XLRE']

EM_CURRENCY_PAIRS = {
    'TRY=X': {'name': '美元/土耳其里拉', 'name_en': 'USD/TRY'},
    'ZAR=X': {'name': '美元/南非蘭特', 'name_en': 'USD/ZAR'},
    'MXN=X': {'name': '美元/墨西哥披索', 'name_en': 'USD/MXN'},
    'BRL=X': {'name': '美元/巴西雷亞爾', 'name_en': 'USD/BRL'},
    'INR=X': {'name': '美元/印度盧比', 'name_en': 'USD/INR'},
}

# Market breadth proxy ETFs: equal-weight vs cap-weight
BREADTH_ETFS = {
    'RSP': {'name': 'S&P 500 等權重', 'name_en': 'S&P 500 Equal Weight'},
    'SPY': {'name': 'S&P 500 市值加權', 'name_en': 'S&P 500 Cap Weight'},
    'IWM': {'name': '羅素2000小型股', 'name_en': 'Russell 2000'},
    'MDY': {'name': 'S&P 400中型股', 'name_en': 'S&P MidCap 400'},
    'IWD': {'name': '羅素1000價值', 'name_en': 'Russell 1000 Value'},
    'IWF': {'name': '羅素1000成長', 'name_en': 'Russell 1000 Growth'},
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ==================== 1. SPY 看跌/看漲比率 ====================

def get_put_call_ratio():
    """
    計算 SPY 看跌/看漲比率
    使用 SPY 期權鏈的總看跌成交量 / 總看漲成交量
    PCR > 1.0 = 看跌情緒濃厚（可能反向看多）
    PCR < 0.7 = 看漲情緒濃厚（可能反向看空）
    """
    log("  計算 SPY Put/Call Ratio...")
    try:
        spy = yf.Ticker("SPY")
        expirations = spy.options
        if not expirations:
            log("    ✗ SPY Put/Call: 無可用期權到期日")
            return {'error': 'No expirations available'}

        # Use the nearest 3 expiration dates for a representative sample
        near_expirations = expirations[:3]

        total_call_volume = 0
        total_put_volume = 0
        total_call_oi = 0
        total_put_oi = 0

        for exp in near_expirations:
            try:
                chain = spy.option_chain(exp)
                calls = chain.calls
                puts = chain.puts

                total_call_volume += calls['volume'].sum() if 'volume' in calls.columns else 0
                total_put_volume += puts['volume'].sum() if 'volume' in puts.columns else 0
                total_call_oi += calls['openInterest'].sum() if 'openInterest' in calls.columns else 0
                total_put_oi += puts['openInterest'].sum() if 'openInterest' in puts.columns else 0
            except Exception:
                continue

        # Calculate ratios
        volume_pcr = float(total_put_volume / total_call_volume) if total_call_volume > 0 else None
        oi_pcr = float(total_put_oi / total_call_oi) if total_call_oi > 0 else None

        # Interpret
        if volume_pcr is not None:
            if volume_pcr > 1.2:
                signal = "極度看跌（反向看多信號）"
                signal_en = "Extreme Bearish (Contrarian Bullish)"
            elif volume_pcr > 1.0:
                signal = "偏看跌"
                signal_en = "Bearish Leaning"
            elif volume_pcr > 0.7:
                signal = "中性"
                signal_en = "Neutral"
            elif volume_pcr > 0.5:
                signal = "偏看漲"
                signal_en = "Bullish Leaning"
            else:
                signal = "極度看漲（反向看空信號）"
                signal_en = "Extreme Bullish (Contrarian Bearish)"
        else:
            signal = "無數據"
            signal_en = "No Data"

        result = {
            'volume_pcr': round(volume_pcr, 3) if volume_pcr else None,
            'oi_pcr': round(oi_pcr, 3) if oi_pcr else None,
            'total_call_volume': int(total_call_volume),
            'total_put_volume': int(total_put_volume),
            'total_call_oi': int(total_call_oi),
            'total_put_oi': int(total_put_oi),
            'expirations_used': list(near_expirations),
            'signal': signal,
            'signal_en': signal_en,
        }
        log(f"    ✓ SPY PCR (Volume): {volume_pcr:.3f} — {signal}")
        return result

    except Exception as e:
        log(f"    ✗ SPY Put/Call: {e}")
        return {'error': str(e)}


# ==================== 2. 板塊輪動分析 ====================

def get_sector_rotation():
    """
    板塊輪動分析：比較各板塊 1 週 / 1 月表現
    判斷 risk-on vs risk-off 傾向
    """
    log("  計算板塊輪動分析...")
    try:
        tickers = list(SECTOR_ETFS.keys())
        data = yf.download(tickers, period='2mo', group_by='ticker', progress=False)

        sectors = []
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    df = data.copy()
                else:
                    df = data[ticker].copy()
                df = df.dropna(subset=['Close'])
                if len(df) < 5:
                    continue

                close = df['Close']
                # Handle MultiIndex columns from yf.download
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]

                latest = float(close.iloc[-1])

                # 1-week return
                if len(close) >= 6:
                    ret_1w = float((close.iloc[-1] / close.iloc[-6] - 1) * 100)
                else:
                    ret_1w = float((close.iloc[-1] / close.iloc[0] - 1) * 100)

                # 1-month return
                if len(close) >= 22:
                    ret_1m = float((close.iloc[-1] / close.iloc[-22] - 1) * 100)
                else:
                    ret_1m = float((close.iloc[-1] / close.iloc[0] - 1) * 100)

                # Momentum score = average of 1w and 1m return
                momentum = (ret_1w + ret_1m) / 2

                meta = SECTOR_ETFS[ticker]
                sectors.append({
                    'ticker': ticker,
                    'name': meta['name'],
                    'name_en': meta['name_en'],
                    'close': round(latest, 2),
                    'return_1w': round(ret_1w, 2),
                    'return_1m': round(ret_1m, 2),
                    'momentum': round(momentum, 2),
                })
            except Exception:
                continue

        # Sort by momentum (strongest first)
        sectors.sort(key=lambda x: x['momentum'], reverse=True)

        # Calculate risk-on vs risk-off spread
        risk_on_avg = np.mean([s['momentum'] for s in sectors if s['ticker'] in RISK_ON_SECTORS]) if sectors else 0
        risk_off_avg = np.mean([s['momentum'] for s in sectors if s['ticker'] in RISK_OFF_SECTORS]) if sectors else 0
        risk_spread = float(risk_on_avg - risk_off_avg)

        if risk_spread > 2:
            regime = "強 Risk-On（風險偏好）"
            regime_en = "Strong Risk-On"
        elif risk_spread > 0.5:
            regime = "偏 Risk-On"
            regime_en = "Leaning Risk-On"
        elif risk_spread > -0.5:
            regime = "中性"
            regime_en = "Neutral"
        elif risk_spread > -2:
            regime = "偏 Risk-Off"
            regime_en = "Leaning Risk-Off"
        else:
            regime = "強 Risk-Off（避險模式）"
            regime_en = "Strong Risk-Off"

        leaders = sectors[:3] if len(sectors) >= 3 else sectors
        laggards = sectors[-3:] if len(sectors) >= 3 else sectors

        result = {
            'sectors': sectors,
            'leaders': [s['ticker'] for s in leaders],
            'laggards': [s['ticker'] for s in laggards],
            'risk_on_avg_momentum': round(float(risk_on_avg), 2),
            'risk_off_avg_momentum': round(float(risk_off_avg), 2),
            'risk_spread': round(risk_spread, 2),
            'regime': regime,
            'regime_en': regime_en,
        }
        log(f"    ✓ 板塊輪動: {regime} (spread: {risk_spread:+.2f})")
        log(f"      領漲: {', '.join(s['ticker'] for s in leaders)}")
        log(f"      落後: {', '.join(s['ticker'] for s in laggards)}")
        return result

    except Exception as e:
        log(f"    ✗ 板塊輪動: {e}")
        return {'error': str(e)}


# ==================== 3. 波動率期限結構 ====================

def get_volatility_term_structure():
    """
    波動率期限結構：VIX vs VIX3M (CBOE 3-Month Volatility)
    Contango (VIX < VIX3M): 正常/平靜，市場無恐慌
    Backwardation (VIX > VIX3M): 恐慌/對沖需求急升
    """
    log("  計算波動率期限結構...")
    try:
        tickers = ['^VIX', '^VIX3M']
        data = yf.download(tickers, period='3mo', group_by='ticker', progress=False)

        # Extract close prices
        vix_close = data['^VIX']['Close'].dropna()
        vix3m_close = data['^VIX3M']['Close'].dropna()

        # Handle MultiIndex
        if isinstance(vix_close, pd.DataFrame):
            vix_close = vix_close.iloc[:, 0]
        if isinstance(vix3m_close, pd.DataFrame):
            vix3m_close = vix3m_close.iloc[:, 0]

        if vix_close.empty or vix3m_close.empty:
            log("    ✗ 波動率期限結構: 無數據")
            return {'error': 'No VIX or VIX3M data'}

        latest_vix = float(vix_close.iloc[-1])
        latest_vix3m = float(vix3m_close.iloc[-1])

        # VIX/VIX3M ratio
        ratio = latest_vix / latest_vix3m if latest_vix3m > 0 else None

        # Term structure slope (negative = backwardation)
        spread = latest_vix3m - latest_vix

        # Historical context: ratio over last month
        common_idx = vix_close.index.intersection(vix3m_close.index)
        if len(common_idx) >= 5:
            ratio_series = vix_close[common_idx] / vix3m_close[common_idx]
            ratio_1m_avg = float(ratio_series.tail(21).mean()) if len(ratio_series) >= 21 else float(ratio_series.mean())
            ratio_1m_high = float(ratio_series.tail(21).max()) if len(ratio_series) >= 21 else float(ratio_series.max())
            ratio_1m_low = float(ratio_series.tail(21).min()) if len(ratio_series) >= 21 else float(ratio_series.min())
        else:
            ratio_1m_avg = ratio
            ratio_1m_high = ratio
            ratio_1m_low = ratio

        # Interpret
        if ratio is not None:
            if ratio > 1.1:
                structure = "嚴重倒掛（Backwardation）— 市場恐慌"
                structure_en = "Severe Backwardation — Market Panic"
                signal = "bearish"
            elif ratio > 1.0:
                structure = "輕微倒掛 — 短期緊張"
                structure_en = "Mild Backwardation — Near-term Stress"
                signal = "cautious"
            elif ratio > 0.9:
                structure = "正常正價差（Contango）— 市場平靜"
                structure_en = "Normal Contango — Market Calm"
                signal = "neutral"
            else:
                structure = "深度正價差 — 市場極度自滿"
                structure_en = "Deep Contango — Extreme Complacency"
                signal = "bullish"
        else:
            structure = "無數據"
            structure_en = "No Data"
            signal = "unknown"

        result = {
            'vix': round(latest_vix, 2),
            'vix3m': round(latest_vix3m, 2),
            'ratio': round(ratio, 4) if ratio else None,
            'spread': round(spread, 2),
            'ratio_1m_avg': round(ratio_1m_avg, 4) if ratio_1m_avg else None,
            'ratio_1m_high': round(ratio_1m_high, 4) if ratio_1m_high else None,
            'ratio_1m_low': round(ratio_1m_low, 4) if ratio_1m_low else None,
            'structure': structure,
            'structure_en': structure_en,
            'signal': signal,
        }
        log(f"    ✓ VIX/VIX3M: {ratio:.4f} — {structure}")
        return result

    except Exception as e:
        log(f"    ✗ 波動率期限結構: {e}")
        return {'error': str(e)}


# ==================== 4. 新興市場貨幣壓力 ====================

def get_em_currency_stress():
    """
    追蹤美元兌主要新興市場貨幣
    大幅波動 = 新興市場壓力信號
    """
    log("  計算新興市場貨幣壓力...")
    try:
        tickers = list(EM_CURRENCY_PAIRS.keys())
        data = yf.download(tickers, period='2mo', group_by='ticker', progress=False)

        currencies = []
        stress_scores = []

        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    df = data.copy()
                else:
                    df = data[ticker].copy()
                df = df.dropna(subset=['Close'])
                if len(df) < 5:
                    continue

                close = df['Close']
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]

                latest = float(close.iloc[-1])

                # 1-week change (USD strengthening vs EM = positive = stress)
                if len(close) >= 6:
                    chg_1w = float((close.iloc[-1] / close.iloc[-6] - 1) * 100)
                else:
                    chg_1w = 0

                # 1-month change
                if len(close) >= 22:
                    chg_1m = float((close.iloc[-1] / close.iloc[-22] - 1) * 100)
                else:
                    chg_1m = float((close.iloc[-1] / close.iloc[0] - 1) * 100)

                # Volatility (20-day realized vol, annualized)
                if len(close) >= 21:
                    returns = close.pct_change().dropna().tail(20)
                    vol_20d = float(returns.std() * np.sqrt(252) * 100)
                else:
                    vol_20d = 0

                # Stress score: combination of recent depreciation and volatility
                stress = abs(chg_1w) * 0.4 + abs(chg_1m) * 0.3 + vol_20d * 0.3

                meta = EM_CURRENCY_PAIRS[ticker]
                currencies.append({
                    'ticker': ticker,
                    'name': meta['name'],
                    'name_en': meta['name_en'],
                    'rate': round(latest, 4),
                    'change_1w_pct': round(chg_1w, 2),
                    'change_1m_pct': round(chg_1m, 2),
                    'vol_20d': round(vol_20d, 2),
                    'stress_score': round(stress, 2),
                })
                stress_scores.append(stress)
            except Exception:
                continue

        # Aggregate stress index
        avg_stress = float(np.mean(stress_scores)) if stress_scores else 0
        max_stress = max(stress_scores) if stress_scores else 0

        if avg_stress > 10:
            level = "高壓力 — 新興市場資金外逃風險"
            level_en = "High Stress — EM Capital Flight Risk"
        elif avg_stress > 5:
            level = "中度壓力 — 關注新興市場動態"
            level_en = "Moderate Stress — Monitor EM Developments"
        elif avg_stress > 2:
            level = "輕微壓力 — 正常波動範圍"
            level_en = "Mild Stress — Normal Volatility"
        else:
            level = "低壓力 — 新興市場穩定"
            level_en = "Low Stress — EM Stable"

        # Sort by stress score (highest first)
        currencies.sort(key=lambda x: x['stress_score'], reverse=True)

        result = {
            'currencies': currencies,
            'avg_stress': round(avg_stress, 2),
            'max_stress': round(max_stress, 2),
            'most_stressed': currencies[0]['name_en'] if currencies else None,
            'level': level,
            'level_en': level_en,
        }
        log(f"    ✓ EM貨幣壓力: 平均 {avg_stress:.2f} — {level}")
        return result

    except Exception as e:
        log(f"    ✗ EM貨幣壓力: {e}")
        return {'error': str(e)}


# ==================== 5. 市場寬度指標 ====================

def get_market_breadth():
    """
    市場寬度指標：
    1. RSP/SPY 比率 — 等權重 vs 市值加權（衡量參與度）
    2. IWM/SPY 比率 — 小型股 vs 大型股
    3. IWD/IWF 比率 — 價值 vs 成長輪動
    上升的 RSP/SPY = 市場參與度廣泛（健康上漲）
    下降的 RSP/SPY = 少數權重股主導（不健康）
    """
    log("  計算市場寬度指標...")
    try:
        tickers = list(BREADTH_ETFS.keys())
        data = yf.download(tickers, period='3mo', group_by='ticker', progress=False)

        prices = {}
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    df = data.copy()
                else:
                    df = data[ticker].copy()
                df = df.dropna(subset=['Close'])
                close = df['Close']
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                prices[ticker] = close
            except Exception:
                continue

        result = {}

        # --- RSP/SPY ratio (breadth participation) ---
        if 'RSP' in prices and 'SPY' in prices:
            rsp = prices['RSP']
            spy = prices['SPY']
            common = rsp.index.intersection(spy.index)
            ratio = rsp[common] / spy[common]

            latest_ratio = float(ratio.iloc[-1])
            if len(ratio) >= 22:
                ratio_1m_ago = float(ratio.iloc[-22])
            else:
                ratio_1m_ago = float(ratio.iloc[0])
            ratio_trend = float((latest_ratio / ratio_1m_ago - 1) * 100)

            if ratio_trend > 1:
                breadth_signal = "市場寬度改善 — 上漲參與度擴大"
                breadth_signal_en = "Breadth Improving — Rally Broadening"
            elif ratio_trend > -1:
                breadth_signal = "市場寬度穩定"
                breadth_signal_en = "Breadth Stable"
            else:
                breadth_signal = "市場寬度收窄 — 少數股主導"
                breadth_signal_en = "Breadth Narrowing — Mega-cap Dominated"

            result['rsp_spy'] = {
                'ratio': round(latest_ratio, 4),
                'change_1m_pct': round(ratio_trend, 2),
                'signal': breadth_signal,
                'signal_en': breadth_signal_en,
            }

        # --- IWM/SPY ratio (small cap vs large cap) ---
        if 'IWM' in prices and 'SPY' in prices:
            iwm = prices['IWM']
            spy = prices['SPY']
            common = iwm.index.intersection(spy.index)
            ratio = iwm[common] / spy[common]

            latest_ratio = float(ratio.iloc[-1])
            if len(ratio) >= 22:
                ratio_1m_ago = float(ratio.iloc[-22])
            else:
                ratio_1m_ago = float(ratio.iloc[0])
            ratio_trend = float((latest_ratio / ratio_1m_ago - 1) * 100)

            if ratio_trend > 1:
                sc_signal = "小型股領漲 — 風險偏好上升"
                sc_signal_en = "Small-caps Leading — Risk Appetite Rising"
            elif ratio_trend > -1:
                sc_signal = "大小型股表現相近"
                sc_signal_en = "Small/Large-cap Balanced"
            else:
                sc_signal = "大型股領漲 — 避險/品質偏好"
                sc_signal_en = "Large-caps Leading — Flight to Quality"

            result['iwm_spy'] = {
                'ratio': round(latest_ratio, 4),
                'change_1m_pct': round(ratio_trend, 2),
                'signal': sc_signal,
                'signal_en': sc_signal_en,
            }

        # --- IWD/IWF ratio (value vs growth) ---
        if 'IWD' in prices and 'IWF' in prices:
            iwd = prices['IWD']
            iwf = prices['IWF']
            common = iwd.index.intersection(iwf.index)
            ratio = iwd[common] / iwf[common]

            latest_ratio = float(ratio.iloc[-1])
            if len(ratio) >= 22:
                ratio_1m_ago = float(ratio.iloc[-22])
            else:
                ratio_1m_ago = float(ratio.iloc[0])
            ratio_trend = float((latest_ratio / ratio_1m_ago - 1) * 100)

            if ratio_trend > 1:
                vg_signal = "價值股領先 — 利率/通脹受益"
                vg_signal_en = "Value Leading — Rate/Inflation Play"
            elif ratio_trend > -1:
                vg_signal = "價值/成長均衡"
                vg_signal_en = "Value/Growth Balanced"
            else:
                vg_signal = "成長股領先 — 科技/動量主導"
                vg_signal_en = "Growth Leading — Tech/Momentum Driven"

            result['iwd_iwf'] = {
                'ratio': round(latest_ratio, 4),
                'change_1m_pct': round(ratio_trend, 2),
                'signal': vg_signal,
                'signal_en': vg_signal_en,
            }

        # Individual ETF performance summary
        etf_summary = []
        for ticker in tickers:
            if ticker not in prices:
                continue
            close = prices[ticker]
            if len(close) < 2:
                continue

            latest = float(close.iloc[-1])
            chg_1d = float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) >= 2 else 0
            chg_1w = float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) >= 6 else chg_1d
            chg_1m = float((close.iloc[-1] / close.iloc[-22] - 1) * 100) if len(close) >= 22 else float((close.iloc[-1] / close.iloc[0] - 1) * 100)

            meta = BREADTH_ETFS[ticker]
            etf_summary.append({
                'ticker': ticker,
                'name': meta['name'],
                'name_en': meta['name_en'],
                'close': round(latest, 2),
                'change_1d_pct': round(chg_1d, 2),
                'change_1w_pct': round(chg_1w, 2),
                'change_1m_pct': round(chg_1m, 2),
            })

        result['etf_summary'] = etf_summary
        log(f"    ✓ 市場寬度: {len(result) - 1} 項比率指標, {len(etf_summary)} ETF")
        return result

    except Exception as e:
        log(f"    ✗ 市場寬度: {e}")
        return {'error': str(e)}


# ==================== 主入口 ====================

def collect_alternative_data():
    """主入口：收集所有替代數據源"""
    log("開始收集替代數據...")

    put_call = get_put_call_ratio()
    sector_rotation = get_sector_rotation()
    vol_structure = get_volatility_term_structure()
    em_stress = get_em_currency_stress()
    breadth = get_market_breadth()

    result = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'put_call_ratio': put_call,
        'sector_rotation': sector_rotation,
        'volatility_term_structure': vol_structure,
        'em_currency_stress': em_stress,
        'market_breadth': breadth,
    }

    log("替代數據收集完成")
    return result


if __name__ == '__main__':
    import json
    data = collect_alternative_data()
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
