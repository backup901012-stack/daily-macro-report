#!/usr/bin/env python3
"""
從已有的 JSON 數據生成精美 HTML+CSS PDF 報告
用法：
  python3 generate_pdf.py              # 使用今天的日期
  python3 generate_pdf.py 2026-02-24   # 指定日期
"""
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.html_report_generator import generate_html_report
from weasyprint import HTML


def _ensure_flow_compat(hot_stocks):
    """
    確保 hot_stocks 數據格式相容 v2（{inflow: [], outflow: []}）

    v2 格式: {'美股': {'inflow': [...], 'outflow': [...]}, ...}
    v1 格式: {'美股': [stock1, stock2, ...], ...}

    如果是 v1 格式，自動轉換為 v2 格式
    """
    MIN_VOL_BUY = 1.5
    MIN_VOL_SELL = 2.5

    for market, data in hot_stocks.items():
        if isinstance(data, dict) and 'inflow' in data:
            # 已經是 v2 格式，不需要轉換
            continue
        elif isinstance(data, list):
            # v1 格式：flat list，需要轉換
            inflow = []
            outflow = []
            for s in data:
                chg = s.get('change_pct', 0)
                vr = s.get('volume_ratio', 1)
                if chg > 0 and vr >= MIN_VOL_BUY:
                    s['flow'] = 'inflow'
                    inflow.append(s)
                elif chg < 0 and vr >= MIN_VOL_SELL:
                    s['flow'] = 'outflow'
                    outflow.append(s)
            hot_stocks[market] = {'inflow': inflow, 'outflow': outflow}

    return hot_stocks


def main():
    report_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    json_path = f"reports/raw_data_{report_date}.json"

    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    market_data = raw.get('market_data', {})
    news_events = raw.get('news_events', [])
    hot_stocks = raw.get('hot_stocks', {})
    stock_analysis = raw.get('stock_analysis', {})
    index_analysis = raw.get('index_analysis', {})
    calendar_events = raw.get('calendar_events', [])

    # 新增：增強版數據
    sentiment_data = raw.get('sentiment_data', {})
    clock_data = raw.get('clock_data', {})
    fund_flows = raw.get('fund_flows', {})

    # 確保格式相容
    hot_stocks = _ensure_flow_compat(hot_stocks)

    print(f"Report date: {report_date}")
    print(f"Hot stocks markets: {list(hot_stocks.keys())}")
    for m, data in hot_stocks.items():
        if isinstance(data, dict):
            in_count = len(data.get('inflow', []))
            out_count = len(data.get('outflow', []))
            print(f"  {m}: 買入放量 {in_count} 支, 賣出放量 {out_count} 支")
        else:
            print(f"  {m}: {len(data)} stocks (legacy format)")

    print("Generating HTML report...")
    html_content = generate_html_report(
        market_data, news_events, hot_stocks, stock_analysis,
        index_analysis, calendar_events, report_date,
        sentiment_data=sentiment_data,
        clock_data=clock_data,
        fund_flows=fund_flows,
    )

    # Save HTML
    html_path = f"reports/daily_report_{report_date}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"HTML saved: {html_path}")

    # Convert to PDF — prefer Chrome headless (correct CJK fonts), fallback to WeasyPrint
    pdf_path = f"reports/daily_report_{report_date}.pdf"
    html_abs = os.path.abspath(html_path)

    chrome_paths = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/usr/bin/google-chrome',
        '/usr/bin/chromium-browser',
    ]
    chrome_bin = None
    for p in chrome_paths:
        if os.path.exists(p):
            chrome_bin = p
            break

    if chrome_bin:
        import subprocess
        print(f"Converting to PDF with Chrome headless...")
        result = subprocess.run([
            chrome_bin, '--headless', '--disable-gpu', '--no-sandbox',
            f'--print-to-pdf={os.path.abspath(pdf_path)}',
            '--print-to-pdf-no-header',
            f'file://{html_abs}'
        ], capture_output=True, text=True, timeout=60)
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
            print(f"PDF saved (Chrome): {pdf_path}")
        else:
            print(f"Chrome PDF failed, fallback to WeasyPrint...")
            HTML(string=html_content).write_pdf(pdf_path)
            print(f"PDF saved (WeasyPrint): {pdf_path}")
    else:
        print("Converting to PDF with WeasyPrint...")
        HTML(string=html_content).write_pdf(pdf_path)
        print(f"PDF saved (WeasyPrint): {pdf_path}")

    print("Done!")


if __name__ == '__main__':
    main()
