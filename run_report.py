#!/usr/bin/env python3
"""
每日宏觀資訊報告 - 主執行腳本
用法：
  python3 run_report.py daily     # 生成綜合日報
  python3 run_report.py asia      # 生成亞洲盤報告
  python3 run_report.py europe    # 生成歐洲盤報告
  python3 run_report.py us        # 生成美洲盤報告
  python3 run_report.py all       # 生成全部四份報告
"""
import sys
import os
import json
from datetime import datetime, timedelta

# 確保模組路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.market_data import (
    get_asia_indices, get_europe_indices, get_us_indices,
    get_commodities, get_forex, get_bonds, get_crypto
)
from modules.news_collector import get_news_for_date
from modules.hot_stocks import get_all_hot_stocks, detect_hot_stocks, US_STOCK_POOL, JP_STOCK_POOL, TW_STOCK_POOL, HK_STOCK_POOL
from modules.ai_analyzer import (
    analyze_macro_news, analyze_index_movements,
    analyze_hot_stocks, generate_economic_calendar_analysis
)
from modules.report_generator import (
    generate_asia_report, generate_europe_report,
    generate_us_report, generate_daily_report
)
from modules.economic_calendar import get_upcoming_events_from_news

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
os.makedirs(REPORT_DIR, exist_ok=True)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def collect_market_data(report_type='daily'):
    """根據報告類型收集市場數據"""
    log("開始收集市場數據...")
    data = {}

    if report_type in ('asia', 'daily', 'all'):
        log("  獲取亞洲指數...")
        data['asia_indices'] = get_asia_indices()
        log(f"  ✓ 亞洲指數: {len(data['asia_indices'])} 項")

    if report_type in ('europe', 'daily', 'all'):
        log("  獲取歐洲指數...")
        data['europe_indices'] = get_europe_indices()
        log(f"  ✓ 歐洲指數: {len(data['europe_indices'])} 項")

    if report_type in ('us', 'daily', 'all'):
        log("  獲取美股指數...")
        data['us_indices'] = get_us_indices()
        log(f"  ✓ 美股指數: {len(data['us_indices'])} 項")

    if report_type in ('daily', 'all'):
        log("  獲取大宗商品...")
        data['commodities'] = get_commodities()
        log(f"  ✓ 大宗商品: {len(data.get('commodities', {}))} 項")

        log("  獲取外匯...")
        data['forex'] = get_forex()
        log(f"  ✓ 外匯: {len(data.get('forex', {}))} 項")

        log("  獲取債券殖利率...")
        data['bonds'] = get_bonds()
        log(f"  ✓ 債券: {len(data.get('bonds', {}))} 項")

        log("  獲取加密貨幣...")
        data['crypto'] = get_crypto()
        log(f"  ✓ 加密貨幣: {len(data.get('crypto', {}))} 項")

    return data


def collect_news():
    """收集新聞數據"""
    log("開始收集新聞...")
    news_data = get_news_for_date()
    log(f"  ✓ 新聞: {len(news_data['articles'])} 篇")
    return news_data


def collect_hot_stocks(report_type, news_trending):
    """收集熱門股票"""
    log("開始偵測熱門股票...")
    hot_stocks = {}

    if report_type in ('asia', 'daily', 'all'):
        log("  偵測日股熱門...")
        hot_stocks['日股'] = detect_hot_stocks(JP_STOCK_POOL, '日股', top_n=5)
        log("  偵測台股熱門...")
        hot_stocks['台股'] = detect_hot_stocks(TW_STOCK_POOL, '台股', top_n=5)
        log("  偵測港股熱門...")
        hot_stocks['港股'] = detect_hot_stocks(HK_STOCK_POOL, '港股', top_n=5)

    if report_type in ('us', 'daily', 'all'):
        log("  偵測美股熱門...")
        hot_stocks['美股'] = detect_hot_stocks(US_STOCK_POOL, '美股', top_n=8)

    log(f"  ✓ 熱門股票偵測完成")
    return hot_stocks


def run_ai_analysis(market_data, news_data, hot_stocks):
    """執行 AI 分析"""
    log("開始 AI 分析...")

    # 1. 分析宏觀新聞
    log("  AI 分析宏觀新聞...")
    news_events = analyze_macro_news(news_data['articles'], news_data['categorized'])
    log(f"  ✓ 歸納出 {len(news_events)} 條宏觀事件")

    # 2. 分析指數漲跌原因
    log("  AI 分析指數漲跌原因...")
    indices_for_analysis = {}
    if 'asia_indices' in market_data:
        indices_for_analysis['亞洲'] = market_data['asia_indices']
    if 'europe_indices' in market_data:
        indices_for_analysis['歐洲'] = market_data['europe_indices']
    if 'us_indices' in market_data:
        indices_for_analysis['美國'] = market_data['us_indices']
    index_analysis = analyze_index_movements(indices_for_analysis, news_events)
    log("  ✓ 指數分析完成")

    # 3. 分析熱門股票
    log("  AI 分析熱門股票...")
    stock_analysis = analyze_hot_stocks(hot_stocks, news_data['articles'])
    log("  ✓ 熱門股票分析完成")

    # 4. 分析經濟日曆
    log("  AI 分析經濟日曆...")
    econ_news = get_upcoming_events_from_news(news_data['articles'])
    # 動態產生經濟日曆提示：讓 AI 從新聞中提取本週重要經濟事件
    from datetime import datetime as _dt
    today = _dt.now()
    current_year = today.year
    # 計算本週日期範圍
    weekday = today.weekday()  # 0=Monday
    week_start = today - timedelta(days=weekday)
    week_dates = [(week_start + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    # 從新聞中提取經濟日曆相關內容
    econ_related_news = []
    econ_keywords = ['CPI', 'GDP', 'PPI', 'NFP', 'nonfarm', 'payroll', 'retail sales', 'unemployment',
                     'inflation', 'interest rate', 'Fed', 'ECB', 'BOJ', 'FOMC', 'PMI', 'manufacturing',
                     'consumer confidence', 'housing', 'trade balance', 'jobless claims',
                     '非農', '通膨', '利率', '央行', 'central bank']
    for article in news_data['articles'][:80]:
        title = article.get('title', '').lower()
        desc = article.get('description', '').lower()
        if any(kw.lower() in title or kw.lower() in desc for kw in econ_keywords):
            econ_related_news.append({
                'title': article.get('title', ''),
                'description': article.get('description', '')[:300],
            })
    
    calendar_text = f"""
今天日期：{today.strftime('%Y-%m-%d')}
本週日期範圍：{week_dates[0]} ~ {week_dates[6]}

請根據以下新聞中提及的經濟數據發布信息，整理出本週需要關注的重要經濟數據發布日曆。
如果新聞中沒有提及具體經濟數據發布，請根據你的知識補充本週可能的重要經濟事件。
所有日期必須使用 {current_year} 年。

相關新聞：
{json.dumps(econ_related_news[:20], ensure_ascii=False, indent=1)}
"""
    calendar_events = generate_economic_calendar_analysis(calendar_text)
    log(f"  ✓ 經濟日曆分析完成: {len(calendar_events)} 事件")

    return news_events, index_analysis, stock_analysis, calendar_events


def save_report(content, filename):
    """保存報告"""
    filepath = os.path.join(REPORT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    log(f"  ✓ 報告已保存: {filepath}")
    return filepath


def main():
    report_type = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    report_date = datetime.now().strftime('%Y-%m-%d')

    log(f"========================================")
    log(f"每日宏觀資訊報告系統")
    log(f"報告類型: {report_type}")
    log(f"報告日期: {report_date}")
    log(f"========================================")

    # 1. 收集市場數據
    market_data = collect_market_data(report_type)

    # 2. 收集新聞
    news_data = collect_news()

    # 3. 收集熱門股票
    hot_stocks = collect_hot_stocks(report_type, news_data.get('trending_tickers', []))

    # 4. AI 分析
    news_events, index_analysis, stock_analysis, calendar_events = run_ai_analysis(
        market_data, news_data, hot_stocks
    )

    # 5. 生成報告
    log("開始生成報告...")

    reports = {}

    if report_type in ('asia', 'all'):
        asia_report = generate_asia_report(
            market_data, news_events, hot_stocks, stock_analysis, index_analysis, report_date
        )
        reports['asia'] = save_report(asia_report, f"asia_report_{report_date}.md")

    if report_type in ('europe', 'all'):
        europe_report = generate_europe_report(
            market_data, news_events, hot_stocks, stock_analysis, index_analysis, report_date
        )
        reports['europe'] = save_report(europe_report, f"europe_report_{report_date}.md")

    if report_type in ('us', 'all'):
        us_report = generate_us_report(
            market_data, news_events, hot_stocks, stock_analysis, index_analysis, report_date
        )
        reports['us'] = save_report(us_report, f"us_report_{report_date}.md")

    if report_type in ('daily', 'all'):
        daily_report = generate_daily_report(
            market_data, news_events, hot_stocks, stock_analysis,
            index_analysis, calendar_events, report_date
        )
        reports['daily'] = save_report(daily_report, f"daily_report_{report_date}.md")

    # 6. 保存原始數據
    raw_data = {
        'market_data': market_data,
        'news_events': news_events,
        'index_analysis': index_analysis,
        'stock_analysis': stock_analysis,
        'calendar_events': calendar_events,
        'hot_stocks_summary': {
            market: [{'symbol': s['symbol'], 'change_pct': s['change_pct'], 'heat_score': s['heat_score']}
                     for s in stocks]
            for market, stocks in hot_stocks.items()
        },
        'report_date': report_date,
        'generated_at': datetime.now().isoformat(),
    }
    raw_path = os.path.join(REPORT_DIR, f"raw_data_{report_date}.json")
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2, default=str)
    log(f"  ✓ 原始數據已保存: {raw_path}")

    log(f"\n========================================")
    log(f"報告生成完成！")
    for name, path in reports.items():
        log(f"  {name}: {path}")
    log(f"========================================")


if __name__ == '__main__':
    main()
