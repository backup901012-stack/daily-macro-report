#!/usr/bin/env python3
"""
報告生成引擎
整合所有數據模組和AI分析，生成四份報告：
1. 亞洲盤報告
2. 歐洲盤報告
3. 美洲盤報告
4. 綜合日報
"""
import json
from datetime import datetime, timedelta


def format_change(change_pct):
    """格式化漲跌幅顯示"""
    if change_pct > 0:
        return f"🟢 +{change_pct:.2f}%"
    elif change_pct < 0:
        return f"🔴 {change_pct:.2f}%"
    else:
        return f"⚪ {change_pct:.2f}%"


def format_number(num):
    """格式化數字"""
    if num is None:
        return "N/A"
    if abs(num) >= 1e9:
        return f"{num/1e9:.2f}B"
    elif abs(num) >= 1e6:
        return f"{num/1e6:.2f}M"
    elif abs(num) >= 1e3:
        return f"{num/1e3:.1f}K"
    else:
        return f"{num:,.2f}"


def generate_indices_table(indices_data, title):
    """生成指數表格"""
    if not indices_data:
        return f"### {title}\n\n暫無數據\n\n"

    md = f"### {title}\n\n"
    md += "| 指數 | 收盤價 | 漲跌 | 漲跌幅 |\n"
    md += "|:-----|-------:|------:|-------:|\n"

    # 按漲跌幅排序
    sorted_items = sorted(indices_data.items(), key=lambda x: x[1]['change_pct'], reverse=True)

    for name, data in sorted_items:
        change_icon = "🟢" if data['change_pct'] > 0 else ("🔴" if data['change_pct'] < 0 else "⚪")
        md += f"| {change_icon} **{name}** | {data['current']:,.2f} | {data['change']:+,.2f} | {data['change_pct']:+.2f}% |\n"

    md += "\n"
    return md


def generate_hot_stocks_table(hot_stocks, market_name, stock_analysis=None):
    """生成熱門股票表格"""
    if not hot_stocks:
        return ""

    md = f"#### {market_name}熱門股票\n\n"
    md += "| 股票 | 收盤價 | 漲跌幅 | 成交量倍率 | 分析 |\n"
    md += "|:-----|-------:|-------:|----------:|:-----|\n"

    for s in hot_stocks:
        change_icon = "\U0001f7e2" if s['change_pct'] > 0 else ("\U0001f534" if s['change_pct'] < 0 else "\u26aa")
        full_symbol = s['symbol']
        symbol_base = full_symbol.split('.')[0]
        analysis = ""
        if stock_analysis:
            # 嘗試完整 symbol 匹配（如 9984.T），再嘗試 base symbol（如 AAPL）
            analysis = stock_analysis.get(full_symbol, stock_analysis.get(symbol_base, ''))

        md += f"| {change_icon} **{s['name']}** ({s['symbol']}) | {s['current']:,.2f} | {s['change_pct']:+.2f}% | {s.get('volume_ratio', 1):.1f}x | {analysis} |\n"

    md += "\n"
    return md


def generate_commodities_table(commodities_data):
    """生成大宗商品表格"""
    if not commodities_data:
        return ""

    md = "### 大宗商品\n\n"
    md += "| 商品 | 價格 | 漲跌 | 漲跌幅 |\n"
    md += "|:-----|-----:|------:|-------:|\n"

    for name, data in commodities_data.items():
        change_icon = "🟢" if data['change_pct'] > 0 else ("🔴" if data['change_pct'] < 0 else "⚪")
        md += f"| {change_icon} **{name}** | ${data['current']:,.2f} | {data['change']:+,.2f} | {data['change_pct']:+.2f}% |\n"

    md += "\n"
    return md


def generate_forex_table(forex_data):
    """生成外匯表格"""
    if not forex_data:
        return ""

    md = "### 外匯市場\n\n"
    md += "| 貨幣對 | 匯率 | 漲跌 | 漲跌幅 |\n"
    md += "|:-------|-----:|------:|-------:|\n"

    for name, data in forex_data.items():
        change_icon = "🟢" if data['change_pct'] > 0 else ("🔴" if data['change_pct'] < 0 else "⚪")
        md += f"| {change_icon} **{name}** | {data['current']:.4f} | {data['change']:+.4f} | {data['change_pct']:+.2f}% |\n"

    md += "\n"
    return md


def generate_bonds_table(bonds_data):
    """生成債券殖利率表格"""
    if not bonds_data:
        return ""

    md = "### 債券殖利率\n\n"
    md += "| 債券 | 殖利率 | 變動 | 變動幅度 |\n"
    md += "|:-----|-------:|-----:|--------:|\n"

    for name, data in bonds_data.items():
        change_icon = "🟢" if data['change_pct'] > 0 else ("🔴" if data['change_pct'] < 0 else "⚪")
        md += f"| {change_icon} **{name}** | {data['current']:.3f}% | {data['change']:+.3f} | {data['change_pct']:+.2f}% |\n"

    md += "\n"
    return md


def generate_crypto_table(crypto_data):
    """生成加密貨幣表格"""
    if not crypto_data:
        return ""

    md = "### 加密貨幣\n\n"
    md += "| 幣種 | 價格 | 漲跌 | 漲跌幅 |\n"
    md += "|:-----|-----:|------:|-------:|\n"

    sorted_items = sorted(crypto_data.items(), key=lambda x: x[1]['change_pct'], reverse=True)

    for name, data in sorted_items:
        change_icon = "🟢" if data['change_pct'] > 0 else ("🔴" if data['change_pct'] < 0 else "⚪")
        md += f"| {change_icon} **{name}** | ${data['current']:,.2f} | {data['change']:+,.2f} | {data['change_pct']:+.2f}% |\n"

    md += "\n"
    return md


def generate_macro_events_section(events):
    """生成宏觀事件章節"""
    if not events:
        return ""

    md = "## 一、宏觀重點新聞\n\n"

    for i, event in enumerate(events, 1):
        impact = event.get('impact_level', '中')
        if impact == '高':
            icon = "🔴"
        elif impact == '中':
            icon = "🟡"
        else:
            icon = "🟢"

        direction = event.get('market_direction', '中性')
        dir_icon = "📈" if direction == '利多' else ("📉" if direction == '利空' else "➡️")

        md += f"### {icon} {i}. {event.get('title', '')}\n\n"
        md += f"> **影響程度**：{impact} | **影響範圍**：{event.get('affected_markets', '')} | **市場方向**：{dir_icon} {direction}\n\n"
        md += f"{event.get('description', '')}\n\n"

        tickers = event.get('related_tickers', [])
        if tickers:
            md += f"**相關標的**：{', '.join(tickers)}\n\n"

        md += "---\n\n"

    return md


def generate_economic_calendar_section(calendar_events):
    """生成經濟日曆章節"""
    if not calendar_events:
        return ""

    md = "## 經濟日曆提示\n\n"
    md += "> 以下為近期需要關注的重要經濟數據發布\n\n"
    md += "| 日期 | 國家 | 事件 | 重要性 | 市場影響 |\n"
    md += "|:-----|:-----|:-----|:------:|:--------|\n"

    for event in calendar_events:
        md += f"| {event.get('date', '')} | {event.get('country', '')} | **{event.get('event', '')}** | {event.get('importance', '★')} | {event.get('description', '')[:80]} |\n"

    md += "\n"

    # 額外的詳細說明
    high_importance = [e for e in calendar_events if '★★★' in e.get('importance', '')]
    if high_importance:
        md += "### 重點關注事件\n\n"
        for event in high_importance:
            md += f"**{event.get('event', '')}**（{event.get('country', '')}，{event.get('date', '')}）\n\n"
            md += f"{event.get('description', '')}\n\n"
            if event.get('consensus'):
                md += f"> 市場預期：{event['consensus']}\n\n"

    return md


# ==================== 四份報告生成函數 ====================

def generate_asia_report(market_data, news_events, hot_stocks, stock_analysis, index_analysis, report_date):
    """生成亞洲盤報告"""
    md = f"# 亞洲盤市場報告\n\n"
    md += f"**報告日期**：{report_date} | **報告類型**：亞洲盤收盤報告\n\n"
    md += "---\n\n"

    # 市場摘要
    if index_analysis and 'asia_analysis' in index_analysis:
        md += "## 市場摘要\n\n"
        md += f"{index_analysis['asia_analysis']}\n\n"
        md += "---\n\n"

    # 亞洲相關宏觀新聞
    asia_events = [e for e in news_events if any(kw in e.get('affected_markets', '').lower()
                   for kw in ['亞洲', '日本', '中國', '台灣', '韓國', '全球', '香港'])]
    if asia_events:
        md += "## 宏觀重點新聞（亞洲相關）\n\n"
        for i, event in enumerate(asia_events[:5], 1):
            impact = event.get('impact_level', '中')
            icon = "🔴" if impact == '高' else ("🟡" if impact == '中' else "🟢")
            md += f"**{icon} {event.get('title', '')}**\n\n"
            md += f"{event.get('description', '')}\n\n"

    md += "---\n\n"

    # 亞洲指數表現
    md += "## 亞洲指數表現\n\n"
    md += generate_indices_table(market_data.get('asia_indices', {}), "亞洲主要指數")

    # 亞洲熱門股票
    md += "## 亞洲熱門股票\n\n"
    for market in ['日股', '台股', '港股']:
        if market in hot_stocks and hot_stocks[market]:
            md += generate_hot_stocks_table(hot_stocks[market], market, stock_analysis)

    md += "---\n\n"
    md += "**資料來源**：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com | **AI 分析**：GPT-4.1-mini\n"

    return md


def generate_europe_report(market_data, news_events, hot_stocks, stock_analysis, index_analysis, report_date):
    """生成歐洲盤報告"""
    md = f"# 歐洲盤市場報告\n\n"
    md += f"**報告日期**：{report_date} | **報告類型**：歐洲盤收盤報告\n\n"
    md += "---\n\n"

    if index_analysis and 'europe_analysis' in index_analysis:
        md += "## 市場摘要\n\n"
        md += f"{index_analysis['europe_analysis']}\n\n"
        md += "---\n\n"

    # 歐洲相關宏觀新聞
    europe_events = [e for e in news_events if any(kw in e.get('affected_markets', '').lower()
                     for kw in ['歐洲', '英國', '德國', '法國', '全球', '歐元區'])]
    if europe_events:
        md += "## 宏觀重點新聞（歐洲相關）\n\n"
        for i, event in enumerate(europe_events[:5], 1):
            impact = event.get('impact_level', '中')
            icon = "🔴" if impact == '高' else ("🟡" if impact == '中' else "🟢")
            md += f"**{icon} {event.get('title', '')}**\n\n"
            md += f"{event.get('description', '')}\n\n"

    md += "---\n\n"

    md += "## 歐洲指數表現\n\n"
    md += generate_indices_table(market_data.get('europe_indices', {}), "歐洲主要指數")

    md += "---\n\n"
    md += "**資料來源**：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com | **AI 分析**：GPT-4.1-mini\n"

    return md


def generate_us_report(market_data, news_events, hot_stocks, stock_analysis, index_analysis, report_date):
    """生成美洲盤報告"""
    md = f"# 美洲盤市場報告\n\n"
    md += f"**報告日期**：{report_date} | **報告類型**：美洲盤收盤報告\n\n"
    md += "---\n\n"

    if index_analysis and 'us_analysis' in index_analysis:
        md += "## 市場摘要\n\n"
        md += f"{index_analysis['us_analysis']}\n\n"
        md += "---\n\n"

    # 美洲相關宏觀新聞
    us_events = [e for e in news_events if any(kw in e.get('affected_markets', '').lower()
                 for kw in ['美國', '美洲', '全球', '聯準會'])]
    if us_events:
        md += "## 宏觀重點新聞（美洲相關）\n\n"
        for i, event in enumerate(us_events[:5], 1):
            impact = event.get('impact_level', '中')
            icon = "🔴" if impact == '高' else ("🟡" if impact == '中' else "🟢")
            md += f"**{icon} {event.get('title', '')}**\n\n"
            md += f"{event.get('description', '')}\n\n"

    md += "---\n\n"

    md += "## 美股指數表現\n\n"
    md += generate_indices_table(market_data.get('us_indices', {}), "美國主要指數")

    # 美股熱門股票
    if '美股' in hot_stocks and hot_stocks['美股']:
        md += "## 美股熱門股票\n\n"
        md += generate_hot_stocks_table(hot_stocks['美股'], '美股', stock_analysis)

    md += "---\n\n"
    md += "**資料來源**：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com | **AI 分析**：GPT-4.1-mini\n"

    return md


def generate_daily_report(market_data, news_events, hot_stocks, stock_analysis,
                          index_analysis, calendar_events, report_date):
    """生成綜合日報"""
    md = f"# 每日宏觀資訊綜合日報\n\n"
    md += f"**報告日期**：{report_date} | **報告類型**：綜合日報\n\n"

    # 全球市場總結
    if index_analysis and 'overall_summary' in index_analysis:
        md += f"> {index_analysis['overall_summary']}\n\n"

    md += "---\n\n"

    # 一、宏觀重點新聞
    md += generate_macro_events_section(news_events)

    # 二、各國指數表現
    md += "## 二、各國指數表現\n\n"

    if index_analysis:
        if 'asia_analysis' in index_analysis:
            md += f"**亞洲市場**：{index_analysis['asia_analysis']}\n\n"
        if 'europe_analysis' in index_analysis:
            md += f"**歐洲市場**：{index_analysis['europe_analysis']}\n\n"
        if 'us_analysis' in index_analysis:
            md += f"**美洲市場**：{index_analysis['us_analysis']}\n\n"

    md += generate_indices_table(market_data.get('asia_indices', {}), "亞洲主要指數")
    md += generate_indices_table(market_data.get('europe_indices', {}), "歐洲主要指數")
    md += generate_indices_table(market_data.get('us_indices', {}), "美國主要指數")

    # 三、大宗商品、外匯、債券
    md += "## 三、商品、外匯與債券\n\n"
    md += generate_commodities_table(market_data.get('commodities', {}))
    md += generate_forex_table(market_data.get('forex', {}))
    md += generate_bonds_table(market_data.get('bonds', {}))

    # 四、加密貨幣
    md += "## 四、加密貨幣市場\n\n"
    md += generate_crypto_table(market_data.get('crypto', {}))

    # 五、熱門股票
    md += "## 五、當日熱門股票\n\n"
    md += "> 熱門股票篩選邏輯：結合新聞提及頻率、成交量異常倍率、漲跌幅絕對值綜合計算熱度分數\n\n"
    for market in ['美股', '港股', '日股', '台股']:
        if market in hot_stocks and hot_stocks[market]:
            md += generate_hot_stocks_table(hot_stocks[market], market, stock_analysis)

    # 六、經濟日曆
    md += "## 六、經濟日曆提示\n\n"
    if calendar_events:
        md += generate_economic_calendar_section(calendar_events)
    else:
        md += "暫無重要經濟數據發布提示。\n\n"

    md += "---\n\n"
    md += "**資料來源**：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com | **AI 分析**：GPT-4.1-mini\n"

    return md
