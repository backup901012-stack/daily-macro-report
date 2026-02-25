#!/usr/bin/env python3
"""
AI 分析模組
使用 OpenAI API 進行新聞歸納、漲跌原因分析、專業客觀的市場分析
"""
import json
from openai import OpenAI

ai_client = OpenAI()
MODEL = "gpt-4.1-mini"


def analyze_macro_news(news_articles, categorized_news):
    """分析宏觀新聞，歸納出當日最重要的5-8條宏觀事件"""

    # 準備新聞摘要給 AI
    news_summaries = []
    for article in news_articles[:60]:
        news_summaries.append({
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'publisher': article.get('publisher', ''),
            'tickers': article.get('tickers', [])[:5],
        })

    prompt = f"""你是一位資深的全球宏觀經濟分析師。請根據以下新聞資料，歸納出當日最重要的 5-8 條宏觀事件。

嚴格要求：
1. 只能根據提供的新聞資料進行歸納，嚴禁編造或添加新聞中沒有提到的事件
2. 優先歸納宏觀層面的事件（央行政策、經濟數據、賿易政策、地緣政治、產業重大變革、大規模併購、重大監管變化），其次才是個股層面的重大事件
3. 每條事件需要有清晰的標題和詳細的描述（2-3句話），描述必須基於新聞原文
4. 標註影響程度（高/中/低）
5. 標註影響的市場範圍（全球/美國/亞洲/歐洲/特定國家）
6. 分析對市場的潛在影響方向（利多/利空/中性）
7. 用繁體中文撰寫
8. 保持專業、客觀的語調
9. 按重要性排序
10. 合併同一事件的多篇報導，不要重複

新聞資料：
{json.dumps(news_summaries, ensure_ascii=False, indent=1)}

請以 JSON 格式回覆，格式如下：
[
  {{
    "title": "事件標題",
    "description": "詳細描述",
    "impact_level": "高/中/低",
    "affected_markets": "影響範圍",
    "market_direction": "利多/利空/中性",
    "related_tickers": ["相關股票代碼"]
  }}
]
"""

    try:
        response = ai_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.3,
        )
        content = response.choices[0].message.content.strip()
        # 清理可能的 markdown 包裝
        if content.startswith('```'):
            content = content.split('\n', 1)[1]
            content = content.rsplit('```', 1)[0]
        return json.loads(content)
    except Exception as e:
        print(f"AI 新聞分析錯誤: {e}")
        return []


def analyze_index_movements(indices_data, news_events):
    """分析指數漲跌原因"""

    # 準備指數數據
    index_summary = {}
    for region, indices in indices_data.items():
        index_summary[region] = {}
        for name, data in indices.items():
            index_summary[region][name] = {
                'change_pct': data['change_pct'],
                'current': data['current'],
            }

    prompt = f"""你是一位資深的全球股市分析師。請根據以下指數表現和當日宏觀事件，分析各主要指數漲跌的可能原因。

指數表現：
{json.dumps(index_summary, ensure_ascii=False, indent=1)}

當日宏觀事件：
{json.dumps(news_events, ensure_ascii=False, indent=1)}

要求：
1. 為每個區域（亞洲、歐洲、美洲）撰寫一段專業的市場分析（3-5句話）
2. 解釋主要指數漲跌的原因，並與宏觀事件做關聯
3. 用繁體中文撰寫
4. 保持專業、客觀的語調
5. 避免使用「可能」「或許」等模糊用語，改用「主要受到」「反映了」等專業表述

請以 JSON 格式回覆：
{{
  "asia_analysis": "亞洲市場分析...",
  "europe_analysis": "歐洲市場分析...",
  "us_analysis": "美洲市場分析...",
  "overall_summary": "全球市場總結（2-3句話）..."
}}
"""

    try:
        response = ai_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1]
            content = content.rsplit('```', 1)[0]
        return json.loads(content)
    except json.JSONDecodeError as je:
        print(f"AI 指數分析 JSON 解析錯誤: {je}")
        # 重試一次
        try:
            response = ai_client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt + "\n\n請確保輸出有效的 JSON 格式，不要包含任何額外文字。"}],
                max_tokens=2000,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
                content = content.rsplit('```', 1)[0]
            return json.loads(content)
        except Exception as e2:
            print(f"AI 指數分析重試失敗: {e2}")
            return {}
    except Exception as e:
        print(f"AI 指數分析錯誤: {e}")
        return {}


def analyze_hot_stocks(hot_stocks_data, news_articles):
    """分析熱門股票的漲跌原因"""

    stocks_info = []
    for market, stocks in hot_stocks_data.items():
        for s in stocks[:8]:
            stocks_info.append({
                'market': market,
                'symbol': s['symbol'],
                'name': s['name'],
                'change_pct': s['change_pct'],
                'volume_ratio': s.get('volume_ratio', 1),
                'news_mentions': s.get('news_mentions', 0),
            })

    # 提取相關新聞
    relevant_news = []
    stock_symbols = {s['symbol'].split('.')[0] for s in stocks_info}
    for article in news_articles[:30]:
        article_tickers = set(article.get('tickers', []))
        if article_tickers & stock_symbols:
            relevant_news.append({
                'title': article['title'],
                'description': article.get('description', '')[:200],
                'tickers': list(article_tickers & stock_symbols),
            })

    prompt = f"""你是一位資深的股票分析師。請根據以下熱門股票數據和相關新聞，為每支熱門股票撰寫簡短的漲跌原因分析。

熱門股票：
{json.dumps(stocks_info, ensure_ascii=False, indent=1)}

相關新聞：
{json.dumps(relevant_news[:15], ensure_ascii=False, indent=1)}

要求：
1. 為每支股票撰寫 1-2 句話的漲跌原因分析
2. 如果有相關新聞，引用新聞內容作為原因
3. 如果沒有明確新聞，根據市場大環境和行業趨勢分析
4. 用繁體中文撰寫
5. 保持專業、客觀
6. 必須為所有列出的股票都提供分析，不可遺漏

請以 JSON 格式回覆，key 使用完整的股票代碼（包含交易所後綴，例如 9984.T、2330.TW、0700.HK），美股則直接使用代碼（例如 AAPL）：
{{
  "AAPL": "分析內容...",
  "9984.T": "分析內容...",
  "2330.TW": "分析內容..."
}}
"""

    try:
        response = ai_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.3,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1]
            content = content.rsplit('```', 1)[0]
        return json.loads(content)
    except Exception as e:
        print(f"AI 熱門股票分析錯誤: {e}")
        return {}


def generate_economic_calendar_analysis(calendar_events):
    """分析經濟日曆事件的重要性和市場影響"""

    prompt = f"""你是一位資深的宏觀經濟分析師。請根據以下經濟日曆事件，撰寫明日/本週需要關注的重點經濟數據提示。

經濟日曆：
{calendar_events}

要求：
1. 標註每個事件的重要性（★★★ 高度關注 / ★★ 中度關注 / ★ 一般關注）
2. 說明該數據對市場的潛在影響
3. 如有預期值，說明市場共識預期
4. 用繁體中文撰寫
5. 保持專業、客觀
6. 日期格式必須使用 2026 年（例如 2026-02-10），不要使用 2024 年

請以 JSON 格式回覆：
[
  {{
    "date": "日期",
    "event": "事件名稱",
    "country": "國家",
    "importance": "★★★/★★/★",
    "description": "描述和市場影響分析",
    "consensus": "市場預期值（如有）"
  }}
]
"""

    try:
        response = ai_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1]
            content = content.rsplit('```', 1)[0]
        return json.loads(content)
    except Exception as e:
        print(f"AI 經濟日曆分析錯誤: {e}")
        return []


if __name__ == '__main__':
    print("AI 分析模組已就緒")
