# 每日宏觀資訊綜合早報

## 自動化架構（2026-03-31 更新）

### 每日流程
```
UTC 21:30（台北 05:30）  GitHub Actions 數據收集
  ├─ 市場數據 / 新聞 / 熱門股 / 情緒 / FRED / 替代數據
  ├─ 新聞標題預翻譯（前 100 篇，continue-on-error）
  └─ git commit 數據到 repo

收集完成 → workflow_run 自動觸發生成+發送
  ├─ 數據驗證（缺失 → exit 1）
  ├─ 生成 HTML 報告
  ├─ Chrome headless 轉 PDF
  ├─ 品質閘門（PDF > 100KB + 新聞中文率）
  ├─ 等待至台北 07:30
  └─ Gmail OAuth2 API 逐一發送（隱私保護）

備用 cron: UTC 23:00（台北 07:00）
```

### 發信方式
- **Gmail OAuth2 API**（不是 SMTP，跟股票量化系統共用同一套）
- Secrets: `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` / `GMAIL_USER`
- 收件人: `EMAIL_TO`（逗號分隔，目前 2 人測試，正式 34 人在 recipients.json）
- 逐一發送，每位收件人只看到自己的地址

### 待完成（P0 最緊急）
- [ ] **Cloudflare Worker 監控**：07:45 檢查是否已發，沒有則觸發補發
- [ ] **D1 發送記錄**：發信後記錄到 D1（防重發 + 監控依據）
- [ ] **34 人名單上線**：等品質確認穩定後切換

## 報告結構（四段式敘事，2026-03-30 確認，不可擅改）
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

## 新聞品質控制
1. 垃圾過濾：正則黑名單
2. 評分制分類：標題 3 分、描述 1 分，最佳匹配
3. 敘事摘要：描述需 ≥2 關鍵詞命中，不足用 why_it_matters 模板
4. 翻譯：數據收集階段預翻譯存入 `title_zh`，報告生成時優先用，不依賴即時 API

## Email 格式
- **純文字正文**（投行風格，不用 HTML 美工）
- 包含：市場總覽 / 中文新聞標題 / 指數亮點 / 加密貨幣 / 經濟日曆
- PDF 作為附件

## PDF 版面規則
- Chrome headless 的 `page-break-inside: avoid` 對超過半頁的元素無效
- 正解：縮減內容高度（如刪除冗餘恐貪儀表 SVG）
- 小表格用 `sub-section-block` 防切斷
- 用函數參數傳入數據，不要字串搜尋插入 HTML
- 每次改版面必須生成 PDF 目視確認

## 關鍵檔案
- `scripts/generate_full_report.py` — 主報告生成（1200+ 行進階版，不可回退）
- `modules/html_report_generator.py` — HTML 模板引擎
- `modules/email_sender.py` — Email 摘要生成
- `modules/news_collector.py` — 新聞收集
- `modules/email_template_v2.py` — Goldman 風格 HTML 模板（備用）
- `recipients.json` — 34 人完整收件名單
