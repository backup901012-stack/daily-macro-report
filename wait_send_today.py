#!/usr/bin/env python3
"""等待到 07:30 (GMT+8) 後發送報告 Email"""
import time
import datetime
import sys
import os

# 確保在項目目錄
os.chdir('/home/ubuntu/daily-macro-report')
sys.path.insert(0, '/home/ubuntu/daily-macro-report')

DATE = '2026-03-20'
PDF_PATH = f'reports/daily_report_{DATE}.pdf'
JSON_PATH = f'reports/raw_data_{DATE}.json'

# 確認文件存在
for f in [PDF_PATH, JSON_PATH]:
    if not os.path.exists(f):
        print(f"ERROR: {f} not found!")
        sys.exit(1)

# 等待到 07:30
now = datetime.datetime.now()
target = now.replace(hour=7, minute=30, second=0, microsecond=0)
diff = (target - now).total_seconds()

if diff > 0:
    print(f"[{now.strftime('%H:%M:%S')}] 等待 {diff:.0f} 秒 ({diff/60:.1f} 分鐘) 到 07:30...")
    # 每 60 秒打印一次進度
    while diff > 0:
        sleep_time = min(60, diff)
        time.sleep(sleep_time)
        now = datetime.datetime.now()
        diff = (target - now).total_seconds()
        if diff > 0:
            print(f"  [{now.strftime('%H:%M:%S')}] 剩餘 {diff:.0f} 秒...")
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 到達 07:30！")
else:
    print(f"[{now.strftime('%H:%M:%S')}] 已過 07:30，立即發送")

# 發送 Email
print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 開始發送 Email...")
from modules.email_sender import send_report_email
result = send_report_email(DATE, PDF_PATH, JSON_PATH)
print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Email 發送完成！")
print(f"結果: {result}")
