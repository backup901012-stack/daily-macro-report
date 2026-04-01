"""
Kimi AI 新聞分析增強模組
用 Moonshot API 將分類後的新聞群組生成專業中文摘要 + 報告總結
fallback：AI 失敗時退回現有規則引擎結果，不影響報告生成
"""
import os
import json
import requests

MOONSHOT_API_KEY = os.environ.get('MOONSHOT_API_KEY', '')
MOONSHOT_API_URL = 'https://api.moonshot.cn/v1/chat/completions'
MODEL = 'moonshot-v1-auto'


def _call_kimi(system_prompt, user_prompt, max_tokens=1500, temperature=0.3):
    """呼叫 Kimi API，失敗回傳 None"""
    if not MOONSHOT_API_KEY:
        return None
    try:
        resp = requests.post(
            MOONSHOT_API_URL,
            headers={
                'Authorization': f'Bearer {MOONSHOT_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': MODEL,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                'max_tokens': max_tokens,
                'temperature': temperature,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content'].strip()
        else:
            print(f'⚠️ Kimi API 回應 {resp.status_code}: {resp.text[:200]}')
            return None
    except Exception as e:
        print(f'⚠️ Kimi API 呼叫失敗: {e}')
        return None


# ========== 新聞敘事摘要 ==========

NEWS_SYSTEM_PROMPT = """你是一位專業的宏觀策略分析師，負責撰寫每日市場晨報的新聞摘要。

要求：
- 用繁體中文撰寫
- 必須使用繁體中文（台灣用語），不可出現簡體字
- 客觀陳述事實，不帶主觀稱呼（不說「早上好」「各位」「基金經理們」）
- 直接講重點：「發生了什麼」+「為什麼重要」+「對市場的影響」
- 如果有具體數字（價格、漲跌幅、政策細節），一定要提到
- 不要寫「根據報導」「據悉」這種廢話，直接陳述事實
- 不要用「總的來說」「綜上所述」這種結尾套話
- 控制在 100-200 字"""


def enhance_news_narrative(group_name, articles, market_snapshot=None):
    """用 Kimi 生成單個新聞主題的專業摘要

    Args:
        group_name: 分類名稱（如「地緣政治/關稅」）
        articles: 該分類下的新聞列表 [{title, desc, publisher, title_zh}, ...]
        market_snapshot: 當日市場數據快照

    Returns:
        str: 中文敘事摘要，失敗回傳 None（退回規則引擎）
    """
    if not articles:
        return None

    # 組裝新聞素材
    news_text = []
    for i, a in enumerate(articles[:8], 1):
        title = a.get('title_zh') or a.get('title', '')
        desc = a.get('desc', '')
        publisher = a.get('publisher', '')
        line = f'{i}. [{publisher}] {title}'
        if desc and len(desc) > 20:
            line += f'\n   {desc[:300]}'
        news_text.append(line)

    user_prompt = f'主題：{group_name}\n\n以下是今天相關的 {len(articles)} 篇新聞：\n\n'
    user_prompt += '\n\n'.join(news_text)

    # 加入市場數據供交叉引用
    if market_snapshot:
        mkt_lines = []
        if market_snapshot.get('sp500_chg'):
            mkt_lines.append(f'S&P 500 {market_snapshot["sp500_chg"]:+.2f}%')
        if market_snapshot.get('gold_price'):
            mkt_lines.append(f'黃金 ${market_snapshot["gold_price"]:.0f} ({market_snapshot.get("gold_chg", 0):+.2f}%)')
        if market_snapshot.get('oil_price'):
            mkt_lines.append(f'WTI ${market_snapshot["oil_price"]:.1f} ({market_snapshot.get("oil_chg", 0):+.2f}%)')
        if market_snapshot.get('vix'):
            mkt_lines.append(f'VIX {market_snapshot["vix"]:.1f}')
        if market_snapshot.get('us10y'):
            mkt_lines.append(f'10Y殖利率 {market_snapshot["us10y"]:.3f}%')
        if mkt_lines:
            user_prompt += f'\n\n今日市場數據：{" | ".join(mkt_lines)}'

    user_prompt += '\n\n請為這個主題撰寫一段簡報摘要（100-200 字）。'

    return _call_kimi(NEWS_SYSTEM_PROMPT, user_prompt)


# ========== 報告總結 ==========

SUMMARY_SYSTEM_PROMPT = """你是一位專業的宏觀策略分析師，負責撰寫每日晨報的結論總結。

嚴格要求：
- 全文必須使用繁體中文（台灣用語），嚴禁出現任何簡體字（例：用「顯示」不用「显示」，用「聯準會」不用「联准会」，用「價格」不用「价格」）
- 客觀陳述，不帶任何稱呼或寒暄
- 分三段，每段要有具體數據和深入分析：
  ① 【今日重點】回顧今日市場關鍵事件和表現（4-5句，引用具體指數漲跌幅、價格）
  ② 【核心驅動】分析背後的驅動因素和邏輯鏈（4-5句，解釋因果關係，如果有矛盾信號要點出）
  ③ 【明日關注】未來需要關注的風險和催化劑（4-5句，具體說明哪些數據/事件/價位值得關注）
- 語氣專業客觀，不用「總的來說」「綜上所述」「值得注意的是」「投資者應」等套話
- 控制在 400-550 字"""


def generate_report_summary(news_events, market_data, sentiment_data=None, calendar_events=None):
    """用 Kimi 生成報告最後的總結段落

    Args:
        news_events: 所有新聞事件列表
        market_data: 完整市場數據
        sentiment_data: 情緒數據（Fear/Greed, VIX）
        calendar_events: 經濟日曆

    Returns:
        str: 中文總結，失敗回傳 None
    """
    # 組裝今日全貌
    parts = []

    # 新聞摘要
    if news_events:
        parts.append('=== 今日重大新聞 ===')
        for e in news_events[:6]:
            title = e.get('title', '')
            direction = e.get('market_direction', '')
            narrative = e.get('narrative', '')[:150]
            parts.append(f'• {title}（{direction}）：{narrative}')

    # 市場表現
    if market_data:
        parts.append('\n=== 市場表現 ===')
        us = market_data.get('us_indices', {})
        for name in ['S&P 500', '納斯達克', '道瓊斯']:
            d = us.get(name, {})
            if d:
                parts.append(f'• {name}: {d.get("current", "?")} ({d.get("change_pct", 0):+.2f}%)')

        commodities = market_data.get('commodities', {})
        for name in ['黃金', '原油(WTI)']:
            d = commodities.get(name, {})
            if d:
                parts.append(f'• {name}: ${d.get("current", "?")} ({d.get("change_pct", 0):+.2f}%)')

        bonds = market_data.get('bonds', {})
        for name in ['美國10年期', '美國2年期']:
            d = bonds.get(name, {})
            if d:
                parts.append(f'• {name}: {d.get("current", "?")}%')

    # 情緒指標
    if sentiment_data:
        fg = sentiment_data.get('fear_greed', {})
        vix = sentiment_data.get('vix', {})
        if fg.get('score') is not None:
            parts.append(f'\n• 恐懼與貪婪指數: {fg["score"]:.0f} ({fg.get("rating", "")})')
        if vix.get('value') is not None:
            parts.append(f'• VIX: {vix["value"]:.1f}')

    # 經濟日曆
    if calendar_events:
        upcoming = [e for e in calendar_events if e.get('importance') == '高'][:3]
        if upcoming:
            parts.append('\n=== 近期重要經濟數據 ===')
            for e in upcoming:
                parts.append(f'• {e.get("date", "")} {e.get("event", "")}')

    user_prompt = '\n'.join(parts)
    user_prompt += '\n\n請根據以上資訊，撰寫今日宏觀晨報的結論總結（200-350 字）。'

    return _call_kimi(SUMMARY_SYSTEM_PROMPT, user_prompt, max_tokens=800)


# ========== 批量處理（控制 API 呼叫次數）==========

def enhance_all_news(news_events, market_snapshot=None, raw_articles_by_group=None):
    """批量增強所有新聞事件的敘事摘要

    只對前 4 個頭條主題用 AI，其他保持原樣。

    Args:
        news_events: gen_news_events() 的輸出
        market_snapshot: 市場數據快照
        raw_articles_by_group: {group_name: [articles]} 原始新聞素材

    Returns:
        list: 增強後的 news_events（原地修改）
    """
    if not MOONSHOT_API_KEY:
        print('⚠️ MOONSHOT_API_KEY 未設定，跳過 AI 增強')
        return news_events

    enhanced_count = 0
    for event in news_events:
        if not event.get('is_headline'):
            continue  # 只增強頭條（前 4 個）

        group_name = event.get('title', '')
        articles = (raw_articles_by_group or {}).get(group_name, [])

        if not articles:
            continue

        ai_narrative = enhance_news_narrative(group_name, articles, market_snapshot)
        if ai_narrative:
            event['narrative'] = ai_narrative
            enhanced_count += 1
            print(f'  ✅ AI 增強: {group_name}')
        else:
            print(f'  ⚠️ AI 失敗，保持原摘要: {group_name}')

    print(f'📝 AI 新聞增強: {enhanced_count}/{sum(1 for e in news_events if e.get("is_headline"))} 個頭條')
    return news_events
