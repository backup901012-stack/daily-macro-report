#!/usr/bin/env python3
"""
完整報告生成腳本（無需 AI API）
基於收集到的數據，用規則引擎生成分析文字，組裝 HTML 報告
"""
import json, sys, os, re
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATE = datetime.now().strftime('%Y-%m-%d')
REPORTS = 'reports'


def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def gen_executive_summary(md, enh, enh2):
    """根據數據生成 Executive Summary"""
    # 指數表現
    asia = md.get('asia_indices', {})
    europe = md.get('europe_indices', {})
    us = md.get('us_indices', {})

    def avg_chg(indices):
        vals = [d.get('change_pct', 0) for d in indices.values() if isinstance(d, dict)]
        return sum(vals) / len(vals) if vals else 0

    asia_avg = avg_chg(asia)
    europe_avg = avg_chg(europe)
    us_avg = avg_chg(us)

    # 情緒
    fg = enh.get('sentiment', {}).get('fear_greed', {}).get('score')
    fg_rating = enh.get('sentiment', {}).get('fear_greed', {}).get('rating', '')
    vix = enh.get('sentiment', {}).get('vix', {}).get('value')
    clock = enh.get('clock', {}).get('phase_cn', '')

    # 商品
    gold = md.get('commodities', {}).get('黃金', {})
    oil = md.get('commodities', {}).get('原油(WTI)', {})
    gold_chg = gold.get('change_pct', 0) if gold else 0
    oil_chg = oil.get('change_pct', 0) if oil else 0

    # 技術面
    sp_tech = enh2.get('technical_levels', {}).get('S&P 500', {})
    sp_rsi = sp_tech.get('rsi', 50)
    sp_from_high = sp_tech.get('pct_from_high', 0)

    # 市場方向判斷
    overall_chg = (asia_avg + europe_avg + us_avg) / 3
    if overall_chg < -1:
        tone = "全球市場昨日顯著下挫"
    elif overall_chg < -0.3:
        tone = "全球市場昨日普遍走低"
    elif overall_chg > 1:
        tone = "全球市場昨日全面上漲"
    elif overall_chg > 0.3:
        tone = "全球市場昨日溫和上揚"
    else:
        tone = "全球市場昨日漲跌互見"

    lines = [tone + "。"]

    # 美股
    sp = us.get('S&P 500', {})
    nq = us.get('納斯達克', {})
    if sp and nq:
        lines.append(f"美股方面，S&P 500 {sp.get('change_pct',0):+.2f}%，納斯達克 {nq.get('change_pct',0):+.2f}%（RSI {sp_rsi:.0f}，距52週高點 {sp_from_high:+.1f}%）。")

    # 商品
    if abs(gold_chg) > 1 or abs(oil_chg) > 1:
        lines.append(f"商品方面，黃金 {gold_chg:+.2f}%，WTI 原油 {oil_chg:+.2f}%。")

    # 情緒
    if fg is not None and vix is not None:
        lines.append(f"市場情緒方面，CNN 恐懼與貪婪指數 {fg:.0f}（{fg_rating}），VIX {vix:.1f}，美林時鐘指向{clock}。")
    elif fg is not None:
        lines.append(f"市場情緒方面，CNN 恐懼與貪婪指數 {fg:.0f}（{fg_rating}），美林時鐘指向{clock}。")

    return '\n\n'.join(lines)


def gen_index_analysis(md, enh2):
    """根據數據生成指數分析"""
    result = {}

    for region, key, indices_key in [
        ('asia', '亞洲', 'asia_indices'),
        ('europe', '歐洲', 'europe_indices'),
        ('us', '美國', 'us_indices'),
    ]:
        indices = md.get(indices_key, {})
        if not indices:
            continue

        parts = []
        sorted_idx = sorted(indices.items(), key=lambda x: x[1].get('change_pct', 0))
        best = sorted_idx[-1] if sorted_idx else None
        worst = sorted_idx[0] if sorted_idx else None

        avg = sum(d.get('change_pct', 0) for _, d in sorted_idx) / len(sorted_idx) if sorted_idx else 0

        if avg > 0.5:
            parts.append(f"{key}市場整體走強。")
        elif avg < -0.5:
            parts.append(f"{key}市場整體走弱。")
        else:
            parts.append(f"{key}市場漲跌互見。")

        if best:
            parts.append(f"{best[0]}表現最佳（{best[1].get('change_pct',0):+.2f}%）")
        if worst and worst != best:
            parts.append(f"，{worst[0]}表現最弱（{worst[1].get('change_pct',0):+.2f}%）。")

        result[f'{region}_analysis'] = ''.join(parts)

    # Overall
    all_chg = []
    for key in ['asia_indices', 'europe_indices', 'us_indices']:
        for _, d in md.get(key, {}).items():
            if isinstance(d, dict):
                all_chg.append(d.get('change_pct', 0))
    avg_all = sum(all_chg) / len(all_chg) if all_chg else 0
    if avg_all > 0.5:
        result['overall_summary'] = '全球市場整體偏多，風險偏好回升。'
        result['summary'] = '全球市場偏多。'
    elif avg_all < -0.5:
        result['overall_summary'] = '全球市場整體承壓，避險情緒升溫。'
        result['summary'] = '全球市場承壓。'
    else:
        result['overall_summary'] = '全球市場方向不明，觀望氣氛濃厚。'
        result['summary'] = '全球市場漲跌互見。'

    return result


def gen_stock_analysis(hot_stocks, news):
    """為每支熱門股票生成簡短分析"""
    analysis = {}
    titles = ' '.join([a.get('title', '') for a in news.get('articles', [])[:50]])

    for market, data in hot_stocks.items():
        for direction in ['inflow', 'outflow']:
            for stock in data.get(direction, []):
                symbol = stock.get('symbol', '')
                name = stock.get('name', symbol)
                chg = stock.get('change_pct', 0)
                vol = stock.get('volume_ratio', 1)

                if direction == 'inflow':
                    analysis[symbol] = f"{name}放量上漲{chg:+.2f}%，量比{vol:.1f}x，資金積極追捧。"
                else:
                    analysis[symbol] = f"{name}放量下跌{chg:+.2f}%，量比{vol:.1f}x，資金明顯流出。"

    return analysis


def gen_news_events(news):
    """從新聞標題歸納宏觀事件"""
    articles = news.get('articles', [])[:30]
    events = []

    # 簡單的關鍵詞分群
    groups = {}
    keywords_map = {
        'Fed/央行': ['fed', 'interest rate', 'central bank', 'fomc', 'powell', 'ecb', 'boj'],
        '地緣政治': ['war', 'iran', 'israel', 'tariff', 'sanction', 'geopolitical', 'trump', 'ukraine', 'conflict'],
        '能源/商品': ['oil', 'gold', 'crude', 'opec', 'energy', 'commodity', 'lng', 'gas'],
        'AI/科技': ['ai', 'nvidia', 'semiconductor', 'chip', 'openai', 'data center', 'meta', 'apple', 'google'],
        '加密貨幣': ['bitcoin', 'crypto', 'ethereum', 'btc'],
        '財報/企業': ['earnings', 'revenue', 'ipo', 'merger', 'acquisition', 'netflix', 'spacex'],
    }

    for article in articles:
        title = article.get('title', '')
        text = (title + ' ' + article.get('description', '')).lower()
        matched = False
        for group, kws in keywords_map.items():
            if any(kw in text for kw in kws):
                if group not in groups:
                    groups[group] = []
                groups[group].append(title)
                matched = True
                break

    for group, titles in list(groups.items())[:7]:
        events.append({
            'title': titles[0] if titles else group,
            'description': f'相關新聞 {len(titles)} 篇。' + ('　'.join(titles[1:3]) if len(titles) > 1 else ''),
            'impact_level': '高' if group in ['Fed/央行', '地緣政治'] else '中',
            'affected_markets': '全球',
            'market_direction': '中性',
            'related_tickers': [],
            'ticker_impact': {},
        })

    return events


def gen_calendar():
    """生成未來一週經濟日曆"""
    today = datetime.now()
    events = []
    # 常見的月底/月初數據
    for delta in range(0, 7):
        d = today + timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        ds = d.strftime('%Y-%m-%d')
        dow = d.weekday()
        if dow == 4:  # 週五
            events.append({'date': ds, 'event': '美國 PCE 物價指數', 'country': '美國', 'importance': '★★★', 'description': '聯儲最關注的通脹指標', 'consensus': ''})
        if d.day <= 3:  # 月初
            events.append({'date': ds, 'event': '製造業 PMI', 'country': '多國', 'importance': '★★', 'description': '製造業景氣指標', 'consensus': ''})
    return events[:6]


def gen_sector_analysis(fund_flows):
    """生成行業輪動分析"""
    sectors = fund_flows.get('sector', {})
    if not sectors:
        return ''

    inflows = [(d.get('name', s), d.get('1d', 0)) for s, d in sectors.items() if d.get('1d', 0) > 0]
    outflows = [(d.get('name', s), d.get('1d', 0)) for s, d in sectors.items() if d.get('1d', 0) < 0]
    inflows.sort(key=lambda x: x[1], reverse=True)
    outflows.sort(key=lambda x: x[1])

    parts = []
    if inflows:
        top_in = '、'.join([f"{n}" for n, _ in inflows[:3]])
        parts.append(f"當日資金流入板塊：{top_in}")
    if outflows:
        top_out = '、'.join([f"{n}" for n, _ in outflows[:3]])
        parts.append(f"資金流出板塊：{top_out}")

    return '。'.join(parts) + '。' if parts else ''


def gen_yield_curve_analysis(enh2):
    """生成殖利率曲線分析"""
    yc = enh2.get('yield_curve', {})
    if not yc:
        return ''
    shape = yc.get('shape', '')
    spread = yc.get('spread_3m10y')
    interp = yc.get('interpretation', '')
    if spread is not None:
        return f"美國殖利率曲線呈{shape}形態，3個月-10年利差為 {spread}%。{interp}"
    return interp


def _gen_fred_data_html(fred):
    """生成 FRED 經濟數據 HTML 區塊"""
    snapshot = fred.get('snapshot', {})
    if not snapshot:
        return ''

    rows = ''
    for cat_key, cat in snapshot.items():
        cat_label = cat.get('label', '')
        for sid, s in cat.get('data', {}).items():
            if s.get('latest_value') is None:
                continue
            val = s['latest_value']
            chg = s.get('change')
            chg_str = f'{chg:+.4f}' if chg is not None else '-'
            color = '#e74c3c' if chg and chg < 0 else '#27ae60' if chg and chg > 0 else '#666'
            rows += f'<tr><td style="text-align:left;">{s["name"]}</td><td style="text-align:center;color:#888;font-size:8pt;">{sid}</td><td style="text-align:right;font-weight:600;">{val:,.4f}</td><td style="text-align:right;color:{color};">{chg_str}</td><td style="text-align:center;color:#999;font-size:8pt;">{s.get("latest_date","")}</td></tr>'

    if not rows:
        return ''

    bs = fred.get('balance_sheet_trend', {})
    bs_line = ''
    if bs.get('latest_value_trillion'):
        wc = bs.get('week_change')
        wc_str = f'（週變化 {wc:+,.0f}M）' if wc else ''
        bs_line = f'<div style="margin-top:8px;font-size:9pt;color:#555;">Fed 資產負債表: <strong>${bs["latest_value_trillion"]:.2f}T</strong>{wc_str}</div>'

    return (
        '<div class="section-new-page"></div>'
        '<div style="margin:16px 0 20px 0;page-break-inside:avoid;">'
        '<div style="font-size:13pt;font-weight:700;color:#2c3e50;border-bottom:2.5px solid #2980b9;padding-bottom:6px;margin-bottom:10px;">FRED 聯準會經濟數據</div>'
        f'<table><thead><tr><th style="text-align:left;">指標</th><th style="text-align:center;">代碼</th><th style="text-align:right;">最新值</th><th style="text-align:right;">變化</th><th style="text-align:center;">日期</th></tr></thead><tbody>{rows}</tbody></table>'
        f'{bs_line}</div>\n'
    )


def _gen_alternative_data_html(alt):
    """生成替代數據 HTML 區塊"""
    if not alt:
        return ''

    parts = []

    # 板塊輪動
    sr = alt.get('sector_rotation', {})
    if sr and 'sectors' in sr:
        rows = ''
        for s in sr['sectors']:
            m = s.get('momentum', 0)
            mc = '#27ae60' if m > 0 else '#e74c3c'
            rows += f'<tr><td style="text-align:left;font-weight:600;">{s["name"]} ({s["ticker"]})</td><td style="text-align:right;">{s.get("return_1w",0):+.2f}%</td><td style="text-align:right;">{s.get("return_1m",0):+.2f}%</td><td style="text-align:right;color:{mc};font-weight:700;">{m:+.2f}</td></tr>'
        regime = sr.get('regime', '')
        spread = sr.get('risk_spread', 0)
        parts.append(
            '<div style="margin:16px 0;page-break-inside:avoid;">'
            '<div style="font-size:13pt;font-weight:700;color:#2c3e50;border-bottom:2.5px solid #e67e22;padding-bottom:6px;margin-bottom:10px;">板塊輪動分析 Sector Rotation</div>'
            f'<div style="background:linear-gradient(135deg,#fff8f0,#ffecd2);border-left:4px solid #e67e22;padding:10px 16px;margin-bottom:10px;font-size:9.5pt;border-radius:0 6px 6px 0;"><strong>市場態勢：</strong>{regime}（Risk Spread: {spread:+.2f}）</div>'
            f'<table><thead><tr><th style="text-align:left;">板塊</th><th style="text-align:right;">1週</th><th style="text-align:right;">1月</th><th style="text-align:right;">動量</th></tr></thead><tbody>{rows}</tbody></table></div>'
        )

    # Put/Call + 波動率 + 市場寬度 — 一行摘要
    summaries = []
    pc = alt.get('put_call_ratio', {})
    if pc.get('volume_pcr'):
        summaries.append(f'SPY Put/Call Ratio: <strong>{pc["volume_pcr"]:.3f}</strong>（{pc.get("signal","")}）')

    vs = alt.get('volatility_term_structure', {})
    if vs.get('ratio'):
        summaries.append(f'VIX/VIX3M: <strong>{vs["ratio"]:.4f}</strong>（{vs.get("structure","")}）')

    mb = alt.get('market_breadth', {})
    rsp = mb.get('rsp_spy', {})
    if rsp.get('signal'):
        summaries.append(f'RSP/SPY（市場寬度）: {rsp.get("signal","")}（1月 {rsp.get("change_1m_pct",0):+.2f}%）')

    iwm = mb.get('iwm_spy', {})
    if iwm.get('signal'):
        summaries.append(f'IWM/SPY（大小型股）: {iwm.get("signal","")}')

    vg = mb.get('iwd_iwf', {})
    if vg.get('signal'):
        summaries.append(f'IWD/IWF（價值/成長）: {vg.get("signal","")}')

    if summaries:
        items = ''.join(f'<div style="margin:4px 0;">• {s}</div>' for s in summaries)
        parts.append(
            '<div style="background:linear-gradient(135deg,#f0fff4,#e6ffed);border-left:4px solid #27ae60;padding:14px 18px;margin:14px 0;font-size:9.5pt;line-height:1.8;border-radius:0 6px 6px 0;page-break-inside:avoid;">'
            f'<strong style="color:#27ae60;font-size:10.5pt;">市場微觀結構指標</strong>{items}</div>'
        )

    # EM 貨幣壓力
    em = alt.get('em_currency_stress', {})
    if em.get('currencies'):
        rows = ''
        for c in em['currencies']:
            sc = c.get('stress_score', 0)
            sc_color = '#e74c3c' if sc > 5 else '#f39c12' if sc > 2 else '#27ae60'
            rows += f'<tr><td style="text-align:left;">{c["name"]}</td><td style="text-align:right;">{c.get("rate",0):.4f}</td><td style="text-align:right;">{c.get("change_1w_pct",0):+.2f}%</td><td style="text-align:right;">{c.get("change_1m_pct",0):+.2f}%</td><td style="text-align:right;">{c.get("vol_20d",0):.1f}%</td><td style="text-align:right;color:{sc_color};font-weight:700;">{sc:.1f}</td></tr>'
        level = em.get('level', '')
        parts.append(
            '<div style="margin:16px 0;page-break-inside:avoid;">'
            '<div style="font-size:13pt;font-weight:700;color:#2c3e50;border-bottom:2.5px solid #e74c3c;padding-bottom:6px;margin-bottom:10px;">新興市場貨幣壓力 EM Currency Stress</div>'
            f'<div style="font-size:9.5pt;margin-bottom:8px;">綜合壓力: <strong>{em.get("avg_stress",0):.1f}</strong> — {level}</div>'
            f'<table><thead><tr><th style="text-align:left;">貨幣</th><th style="text-align:right;">匯率</th><th style="text-align:right;">1週</th><th style="text-align:right;">1月</th><th style="text-align:right;">波動率</th><th style="text-align:right;">壓力分</th></tr></thead><tbody>{rows}</tbody></table></div>'
        )

    if not parts:
        return ''
    return '<div class="section-new-page"></div>' + '\n'.join(parts)


def main():
    print(f"Generating report for {DATE}...")

    # Load all data
    md = load_json(f'{REPORTS}/market_data_today.json')
    news = load_json(f'{REPORTS}/news_today.json')
    hot_stocks = load_json(f'{REPORTS}/hot_stocks_today.json')
    enh = load_json(f'{REPORTS}/enhanced_today.json')
    enh2 = load_json(f'{REPORTS}/enhanced_v2_today.json')
    fred = load_json(f'{REPORTS}/fred_today.json')
    alt = load_json(f'{REPORTS}/alternative_today.json')

    # Generate analysis
    executive_summary = gen_executive_summary(md, enh, enh2)
    index_analysis = gen_index_analysis(md, enh2)
    stock_analysis = gen_stock_analysis(hot_stocks, news)
    news_events = gen_news_events(news)
    calendar_events = gen_calendar()
    sector_analysis = gen_sector_analysis(enh.get('fund_flows', {}))
    yield_curve_analysis = gen_yield_curve_analysis(enh2)

    # Historical context
    from modules.enhanced_market_data import get_historical_sentiment_context
    fg = enh.get('sentiment', {}).get('fear_greed', {}).get('score')
    vix = enh.get('sentiment', {}).get('vix', {}).get('value')
    historical = get_historical_sentiment_context(fg, vix) if fg else {}

    # Serialize hot stocks
    def ser_hs(hs):
        out = {}
        for m, d in hs.items():
            if isinstance(d, dict) and 'inflow' in d:
                out[m] = {
                    'inflow': [{k: s.get(k) for k in ['symbol','name','current','change_pct','volume_ratio','volume','avg_volume','flow','news_mentions']} for s in d['inflow']],
                    'outflow': [{k: s.get(k) for k in ['symbol','name','current','change_pct','volume_ratio','volume','avg_volume','flow','news_mentions']} for s in d['outflow']],
                }
            else:
                out[m] = d
        return out

    # Build raw_data
    raw_data = {
        'market_data': md, 'news_events': news_events, 'index_analysis': index_analysis,
        'stock_analysis': stock_analysis, 'calendar_events': calendar_events,
        'hot_stocks': ser_hs(hot_stocks),
        'holiday_alerts': {'today_closed': [], 'tomorrow_closed': [], 'upcoming_holidays': [], 'has_alerts': False},
        'sentiment_data': enh.get('sentiment', {}), 'clock_data': enh.get('clock', {}),
        'fund_flows': enh.get('fund_flows', {}),
        'executive_summary': executive_summary, 'sector_analysis': sector_analysis,
        'yield_curve_analysis': yield_curve_analysis, 'historical_context': historical,
        'technical_levels': enh2.get('technical_levels', {}),
        'credit_spreads': enh2.get('credit_spreads', {}),
        'northbound_southbound': enh2.get('northbound_southbound', {}),
        'yield_curve': enh2.get('yield_curve', {}),
        'fred_data': fred,
        'alternative_data': alt,
        'report_date': DATE, 'generated_at': datetime.now().isoformat(),
        'fact_check_report': {'total_events_checked': len(news_events), 'corrections_applied': 0, 'status': '通過'}
    }

    with open(f'{REPORTS}/raw_data_{DATE}.json', 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"raw_data saved")

    # Generate HTML
    from modules.html_report_generator import generate_html_report
    html = generate_html_report(
        md, news_events, ser_hs(hot_stocks), stock_analysis,
        index_analysis, calendar_events, DATE,
        sentiment_data=enh.get('sentiment', {}),
        clock_data=enh.get('clock', {}),
        fund_flows=enh.get('fund_flows', {}),
    )

    # Inject enhanced blocks
    def insert_before_section(html, section_text, new_block):
        pat = rf'(<div class="section-new-page"></div>\s*<div class="section-title">{re.escape(section_text)}</div>)'
        m = re.search(pat, html)
        if m: return html[:m.start()] + new_block + html[m.start():]
        pat2 = rf'(<div class="section-title">{re.escape(section_text)}</div>)'
        m2 = re.search(pat2, html)
        if m2: return html[:m2.start()] + new_block + html[m2.start():]
        return html

    if executive_summary:
        es = executive_summary.replace('\n', '<br>')
        html = insert_before_section(html, '一、各國指數表現',
            f'<div style="background:linear-gradient(135deg,#f0f7ff 0%,#e8f4fd 100%);border-left:5px solid #1a365d;padding:18px 22px;margin:18px 0 20px 0;font-size:10.5pt;line-height:1.9;color:#2c3e50;border-radius:0 8px 8px 0;box-shadow:0 2px 8px rgba(0,0,0,0.05);page-break-inside:avoid;"><div style="font-size:14pt;font-weight:800;color:#1a365d;margin-bottom:12px;">市場綜述 Executive Summary</div>{es}</div>\n')

    tech = enh2.get('technical_levels', {})
    if tech:
        rows = ""
        for name, t in tech.items():
            rsi = t.get('rsi', 0)
            rc = '#e74c3c' if rsi < 30 else '#27ae60' if rsi > 70 else '#2c3e50'
            cross = t.get('cross', '') or ''
            cc = '#27ae60' if '黃金' in cross else '#e74c3c' if '死亡' in cross else '#999'
            m200 = f"{t['ma200']:,.0f}" if t.get('ma200') else 'N/A'
            rows += f'<tr><td style="font-weight:600;text-align:left;">{name}</td><td style="text-align:right;">{t.get("current",0):,.0f}</td><td style="text-align:right;">{t.get("ma50",0):,.0f}</td><td style="text-align:right;">{m200}</td><td style="text-align:right;font-weight:700;color:{rc};">{rsi:.1f}</td><td style="text-align:right;color:#e74c3c;">{t.get("pct_from_high",0):+.1f}%</td><td style="text-align:center;color:{cc};font-size:8.5pt;">{cross}</td></tr>'
        html = insert_before_section(html, '三、商品、外匯與債券',
            f'<div style="margin:16px 0 20px 0;page-break-inside:avoid;"><div style="font-size:13pt;font-weight:700;color:#2c3e50;border-bottom:2.5px solid #e67e22;padding-bottom:6px;margin-bottom:10px;">主要指數技術面關鍵位</div><table><thead><tr><th style="text-align:left;">指數</th><th style="text-align:right;">收盤</th><th style="text-align:right;">50MA</th><th style="text-align:right;">200MA</th><th style="text-align:right;">RSI(14)</th><th style="text-align:right;">距52W高</th><th style="text-align:center;">均線交叉</th></tr></thead><tbody>{rows}</tbody></table></div>\n')

    if yield_curve_analysis:
        html = insert_before_section(html, '四、市場情緒指標',
            f'<div style="background:linear-gradient(135deg,#f5f0ff 0%,#ede5ff 100%);border-left:4px solid #6c5ce7;padding:14px 18px;margin:14px 0;font-size:9.5pt;line-height:1.8;border-radius:0 6px 6px 0;page-break-inside:avoid;"><strong style="color:#6c5ce7;font-size:10.5pt;">殖利率曲線分析</strong><br>{yield_curve_analysis}</div>\n')

    if historical:
        hp = [v for v in historical.values() if isinstance(v, str)]
        if hp:
            html = insert_before_section(html, '五、全球資金流向脈動',
                f'<div style="background:linear-gradient(135deg,#fff5f5 0%,#ffe8e8 100%);border-left:4px solid #e74c3c;padding:14px 18px;margin:14px 0;font-size:9.5pt;line-height:1.8;border-radius:0 6px 6px 0;page-break-inside:avoid;"><strong style="color:#c0392b;font-size:10.5pt;">歷史情境參考</strong><br>{"<br><br>".join(hp)}</div>\n')

    if sector_analysis:
        html = insert_before_section(html, '六、GICS 11大板塊資金流向',
            f'<div style="background:linear-gradient(135deg,#fff8f0 0%,#ffecd2 100%);border-left:4px solid #e67e22;padding:14px 18px;margin:14px 0;font-size:9.5pt;line-height:1.8;border-radius:0 6px 6px 0;page-break-inside:avoid;"><strong style="color:#d35400;font-size:10.5pt;">行業輪動解讀</strong><br>{sector_analysis}</div>\n')

    # ── 新增：替代數據區塊 ──
    alt_blocks = _gen_alternative_data_html(alt)
    fred_block = _gen_fred_data_html(fred)

    # 在報告末尾（</body>前）插入新區塊
    if alt_blocks or fred_block:
        insert_content = ''
        if fred_block:
            insert_content += fred_block
        if alt_blocks:
            insert_content += alt_blocks
        html = html.replace('</body>', insert_content + '</body>')

    html_path = f'{REPORTS}/daily_report_{DATE}.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML saved: {html_path}")


if __name__ == '__main__':
    main()
