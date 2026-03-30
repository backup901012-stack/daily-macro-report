# 每日宏觀資訊綜合早報

## 自動化排程
- 數據收集：GitHub Actions `daily-report.yml`，UTC 21:30（台北 05:30）
- 報告發送：`daily-send.yml`，由數據收集完成後 `workflow_run` 自動觸發 + 備用 cron UTC 22:50
- Gmail 密碼存 GitHub Secrets（`GMAIL_APP_PASSWORD`），不在代碼中
- 必要數據缺失會 `exit 1` 中止發送

## 報告結構（四段式敘事，2026-03-30 確認）
```
第一段：發生了什麼
  一、宏觀重點新聞（中文翻譯+分類標籤+敘事摘要+市場數據）
  二、全球指數表現 + 技術面關鍵位

第二段：為什麼
  三、債券・殖利率 + 殖利率曲線分析
  四、外匯市場 + 新興市場貨幣壓力
  五、大宗商品
  六、加密貨幣
  七、市場情緒指標（卡片+比較表+美林時鐘+歷史情境，必須一頁內）

第三段：錢怎麼流
  八、全球資金流向
  九、板塊輪動
  十、當日熱門股票

第四段：往前看
  十一、經濟日曆 + FRED
```

## 新聞品質控制（三層）
1. 垃圾過濾：正則黑名單
2. 評分制分類：標題 3 分、描述 1 分，最佳匹配
3. 敘事摘要：描述需 ≥2 關鍵詞命中，不足用 why_it_matters 模板

## PDF 版面規則
- Chrome headless 的 `page-break-inside: avoid` 對超過半頁的元素無效
- 解法：縮減內容高度，不要硬塞（如刪除冗餘恐貪儀表 SVG）
- 小表格可用 `sub-section-block` 包住防切斷
- 不要用字串搜尋插入 HTML — 用函數參數傳入
- 每次改版面必須生成 PDF 目視確認

## 關鍵檔案
- `scripts/generate_full_report.py` — 主報告生成（1200+ 行進階版，不可回退）
- `modules/html_report_generator.py` — HTML 模板引擎
- `modules/email_sender.py` — Email 摘要
- `modules/news_collector.py` — 新聞收集
