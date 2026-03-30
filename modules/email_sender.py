"""
郵件發送模組（Gmail OAuth2 API 版）
- 使用 Gmail API + OAuth2 發信，不再依賴 SMTP App Password
- 讀取 recipients.json 管理收件人
- 自動生成 HTML 美編正文 + 純文字備用 + PDF 附件
- 支持群組發送，逐封發送保護隱私
"""

import json
import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPIENTS_FILE = os.path.join(PROJECT_ROOT, 'recipients.json')
CREDENTIALS_DIR = os.path.join(PROJECT_ROOT, 'credentials')
CLIENT_SECRET_FILE = os.path.join(CREDENTIALS_DIR, 'client_secret.json')
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, 'token.json')

SENDER_NAME = '何宣逸'
SENDER_EMAIL = 'backup901012@gmail.com'

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def _get_gmail_service():
    """取得 Gmail API service（自動處理 OAuth2 認證）"""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    # 優先從環境變數讀取 token（GitHub Actions 用）
    token_json_env = os.environ.get('GMAIL_TOKEN_JSON')
    if token_json_env:
        import json as _json
        token_data = _json.loads(token_json_env)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    # 從檔案讀取 token
    if not creds and os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Token 過期或不存在，重新認證
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token 過期，自動刷新中...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"找不到 OAuth2 client secret: {CLIENT_SECRET_FILE}\n"
                    "請先放入 Google Cloud Console 下載的 client_secret.json"
                )
            print("首次認證，將開啟瀏覽器進行 Google 登入...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # 儲存 token
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        print(f"Token 已儲存至 {TOKEN_FILE}")

    return build('gmail', 'v1', credentials=creds)


def _parse_recipient(item):
    """解析收件人項目，支援字串或 {name, email} 格式"""
    if isinstance(item, dict):
        return {'name': item.get('name'), 'email': item['email']}
    return {'name': None, 'email': item}


def load_recipients(group=None):
    """讀取收件人清單"""
    with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if group is None:
        group = config.get('active_group', 'default')

    group_data = config['groups'].get(group, {})
    return {
        'to': [_parse_recipient(r) for r in group_data.get('to', [])],
        'cc': [_parse_recipient(r) for r in group_data.get('cc', [])],
        'bcc': [_parse_recipient(r) for r in group_data.get('bcc', [])]
    }


def add_recipient(email, name=None, group='default', role='to'):
    """新增收件人"""
    with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if group not in config['groups']:
        config['groups'][group] = {'description': f'{group} 群組', 'to': [], 'cc': [], 'bcc': []}

    existing_emails = []
    for item in config['groups'][group][role]:
        existing_emails.append(item['email'] if isinstance(item, dict) else item)

    if email not in existing_emails:
        entry = {'name': name, 'email': email} if name else email
        config['groups'][group][role].append(entry)

    with open(RECIPIENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    display = f"{name} <{email}>" if name else email
    print(f"已新增 {display} 到 {group} 群組的 {role} 清單")


def remove_recipient(email, group='default', role='to'):
    """移除收件人"""
    with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if group not in config['groups']:
        print(f"未找到 {email} 在 {group} 群組的 {role} 清單中")
        return

    role_list = config['groups'][group].get(role, [])
    new_list = [item for item in role_list if (item['email'] if isinstance(item, dict) else item) != email]

    if len(new_list) < len(role_list):
        config['groups'][group][role] = new_list
        with open(RECIPIENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"已從 {group} 群組的 {role} 清單移除 {email}")
    else:
        print(f"未找到 {email} 在 {group} 群組的 {role} 清單中")


def list_recipients():
    """列出所有收件人"""
    with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    def _display_list(items):
        if not items:
            return '無'
        parts = []
        for item in items:
            if isinstance(item, dict):
                name = item.get('name', '')
                email = item.get('email', '')
                parts.append(f"{name} <{email}>" if name else email)
            else:
                parts.append(item)
        return ', '.join(parts)

    print(f"當前啟用群組：{config.get('active_group', 'default')}")
    print("=" * 50)

    for group_name, group_data in config['groups'].items():
        desc = group_data.get('description', '')
        print(f"\n群組：{group_name} ({desc})")
        print(f"  收件人 (To)：{_display_list(group_data.get('to', []))}")
        print(f"  副本 (CC)：{_display_list(group_data.get('cc', []))}")
        print(f"  密件副本 (BCC)：{_display_list(group_data.get('bcc', []))}")


def _format_pct(pct):
    if pct is None or pct == 0:
        return "0.00%"
    return f"{pct:+.2f}%"


def _format_price(price, symbol=""):
    if price is None or price == 0:
        return ""
    if price >= 1000:
        return f"${price:,.0f}"
    elif price >= 1:
        return f"${price:,.2f}"
    return f"${price:.4f}"


def _format_calendar_date(date_str):
    """格式化經濟日曆日期"""
    if not date_str:
        return date_str

    def _single_date(s):
        s = s.strip()
        parts = s.split('-')
        if len(parts) == 3:
            try:
                return f"{int(parts[1])}/{int(parts[2])}"
            except ValueError:
                return s
        return s

    if '~' in date_str:
        segments = date_str.split('~')
        return '~'.join([_single_date(seg) for seg in segments])
    return _single_date(date_str)


def generate_email_summary(json_path):
    """從 JSON 數據自動生成精簡摘要郵件正文（純文字版）"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    report_date = data.get('report_date', '')
    md = data.get('market_data', {})
    news = data.get('news_events', [])
    index_analysis = data.get('index_analysis', {})
    calendar = data.get('calendar_events', [])
    holiday = data.get('holiday_alerts', {})

    lines = [f"以下為 {report_date} 每日宏觀資訊綜合早報摘要：", ""]

    # 休市提醒
    if holiday and holiday.get('has_alerts'):
        today_closed = holiday.get('today_closed', [])
        tomorrow_closed = holiday.get('tomorrow_closed', [])
        if today_closed or tomorrow_closed:
            lines.append("【市場休市提醒】")
            if today_closed:
                names = '、'.join(today_closed) if isinstance(today_closed[0], str) else '、'.join(a.get('name_zh', '') for a in today_closed)
                lines.append(f"今日休市：{names}（數據為前一交易日收盤）")
            if tomorrow_closed:
                names = '、'.join(tomorrow_closed) if isinstance(tomorrow_closed[0], str) else '、'.join(a.get('name_zh', '') for a in tomorrow_closed)
                lines.append(f"明日休市提醒：{names}")
            lines.append("")

    # 市場總覽（用 executive_summary，更完整）
    executive = data.get('executive_summary', '')
    overall = index_analysis.get('overall_summary', '')
    if executive:
        lines.append("【市場總覽】")
        lines.append(executive)
        lines.append("")
    elif overall:
        lines.extend(["【市場總覽】", overall, ""])

    # 新聞（取每組的第一條翻譯標題，不是分類名）
    if news:
        lines.append("【宏觀重點新聞】")
        for i, n in enumerate(news[:5], 1):
            # 優先用 headlines 裡的中文標題
            headlines = n.get('headlines', [])
            if headlines:
                lines.append(f"{i}. {headlines[0]}")
            else:
                # fallback 到 description
                desc = n.get('description', n.get('title', ''))
                lines.append(f"{i}. {desc[:60]}")
        lines.append("")

    # 指數亮點
    lines.append("【指數表現亮點】")
    for region_name, region_key in [('亞洲', 'asia_indices'), ('歐洲', 'europe_indices'), ('美國', 'us_indices')]:
        indices = md.get(region_key, {})
        if indices:
            sorted_idx = sorted(indices.items(), key=lambda x: abs(x[1].get('change_pct', 0)) if isinstance(x[1], dict) else 0, reverse=True)
            items = [f"{name} {_format_pct(v.get('change_pct', 0))}" for name, v in sorted_idx[:3] if isinstance(v, dict)]
            if items:
                lines.append(f"- {region_name}：{'、'.join(items)}")
    lines.append("")

    # 加密貨幣
    crypto = md.get('crypto', {})
    if crypto:
        lines.append("【加密貨幣】")
        items = []
        for name in ['Bitcoin', 'Ethereum', 'Solana', 'XRP', 'BNB']:
            if name in crypto and isinstance(crypto[name], dict):
                v = crypto[name]
                price_str = _format_price(v.get('price', 0))
                items.append(f"{name} {_format_pct(v.get('change_pct', 0))}" + (f" ({price_str})" if price_str else ""))
        if items:
            lines.append(f"- {'、'.join(items)}")
        lines.append("")

    # 經濟日曆
    if calendar:
        lines.append("【本週經濟日曆重點】")
        for evt in calendar[:6]:
            if isinstance(evt, dict):
                lines.append(f"- {_format_calendar_date(evt.get('date', ''))} {evt.get('event', '')}")
        lines.append("")

    lines.extend(["完整報告請見附件 PDF。", "", "資料來源：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com"])
    return "\n".join(lines)


def generate_email_html(json_path):
    """從 JSON 數據生成簡潔引導式 HTML 郵件正文（v3 模板）"""
    from modules.email_template_v2 import (
        get_morning_briefing_template,
        format_pct, pct_color, vix_color_fn,
    )

    def verdict_color_fn(sentiment):
        return {'bullish': '#27ae60', 'bearish': '#e74c3c'}.get(sentiment, '#e67e22')

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    report_date = data.get('report_date', '')
    md = data.get('market_data', {})
    news = data.get('news_events', [])
    calendar = data.get('calendar_events', [])
    executive_summary = data.get('executive_summary', '')
    sentiment = data.get('sentiment_data', {})
    index_analysis = data.get('index_analysis', {})
    sector_analysis = data.get('sector_analysis', '')
    alt = data.get('alternative_data', {})

    # === 提取關鍵指標 ===
    def _get(d, *keys, default=None):
        for k in keys:
            if isinstance(d, dict):
                d = d.get(k)
            else:
                return default
        return d if d is not None else default

    sp = md.get('us_indices', {}).get('S&P 500', {})
    nq = md.get('us_indices', {}).get('納斯達克', {})
    gold = md.get('commodities', {}).get('黃金', {})
    oil = md.get('commodities', {}).get('原油(WTI)', {})
    btc = md.get('crypto', {}).get('Bitcoin', {})
    dxy = md.get('forex', {}).get('美元指數', {})  # DXY 從市場數據拿
    us10y = sentiment.get('us10y', {})
    vix = sentiment.get('vix', {})
    fg = sentiment.get('fear_greed', {})

    sp_pct = sp.get('change_pct')
    nq_pct = nq.get('change_pct')

    # === 自動生成 Market Verdict ===
    if not executive_summary:
        avg_us = ((sp_pct or 0) + (nq_pct or 0)) / 2
        if avg_us < -1:
            market_verdict = '美股顯著回落，風險偏好降溫。建議降低倉位，關注避險資產配置。'
            verdict_sentiment = 'bearish'
        elif avg_us < -0.3:
            market_verdict = '美股溫和走弱，市場觀望情緒濃厚。維持謹慎操作，等待方向明朗。'
            verdict_sentiment = 'bearish'
        elif avg_us > 1:
            market_verdict = '美股全面走強，風險偏好回升。可適度增加風險敞口，但注意高位追漲風險。'
            verdict_sentiment = 'bullish'
        elif avg_us > 0.3:
            market_verdict = '美股溫和上漲，市場情緒穩定。維持現有配置，關注輪動機會。'
            verdict_sentiment = 'bullish'
        else:
            market_verdict = '美股漲跌互見，方向不明。建議觀望為主，等待催化劑出現。'
            verdict_sentiment = 'neutral'
    else:
        market_verdict = executive_summary.split('。')[0] + '。' if '。' in executive_summary else executive_summary[:100]
        avg_us = ((sp_pct or 0) + (nq_pct or 0)) / 2
        verdict_sentiment = 'bearish' if avg_us < -0.3 else 'bullish' if avg_us > 0.3 else 'neutral'

    # === 自動生成三大焦點 ===
    focuses = []
    # 焦點1: 從新聞事件提取最重要的
    if news:
        top_news = [n for n in news if n.get('impact_level') == '高']
        if not top_news:
            top_news = news[:1]
        if top_news:
            n = top_news[0]
            focuses.append((n.get('title', '市場要聞'), n.get('description', '')))
    # 焦點2: 板塊輪動
    sr = alt.get('sector_rotation', {})
    if sr.get('regime'):
        leaders = ', '.join(sr.get('leaders', [])[:3])
        laggards = ', '.join(sr.get('laggards', [])[:3])
        focuses.append((
            f'板塊輪動：{sr["regime"]}',
            f'領漲板塊：{leaders}；落後板塊：{laggards}。Risk Spread {sr.get("risk_spread",0):+.2f}，{"防禦性板塊受追捧，資金向安全資產轉移" if sr.get("risk_spread",0) < -1 else "週期性板塊回暖，市場風險偏好改善" if sr.get("risk_spread",0) > 1 else "板塊分化不明顯，市場處於觀望狀態"}。'
        ))
    elif sector_analysis:
        focuses.append(('行業輪動動態', sector_analysis[:150]))
    # 焦點3: 情緒/VIX
    fg_score = fg.get('score')
    vix_val = vix.get('value')
    if fg_score is not None:
        fg_text = f'CNN 恐懼與貪婪指數報 {fg_score:.0f}（{fg.get("rating","")}）'
        if vix_val:
            fg_text += f'，VIX {vix_val:.1f}'
        fg_text += '。'
        if fg_score < 20:
            fg_text += '市場處於極度恐懼區間，歷史上類似水平後 3-6 個月常見反彈，但短期波動仍大。'
        elif fg_score < 40:
            fg_text += '恐懼情緒主導，逢低佈局需耐心等待企穩訊號。'
        elif fg_score > 75:
            fg_text += '市場過度樂觀，需警惕回調風險。'
        else:
            fg_text += '情緒中性偏弱，關注催化劑方向。'
        focuses.append(('市場情緒與波動率', fg_text))

    # 補足三個焦點
    while len(focuses) < 3:
        if news and len(focuses) < len(news):
            n = news[len(focuses)]
            focuses.append((n.get('title', ''), n.get('description', '')))
        else:
            focuses.append(('待觀察', '暫無額外焦點。'))

    # === 風險與機會 ===
    risks = []
    opportunities = []

    if fg_score is not None and fg_score < 25:
        opportunities.append('恐懼指數極低（反向指標），歷史上為中期買點')
    if vix_val and vix_val > 25:
        risks.append(f'VIX {vix_val:.0f} 偏高，短期波動劇烈')
    if sp_pct and sp_pct < -1:
        risks.append(f'S&P 500 單日跌 {sp_pct:.2f}%，空方動能強')
    if gold and gold.get('change_pct', 0) > 1:
        opportunities.append('黃金走強，避險資產配置價值上升')
    if oil and oil.get('change_pct', 0) < -2:
        risks.append('油價大跌，可能反映經濟放緩預期')

    # 從替代數據補充
    em = alt.get('em_currency_stress', {})
    if em.get('avg_stress', 0) > 5:
        risks.append(f'新興市場貨幣壓力偏高（{em["avg_stress"]:.1f}），資金外流風險')
    vs = alt.get('volatility_term_structure', {})
    if vs.get('ratio', 0) > 1.05:
        risks.append('VIX 期限結構倒掛，市場對沖需求急升')
    mb = alt.get('market_breadth', {})
    rsp_spy = mb.get('rsp_spy', {})
    if rsp_spy.get('change_1m_pct', 0) > 1:
        opportunities.append('市場寬度改善，上漲不再僅靠少數權重股')

    if not risks:
        risks = ['目前無顯著風險信號']
    if not opportunities:
        opportunities = ['持續觀察中']

    # === 今日關注 ===
    watch = []
    for evt in calendar[:4]:
        if isinstance(evt, dict):
            watch.append(f'{_format_calendar_date(evt.get("date",""))} {evt.get("event","")}')
    if not watch:
        watch = ['本日無重大經濟數據發布']

    # === 生成焦點的簡短版（一句話）===
    def _brief(body, max_len=50):
        """截取描述的第一句話作為簡短摘要"""
        if not body:
            return ''
        first = body.split('。')[0]
        if len(first) > max_len:
            first = first[:max_len] + '...'
        return first

    # === 填充模板 ===
    template = get_morning_briefing_template()

    # DXY 和 BTC 數據
    dxy_pct = dxy.get('change_pct') if isinstance(dxy, dict) else None
    btc_pct = btc.get('change_pct') if isinstance(btc, dict) else None

    # 焦點標題（帶簡短說明）
    focus_titles = []
    for title, body in focuses[:3]:
        brief = _brief(body, 60)
        if brief:
            focus_titles.append(f'{title} — {brief}')
        else:
            focus_titles.append(title)

    # === 【市場總覽】 ===
    overview_parts = []
    oil_chg = oil.get('change_pct', 0) if oil else 0
    gold_chg = gold.get('change_pct', 0) if gold else 0
    fg_score = fg.get('score')

    # 整體方向
    avg_us = ((sp_pct or 0) + (nq_pct or 0)) / 2
    if avg_us < -1:
        overview_parts.append('全球市場今日普遍承壓')
    elif avg_us < -0.3:
        overview_parts.append('全球市場今日溫和走弱')
    elif avg_us > 1:
        overview_parts.append('全球市場今日全面上漲')
    elif avg_us > 0.3:
        overview_parts.append('全球市場今日穩中偏強')
    else:
        overview_parts.append('全球市場今日漲跌互見')

    # 驅動因素
    drivers = []
    if abs(oil_chg) > 3:
        drivers.append('能源供應風險')
    if fg_score and fg_score < 25:
        drivers.append('避險情緒升溫')
    if vix_val and vix_val > 25:
        drivers.append('波動率飆升')
    if abs(gold_chg) > 2:
        drivers.append(f'黃金{"走強" if gold_chg > 0 else "回落"}')
    if drivers:
        overview_parts.append('，主要受到' + '及'.join(drivers[:2]) + '的影響')
    overview_parts.append('。')

    # 情緒總結
    if fg_score is not None:
        if fg_score < 20:
            overview_parts.append(f'市場情緒極度恐懼（CNN Fear & Greed: {fg_score:.0f}），VIX {vix_val:.1f}。資金流向避險資產。')
        elif fg_score < 40:
            overview_parts.append(f'市場情緒偏謹慎（CNN Fear & Greed: {fg_score:.0f}），觀望氣氛濃厚。')
        elif fg_score > 75:
            overview_parts.append(f'市場情緒樂觀（CNN Fear & Greed: {fg_score:.0f}），需警惕過度追高。')

    market_overview = ''.join(overview_parts)

    # === 【宏觀重點新聞】 ===
    # 從所有新聞組收集標題，過濾掉非金融相關的垃圾
    import re as _re
    def _clean(text):
        return _re.sub(r'\s*[-–—]\s*(reuters|bloomberg|cnbc|bbc|wsj|cnn|ft|com)[\w.\s]*$', '', text, flags=_re.IGNORECASE).strip()

    # 上游已做好品質控制，直接從各組取最佳標題+敘事
    news_lines = []
    seen = set()
    if news:
        for n in news:
            for h in n.get('headlines', []):
                h = _clean(h)
                if len(h) > 10 and h[:15] not in seen:
                    seen.add(h[:15])
                    narrative = n.get('narrative', '')
                    brief = ''
                    if narrative:
                        first_sentence = narrative.split('。')[0]
                        if len(first_sentence) > 10:
                            brief = first_sentence
                    if brief:
                        news_lines.append(f'{len(news_lines)+1}. {h}<br>\n<span style="color:#666;font-size:13px;">　　{brief}</span>')
                    else:
                        news_lines.append(f'{len(news_lines)+1}. {h}')
                    break
            if len(news_lines) >= 5:
                break
    news_highlights = '<br>\n'.join(news_lines) if news_lines else '暫無重大新聞。'

    # === 【指數表現亮點】 ===
    index_lines = []
    for region_name, region_key in [('亞洲', 'asia_indices'), ('歐洲', 'europe_indices'), ('美國', 'us_indices')]:
        indices = md.get(region_key, {})
        if not indices:
            continue
        sorted_idx = sorted(indices.items(), key=lambda x: abs(x[1].get('change_pct', 0)) if isinstance(x[1], dict) else 0, reverse=True)
        items = [f'{name} {x.get("change_pct",0):+.2f}%' for name, x in sorted_idx[:3] if isinstance(x, dict)]
        if items:
            index_lines.append(f'- {region_name}：{"、".join(items)}')
    index_highlights = '<br>\n'.join(index_lines) if index_lines else ''

    # === 【加密貨幣】 ===
    crypto = md.get('crypto', {})
    crypto_items = []
    for name, c in crypto.items():
        if isinstance(c, dict) and c.get('change_pct') is not None:
            crypto_items.append(f'{name} {c["change_pct"]:+.2f}%')
    crypto_highlights = '- ' + '、'.join(crypto_items) if crypto_items else '暫無數據'

    # === 【本週經濟日曆重點】 ===
    cal_lines = []
    for evt in calendar[:6]:
        if isinstance(evt, dict):
            cal_lines.append(f'- {evt.get("date","")} {evt.get("event","")}')
    calendar_highlights = '<br>\n'.join(cal_lines) if cal_lines else '本週暫無重大經濟數據。'

    # 構建 v2 模板所需的完整數據
    from modules.email_template_v2 import build_list_items, format_pct, pct_color, vix_color_fn, verdict_color_fn

    # 休市提醒
    holiday_html = ''
    holiday_data = data.get('holiday_alerts', {})
    if holiday_data and holiday_data.get('has_alerts'):
        from modules.email_template_v2 import get_holiday_alert_block
        parts = []
        if holiday_data.get('today_closed'):
            names = '、'.join(m.get('market','') for m in holiday_data['today_closed'])
            parts.append(f'今日休市：{names}')
        if holiday_data.get('tomorrow_closed'):
            names = '、'.join(m.get('market','') for m in holiday_data['tomorrow_closed'])
            parts.append(f'明日休市：{names}')
        if parts:
            holiday_html = get_holiday_alert_block().format(holiday_text='　|　'.join(parts))

    template_data = {
        'report_date': report_date,
        'holiday_alert_html': holiday_html,
        'market_verdict': market_verdict,
        'verdict_color': verdict_color_fn(verdict_sentiment),
        'focus_1_title': focus_titles[0] if len(focus_titles) > 0 else '',
        'focus_1_body': focuses[0][1] if len(focuses) > 0 else '',
        'focus_2_title': focus_titles[1] if len(focus_titles) > 1 else '',
        'focus_2_body': focuses[1][1] if len(focuses) > 1 else '',
        'focus_3_title': focus_titles[2] if len(focus_titles) > 2 else '',
        'focus_3_body': focuses[2][1] if len(focuses) > 2 else '',
        'sp500_val': f'{sp.get("current",0):,.0f}' if sp else 'N/A',
        'sp500_pct': format_pct(sp_pct),
        'sp500_color': pct_color(sp_pct),
        'nasdaq_val': f'{nq.get("current",0):,.0f}' if nq else 'N/A',
        'nasdaq_pct': format_pct(nq_pct),
        'nasdaq_color': pct_color(nq_pct),
        'dxy_val': f'{dxy.get("current",0):.2f}' if isinstance(dxy, dict) and dxy.get("current") else 'N/A',
        'dxy_pct': format_pct(dxy.get('change_pct') if isinstance(dxy, dict) else None),
        'dxy_color': pct_color(dxy.get('change_pct') if isinstance(dxy, dict) else None),
        'us10y_val': f'{us10y.get("yield",0):.3f}%' if us10y.get("yield") else 'N/A',
        'us10y_pct': f'{us10y.get("change",0):+.4f}' if us10y.get("change") else 'N/A',
        'us10y_color': pct_color(us10y.get('change', 0)),
        'vix_val': f'{vix_val:.1f}' if vix_val else 'N/A',
        'vix_color': vix_color_fn(vix_val),
        'gold_val': f'${gold.get("current",0):,.0f}' if gold else 'N/A',
        'gold_pct': format_pct(gold.get('change_pct') if gold else None),
        'gold_color': pct_color(gold.get('change_pct') if gold else None),
        'oil_val': f'${oil.get("current",0):.1f}' if oil else 'N/A',
        'oil_pct': format_pct(oil.get('change_pct') if oil else None),
        'oil_color': pct_color(oil.get('change_pct') if oil else None),
        'btc_val': f'${btc.get("current",0):,.0f}' if btc else 'N/A',
        'btc_pct': format_pct(btc.get('change_pct') if isinstance(btc, dict) else None),
        'btc_color': pct_color(btc.get('change_pct') if isinstance(btc, dict) else None),
        'risk_items': build_list_items(risks),
        'opportunity_items': build_list_items(opportunities),
        'watch_items': build_list_items(watch),
        'sender_name': SENDER_NAME,
    }

    return template.format(**template_data)


def send_report_email(report_date, pdf_path, json_path=None, group=None):
    """通過 Gmail API 全自動發送報告郵件

    格式：HTML 美編正文 + 純文字備用 + PDF 附件
    逐封發送，每位收件者只看到自己
    """
    recipients = load_recipients(group)

    # 合併所有收件人，逐封發送
    all_recipients = list(recipients.get('to', [])) + list(recipients.get('cc', [])) + list(recipients.get('bcc', []))
    seen = set()
    unique_recipients = []
    for r in all_recipients:
        email = r['email'] if isinstance(r, dict) else r
        if email not in seen:
            seen.add(email)
            unique_recipients.append(r)
    all_recipients = unique_recipients
    if not all_recipients:
        print("錯誤：沒有收件人")
        return False

    # 自動推斷 JSON 路徑
    if json_path is None:
        report_dir = os.path.dirname(pdf_path)
        json_path = os.path.join(report_dir, f"raw_data_{report_date}.json")

    subject = f"每日宏觀資訊綜合早報 | {report_date}"

    # 生成正文
    plain_content = f"以下為 {report_date} 每日宏觀資訊綜合早報：\n\n完整報告請見附件 PDF。\n\n資料來源：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com"
    html_content = None
    if os.path.exists(json_path):
        try:
            plain_content = generate_email_summary(json_path)
            html_content = generate_email_html(json_path)
            print("已生成 HTML 美編郵件正文")
        except Exception as e:
            print(f"生成摘要失敗：{e}")

    # 讀取 PDF 附件
    pdf_payload = None
    pdf_filename = None
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            pdf_payload = f.read()
        pdf_filename = os.path.basename(pdf_path)
        print(f"已載入 PDF：{pdf_filename} ({len(pdf_payload)/1024:.0f} KB)")
    else:
        print(f"警告：PDF 不存在：{pdf_path}")

    # 取得 Gmail API service
    print("正在連接 Gmail API...")
    service = _get_gmail_service()

    print(f"\n正在逐封發送郵件...")
    print(f"  發件人：{SENDER_NAME} <{SENDER_EMAIL}>")
    print(f"  收件人：{len(all_recipients)} 位")

    success_count = 0
    fail_list = []

    for recipient in all_recipients:
        try:
            if isinstance(recipient, dict):
                rcpt_email = recipient['email']
                rcpt_name = recipient.get('name')
                rcpt_display = f"{rcpt_name} <{rcpt_email}>" if rcpt_name else rcpt_email
            else:
                rcpt_email = recipient
                rcpt_display = recipient

            # 組裝 MIME: mixed > alternative(plain+html) + PDF
            msg = MIMEMultipart('mixed')
            msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
            msg['To'] = rcpt_display
            msg['Subject'] = subject

            alt = MIMEMultipart('alternative')
            alt.attach(MIMEText(plain_content, 'plain', 'utf-8'))
            if html_content:
                alt.attach(MIMEText(html_content, 'html', 'utf-8'))
            msg.attach(alt)

            if pdf_payload:
                pdf_attachment = MIMEBase('application', 'pdf')
                pdf_attachment.set_payload(pdf_payload)
                encoders.encode_base64(pdf_attachment)
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
                msg.attach(pdf_attachment)

            # Gmail API 用 base64url 編碼
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
            service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            success_count += 1
            print(f"  OK {rcpt_display}")
        except Exception as e:
            fail_list.append(rcpt_display)
            print(f"  FAIL {rcpt_display} -- {e}")

    print(f"\n發送完成：{success_count}/{len(all_recipients)} 成功")
    if fail_list:
        print(f"失敗名單：{', '.join(fail_list)}")
    return success_count > 0


# CLI 介面
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法：")
        print("  python email_sender.py list                              - 列出所有收件人")
        print("  python email_sender.py add <email> [name] [group] [role] - 新增收件人")
        print("  python email_sender.py remove <email> [group] [role]     - 移除收件人")
        print("  python email_sender.py send <date> <pdf_path> [json_path] - 發送報告")
        print("  python email_sender.py preview <json_path>               - 預覽郵件摘要")
        print("  python email_sender.py auth                              - 執行 OAuth2 認證")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'list':
        list_recipients()
    elif cmd == 'add':
        email = sys.argv[2]
        name = sys.argv[3] if len(sys.argv) > 3 else None
        group = sys.argv[4] if len(sys.argv) > 4 else 'default'
        role = sys.argv[5] if len(sys.argv) > 5 else 'to'
        add_recipient(email, name, group, role)
    elif cmd == 'remove':
        email = sys.argv[2]
        group = sys.argv[3] if len(sys.argv) > 3 else 'default'
        role = sys.argv[4] if len(sys.argv) > 4 else 'to'
        remove_recipient(email, group, role)
    elif cmd == 'send':
        report_date = sys.argv[2]
        pdf_path = sys.argv[3]
        json_path = sys.argv[4] if len(sys.argv) > 4 else None
        send_report_email(report_date, pdf_path, json_path)
    elif cmd == 'preview':
        json_path = sys.argv[2]
        print(generate_email_summary(json_path))
    elif cmd == 'auth':
        print("執行 OAuth2 認證...")
        service = _get_gmail_service()
        print("認證成功！Gmail API 已就緒。")
    else:
        print(f"未知命令：{cmd}")
