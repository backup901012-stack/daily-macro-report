"""
郵件發送模組
- 讀取 recipients.json 管理收件人
- 支持群組發送
- 整合 Gmail MCP 發送
"""

import json
import os
import subprocess

RECIPIENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'recipients.json')


def load_recipients(group=None):
    """讀取收件人清單"""
    with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if group is None:
        group = config.get('active_group', 'default')
    
    group_data = config['groups'].get(group, {})
    return {
        'to': group_data.get('to', []),
        'cc': group_data.get('cc', []),
        'bcc': group_data.get('bcc', [])
    }


def add_recipient(email, group='default', role='to'):
    """新增收件人
    
    Args:
        email: 郵箱地址
        group: 群組名稱
        role: 角色 ('to', 'cc', 'bcc')
    """
    with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if group not in config['groups']:
        config['groups'][group] = {
            'description': f'{group} 群組',
            'to': [],
            'cc': [],
            'bcc': []
        }
    
    if email not in config['groups'][group][role]:
        config['groups'][group][role].append(email)
    
    with open(RECIPIENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"已新增 {email} 到 {group} 群組的 {role} 清單")


def remove_recipient(email, group='default', role='to'):
    """移除收件人"""
    with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if group in config['groups'] and email in config['groups'][group].get(role, []):
        config['groups'][group][role].remove(email)
        with open(RECIPIENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"已從 {group} 群組的 {role} 清單移除 {email}")
    else:
        print(f"未找到 {email} 在 {group} 群組的 {role} 清單中")


def list_recipients():
    """列出所有收件人"""
    with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print(f"當前啟用群組：{config.get('active_group', 'default')}")
    print("=" * 50)
    
    for group_name, group_data in config['groups'].items():
        desc = group_data.get('description', '')
        print(f"\n群組：{group_name} ({desc})")
        print(f"  收件人 (To)：{', '.join(group_data.get('to', [])) or '無'}")
        print(f"  副本 (CC)：{', '.join(group_data.get('cc', [])) or '無'}")
        print(f"  密件副本 (BCC)：{', '.join(group_data.get('bcc', [])) or '無'}")


def send_report_email(report_date, pdf_path, group=None):
    """通過 Gmail MCP 發送報告郵件
    
    Args:
        report_date: 報告日期字串 (如 '2026-02-24')
        pdf_path: PDF 報告的絕對路徑
        group: 收件群組名稱，None 則使用 active_group
    """
    recipients = load_recipients(group)
    
    if not recipients['to']:
        print("錯誤：沒有收件人")
        return False
    
    # 構建郵件內容
    subject = f"每日宏觀資訊綜合早報 | {report_date}"
    content = f"""您好，

附上今日的每日宏觀資訊綜合早報（{report_date}），內容涵蓋：

一、各國指數表現（亞洲/歐洲/美國）
二、宏觀重點新聞
三、商品、外匯與債券
四、當日熱門股票（美股/港股/日股/台股）
五、加密貨幣市場
六、本週經濟日曆

完整報告請見附件 PDF。

資料來源：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com"""

    # 構建 MCP 調用參數
    message = {
        "to": recipients['to'],
        "subject": subject,
        "content": content,
        "attachments": [pdf_path]
    }
    
    if recipients['cc']:
        message['cc'] = recipients['cc']
    if recipients['bcc']:
        message['bcc'] = recipients['bcc']
    
    mcp_input = json.dumps({"messages": [message]}, ensure_ascii=False)
    
    print(f"發送報告郵件...")
    print(f"  收件人：{', '.join(recipients['to'])}")
    if recipients['cc']:
        print(f"  副本：{', '.join(recipients['cc'])}")
    if recipients['bcc']:
        print(f"  密件副本：{', '.join(recipients['bcc'])}")
    
    # 調用 Gmail MCP
    try:
        result = subprocess.run(
            ['manus-mcp-cli', 'tool', 'call', 'gmail_send_messages',
             '--server', 'gmail', '--input', mcp_input],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            print(f"郵件發送成功！")
            return True
        else:
            print(f"郵件發送失敗：{result.stderr}")
            return False
    except Exception as e:
        print(f"郵件發送異常：{e}")
        return False


# CLI 介面
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法：")
        print("  python email_sender.py list                          - 列出所有收件人")
        print("  python email_sender.py add <email> [group] [role]    - 新增收件人")
        print("  python email_sender.py remove <email> [group] [role] - 移除收件人")
        print("  python email_sender.py send <date> <pdf_path>        - 發送報告")
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
        send_report_email(report_date, pdf_path)
    else:
        print(f"未知命令：{cmd}")
