"""
郵件發送模組
- 讀取 recipients.json 管理收件人
- 自動從報告數據生成精簡摘要郵件正文
- 支持群組發送
- 使用 SMTP 全自動發送（無需人工介入）
"""

import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

RECIPIENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'recipients.json')

# SMTP 配置
SMTP_CONFIG = {
    'server': 'smtp.gmail.com',
    'port': 587,
    'sender_email': 'cbe566@gmail.com',
    'app_password': 'bpws gyoc nsur evdc',  # Google 應用程式密碼
    'sender_name': '何宣逸'
}


def _parse_recipient(item):
    """解析收件人項目，支援字串或 {name, email} 格式
    
    Returns:
        dict: {'name': str or None, 'email': str}
    """
    if isinstance(item, dict):
        return {'name': item.get('name'), 'email': item['email']}
    else:
        return {'name': None, 'email': item}


def _format_recipient_addr(recipient):
    """將收件人格式化為 RFC 5322 地址格式
    
    Args:
        recipient: dict with 'name' and 'email' keys
    Returns:
        str: 'Name <email>' or 'email'
    """
    if recipient.get('name'):
        return f"{recipient['name']} <{recipient['email']}>"
    return recipient['email']


def load_recipients(group=None):
    """讀取收件人清單
    
    支援兩種格式：
    - 舊格式（純字串）: ["a@b.com", "c@d.com"]
    - 新格式（帶名字）: [{"name": "Alice", "email": "a@b.com"}, ...]
    
    Returns:
        dict: {'to': [{'name': str|None, 'email': str}, ...], 'cc': [...], 'bcc': [...]}
    """
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
        config['groups'][group] = {
            'description': f'{group} 群組',
            'to': [],
            'cc': [],
            'bcc': []
        }
    
    # 檢查是否已存在（相容新舊格式）
    existing_emails = []
    for item in config['groups'][group][role]:
        if isinstance(item, dict):
            existing_emails.append(item['email'])
        else:
            existing_emails.append(item)
    
    if email not in existing_emails:
        entry = {'name': name, 'email': email} if name else email
        config['groups'][group][role].append(entry)
    
    with open(RECIPIENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    display = f"{name} <{email}>" if name else email
    print(f"已新增 {display} 到 {group} 群組的 {role} 清單")


def remove_recipient(email, group='default', role='to'):
    """移除收件人（相容新舊格式）"""
    with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if group not in config['groups']:
        print(f"未找到 {email} 在 {group} 群組的 {role} 清單中")
        return
    
    role_list = config['groups'][group].get(role, [])
    found = False
    new_list = []
    for item in role_list:
        item_email = item['email'] if isinstance(item, dict) else item
        if item_email == email:
            found = True
        else:
            new_list.append(item)
    
    if found:
        config['groups'][group][role] = new_list
        with open(RECIPIENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"已從 {group} 群組的 {role} 清單移除 {email}")
    else:
        print(f"未找到 {email} 在 {group} 群組的 {role} 清單中")


def list_recipients():
    """列出所有收件人（顯示名字）"""
    with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    def _display_list(items):
        """格式化收件人列表顯示"""
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
    """格式化漲跌幅"""
    if pct is None or pct == 0:
        return "0.00%"
    return f"{pct:+.2f}%"


def _format_price(price, symbol=""):
    """格式化價格"""
    if price is None or price == 0:
        return ""
    if price >= 1000:
        return f"${price:,.0f}"
    elif price >= 1:
        return f"${price:,.2f}"
    else:
        return f"${price:.4f}"


def _format_calendar_date(date_str):
    """格式化經濟日曆日期，支援單一日期和日期範圍
    
    支援格式：
      - '2026-03-05'              → '3/5'
      - '2026-03-04 ~ 2026-03-08' → '3/4~3/8'
      - 其他格式                   → 原樣返回
    """
    if not date_str:
        return date_str
    
    def _single_date(s):
        """將 YYYY-MM-DD 轉為 M/D"""
        s = s.strip()
        parts = s.split('-')
        if len(parts) == 3:
            try:
                return f"{int(parts[1])}/{int(parts[2])}"
            except ValueError:
                return s
        return s
    
    # 處理日期範圍（含 ~ 分隔符）
    if '~' in date_str:
        segments = date_str.split('~')
        formatted = [_single_date(seg) for seg in segments]
        return '~'.join(formatted)
    
    # 單一日期
    return _single_date(date_str)


def generate_email_summary(json_path):
    """從 JSON 數據自動生成精簡摘要郵件正文"""
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    report_date = data.get('report_date', '')
    md = data.get('market_data', {})
    news = data.get('news_events', [])
    index_analysis = data.get('index_analysis', {})
    calendar = data.get('calendar_events', [])
    holiday = data.get('holiday_alerts', {})
    
    lines = []
    lines.append(f"以下為 {report_date} 每日宏觀資訊綜合早報摘要：")
    lines.append("")
    
    # ===== 休市提醒 =====
    if holiday and holiday.get('has_alerts'):
        today_closed = holiday.get('today_closed', [])
        tomorrow_closed = holiday.get('tomorrow_closed', [])
        upcoming = holiday.get('upcoming_holidays', [])
        
        if today_closed or tomorrow_closed:
            lines.append("【市場休市提醒】")
            if today_closed:
                names = '、'.join(today_closed) if isinstance(today_closed[0], str) else '、'.join(a.get('name_zh', '') for a in today_closed)
                lines.append(f"\u26a0\ufe0f 今日休市：{names}（數據為前一交易日收盤）")
            if tomorrow_closed:
                names = '、'.join(tomorrow_closed) if isinstance(tomorrow_closed[0], str) else '、'.join(a.get('name_zh', '') for a in tomorrow_closed)
                next_biz = holiday.get('next_business_day', '')
                lines.append(f"\U0001f4c5 明日休市提醒：{names}（{next_biz}）")
            if upcoming:
                for h in upcoming:
                    if isinstance(h, dict):
                        date_str = h.get('date', '')
                        if '-' in date_str:
                            parts = date_str.split('-')
                            date_str = f"{parts[1]}/{parts[2]}"
                        weekday = h.get('weekday', '')
                        markets = h.get('markets', [])
                        if isinstance(markets, list):
                            mkt_str = '、'.join(markets)
                        else:
                            mkt_str = str(markets)
                        lines.append(f"- {date_str}（週{weekday}）{mkt_str} 休市")
            lines.append("")
    
    # ===== 市場總覽 =====
    overall = index_analysis.get('overall_summary', '')
    if overall:
        lines.append("【市場總覽】")
        lines.append(overall)
        lines.append("")
    
    # ===== 宏觀重點新聞 =====
    if news:
        lines.append("【宏觀重點新聞】")
        for i, n in enumerate(news[:5], 1):
            title = n.get('title', '')
            lines.append(f"{i}. {title}")
        lines.append("")
    
    # ===== 指數表現亮點 =====
    lines.append("【指數表現亮點】")
    
    # 亞洲
    asia = md.get('asia_indices', {})
    if asia:
        asia_items = []
        sorted_asia = sorted(asia.items(), key=lambda x: abs(x[1].get('change_pct', 0)) if isinstance(x[1], dict) else 0, reverse=True)
        for name, v in sorted_asia[:3]:
            if isinstance(v, dict):
                pct = v.get('change_pct', 0)
                asia_items.append(f"{name} {_format_pct(pct)}")
        if asia_items:
            lines.append(f"- 亞洲：{'、'.join(asia_items)}")
    
    # 歐洲
    europe = md.get('europe_indices', {})
    if europe:
        europe_items = []
        sorted_europe = sorted(europe.items(), key=lambda x: abs(x[1].get('change_pct', 0)) if isinstance(x[1], dict) else 0, reverse=True)
        for name, v in sorted_europe[:3]:
            if isinstance(v, dict):
                pct = v.get('change_pct', 0)
                europe_items.append(f"{name} {_format_pct(pct)}")
        if europe_items:
            lines.append(f"- 歐洲：{'、'.join(europe_items)}")
    
    # 美國
    us = md.get('us_indices', {})
    if us:
        us_items = []
        sorted_us = sorted(us.items(), key=lambda x: abs(x[1].get('change_pct', 0)) if isinstance(x[1], dict) else 0, reverse=True)
        for name, v in sorted_us[:3]:
            if isinstance(v, dict):
                pct = v.get('change_pct', 0)
                us_items.append(f"{name} {_format_pct(pct)}")
        if us_items:
            lines.append(f"- 美國：{'、'.join(us_items)}")
    
    lines.append("")
    
    # ===== 加密貨幣 =====
    crypto = md.get('crypto', {})
    if crypto:
        lines.append("【加密貨幣】")
        crypto_items = []
        priority = ['Bitcoin', 'Ethereum', 'Solana', 'XRP', 'BNB']
        for name in priority:
            if name in crypto and isinstance(crypto[name], dict):
                v = crypto[name]
                pct = v.get('change_pct', 0)
                price = v.get('price', 0)
                price_str = _format_price(price) if price else ""
                if price_str:
                    crypto_items.append(f"{name} {_format_pct(pct)} ({price_str})")
                else:
                    crypto_items.append(f"{name} {_format_pct(pct)}")
        if crypto_items:
            lines.append(f"- {'、'.join(crypto_items)}")
        lines.append("")
    
    # ===== 本週經濟日曆重點 =====
    if calendar:
        lines.append("【本週經濟日曆重點】")
        for evt in calendar[:6]:
            if isinstance(evt, dict):
                date = evt.get('date', '')
                event_name = evt.get('event', '')
                short_date = _format_calendar_date(date)
                lines.append(f"- {short_date} {event_name}")
        lines.append("")
    
    # ===== 結尾 =====
    lines.append("完整報告請見附件 PDF。")
    lines.append("")
    lines.append("資料來源：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com")
    
    return "\n".join(lines)


def send_report_email(report_date, pdf_path, json_path=None, group=None):
    """通過 SMTP 全自動發送報告郵件（逐封發送，保護隱私 + 相容企業信箱）
    
    每位收件者收到一封獨立信件，To 欄位只有自己，
    彼此看不到其他收件者，且不會被企業郵件系統擋掉。
    
    Args:
        report_date: 報告日期字串 (如 '2026-02-24')
        pdf_path: PDF 報告的絕對路徑
        json_path: JSON 數據文件路徑（用於生成摘要），None 則自動推斷
        group: 收件群組名稱，None 則使用 active_group
    """
    recipients = load_recipients(group)
    
    # 合併所有收件人（不管放在 to/cc/bcc，全部逐封發送）
    all_recipients = list(recipients.get('to', [])) + list(recipients.get('cc', [])) + list(recipients.get('bcc', []))
    # 去重（以 email 為 key）
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
    
    # 生成郵件正文
    subject = f"每日宏觀資訊綜合早報 | {report_date}"
    
    if os.path.exists(json_path):
        try:
            content = generate_email_summary(json_path)
            print("已從數據自動生成郵件摘要")
        except Exception as e:
            print(f"生成摘要失敗，使用預設正文：{e}")
            content = _fallback_content(report_date)
    else:
        print(f"JSON 數據文件不存在：{json_path}，使用預設正文")
        content = _fallback_content(report_date)
    
    # 讀取 PDF 附件（只讀一次，重複使用）
    pdf_payload = None
    pdf_filename = None
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            pdf_payload = f.read()
        pdf_filename = os.path.basename(pdf_path)
        print(f"已載入 PDF：{pdf_filename}")
    else:
        print(f"警告：PDF 文件不存在：{pdf_path}")
    
    # 逐封發送
    print(f"\n正在逐封發送郵件...")
    print(f"  發件人：{SMTP_CONFIG['sender_name']} <{SMTP_CONFIG['sender_email']}>")
    print(f"  收件人：{len(all_recipients)} 位")
    
    success_count = 0
    fail_list = []
    
    try:
        server = smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port'])
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_CONFIG['sender_email'], SMTP_CONFIG['app_password'])
        
        for recipient in all_recipients:
            try:
                # 解析收件人資訊
                if isinstance(recipient, dict):
                    rcpt_email = recipient['email']
                    rcpt_name = recipient.get('name')
                    rcpt_display = f"{rcpt_name} <{rcpt_email}>" if rcpt_name else rcpt_email
                else:
                    rcpt_email = recipient
                    rcpt_name = None
                    rcpt_display = recipient
                
                # 每封信獨立構建，To 只有該收件者
                msg = MIMEMultipart()
                msg['From'] = f"{SMTP_CONFIG['sender_name']} <{SMTP_CONFIG['sender_email']}>"
                msg['To'] = rcpt_display
                msg['Subject'] = subject
                
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
                
                # 附加 PDF
                if pdf_payload:
                    pdf_attachment = MIMEBase('application', 'pdf')
                    pdf_attachment.set_payload(pdf_payload)
                    encoders.encode_base64(pdf_attachment)
                    pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
                    msg.attach(pdf_attachment)
                
                server.sendmail(SMTP_CONFIG['sender_email'], [rcpt_email], msg.as_string())
                success_count += 1
                print(f"  ✅ {rcpt_display}")
            except Exception as e:
                fail_list.append(rcpt_display)
                print(f"  ❌ {rcpt_display} — {e}")
        
        server.quit()
        
        print(f"\n發送完成：{success_count}/{len(all_recipients)} 成功")
        if fail_list:
            print(f"失敗名單：{', '.join(fail_list)}")
        return success_count > 0
    
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ SMTP 認證失敗：{e}")
        print("請確認應用程式密碼是否正確。")
        return False
    except smtplib.SMTPException as e:
        print(f"\n❌ SMTP 連線失敗：{e}")
        return False
    except Exception as e:
        print(f"\n❌ 郵件發送異常：{e}")
        return False


def _fallback_content(report_date):
    """預設郵件正文（當 JSON 不可用時）"""
    return f"""以下為 {report_date} 每日宏觀資訊綜合早報：

完整報告請見附件 PDF。

資料來源：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com"""


# CLI 介面
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法：")
        print("  python email_sender.py list                              - 列出所有收件人")
        print("  python email_sender.py add <email> [group] [role]        - 新增收件人")
        print("  python email_sender.py remove <email> [group] [role]     - 移除收件人")
        print("  python email_sender.py send <date> <pdf_path> [json_path] - 發送報告")
        print("  python email_sender.py preview <json_path>               - 預覽郵件摘要")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'list':
        list_recipients()
    elif cmd == 'add':
        email = sys.argv[2]
        group = sys.argv[3] if len(sys.argv) > 3 else 'default'
        role = sys.argv[4] if len(sys.argv) > 4 else 'to'
        add_recipient(email, group, role)
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
    else:
        print(f"未知命令：{cmd}")
