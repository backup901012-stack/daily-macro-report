#!/usr/bin/env python3
"""
HTML 報告生成引擎 v2
使用 HTML+CSS 生成專業精美的 PDF 報告
參考 Saxo Bank / Goldman Sachs 風格
新增：市場情緒指標、美林時鐘、全球資金流向、GICS板塊資金流向
"""
import json
import math
from datetime import datetime, timedelta


# ==================== CSS 樣式 ====================

REPORT_CSS = """
@page {
    size: A4;
    margin: 15mm 12mm 20mm 12mm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-size: 8pt;
        color: #95a5a6;
        font-family: 'PingFang TC', 'PingFang SC', 'Heiti TC', 'Noto Sans TC', sans-serif;
    }
}
@page :first {
    margin-top: 0;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'PingFang TC', 'PingFang SC', 'Heiti TC', 'Noto Sans TC', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.65;
    color: #2c3e50;
    background: #fff;
    max-width: 210mm;
}

/* ===== 報告頭部 ===== */
.report-header {
    background: #2c3e50;
    color: white;
    padding: 24px 24px 18px;
    margin: 0 -12mm 0 -12mm;
    padding-left: 24mm;
    padding-right: 24mm;
}

.report-header h1 {
    font-size: 26pt;
    font-weight: 800;
    letter-spacing: 2px;
    margin-bottom: 4px;
}

.report-header .subtitle {
    font-size: 11pt;
    color: rgba(255,255,255,0.7);
    margin-bottom: 2px;
}

.report-header .date-line {
    font-size: 10pt;
    color: rgba(255,255,255,0.6);
}

.header-divider {
    height: 3px;
    background: #e67e22;
    margin: 0 -12mm;
}

/* ===== 市場速覽 ===== */
.snapshot-box {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    padding: 14px 18px;
    margin: 16px 0;
    font-size: 9.5pt;
    line-height: 1.8;
    color: #2c3e50;
}

.snapshot-box .snapshot-label {
    font-weight: 700;
    color: #2c3e50;
    display: inline;
}

.snapshot-line {
    margin-bottom: 4px;
}

/* ===== 章節標題 ===== */
.section-title {
    font-size: 15pt;
    font-weight: 800;
    color: #2c3e50;
    margin: 18px 0 4px;
    padding-bottom: 6px;
    border-bottom: 2.5px solid #e67e22;
    page-break-after: avoid;
}

.sub-section-title {
    font-size: 12pt;
    font-weight: 700;
    color: #2c3e50;
    margin: 12px 0 5px;
    padding-left: 10px;
    border-left: 3.5px solid #3498db;
    page-break-after: avoid;
}

/* ===== 分析段落 ===== */
.analysis-text {
    font-size: 9.5pt;
    color: #555;
    line-height: 1.75;
    margin-bottom: 6px;
    text-align: justify;
}

/* ===== 表格 ===== */
table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 10px;
    font-size: 9.5pt;
}

table thead th {
    background: #f1f3f5;
    color: #2c3e50;
    font-weight: 700;
    padding: 8px 8px;
    text-align: left;
    font-size: 8.5pt;
    border-bottom: 2px solid #dee2e6;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

table thead th:not(:first-child) {
    text-align: right;
}

table tbody td {
    padding: 6px 8px;
    border-bottom: 1px solid #ecf0f1;
}

table tbody td:not(:first-child) {
    text-align: right;
}

table tbody tr:nth-child(even) {
    background: #f9fafb;
}

table tbody tr:hover {
    background: #eef2f7;
}

table tbody tr {
    page-break-inside: avoid;
}

thead {
    display: table-header-group;
}

td.name-cell {
    font-weight: 600;
    color: #2c3e50;
    text-align: left;
}

/* ===== 漲跌顏色 ===== */
.up, .snapshot-box .up {
    color: #27ae60 !important;
    font-weight: 600;
}

.down, .snapshot-box .down {
    color: #e74c3c !important;
    font-weight: 600;
}

.flat, .snapshot-box .flat {
    color: #95a5a6 !important;
}

.trend-up { color: #27ae60; font-weight: 700; }
.trend-down { color: #e74c3c; font-weight: 700; }
.trend-strong-up { color: #1e8449; font-weight: 700; }
.trend-strong-down { color: #c0392b; font-weight: 700; }

/* ===== 新聞卡片 ===== */
.news-card {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-left: 4px solid #3498db;
    border-radius: 3px;
    padding: 5px 10px;
    margin-bottom: 4px;
    page-break-inside: avoid;
}

.news-card h3 {
    font-size: 9.5pt;
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 2px;
}

.news-meta {
    font-size: 8pt;
    margin-bottom: 2px;
}

.badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-weight: 600;
    font-size: 8pt;
    margin-right: 4px;
}

.badge-high { background: #e74c3c; color: #fff; }
.badge-medium { background: #e67e22; color: #fff; }
.badge-low { background: #95a5a6; color: #fff; }
.badge-bullish { color: #27ae60; }
.badge-bearish { color: #e74c3c; }
.badge-neutral { color: #7f8c8d; }

.news-body {
    font-size: 8.5pt;
    color: #555;
    line-height: 1.4;
}

.news-tickers {
    font-size: 8pt;
    color: #7f8c8d;
    margin-top: 2px;
}

.news-tickers code {
    background: #ecf0f1;
    padding: 1px 4px;
    border-radius: 2px;
    font-size: 8pt;
    color: #2c3e50;
}

/* ===== 熱門股票 ===== */
.stock-analysis {
    font-size: 8.5pt;
    color: #666;
    line-height: 1.4;
    max-width: 280px;
}

.filter-note {
    font-size: 8.5pt;
    color: #7f8c8d;
    margin-bottom: 6px;
    padding: 6px 10px;
    background: #f8f9fa;
    border-radius: 4px;
    page-break-after: avoid;
}

.hot-label {
    font-size: 10pt;
    font-weight: 700;
    margin: 8px 0 4px;
    page-break-after: avoid;
}
.hot-label.buy { color: #e74c3c; }
.hot-label.sell { color: #27ae60; }

/* ===== 經濟日曆 ===== */
.calendar-highlight {
    background: #fff8e1;
    border-left: 3px solid #f1c40f;
    padding: 10px 14px;
    margin-top: 12px;
    margin-bottom: 8px;
    page-break-inside: avoid;
}

.calendar-highlight strong {
    color: #2c3e50;
}

/* ===== 分隔線 ===== */
.divider {
    border: none;
    border-top: 1px solid #ddd;
    margin: 18px 0;
}

/* ===== 底部 ===== */
.footer {
    margin-top: 15px;
    padding-top: 8px;
    border-top: 1px solid #ddd;
    font-size: 7.5pt;
    color: #95a5a6;
    text-align: left;
    page-break-before: avoid;
}

.footer strong {
    color: #666;
}

/* ===== 頁面控制 ===== */
.page-break {
    page-break-before: always;
}

.section-new-page {
    page-break-before: auto;
    margin-top: 12px;
}

/* ===== 情緒指標卡片 ===== */
.sentiment-container {
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
}
.sentiment-card {
    flex: 1;
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    padding: 12px;
    text-align: center;
}
.sentiment-card .label {
    font-size: 8.5pt;
    color: #7f8c8d;
    margin-bottom: 4px;
}
.sentiment-card .value {
    font-size: 20pt;
    font-weight: 800;
}
.sentiment-card .sub {
    font-size: 8.5pt;
    margin-top: 2px;
}

/* ===== 美林時鐘 ===== */
.clock-wrapper {
    display: flex;
    gap: 24px;
    align-items: center;
    margin: 15px 0;
    padding: 15px;
    background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
    border-radius: 10px;
    border: 1px solid #e8ecef;
}
.clock-svg-box {
    flex: 0 0 280px;
    text-align: center;
}
.clock-info-box {
    flex: 1;
}
.clock-phase-title {
    font-size: 16pt;
    font-weight: 800;
    margin-bottom: 6px;
    letter-spacing: 0.5px;
}
.clock-phase-sub {
    font-size: 9pt;
    color: #555;
    line-height: 1.6;
    margin-bottom: 8px;
}
.clock-indicator-row {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
}
.clock-ind-card {
    flex: 1;
    background: #fff;
    border-radius: 8px;
    padding: 8px 6px;
    text-align: center;
    border: 1px solid #e8ecef;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.clock-ind-card .ind-label {
    font-size: 7pt;
    color: #7f8c8d;
    margin-bottom: 3px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
.clock-ind-card .ind-value {
    font-size: 13pt;
    font-weight: 700;
    color: #2c3e50;
}

/* ===== 資金流向 ===== */
.flow-val-cell {
    position: relative;
    min-width: 70px;
}
.flow-val-cell .bar {
    display: inline-block;
    height: 10px;
    border-radius: 2px;
    opacity: 0.45;
    vertical-align: middle;
    margin-left: 4px;
}
.flow-val-cell .bar.positive {
    background: #27ae60;
}
.flow-val-cell .bar.negative {
    background: #e74c3c;
}
.bond-flow-table td:first-child {
    font-weight: 600;
}
"""


# ==================== 輔助函數 ====================

def _change_class(val):
    """根據數值返回 CSS class"""
    if val is None:
        return "flat"
    if val > 0:
        return "up"
    elif val < 0:
        return "down"
    return "flat"


def _trend_arrow(val):
    """根據漲跌幅返回趨勢箭頭"""
    if val is None:
        return "—"
    if val >= 3:
        return '<span class="trend-strong-up">▲▲</span>'
    elif val >= 0.5:
        return '<span class="trend-up">▲</span>'
    elif val > -0.5:
        return '—'
    elif val > -3:
        return '<span class="trend-down">▼</span>'
    else:
        return '<span class="trend-strong-down">▼▼</span>'


def _format_pct(val):
    """格式化百分比"""
    if val is None:
        return "N/A"
    cls = _change_class(val)
    sign = "+" if val > 0 else ""
    return f'<span class="{cls}">{sign}{val:.2f}%</span>'


def _format_change(val):
    """格式化漲跌值"""
    if val is None:
        return "N/A"
    cls = _change_class(val)
    sign = "+" if val > 0 else ""
    return f'<span class="{cls}">{sign}{val:,.2f}</span>'


def _format_change4(val):
    """格式化漲跌值（4位小數）"""
    if val is None:
        return "N/A"
    cls = _change_class(val)
    sign = "+" if val > 0 else ""
    return f'<span class="{cls}">{sign}{val:.4f}</span>'


def _fmt_flow(val):
    """Format capital flow in Chinese 億 (100M USD)."""
    if val is None:
        return "N/A"
    yi = val / 1e8
    sign = "+" if yi > 0 else ""
    if abs(yi) >= 100:
        return f"{sign}{yi:.0f}億"
    elif abs(yi) >= 1:
        return f"{sign}{yi:.1f}億"
    else:
        wan = val / 1e4
        return f"{sign}{wan:.0f}萬"


def _flow_color(val):
    if val is None:
        return ""
    return "up" if val > 0 else "down"


def _flow_cell(val, max_v):
    """Generate a table cell with value + inline bar."""
    cls = _flow_color(val)
    txt = _fmt_flow(val)
    if val is None or val == 0 or max_v == 0:
        return f'<td class="flow-val-cell {cls}">{txt}</td>'
    bar_w = min(int(abs(val) / max_v * 50), 50)
    bar_cls = 'positive' if val > 0 else 'negative'
    return f'<td class="flow-val-cell {cls}">{txt}<span class="bar {bar_cls}" style="width:{bar_w}px;"></span></td>'


# ==================== 市場速覽 ====================

def _gen_snapshot(market_data, news_events):
    """生成市場速覽區塊"""
    html = '<div class="snapshot-box">\n'

    asia = market_data.get('asia_indices', {})
    europe = market_data.get('europe_indices', {})
    us = market_data.get('us_indices', {})

    def _idx_str(indices, names):
        parts = []
        for n in names:
            if n in indices:
                d = indices[n]
                cls = _change_class(d['change_pct'])
                parts.append(f'{n} <span class="{cls}">{d["change_pct"]:+.2f}%</span>')
        return '，'.join(parts) if parts else ''

    us_str = _idx_str(us, ['S&P 500', '納斯達克', '道瓊斯'])
    asia_str = _idx_str(asia, ['日經225', '台灣加權', '香港恆生'])
    europe_str = _idx_str(europe, ['德國DAX', '英國FTSE100', '法國CAC40'])

    html += f'<div class="snapshot-line"><span class="snapshot-label">股市：</span>{us_str}；亞洲 {asia_str}；歐洲 {europe_str}</div>\n'

    # 商品
    commodities = market_data.get('commodities', {})
    comm_parts = []
    for name, data in list(commodities.items())[:4]:
        cls = _change_class(data['change_pct'])
        comm_parts.append(f'{name} <span class="{cls}">{data["change_pct"]:+.2f}%</span>')
    if comm_parts:
        html += f'<div class="snapshot-line"><span class="snapshot-label">商品：</span>{" ｜ ".join(comm_parts)}</div>\n'

    # 外匯
    forex = market_data.get('forex', {})
    fx_parts = []
    for name, data in list(forex.items())[:3]:
        fx_parts.append(f'{name} {data["current"]:.4f}（<span class="{_change_class(data["change_pct"])}">{data["change_pct"]:+.2f}%</span>）')
    if fx_parts:
        html += f'<div class="snapshot-line"><span class="snapshot-label">外匯：</span>{" ｜ ".join(fx_parts)}</div>\n'

    # 加密貨幣
    crypto = market_data.get('crypto', {})
    if crypto:
        crypto_parts = []
        for coin in ['Bitcoin', 'Ethereum']:
            if coin in crypto:
                d = crypto[coin]
                short = 'BTC' if coin == 'Bitcoin' else 'ETH'
                cls = _change_class(d['change_pct'])
                crypto_parts.append(f'{short} ${d["current"]:,.0f}（<span class="{cls}">{d["change_pct"]:+.2f}%</span>）')
        if crypto_parts:
            html += f'<div class="snapshot-line"><span class="snapshot-label">加密貨幣：</span>{" ｜ ".join(crypto_parts)}</div>\n'

    # 焦點事件
    if news_events:
        top = news_events[0].get('title', '')
        html += f'<div class="snapshot-line"><span class="snapshot-label">焦點事件：</span>{top}</div>\n'

    html += '</div>\n'
    return html


# ==================== 指數表格 ====================

def _gen_index_table(indices_data):
    """生成單個區域的指數表格"""
    if not indices_data:
        return ""

    html = '<table>\n<thead><tr>'
    html += '<th>指數</th><th>收盤價</th><th>昨日漲跌</th><th>昨日漲跌幅</th><th>昨日趨勢</th><th>年初至今(%)</th>'
    html += '</tr></thead>\n<tbody>\n'

    for name, data in indices_data.items():
        cls = _change_class(data['change_pct'])
        ytd_pct = data.get('ytd_pct')
        ytd_cls = _change_class(ytd_pct) if ytd_pct is not None else 'flat'
        ytd_str = _format_pct(ytd_pct) if ytd_pct is not None else '<span class="flat">N/A</span>'
        html += '<tr>'
        html += f'<td class="name-cell">{name}</td>'
        html += f'<td>{data["current"]:,.2f}</td>'
        html += f'<td class="{cls}">{_format_change(data["change"])}</td>'
        html += f'<td class="{cls}">{_format_pct(data["change_pct"])}</td>'
        html += f'<td class="{cls}">{_trend_arrow(data["change_pct"])}</td>'
        html += f'<td>{ytd_str}</td>'
        html += '</tr>\n'

    html += '</tbody></table>\n'
    return html


def _gen_indices_section(market_data, index_analysis):
    """生成各國指數表現章節"""
    html = '<div class="section-title">一、各國指數表現</div>\n'

    regions = [
        ('亞洲市場', 'asia_indices', 'asia_analysis'),
        ('歐洲市場', 'europe_indices', 'europe_analysis'),
        ('美國市場', 'us_indices', 'us_analysis'),
    ]

    # 如果有新興市場數據，加入
    if market_data.get('emerging_indices'):
        regions.insert(1, ('新興市場', 'emerging_indices', 'emerging_analysis'))

    for region, key, analysis_key in regions:
        data = market_data.get(key, {})
        if data:
            html += f'<div class="sub-section-title">{region}</div>\n'
            if index_analysis and analysis_key in index_analysis:
                html += f'<p class="analysis-text">{index_analysis[analysis_key]}</p>\n'
            html += _gen_index_table(data)

    html += '<hr class="divider">\n'
    return html


# ==================== 宏觀新聞 ====================

def _gen_news_section(events):
    """生成宏觀重點新聞章節"""
    if not events:
        return ""

    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">二、宏觀重點新聞</div>\n'

    for i, event in enumerate(events, 1):
        impact = event.get('impact_level', '中')
        if impact == '高':
            badge_cls = 'badge-high'
            badge_text = '高影響'
        elif impact == '中':
            badge_cls = 'badge-medium'
            badge_text = '中影響'
        else:
            badge_cls = 'badge-low'
            badge_text = '低影響'

        direction = event.get('market_direction', '中性')
        if direction == '利多':
            dir_cls = 'badge-bullish'
            dir_text = '▲ 利多'
            border_color = '#27ae60'
        elif direction == '利空':
            dir_cls = 'badge-bearish'
            dir_text = '▼ 利空'
            border_color = '#e74c3c'
        else:
            dir_cls = 'badge-neutral'
            dir_text = '— 中性'
            border_color = '#3498db'

        affected = event.get('affected_markets', '')

        html += f'<div class="news-card" style="border-left-color:{border_color};">\n'
        html += f'<h3>{i}. {event.get("title", "")}</h3>\n'
        html += f'<div class="news-meta">'
        html += f'<span class="badge {badge_cls}">{badge_text}</span>'
        html += f'<span class="badge {dir_cls}">{dir_text}</span>'
        html += f'<span style="font-size:8pt;color:#999;">影響範圍：{affected}</span>'
        html += '</div>\n'
        html += f'<div class="news-body">{event.get("description", "")}</div>\n'

        tickers = event.get('related_tickers', [])
        ticker_impact = event.get('ticker_impact', {})
        if tickers:
            if ticker_impact:
                impact_parts = []
                for t in tickers:
                    impact_desc = ticker_impact.get(t, '')
                    if impact_desc:
                        impact_parts.append(f'<code>{t}</code> {impact_desc}')
                    else:
                        impact_parts.append(f'<code>{t}</code>')
                html += f'<div class="news-tickers">相關標的影響：{"；".join(impact_parts)}</div>\n'
            else:
                ticker_html = '、'.join([f'<code>{t}</code>' for t in tickers])
                html += f'<div class="news-tickers">相關標的：{ticker_html}</div>\n'

        html += '</div>\n'

    html += '<hr class="divider">\n'
    return html


# ==================== 商品、外匯、債券 ====================

def _gen_commodities_forex_bonds(market_data):
    """生成商品、外匯與債券章節"""
    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">三、商品、外匯與債券</div>\n'

    # 大宗商品
    commodities = market_data.get('commodities', {})
    if commodities:
        html += '<div class="sub-section-title">大宗商品</div>\n'
        html += '<table>\n<thead><tr>'
        html += '<th>商品</th><th>價格</th><th>漲跌</th><th>漲跌幅</th><th>趨勢</th>'
        html += '</tr></thead>\n<tbody>\n'
        for name, data in commodities.items():
            cls = _change_class(data['change_pct'])
            html += '<tr>'
            html += f'<td class="name-cell">{name}</td>'
            html += f'<td>${data["current"]:,.2f}</td>'
            html += f'<td class="{cls}">{_format_change(data["change"])}</td>'
            html += f'<td class="{cls}">{_format_pct(data["change_pct"])}</td>'
            html += f'<td class="{cls}">{_trend_arrow(data["change_pct"])}</td>'
            html += '</tr>\n'
        html += '</tbody></table>\n'

    # 外匯
    forex = market_data.get('forex', {})
    if forex:
        html += '<div class="sub-section-title">外匯市場</div>\n'
        html += '<table>\n<thead><tr>'
        html += '<th>貨幣對</th><th>匯率</th><th>漲跌</th><th>漲跌幅</th><th>趨勢</th>'
        html += '</tr></thead>\n<tbody>\n'
        for name, data in forex.items():
            cls = _change_class(data['change_pct'])
            html += '<tr>'
            html += f'<td class="name-cell">{name}</td>'
            html += f'<td>{data["current"]:.4f}</td>'
            html += f'<td class="{cls}">{_format_change4(data["change"])}</td>'
            html += f'<td class="{cls}">{_format_pct(data["change_pct"])}</td>'
            html += f'<td class="{cls}">{_trend_arrow(data["change_pct"])}</td>'
            html += '</tr>\n'
        html += '</tbody></table>\n'

    # 債券
    bonds = market_data.get('bonds', {})
    if bonds:
        html += '<div class="sub-section-title">債券殖利率</div>\n'
        html += '<table>\n<thead><tr>'
        html += '<th>債券</th><th>殖利率</th><th>變動</th><th>變動幅度</th><th>趨勢</th>'
        html += '</tr></thead>\n<tbody>\n'
        for name, data in bonds.items():
            cls = _change_class(data['change_pct'])
            html += '<tr>'
            html += f'<td class="name-cell">{name}</td>'
            html += f'<td>{data["current"]:.3f}%</td>'
            html += f'<td class="{cls}">{_format_change4(data["change"])}</td>'
            html += f'<td class="{cls}">{_format_pct(data["change_pct"])}</td>'
            html += f'<td class="{cls}">{_trend_arrow(data["change_pct"])}</td>'
            html += '</tr>\n'
        html += '</tbody></table>\n'

    html += '<hr class="divider">\n'
    return html


# ==================== 市場情緒指標 (NEW) ====================

def _gen_sentiment_section(sentiment_data, clock_data, sentiment_analysis=None):
    """生成市場情緒指標章節，包含 Fear & Greed、VIX、US10Y、DXY 和美林時鐘"""
    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">四、市場情緒指標</div>\n'

    if sentiment_analysis:
        html += f'<p class="analysis-text">{sentiment_analysis}</p>\n'

    fg = sentiment_data.get('fear_greed', {})
    vix = sentiment_data.get('vix', {})
    us10y = sentiment_data.get('us10y', {})
    dxy = sentiment_data.get('dxy', {})

    fg_score = fg.get('score', 50)
    fg_color = "#e74c3c" if fg_score < 25 else "#e67e22" if fg_score < 45 else "#f1c40f" if fg_score < 55 else "#27ae60"
    fg_rating_zh = "極度恐懼" if fg_score < 25 else "恐懼" if fg_score < 45 else "中性" if fg_score < 55 else "貪婪" if fg_score < 75 else "極度貪婪"

    vix_val = vix.get('value', 0)
    vix_change = vix.get('change', 0)
    vix_change_pct = vix.get('change_pct', 0)
    vix_color = "#e74c3c" if vix_val > 25 else "#e67e22" if vix_val > 20 else "#27ae60"

    us10y_yield = us10y.get('yield', 0)
    us10y_change = us10y.get('change', 0)
    dxy_val = dxy.get('value', 0)

    # Sentiment cards
    vix_cls = "down" if vix_change > 0 else "up"
    vix_sign = "+" if vix_change > 0 else ""
    us10y_cls = "up" if us10y_change > 0 else "down"
    us10y_sign = "+" if us10y_change > 0 else ""

    html += '<div class="sentiment-container">\n'
    html += f'''<div class="sentiment-card">
  <div class="label">CNN 恐懼與貪婪指數</div>
  <div class="value" style="color:{fg_color};">{fg_score:.1f}</div>
  <div class="sub" style="color:{fg_color}; font-weight:600;">{fg_rating_zh}</div>
</div>
<div class="sentiment-card">
  <div class="label">VIX 恐慌指數</div>
  <div class="value" style="color:{vix_color};">{vix_val:.2f}</div>
  <div class="sub {vix_cls}">{vix_sign}{vix_change:.2f} ({vix_sign}{vix_change_pct:.1f}%)</div>
</div>
<div class="sentiment-card">
  <div class="label">美10Y殖利率</div>
  <div class="value">{us10y_yield:.3f}%</div>
  <div class="sub {us10y_cls}">{us10y_sign}{us10y_change:.4f}</div>
</div>
<div class="sentiment-card">
  <div class="label">美元指數 DXY</div>
  <div class="value">{dxy_val:.2f}</div>
  <div class="sub">—</div>
</div>
'''
    html += '</div>\n'

    # Fear & Greed semicircle gauge (SVG)
    cx, cy = 150, 140
    R_out, R_in, R_lbl = 110, 75, 120

    def arc_pt(r, deg):
        rad = math.radians(deg)
        return cx + r * math.cos(rad), cy - r * math.sin(rad)

    angles = [180, 144, 108, 72, 36, 0]
    seg_colors = ['#c0392b', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60']
    seg_labels = ['極度恐懼', '恐懼', '中性', '貪婪', '極度貪婪']
    lbl_colors = ['#c0392b', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60']

    arc_paths = ''
    for i in range(5):
        a1, a2 = angles[i], angles[i+1]
        ox1, oy1 = arc_pt(R_out, a1)
        ox2, oy2 = arc_pt(R_out, a2)
        ix2, iy2 = arc_pt(R_in, a2)
        ix1, iy1 = arc_pt(R_in, a1)
        arc_paths += f'<path d="M {ox1:.1f} {oy1:.1f} A {R_out} {R_out} 0 0 1 {ox2:.1f} {oy2:.1f} L {ix2:.1f} {iy2:.1f} A {R_in} {R_in} 0 0 0 {ix1:.1f} {iy1:.1f} Z" fill="{seg_colors[i]}"/>\n'

    needle_deg = 180 - (fg_score / 100) * 180
    nx, ny = arc_pt(85, needle_deg)

    label_svg = ''
    mid_angles = [(angles[i] + angles[i+1]) / 2 for i in range(5)]
    for i, ma in enumerate(mid_angles):
        lx, ly = arc_pt(R_lbl + 8, ma)
        label_svg += f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle" font-size="6.5" fill="{lbl_colors[i]}">{seg_labels[i]}</text>\n'

    html += f'''<div style="margin-bottom:10px;">
  <div style="font-size:9pt; font-weight:600; margin-bottom:2px;">恐懼與貪婪指數</div>
  <div style="text-align:center;">
  <svg viewBox="0 0 300 170" width="320" height="180" style="display:block; margin:0 auto;">
    {arc_paths}
    <line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#2c3e50" stroke-width="2.5" stroke-linecap="round"/>
    <circle cx="{cx}" cy="{cy}" r="5" fill="#2c3e50"/>
    <text x="{cx}" y="{cy - 15}" text-anchor="middle" font-size="22" font-weight="800" fill="{fg_color}">{fg_score:.1f}</text>
    <text x="{cx}" y="{cy - 2}" text-anchor="middle" font-size="9" font-weight="600" fill="{fg_color}">{fg_rating_zh}</text>
    {label_svg}
  </svg>
  </div>
</div>
'''

    # Sentiment comparison table
    html += '<table><thead><tr><th>指標</th><th>當前</th><th>前日</th><th>一週前</th><th>一月前</th><th>一年前</th></tr></thead><tbody>\n'
    fg_prev = fg.get('previous_close', 0) or 0
    fg_1w = fg.get('previous_1_week', 0) or 0
    fg_1m = fg.get('previous_1_month', 0) or 0
    fg_1y = fg.get('previous_1_year', 0) or 0
    html += f'<tr><td class="name-cell">恐懼與貪婪</td><td class="down">{fg_score:.1f}</td><td>{fg_prev:.1f}</td><td>{fg_1w:.1f}</td><td>{fg_1m:.1f}</td><td>{fg_1y:.1f}</td></tr>\n'
    html += '</tbody></table>\n'

    # ─── Investment Clock (美林時鐘) ───
    if clock_data and clock_data.get('phase') != 'Unknown':
        html += _gen_investment_clock(clock_data)

    return html


def _gen_investment_clock(clock_data):
    """生成美林時鐘 SVG 和資訊面板"""
    html = '<div class="sub-section-title" style="margin-top:15px;">經濟週期指示器</div>\n'

    ck_phase = clock_data.get('phase', 'Unknown')
    ck_phase_cn = clock_data.get('phase_cn', '未知')
    ck_confidence = clock_data.get('confidence', '弱')
    ck_growth = clock_data.get('growth_direction', 'down')
    ck_inflation = clock_data.get('inflation_direction', 'up')
    ck_yield_10y = clock_data.get('yield_10y', 0)
    ck_yield_5y = clock_data.get('yield_5y', 0)
    ck_yield_slope = clock_data.get('yield_slope', 0)
    ck_oil = clock_data.get('oil_price', 0)

    phase_colors = {
        'Reflation': '#2980b9', 'Recovery': '#27ae60',
        'Overheat': '#e67e22', 'Stagflation': '#e74c3c'
    }
    phase_desc = {
        'Reflation': '經濟增長動能減弱且通脹壓力消退，央行政策傾向寬鬆以刺激經濟復甦，利率環境向下調整。',
        'Recovery': '經濟開始復甦但通脹仍維持低位，企業盈利逐步改善，產出缺口收窄，市場信心回升。',
        'Overheat': '經濟強勁增長伴隨通脹升溫，產出缺口擴大，實體需求旺盛推升商品價格，央行面臨緊縮壓力。',
        'Stagflation': '經濟增長動能減弱但通脹壓力仍然高企，市場面臨滯脹環境，企業成本上升而盈利增速放緩。'
    }
    colors_active = {
        'Recovery': '#27ae60', 'Overheat': '#e67e22',
        'Stagflation': '#e74c3c', 'Reflation': '#2980b9'
    }
    colors_light = {
        'Recovery': '#eafaf1', 'Overheat': '#fef5e7',
        'Stagflation': '#fdedec', 'Reflation': '#ebf5fb'
    }
    colors_mid = {
        'Recovery': '#a9dfbf', 'Overheat': '#f5cba7',
        'Stagflation': '#f5b7b1', 'Reflation': '#aed6f1'
    }

    ck_color = phase_colors.get(ck_phase, '#2c3e50')
    ck_desc = phase_desc.get(ck_phase, '')
    growth_arrow = '↑' if ck_growth == 'up' else '↓'
    inflation_arrow = '↑' if ck_inflation == 'up' else '↓'

    # SVG Investment Clock
    clock_cx, clock_cy = 160, 160
    clock_r = 115

    needle_angles = {
        'Recovery': 225, 'Overheat': 315,
        'Stagflation': 45, 'Reflation': 135,
    }

    clock_svg = ''

    # Defs for gradients
    clock_svg += '<defs>\n'
    for pname in ['Recovery', 'Overheat', 'Stagflation', 'Reflation']:
        clock_svg += f'  <radialGradient id="grad_{pname}" cx="50%" cy="50%" r="70%">\n'
        clock_svg += f'    <stop offset="0%" stop-color="{colors_mid[pname]}"/>\n'
        clock_svg += f'    <stop offset="100%" stop-color="{colors_light[pname]}"/>\n'
        clock_svg += f'  </radialGradient>\n'
        clock_svg += f'  <radialGradient id="grad_{pname}_active" cx="50%" cy="50%" r="70%">\n'
        clock_svg += f'    <stop offset="0%" stop-color="{colors_active[pname]}"/>\n'
        clock_svg += f'    <stop offset="100%" stop-color="{colors_mid[pname]}"/>\n'
        clock_svg += f'  </radialGradient>\n'
    clock_svg += '  <filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>\n'
    clock_svg += '  <filter id="needle-shadow" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="1" dy="1" stdDeviation="2" flood-opacity="0.3"/></filter>\n'
    clock_svg += '</defs>\n'

    # Outer dashed circle (no arrowhead)
    clock_svg += f'<circle cx="{clock_cx}" cy="{clock_cy}" r="{clock_r + 2}" fill="none" stroke="#dce1e6" stroke-width="1.5"/>\n'

    # Quadrant paths
    quad_data = [
        ('Recovery', f'M {clock_cx} {clock_cy} L {clock_cx - clock_r} {clock_cy} A {clock_r} {clock_r} 0 0 1 {clock_cx} {clock_cy - clock_r} Z'),
        ('Overheat', f'M {clock_cx} {clock_cy} L {clock_cx} {clock_cy - clock_r} A {clock_r} {clock_r} 0 0 1 {clock_cx + clock_r} {clock_cy} Z'),
        ('Stagflation', f'M {clock_cx} {clock_cy} L {clock_cx + clock_r} {clock_cy} A {clock_r} {clock_r} 0 0 1 {clock_cx} {clock_cy + clock_r} Z'),
        ('Reflation', f'M {clock_cx} {clock_cy} L {clock_cx} {clock_cy + clock_r} A {clock_r} {clock_r} 0 0 1 {clock_cx - clock_r} {clock_cy} Z'),
    ]

    for qname, qpath in quad_data:
        is_active = (qname == ck_phase)
        if is_active:
            fill = f'url(#grad_{qname}_active)'
            stroke_w = '2.5'
            stroke_c = colors_active[qname]
            filt = ' filter="url(#glow)"'
        else:
            fill = f'url(#grad_{qname})'
            stroke_w = '0.5'
            stroke_c = '#ccc'
            filt = ''
        clock_svg += f'<path d="{qpath}" fill="{fill}" stroke="{stroke_c}" stroke-width="{stroke_w}"{filt}/>\n'

    # Cross axis lines
    clock_svg += f'<line x1="{clock_cx - clock_r}" y1="{clock_cy}" x2="{clock_cx + clock_r}" y2="{clock_cy}" stroke="#fff" stroke-width="2"/>\n'
    clock_svg += f'<line x1="{clock_cx}" y1="{clock_cy - clock_r}" x2="{clock_cx}" y2="{clock_cy + clock_r}" stroke="#fff" stroke-width="2"/>\n'

    # Quadrant labels
    label_positions = [
        ('Recovery', '復甦期', clock_cx - 55, clock_cy - 35),
        ('Overheat', '過熱期', clock_cx + 55, clock_cy - 35),
        ('Stagflation', '滯脹期', clock_cx + 55, clock_cy + 42),
        ('Reflation', '衰退期', clock_cx - 55, clock_cy + 42),
    ]

    for qname, qlabel, lx, ly in label_positions:
        is_active = (qname == ck_phase)
        fw = '800' if is_active else '500'
        fc = '#fff' if is_active else '#666'
        fs = '13' if is_active else '10'
        clock_svg += f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="{fs}" font-weight="{fw}" fill="{fc}">{qlabel}</text>\n'

    # Axis labels OUTSIDE circle
    arrow_y_top = clock_cy - clock_r - 12
    arrow_y_bot = clock_cy + clock_r + 20
    arrow_x_left = clock_cx - clock_r - 30
    arrow_x_right = clock_cx + clock_r + 30
    clock_svg += f'<text x="{clock_cx}" y="{arrow_y_top}" text-anchor="middle" font-size="9" fill="#e74c3c" font-weight="600">通脹上升 →</text>\n'
    clock_svg += f'<text x="{clock_cx}" y="{arrow_y_bot}" text-anchor="middle" font-size="9" fill="#2980b9" font-weight="600">← 通脹下降</text>\n'
    clock_svg += f'<text x="{arrow_x_left}" y="{clock_cy + 4}" text-anchor="middle" font-size="9" fill="#27ae60" font-weight="600">↑</text>\n'
    clock_svg += f'<text x="{arrow_x_left}" y="{clock_cy + 16}" text-anchor="middle" font-size="8" fill="#27ae60" font-weight="600">增長</text>\n'
    clock_svg += f'<text x="{arrow_x_right}" y="{clock_cy + 4}" text-anchor="middle" font-size="9" fill="#e67e22" font-weight="600">↓</text>\n'
    clock_svg += f'<text x="{arrow_x_right}" y="{clock_cy + 16}" text-anchor="middle" font-size="8" fill="#e67e22" font-weight="600">放緩</text>\n'

    # Needle
    needle_angle_deg = needle_angles.get(ck_phase, 45)
    needle_angle_rad = math.radians(needle_angle_deg)
    needle_len = clock_r * 0.7
    needle_tip_x = clock_cx + needle_len * math.cos(needle_angle_rad)
    needle_tip_y = clock_cy + needle_len * math.sin(needle_angle_rad)
    needle_base_w = 6
    perp_angle = needle_angle_rad + math.pi / 2
    nb1_x = clock_cx + needle_base_w * math.cos(perp_angle)
    nb1_y = clock_cy + needle_base_w * math.sin(perp_angle)
    nb2_x = clock_cx - needle_base_w * math.cos(perp_angle)
    nb2_y = clock_cy - needle_base_w * math.sin(perp_angle)
    clock_svg += f'<polygon points="{needle_tip_x:.1f},{needle_tip_y:.1f} {nb1_x:.1f},{nb1_y:.1f} {nb2_x:.1f},{nb2_y:.1f}" fill="{ck_color}" stroke="#fff" stroke-width="0.5" filter="url(#needle-shadow)"/>\n'

    # Center dot
    clock_svg += f'<circle cx="{clock_cx}" cy="{clock_cy}" r="6" fill="#2c3e50" stroke="#fff" stroke-width="2"/>\n'

    # Dashed arc outside (no arrowhead)
    clock_svg += f'<path d="M {clock_cx + 8} {clock_cy - clock_r - 5} A {clock_r + 6} {clock_r + 6} 0 1 1 {clock_cx - 8} {clock_cy - clock_r - 5}" fill="none" stroke="#bdc3c7" stroke-width="1.2" stroke-dasharray="4,3"/>\n'

    growth_ind = clock_data.get('growth_indicator', '10Y-5Y殖利率利差 20日MA斜率')
    inflation_ind = clock_data.get('inflation_indicator', 'TIP/IEF比率 20日MA斜率（隱含通脹預期）')

    html += f'''<div class="clock-wrapper">
  <div class="clock-svg-box">
    <svg viewBox="0 0 340 340" width="300" height="300">
      {clock_svg}
    </svg>
  </div>
  <div class="clock-info-box">
    <div class="clock-phase-title" style="color:{ck_color};">{ck_phase_cn}（{ck_phase}）</div>
    <div class="clock-phase-sub">
      增長方向：{growth_arrow} ｜ 通脹方向：{inflation_arrow} ｜ 信號強度：{ck_confidence}
    </div>
    <div class="clock-phase-sub">{ck_desc}</div>
    <div class="clock-indicator-row">
      <div class="clock-ind-card">
        <div class="ind-label">10Y殖利率</div>
        <div class="ind-value">{ck_yield_10y:.3f}%</div>
      </div>
      <div class="clock-ind-card">
        <div class="ind-label">5Y殖利率</div>
        <div class="ind-value">{ck_yield_5y:.3f}%</div>
      </div>
      <div class="clock-ind-card">
        <div class="ind-label">10Y-5Y利差</div>
        <div class="ind-value">{ck_yield_slope:.3f}</div>
      </div>
      <div class="clock-ind-card">
        <div class="ind-label">原油</div>
        <div class="ind-value">${ck_oil:.1f}</div>
      </div>
    </div>
    <div style="font-size:7pt; color:#95a5a6; margin-top:4px;">判斷依據：{growth_ind}（增長）+ {inflation_ind}（通脹）</div>
  </div>
</div>
'''
    return html


# ==================== 全球資金流向 (NEW) ====================

def _gen_fund_flow_section(fund_flows, flow_analysis=None):
    """生成全球資金流向脈動章節"""
    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">五、全球資金流向脈動</div>\n'

    if flow_analysis:
        html += f'<p class="analysis-text">{flow_analysis}</p>\n'

    html += '<div class="sub-section-title">各國/地區資金流向（基於ETF CMF×成交量）</div>\n'

    # Collect all country + extra flows
    country_flows = fund_flows.get('country', {})
    extra_flows = fund_flows.get('extra', {})

    all_flows = []
    for sym, d in country_flows.items():
        all_flows.append((d.get('name', sym), sym, d.get('1d', 0), d.get('5d', 0), d.get('1m', 0), d.get('ytd', 0)))
    for sym, d in extra_flows.items():
        all_flows.append((d.get('name', sym), sym, d.get('1d', 0), d.get('5d', 0), d.get('1m', 0), d.get('ytd', 0)))

    if not all_flows:
        html += '<p class="analysis-text">資金流向數據暫無。</p>\n'
        return html

    # Max values for bar scaling
    def get_max_abs(data, idx):
        vals = [abs(r[idx]) for r in data if r[idx] is not None]
        return max(vals) if vals else 1

    max_vals = {i: get_max_abs(all_flows, i) for i in [2, 3, 4, 5]}

    html += '<table><thead><tr><th>國家/地區</th><th>ETF</th><th>當日</th><th>近一週</th><th>近一月</th><th>年初至今</th></tr></thead><tbody>\n'
    for name, sym, v1d, v5d, v1m, vytd in all_flows:
        html += f'<tr><td class="name-cell">{name}</td><td>{sym}</td>'
        html += _flow_cell(v1d, max_vals[2])
        html += _flow_cell(v5d, max_vals[3])
        html += _flow_cell(v1m, max_vals[4])
        html += _flow_cell(vytd, max_vals[5])
        html += '</tr>\n'
    html += '</tbody></table>\n'

    return html


# ==================== GICS 板塊資金流向 (NEW) ====================

def _gen_gics_sector_section(fund_flows, sector_analysis=None):
    """生成 GICS 11大板塊資金流向章節"""
    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">六、GICS 11大板塊資金流向</div>\n'

    if sector_analysis:
        html += f'<p class="analysis-text">{sector_analysis}</p>\n'

    sector_flows = fund_flows.get('sector', {})
    if not sector_flows:
        html += '<p class="analysis-text">板塊資金流向數據暫無。</p>\n'
        return html

    sorted_sectors = sorted(sector_flows.items(), key=lambda x: x[1].get('1d', 0))
    sector_data = [(d.get('name', sym), sym, d.get('1d', 0), d.get('5d', 0), d.get('1m', 0), d.get('ytd', 0)) for sym, d in sorted_sectors]

    def get_max_abs(data, idx):
        vals = [abs(r[idx]) for r in data if r[idx] is not None]
        return max(vals) if vals else 1

    max_sec = {i: get_max_abs(sector_data, i) for i in [2, 3, 4, 5]}

    html += '<table><thead><tr><th>板塊</th><th>ETF</th><th>當日</th><th>近一週</th><th>近一月</th><th>年初至今</th></tr></thead><tbody>\n'
    for name, sym, v1d, v5d, v1m, vytd in sector_data:
        html += f'<tr><td class="name-cell">{name}</td><td>{sym}</td>'
        html += _flow_cell(v1d, max_sec[2])
        html += _flow_cell(v5d, max_sec[3])
        html += _flow_cell(v1m, max_sec[4])
        html += _flow_cell(vytd, max_sec[5])
        html += '</tr>\n'
    html += '</tbody></table>\n'

    # Bond market flows
    bond_flows = fund_flows.get('bond', {})
    if bond_flows:
        html += '<div class="sub-section-title">債券市場資金流向</div>\n'
        bond_data = [(d.get('name', sym), sym, d.get('1d', 0), d.get('5d', 0), d.get('1m', 0), d.get('ytd', 0)) for sym, d in bond_flows.items()]
        max_bond = {i: get_max_abs(bond_data, i) for i in [2, 3, 4, 5]}

        html += '<table class="bond-flow-table"><thead><tr><th>債券類型</th><th>ETF</th><th>當日</th><th>近一週</th><th>近一月</th><th>年初至今</th></tr></thead><tbody>\n'
        for name, sym, v1d, v5d, v1m, vytd in bond_data:
            html += f'<tr><td class="name-cell">{name}</td><td>{sym}</td>'
            html += _flow_cell(v1d, max_bond[2])
            html += _flow_cell(v5d, max_bond[3])
            html += _flow_cell(v1m, max_bond[4])
            html += _flow_cell(vytd, max_bond[5])
            html += '</tr>\n'
        html += '</tbody></table>\n'

    return html


# ==================== 熱門股票 ====================

def _gen_stock_table_html(stocks, stock_analysis):
    """渲染一組股票的 HTML 表格"""
    if not stocks:
        return ""
    html = '<table>\n<thead><tr>'
    html += '<th>股票</th><th>代碼</th><th>收盤價</th><th>漲跌幅</th><th>量比</th><th>分析</th>'
    html += '</tr></thead>\n<tbody>\n'
    for s in stocks:
        full_symbol = s['symbol']
        symbol_base = full_symbol.split('.')[0]
        analysis = ""
        if stock_analysis:
            analysis = stock_analysis.get(full_symbol, stock_analysis.get(symbol_base, ''))
        name = s['name']
        if len(name) > 50:
            name = name[:48] + "..."
        vol_ratio = s.get('volume_ratio', 1)
        cls = _change_class(s.get('change_pct', 0))
        html += '<tr>'
        html += f'<td class="name-cell">{name}</td>'
        html += f'<td><code style="font-size:8pt;">{s["symbol"]}</code></td>'
        html += f'<td>{s["current"]:,.2f}</td>'
        html += f'<td class="{cls}">{_format_pct(s["change_pct"])}</td>'
        html += f'<td>{vol_ratio:.1f}x</td>'
        html += f'<td class="stock-analysis">{analysis}</td>'
        html += '</tr>\n'
    html += '</tbody></table>\n'
    return html


def _extract_stocks_html(market_data):
    """從 v2 格式的 market_data 中提取 inflow 和 outflow 列表"""
    if isinstance(market_data, dict) and 'inflow' in market_data:
        return market_data.get('inflow', []), market_data.get('outflow', [])
    elif isinstance(market_data, list):
        inflow = [s for s in market_data if s.get('flow') == 'inflow']
        outflow = [s for s in market_data if s.get('flow') == 'outflow']
        return inflow, outflow
    return [], []


def _gen_hot_stocks_section(hot_stocks, stock_analysis):
    """生成當日熱門股票章節"""
    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">七、當日熱門股票</div>\n'
    html += '<div class="filter-note">篩選邏輯：資金追捧（量比 ≥ 1.5x + 上漲）；資金出清（量比 ≥ 2.5x + 下跌）<br/>'
    html += '排序方式：量比門檻（硬篩）→ 漲跌幅排序 → 新聞提及加分 | 每市場最多 5 支買入 + 5 支賣出</div>\n'

    for market in ['美股', '港股', '日股', '台股']:
        if market not in hot_stocks or not hot_stocks[market]:
            continue

        inflow, outflow = _extract_stocks_html(hot_stocks[market])

        if not inflow and not outflow:
            continue

        html += f'<div class="sub-section-title">{market}</div>\n'

        if inflow:
            html += '<p class="hot-label buy">🔥 資金追捧（買入放量 ≥ 1.5x + 上漲）</p>\n'
            html += _gen_stock_table_html(inflow, stock_analysis)

        if outflow:
            html += '<p class="hot-label sell">⚠️ 資金出清（賣出放量 ≥ 2.5x + 下跌）</p>\n'
            html += _gen_stock_table_html(outflow, stock_analysis)

    html += '<hr class="divider">\n'
    return html


# ==================== 加密貨幣 ====================

def _gen_crypto_section(crypto_data):
    """生成加密貨幣市場章節"""
    if not crypto_data:
        return ""

    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">八、加密貨幣市場</div>\n'
    html += '<table>\n<thead><tr>'
    html += '<th>幣種</th><th>價格（USD）</th><th>24h 漲跌</th><th>漲跌幅</th><th>趨勢</th>'
    html += '</tr></thead>\n<tbody>\n'

    for name, data in crypto_data.items():
        cls = _change_class(data['change_pct'])
        html += '<tr>'
        html += f'<td class="name-cell">{name}</td>'
        html += f'<td>${data["current"]:,.2f}</td>'
        html += f'<td class="{cls}">{_format_change(data["change"])}</td>'
        html += f'<td class="{cls}">{_format_pct(data["change_pct"])}</td>'
        html += f'<td class="{cls}">{_trend_arrow(data["change_pct"])}</td>'
        html += '</tr>\n'

    html += '</tbody></table>\n'
    html += '<hr class="divider">\n'
    return html


# ==================== 經濟日曆 ====================

def _gen_calendar_section(calendar_events):
    """生成經濟日曆提示章節"""
    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">九、本週經濟日曆</div>\n'

    if not calendar_events:
        html += '<p class="analysis-text">本週暫無重大經濟數據發布。</p>\n'
        return html

    html += '<p class="analysis-text" style="color:#999;font-style:italic;">以下為本週需要關注的重要經濟數據與事件</p>\n'

    html += '<table>\n<thead><tr>'
    html += '<th>日期</th><th>國家/地區</th><th>事件</th><th>重要性</th><th>預期影響</th>'
    html += '</tr></thead>\n<tbody>\n'

    for event in calendar_events:
        importance = event.get('importance', '★')
        if '★★★' in importance:
            imp_style = 'color:#c0392b;font-weight:700;'
        elif '★★' in importance:
            imp_style = 'color:#d4a017;font-weight:600;'
        else:
            imp_style = 'color:#999;'

        desc = event.get('description', '')

        html += '<tr>'
        html += f'<td>{event.get("date", "")}</td>'
        html += f'<td>{event.get("country", "")}</td>'
        html += f'<td class="name-cell">{event.get("event", "")}</td>'
        html += f'<td style="{imp_style}">{importance}</td>'
        html += f'<td style="font-size:9pt;color:#666;text-align:left;line-height:1.4;">{desc}</td>'
        html += '</tr>\n'

    html += '</tbody></table>\n'

    # 重點關注事件
    high_importance = [e for e in calendar_events if '★★★' in e.get('importance', '')]
    if high_importance:
        html += '<div class="sub-section-title">重點關注</div>\n'
        for event in high_importance:
            html += '<div class="calendar-highlight">\n'
            html += f'<strong>{event.get("event", "")}</strong>（{event.get("country", "")}，{event.get("date", "")}）<br>\n'
            html += f'<span style="font-size:10pt;color:#555;">{event.get("description", "")}</span>\n'
            if event.get('consensus'):
                html += f'<br><span style="font-size:10pt;color:#2c3e50;">市場預期：{event["consensus"]}</span>\n'
            html += '</div>\n'

    return html


# ==================== 主函數 ====================

def generate_html_report(market_data, news_events, hot_stocks, stock_analysis,
                         index_analysis, calendar_events, report_date,
                         sentiment_data=None, clock_data=None, fund_flows=None,
                         sentiment_analysis=None, flow_analysis=None, sector_analysis=None):
    """
    生成完整的 HTML 報告 v2
    新增參數：
    - sentiment_data: 市場情緒數據（Fear & Greed, VIX, US10Y, DXY）
    - clock_data: 美林時鐘數據
    - fund_flows: 全球資金流向數據（country, sector, bond, extra）
    - sentiment_analysis: AI 生成的情緒分析文字
    - flow_analysis: AI 生成的資金流向分析文字
    - sector_analysis: AI 生成的板塊分析文字
    """

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>每日宏觀資訊綜合早報 | {report_date}</title>
<style>
{REPORT_CSS}
</style>
</head>
<body>

<div class="report-header">
    <h1>每日宏觀資訊綜合早報</h1>
    <div class="subtitle">Daily Macro Market Briefing</div>
    <div class="date-line">{report_date} ｜ 綜合早報</div>
</div>
<div class="header-divider"></div>

"""

    # 市場速覽
    html += _gen_snapshot(market_data, news_events)

    # 一、各國指數表現
    html += _gen_indices_section(market_data, index_analysis)

    # 二、宏觀重點新聞
    html += _gen_news_section(news_events)

    # 三、商品、外匯與債券
    html += _gen_commodities_forex_bonds(market_data)

    # 四、市場情緒指標 (NEW)
    if sentiment_data and clock_data:
        html += _gen_sentiment_section(sentiment_data, clock_data, sentiment_analysis)

    # 五、全球資金流向脈動 (NEW)
    if fund_flows:
        html += _gen_fund_flow_section(fund_flows, flow_analysis)

    # 六、GICS 板塊資金流向 (NEW)
    if fund_flows:
        html += _gen_gics_sector_section(fund_flows, sector_analysis)

    # 七、當日熱門股票
    html += _gen_hot_stocks_section(hot_stocks, stock_analysis)

    # 八、加密貨幣市場
    html += _gen_crypto_section(market_data.get('crypto', {}))

    # 九、經濟日曆提示
    html += _gen_calendar_section(calendar_events)

    # 底部
    html += f"""
<div class="footer" style="line-height:1.6;">
    <strong style="font-size:8.5pt; color:#2c3e50;">何宣逸</strong><br>
    <span>副總裁 ｜ 私人財富管理部</span><br>
    <span>華泰金融控股（香港）有限公司</span><br>
    <span>電話：+852 3658 6180 ｜ 手機：+852 6765 0336 / +86 130 0329 5233</span><br>
    <span>電郵：jamieho@htsc.com</span><br>
    <span>地址：香港皇后大道中99號中環中心69樓</span><br>
    <span style="font-size:6.5pt; color:#aaa;">華泰證券股份有限公司全資附屬公司 (SSE: 601688; SEHK: 6886; LSE: HTSC)</span>
</div>

<div class="footer" style="margin-top:10px; padding-top:8px; border-top:1px solid #ddd;">
    <strong>報告製作時間</strong>：{datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC+8)<br>
    <strong>資料來源</strong>：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com、CNN Fear &amp; Greed Index<br>
    資金流向數據基於ETF Chaikin Money Flow (CMF) × 成交量計算<br><br>
    <em>本報告僅供參考，不構成任何投資建議。投資有風險，入市需謹慎。</em>
</div>

</body>
</html>
"""

    return html
