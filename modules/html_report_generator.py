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
    padding: 10px 14px;
    margin: 8px 0;
    font-size: 9.5pt;
    line-height: 1.6;
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
    margin: 10px 0 3px;
    padding-bottom: 4px;
    border-bottom: 2.5px solid #e67e22;
    page-break-after: avoid;
}

.sub-section-title {
    font-size: 12pt;
    font-weight: 700;
    color: #2c3e50;
    margin: 8px 0 3px;
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
    margin-bottom: 6px;
    font-size: 9.5pt;
}

table thead th {
    background: #f1f3f5;
    color: #2c3e50;
    font-weight: 700;
    padding: 6px 8px;
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

/* 表格允許跨頁（大表格 avoid 會造成整頁空白） */
table {
    page-break-inside: auto;
}

thead {
    display: table-header-group;
}

/* 小型子區塊防切斷（大區塊不要用這個 class） */
.sub-section-block {
    page-break-inside: avoid;
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

/* ===== 底部（名片+聲明不分頁）===== */
.footer-wrapper {
    page-break-inside: avoid;
    margin-top: 20px;
}
.footer {
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid #ddd;
    font-size: 7.5pt;
    color: #95a5a6;
    text-align: left;
}

.footer strong {
    color: #666;
}

/* ===== 頁面控制 ===== */
@page {
    margin: 15mm;
    @top-left { content: ''; }
    @top-right { content: ''; }
    @bottom-left { content: ''; }
    @bottom-right { content: ''; }
}
.page-break {
    page-break-before: always;
}

.section-new-page {
    page-break-before: auto;
    margin-top: 4px;
}

/* ===== 情緒指標卡片 ===== */
.sentiment-container {
    display: flex;
    gap: 8px;
    margin-bottom: 6px;
}
.sentiment-card {
    flex: 1;
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    padding: 6px;
    text-align: center;
}
.sentiment-card .label {
    font-size: 7.5pt;
    color: #7f8c8d;
    margin-bottom: 2px;
}
.sentiment-card .value {
    font-size: 18pt;
    font-weight: 800;
}
.sentiment-card .sub {
    font-size: 7.5pt;
    margin-top: 1px;
}

/* ===== 美林時鐘 ===== */
.clock-wrapper {
    display: flex;
    gap: 16px;
    align-items: center;
    margin: 8px 0;
    padding: 10px;
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

def _is_valid_number(val):
    """檢查值是否為有效數字（非 None、非 NaN、非 inf）"""
    import math
    if val is None:
        return False
    try:
        return not (math.isnan(float(val)) or math.isinf(float(val)))
    except (TypeError, ValueError):
        return False


def _gen_index_table(indices_data):
    """生成單個區域的指數表格"""
    if not indices_data:
        return ""

    html = '<table>\n<thead><tr>'
    html += '<th>指數</th><th>收盤價</th><th>昨日漲跌</th><th>昨日漲跌幅</th><th>昨日趨勢</th><th>年初至今(%)</th>'
    html += '</tr></thead>\n<tbody>\n'

    for name, data in indices_data.items():
        # 檢查數據是否有效（非 NaN）
        current = data.get('current')
        if not _is_valid_number(current):
            # 數據無效 → 顯示「休市」
            html += '<tr>'
            html += f'<td class="name-cell">{name}</td>'
            html += '<td colspan="5" style="text-align:center;color:#999;font-style:italic;">休市</td>'
            html += '</tr>\n'
            continue

        cls = _change_class(data['change_pct'])
        ytd_pct = data.get('ytd_pct')
        ytd_str = _format_pct(ytd_pct) if _is_valid_number(ytd_pct) else '<span class="flat">N/A</span>'
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
    html = '<div class="section-title">二、全球指數表現</div>\n'

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
            html += '<div class="sub-section-block">\n'
            html += f'<div class="sub-section-title">{region}</div>\n'
            if index_analysis and analysis_key in index_analysis:
                html += f'<p class="analysis-text">{index_analysis[analysis_key]}</p>\n'
            html += _gen_index_table(data)
            html += '</div>\n'

    html += '<hr class="divider">\n'
    return html


# ==================== 宏觀新聞 ====================

def _gen_news_section(events):
    """生成宏觀重點新聞

    每組新聞三層結構：
    1. 敘事摘要（narrative）— 讀完就知道發生什麼事
    2. 重點標題（headlines）— 各個面向的具體報導
    3. 數據佐證（data_points）— 市場如何反應
    """
    if not events:
        return ""

    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">一、宏觀重點新聞</div>\n'

    headlines = [e for e in events if e.get('is_headline', False)]
    briefs = [e for e in events if not e.get('is_headline', False)]

    # === 頭條主題（詳細版）===
    for i, event in enumerate(headlines, 1):
        direction = event.get('market_direction', '中性')
        impact = event.get('impact_level', '中')

        # 顏色
        colors = {
            '利空': ('#e74c3c', '#e74c3c', '▼ 利空'),
            '利多': ('#27ae60', '#27ae60', '▲ 利多'),
            '中性': ('#3498db', '#7f8c8d', '— 中性'),
        }
        border_color, dir_bg, dir_label = colors.get(direction, colors['中性'])
        impact_bg = '#c0392b' if impact == '高' else '#e67e22' if impact == '中' else '#95a5a6'

        html += f'<div style="border-left:5px solid {border_color};padding:12px 16px;margin:8px 0;background:#fafbfc;border-radius:0 6px 6px 0;">\n'

        # 標題行 + badges
        title = event.get('title', '')
        html += f'<div style="margin-bottom:8px;">'
        html += f'<span style="font-size:14pt;font-weight:800;color:#1a1a2e;">{i}. {title}</span> '
        html += f'<span style="background:{impact_bg};color:#fff;padding:2px 8px;border-radius:3px;font-size:7.5pt;font-weight:700;">{impact}影響</span> '
        html += f'<span style="background:{dir_bg};color:#fff;padding:2px 8px;border-radius:3px;font-size:7.5pt;font-weight:700;">{dir_label}</span>'
        html += f'</div>\n'
        html += f'<div style="font-size:8pt;color:#999;margin-bottom:12px;">{event.get("source_info", "")} ｜ 影響範圍：{event.get("affected_markets", "")}</div>\n'

        # 敘事摘要
        narrative = event.get('narrative', '')
        if narrative:
            html += f'<div style="font-size:10pt;line-height:1.8;color:#2c3e50;margin-bottom:10px;padding:10px 14px;background:#fff;border-radius:4px;border:1px solid #eee;">{narrative}</div>\n'

        # 重點標題 + 數據條 並排佈局
        news_headlines = event.get('headlines', [])
        data_pts = event.get('data_points', [])
        tickers = event.get('related_tickers', [])

        if news_headlines or data_pts:
            html += '<div style="display:flex;gap:16px;flex-wrap:wrap;">\n'

            # 左側：重點標題
            if news_headlines:
                html += '<div style="flex:1;min-width:280px;">\n'
                html += '<div style="font-size:8pt;font-weight:700;color:#95a5a6;margin-bottom:4px;letter-spacing:0.5px;">HEADLINES</div>\n'
                for h in news_headlines[:4]:
                    html += f'<div style="font-size:9.5pt;line-height:1.6;color:#34495e;padding:2px 0 2px 12px;border-left:2px solid {border_color}40;margin:3px 0;">• {h}</div>\n'
                html += '</div>\n'

            # 右側：數據（不顯示股票代碼標籤）
            if data_pts:
                html += '<div style="min-width:180px;">\n'
                html += '<div style="font-size:8pt;font-weight:700;color:#95a5a6;margin-bottom:4px;letter-spacing:0.5px;">MARKET DATA</div>\n'
                html += '<div style="background:#f0f4f8;padding:8px 12px;border-radius:4px;font-size:9.5pt;line-height:1.8;">'
                for dp in data_pts:
                    html += f'<div><strong>{dp}</strong></div>'
                html += '</div>\n'
                html += '</div>\n'

            html += '</div>\n'

        html += '</div>\n'

    # === 其他要聞（卡片式，跟頭條統一風格）===
    if briefs:
        html += '<div style="margin:24px 0 12px 0;font-size:12pt;font-weight:700;color:#1a1a2e;border-bottom:2.5px solid #2c3e50;padding-bottom:6px;">其他要聞</div>\n'
        for event in briefs:
            direction = event.get('market_direction', '中性')
            colors = {
                '利空': ('#e74c3c', '#e74c3c', '▼ 利空'),
                '利多': ('#27ae60', '#27ae60', '▲ 利多'),
                '中性': ('#95a5a6', '#7f8c8d', '— 中性'),
            }
            border_color, dir_bg, dir_label = colors.get(direction, colors['中性'])
            title = event.get('title', '')
            narrative = event.get('narrative', '')
            news_headlines = event.get('headlines', [])

            html += f'<div style="border-left:4px solid {border_color};padding:12px 16px;margin:10px 0;background:#fafbfc;border-radius:0 6px 6px 0;page-break-inside:avoid;">\n'

            # 標題行
            html += f'<div style="margin-bottom:6px;">'
            html += f'<strong style="font-size:11pt;color:#1a1a2e;">{title}</strong> '
            html += f'<span style="background:{dir_bg};color:#fff;padding:1px 6px;border-radius:3px;font-size:7pt;font-weight:700;">{dir_label}</span> '
            html += f'<span style="font-size:7.5pt;color:#aaa;">{event.get("source_info", "")}</span>'
            html += '</div>\n'

            # 敘事（完整顯示，不截斷）
            if narrative:
                html += f'<div style="font-size:9.5pt;color:#444;line-height:1.7;margin-bottom:6px;">{narrative}</div>\n'

            # 重點標題（最多2條）
            if news_headlines:
                for h in news_headlines[:2]:
                    html += f'<div style="font-size:9pt;color:#555;padding-left:12px;border-left:2px solid {border_color}33;line-height:1.6;margin:2px 0;">• {h}</div>\n'

            # 數據條
            data_pts = event.get('data_points', [])
            if data_pts:
                dp_html = '&nbsp;&nbsp;｜&nbsp;&nbsp;'.join([f'<strong>{dp}</strong>' for dp in data_pts[:3]])
                html += f'<div style="font-size:8.5pt;color:#2980b9;margin-top:6px;">{dp_html}</div>\n'

            html += '</div>\n'

    html += '<hr class="divider">\n'
    return html


# ==================== 債券・殖利率 ====================

def _gen_bonds_section(market_data):
    """生成債券殖利率章節"""
    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">三、債券・殖利率</div>\n'
    bonds = market_data.get('bonds', {})
    if bonds:
        html += '<div class="sub-section-block">\n'
        html += '<table>\n<thead><tr>'
        html += '<th>債券</th><th>殖利率</th><th>變動</th><th>變動幅度</th><th>趨勢</th>'
        html += '</tr></thead>\n<tbody>\n'
        for name, data in bonds.items():
            cls = _change_class(data['change_pct'])
            html += f'<tr><td class="name-cell">{name}</td><td>{data["current"]:.3f}%</td><td class="{cls}">{_format_change4(data["change"])}</td><td class="{cls}">{_format_pct(data["change_pct"])}</td><td class="{cls}">{_trend_arrow(data["change_pct"])}</td></tr>\n'
        html += '</tbody></table>\n</div>\n'
    return html


# ==================== 外匯市場 ====================

def _gen_forex_section(market_data):
    """生成外匯市場章節"""
    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">四、外匯市場</div>\n'
    forex = market_data.get('forex', {})
    if forex:
        html += '<div class="sub-section-block">\n'
        html += '<div class="sub-section-title">主要貨幣對</div>\n'
        html += '<table>\n<thead><tr>'
        html += '<th>貨幣對</th><th>匯率</th><th>漲跌</th><th>漲跌幅</th><th>趨勢</th>'
        html += '</tr></thead>\n<tbody>\n'
        for name, data in forex.items():
            cls = _change_class(data['change_pct'])
            html += f'<tr><td class="name-cell">{name}</td><td>{data["current"]:.4f}</td><td class="{cls}">{_format_change4(data["change"])}</td><td class="{cls}">{_format_pct(data["change_pct"])}</td><td class="{cls}">{_trend_arrow(data["change_pct"])}</td></tr>\n'
        html += '</tbody></table>\n</div>\n'
    return html


# ==================== 大宗商品 ====================

def _gen_commodities_section(market_data):
    """生成大宗商品章節"""
    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">五、大宗商品</div>\n'
    commodities = market_data.get('commodities', {})
    if commodities:
        html += '<div class="sub-section-block">\n'
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
        html += '</div>\n'
    return html


# ==================== 恐懼與貪婪儀表盤 ====================

def _gen_fear_greed_gauge(score, rating_zh, color):
    """生成平滑彩虹漸層半圓儀表盤 SVG"""
    import math

    cx, cy = 200, 158
    r = 110
    arc_w = 28

    # 彩虹色標：紅→橙→黃→綠（用 50 個小段模擬平滑漸層）
    color_stops = [
        (0.00, (183, 28, 28)),    # 深紅
        (0.20, (229, 57, 53)),    # 紅
        (0.40, (239, 108, 0)),    # 橙
        (0.50, (249, 168, 37)),   # 黃橙
        (0.60, (253, 216, 53)),   # 黃
        (0.75, (124, 179, 66)),   # 淺綠
        (1.00, (46, 125, 50)),    # 深綠
    ]

    def interp_color(t):
        """在色標之間線性插值"""
        for i in range(len(color_stops) - 1):
            t0, c0 = color_stops[i]
            t1, c1 = color_stops[i + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0)
                return tuple(int(c0[j] + f * (c1[j] - c0[j])) for j in range(3))
        return color_stops[-1][1]

    labels = [
        (0,   '極度恐懼', 'end'),
        (20,  '恐懼', 'end'),
        (45,  '沮喪', 'middle'),
        (55,  '中性', 'middle'),
        (80,  '貪婪', 'start'),
        (100, '極度貪婪', 'start'),
    ]

    svg = '<svg viewBox="0 0 400 230" width="260" height="150" style="display:block;margin:0 auto;">\n'
    svg += '<defs><filter id="ns" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000" flood-opacity="0.15"/></filter></defs>\n'

    # 底部灰色軌道
    svg += f'<path d="M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy}" fill="none" stroke="#f0f0f0" stroke-width="{arc_w + 6}" stroke-linecap="round"/>\n'

    # 平滑彩虹弧線（50 小段）
    n_seg = 50
    for i in range(n_seg):
        t0 = i / n_seg
        t1 = (i + 1) / n_seg
        a0 = math.radians(180 - t0 * 180)
        a1 = math.radians(180 - t1 * 180)
        x0 = cx + r * math.cos(a0)
        y0 = cy - r * math.sin(a0)
        x1 = cx + r * math.cos(a1)
        y1 = cy - r * math.sin(a1)
        rgb = interp_color((t0 + t1) / 2)
        svg += f'<path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 0 0 {x1:.1f} {y1:.1f}" fill="none" stroke="rgb({rgb[0]},{rgb[1]},{rgb[2]})" stroke-width="{arc_w}" stroke-linecap="butt"/>\n'

    # 兩端圓角蓋
    a_start = math.radians(180)
    a_end = math.radians(0)
    rgb_start = interp_color(0)
    rgb_end = interp_color(1)
    svg += f'<circle cx="{cx + r * math.cos(a_start):.1f}" cy="{cy - r * math.sin(a_start):.1f}" r="{arc_w / 2}" fill="rgb({rgb_start[0]},{rgb_start[1]},{rgb_start[2]})"/>\n'
    svg += f'<circle cx="{cx + r * math.cos(a_end):.1f}" cy="{cy - r * math.sin(a_end):.1f}" r="{arc_w / 2}" fill="rgb({rgb_end[0]},{rgb_end[1]},{rgb_end[2]})"/>\n'

    # 標籤
    for l_pos, l_text, l_anchor in labels:
        la = math.radians(180 - (l_pos / 100) * 180)
        label_r = r + arc_w / 2 + 14
        lx = cx + label_r * math.cos(la)
        ly = cy - label_r * math.sin(la)
        svg += f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{l_anchor}" font-size="9" fill="#95a5a6" font-weight="500">{l_text}</text>\n'

    # 指針
    needle_deg = 180 - (score / 100) * 180
    needle_rad = math.radians(needle_deg)
    needle_len = r - 8
    nx = cx + needle_len * math.cos(needle_rad)
    ny = cy - needle_len * math.sin(needle_rad)
    tail_len = 18
    tx = cx - tail_len * math.cos(needle_rad)
    ty = cy + tail_len * math.sin(needle_rad)
    bw = 2.5
    tw = 4
    perp = needle_rad + math.pi / 2
    b1x = cx + bw * math.cos(perp)
    b1y = cy - bw * math.sin(perp)
    b2x = cx - bw * math.cos(perp)
    b2y = cy + bw * math.sin(perp)
    t1x = tx + tw * math.cos(perp)
    t1y = ty - tw * math.sin(perp)
    t2x = tx - tw * math.cos(perp)
    t2y = ty + tw * math.sin(perp)
    svg += f'<polygon points="{nx:.1f},{ny:.1f} {b1x:.1f},{b1y:.1f} {t1x:.1f},{t1y:.1f} {t2x:.1f},{t2y:.1f} {b2x:.1f},{b2y:.1f}" fill="#34495e" filter="url(#ns)"/>\n'
    svg += f'<circle cx="{cx}" cy="{cy}" r="9" fill="#fff" stroke="#34495e" stroke-width="2.5"/>\n'
    svg += f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="#34495e"/>\n'

    # 分數 + 文字
    svg += f'<text x="{cx}" y="{cy + 40}" text-anchor="middle" font-size="30" font-weight="800" fill="{color}">{score:.1f}</text>\n'
    svg += f'<text x="{cx}" y="{cy + 56}" text-anchor="middle" font-size="11" font-weight="600" fill="{color}">{rating_zh}</text>\n'

    svg += '</svg>\n'
    return f'<div style="text-align:center;margin:4px 0;">{svg}</div>\n'


# ==================== 市場情緒指標 (NEW) ====================

def _gen_sentiment_section(sentiment_data, clock_data, sentiment_analysis=None, historical_context=None):
    """生成市場情緒指標章節，包含 Fear & Greed、VIX、US10Y、DXY、美林時鐘和歷史情境"""
    html = '<div style="page-break-before:always;"></div>\n'
    html += '<div class="section-title" style="margin-top:0;">七、市場情緒指標</div>\n'

    if sentiment_analysis:
        html += f'<p class="analysis-text">{sentiment_analysis}</p>\n'

    fg = sentiment_data.get('fear_greed', {})
    vix = sentiment_data.get('vix', {})
    us10y = sentiment_data.get('us10y', {})
    dxy = sentiment_data.get('dxy', {})

    fg_score = fg.get('score', 50)
    fg_color = "#e74c3c" if fg_score < 25 else "#e67e22" if fg_score < 45 else "#f1c40f" if fg_score < 55 else "#27ae60"
    fg_rating_zh = "極度恐懼" if fg_score < 25 else "恐懼" if fg_score < 45 else "中性" if fg_score < 55 else "貪婪" if fg_score < 75 else "極度貪婪"

    vix_val = vix.get('value') if 'error' not in vix else None
    vix_change = vix.get('change', 0) if vix_val else 0
    vix_change_pct = vix.get('change_pct', 0) if vix_val else 0
    if vix_val is None:
        vix_val = 0
    vix_color = "#e74c3c" if vix_val > 25 else "#e67e22" if vix_val > 20 else "#999" if vix_val == 0 else "#27ae60"

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
  <div class="value" style="color:{vix_color};">{"N/A" if vix_val == 0 else f"{vix_val:.2f}"}</div>
  <div class="sub {vix_cls}">{"數據暫缺" if vix_val == 0 else f"{vix_sign}{vix_change:.2f} ({vix_sign}{vix_change_pct:.1f}%)"}</div>
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

    # ===== 恐懼與貪婪儀表盤 =====
    html += '<div class="sub-section-title">恐懼與貪婪指數</div>\n'
    html += _gen_fear_greed_gauge(fg_score, fg_rating_zh, fg_color)

    # 恐貪歷史比較
    fg_prev = fg.get('previous_close', 0) or 0
    fg_1w = fg.get('previous_1_week', 0) or 0
    fg_1m = fg.get('previous_1_month', 0) or 0
    fg_1y = fg.get('previous_1_year', 0) or 0
    html += '<table><thead><tr><th>指標</th><th>當前</th><th>前日</th><th>一週前</th><th>一月前</th><th>一年前</th></tr></thead><tbody>\n'
    html += f'<tr><td class="name-cell">恐懼與貪婪</td><td class="down">{fg_score:.1f}</td><td>{fg_prev:.1f}</td><td>{fg_1w:.1f}</td><td>{fg_1m:.1f}</td><td>{fg_1y:.1f}</td></tr>\n'
    html += '</tbody></table>\n'

    # 美林時鐘 + 歷史情境
    if clock_data and clock_data.get('phase') != 'Unknown':
        html += _gen_investment_clock(clock_data, historical_context)
    elif historical_context:
        hp = [v for v in historical_context.values() if isinstance(v, str)]
        if hp:
            html += f'<div style="background:linear-gradient(135deg,#fff5f5 0%,#ffe8e8 100%);border-left:4px solid #e74c3c;padding:10px 14px;margin:10px 0;font-size:8.5pt;line-height:1.6;border-radius:0 6px 6px 0;"><strong style="color:#c0392b;font-size:9pt;">歷史情境參考</strong><br>{"<br>".join(hp)}</div>\n'

    return html


def _gen_investment_clock(clock_data, historical_context=None):
    """生成美林時鐘 SVG 和資訊面板（含歷史情境）"""
    html = '<div>\n'
    html += '<div class="sub-section-title" style="margin-top:8px;">經濟週期指示器</div>\n'

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
    <svg viewBox="0 0 340 340" width="180" height="180">
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
    # 歷史情境參考（嵌在同一個區塊裡）
    if historical_context:
        hp = [v for v in historical_context.values() if isinstance(v, str)]
        if hp:
            html += f'<div style="background:linear-gradient(135deg,#fff5f5 0%,#ffe8e8 100%);border-left:4px solid #e74c3c;padding:10px 14px;margin:10px 0;font-size:8.5pt;line-height:1.6;border-radius:0 6px 6px 0;"><strong style="color:#c0392b;font-size:9pt;">歷史情境參考</strong><br>{"<br>".join(hp)}</div>\n'

    html += '</div>\n'  # 關閉區塊
    return html


# ==================== 全球資金流向 (NEW) ====================

def _gen_fund_flow_section(fund_flows, flow_analysis=None):
    """生成全球資金流向脈動章節"""
    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">八、全球資金流向</div>\n'

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
    html += '<div class="section-title">九、板塊輪動</div>\n'

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

def _gen_stock_table_html(stocks, stock_analysis, is_outflow=False):
    """渲染一組股票的 HTML 表格（含量化評分）

    is_outflow=True 時，綜合分顯示為負數（資金出清 = 負面信號）
    """
    if not stocks:
        return ""

    # 檢查是否有量化數據（匹配率 ≥ 50% 才顯示量化欄位）
    matched_count = sum(1 for s in stocks if s.get('quant_matched'))
    has_quant = matched_count >= len(stocks) * 0.5 if stocks else False

    html = '<table>\n<thead><tr>'
    html += '<th style="text-align:left;">股票</th><th>代碼</th><th style="text-align:right;">收盤價</th><th style="text-align:right;">漲跌幅</th><th style="text-align:right;">量比</th>'
    if has_quant:
        html += '<th style="text-align:right;">量化分</th><th style="text-align:right;">綜合分</th>'
    else:
        html += '<th style="text-align:right;">成交量</th>'
    html += '</tr></thead>\n<tbody>\n'

    for i, s in enumerate(stocks):
        name = s['name']
        if len(name) > 25:
            name = name[:23] + "..."
        vol_ratio = s.get('volume_ratio', 1)
        volume = s.get('volume', 0)
        cls = _change_class(s.get('change_pct', 0))

        # 量比顏色
        vr_color = '#e74c3c' if vol_ratio >= 3 else '#e67e22' if vol_ratio >= 2 else '#333'

        # 排名標記
        rank_badge = ''
        if i < 3:
            medals = ['🥇', '🥈', '🥉']
            rank_badge = f'<span style="font-size:7pt;">{medals[i]}</span> '

        html += '<tr>'
        html += f'<td class="name-cell" style="text-align:left;">{rank_badge}{name}</td>'
        html += f'<td style="text-align:center;"><code style="font-size:8pt;color:#666;">{s["symbol"]}</code></td>'
        html += f'<td style="text-align:right;">{s["current"]:,.2f}</td>'
        html += f'<td class="{cls}" style="text-align:right;font-weight:600;">{_format_pct(s["change_pct"])}</td>'
        html += f'<td style="text-align:right;color:{vr_color};font-weight:600;">{vol_ratio:.1f}x</td>'

        if has_quant:
            # 量化分數（買入用 buy_score，賣出用 sell_score）
            if s.get('quant_matched'):
                flow = s.get('flow', '')
                q_score = s.get('quant_buy_score', 50) if flow == 'inflow' else s.get('quant_sell_score', 50)
                q_color = '#27ae60' if q_score >= 70 else '#e67e22' if q_score >= 40 else '#999'
                total_s = s.get('quant_total_score', 0)
                ts_sign = '+' if total_s > 0 else ''
                html += f'<td style="text-align:right;color:{q_color};font-weight:600;">{q_score}<span style="font-size:7pt;color:#999;"> ({ts_sign}{total_s})</span></td>'
            else:
                html += '<td style="text-align:right;color:#ccc;font-size:8pt;">—</td>'
            # 綜合分（outflow 顯示為負數）
            comp = s.get('composite_score', 0)
            if is_outflow:
                display_comp = -comp
                comp_color = '#e74c3c'
                html += f'<td style="text-align:right;color:{comp_color};font-weight:700;">{display_comp:.0f}</td>'
            else:
                comp_color = '#c0392b' if comp >= 70 else '#e67e22' if comp >= 50 else '#333'
                html += f'<td style="text-align:right;color:{comp_color};font-weight:700;">{comp:.0f}</td>'
        else:
            # 無量化數據時顯示成交量
            if volume >= 1_000_000_000:
                vol_str = f'{volume/1_000_000_000:.1f}B'
            elif volume >= 1_000_000:
                vol_str = f'{volume/1_000_000:.1f}M'
            elif volume >= 1_000:
                vol_str = f'{volume/1_000:.0f}K'
            else:
                vol_str = f'{volume:,.0f}'
            html += f'<td style="text-align:right;color:#999;font-size:8.5pt;">{vol_str}</td>'

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
    html += '<div class="section-title">十、當日熱門股票</div>\n'
    html += '<div class="filter-note">'
    html += '<strong>篩選方法論</strong><br/>'
    html += '本系統透過三層篩選機制識別當日異常資金活動的股票：<br/>'
    html += '① <strong>放量門檻</strong>：成交量相對 20 日均量的倍數（量比），篩選出成交異常放大的標的<br/>'
    html += '② <strong>量化驗證</strong>：整合技術面信號（均線/RSI）、均值回歸（Z-Score）、基本面評分（F-Score）及分析師目標價進行多維度驗證<br/>'
    html += '③ <strong>複合排名</strong>：量能權重 30% + 量化評分 40% + 價格動量 30%，綜合排序<br/>'
    html += '<span style="color:#888;">量化數據來源：股票量化研究系統（覆蓋美/港/日/台約 4,000+ 支指數成分股）</span>'
    html += '</div>\n'

    for market in ['美股', '港股', '日股', '台股']:
        if market not in hot_stocks or not hot_stocks[market]:
            continue

        inflow, outflow = _extract_stocks_html(hot_stocks[market])

        if not inflow and not outflow:
            continue

        html += f'<div class="sub-section-title">{market}</div>\n'

        if inflow:
            html += '<p class="hot-label buy">🔥 資金追捧</p>\n'
            html += _gen_stock_table_html(inflow, stock_analysis, is_outflow=False)

        if outflow:
            html += '<p class="hot-label sell">⚠️ 資金出清</p>\n'
            html += _gen_stock_table_html(outflow, stock_analysis, is_outflow=True)

    html += '<hr class="divider">\n'
    return html


# ==================== 加密貨幣 ====================

def _gen_crypto_section(crypto_data):
    """生成加密貨幣市場章節"""
    if not crypto_data:
        return ""

    html = '<div class="section-new-page"></div>\n'
    html += '<div class="section-title">六、加密貨幣市場</div>\n'
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
    html += '<div class="section-title">十一、本週經濟日曆</div>\n'

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
                         sentiment_analysis=None, flow_analysis=None, sector_analysis=None,
                         historical_context=None):
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

    # ═══ 第一段：發生了什麼 ═══
    html += _gen_news_section(news_events)
    html += _gen_indices_section(market_data, index_analysis)

    # ═══ 第二段：為什麼 ═══
    html += _gen_bonds_section(market_data)
    html += _gen_forex_section(market_data)
    html += _gen_commodities_section(market_data)
    html += _gen_crypto_section(market_data.get('crypto', {}))
    if sentiment_data and clock_data:
        html += _gen_sentiment_section(sentiment_data, clock_data, sentiment_analysis, historical_context)

    # ═══ 第三段：錢怎麼流 ═══
    if fund_flows:
        html += _gen_fund_flow_section(fund_flows, flow_analysis)
    if fund_flows:
        html += _gen_gics_sector_section(fund_flows, sector_analysis)
    html += _gen_hot_stocks_section(hot_stocks, stock_analysis)

    # ═══ 第四段：往前看 ═══
    html += _gen_calendar_section(calendar_events)

    # 底部（用 footer-wrapper 包住，避免分頁切開）
    html += f"""
<div class="footer-wrapper">
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
</div><!-- /footer-wrapper -->

</body>
</html>
"""

    return html
