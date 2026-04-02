# 每日宏觀資訊綜合早報

## 自動化架構（2026-04-02 更新）

### 每日流程（唯一路徑，不可加備份觸發）
```
UTC 21:00（台北 05:00）  GitHub Actions 數據收集
  ├─ 以美股收盤（UTC 20:00）為基準，收盤後 1 小時啟動
  ├─ 此時全球所有市場（亞洲/歐洲/美股/商品/外匯/加密）當日數據已定案
  ├─ 市場數據 / 新聞 / 熱門股 / 情緒 / FRED / 替代數據
  ├─ 新聞標題預翻譯（前 100 篇，continue-on-error）
  ├─ 數據新鮮度驗證（US 數據超過 2 天 → exit 1 攔截）
  └─ git commit 數據到 repo

收集完成 → workflow_run 自動觸發生成+發送（唯一觸發路徑）
  ├─ 數據驗證（缺失 → exit 1）
  ├─ 生成 HTML 報告
  ├─ Chrome headless 轉 PDF
  ├─ 品質閘門（PDF > 100KB + 新聞中文率）
  ├─ 等待至台北 07:30（上限 10800 秒 = 3 小時）
  ├─ 防重發（D1 查詢，重試 3 次，失敗預設「已發」寧漏不重）
  └─ Gmail OAuth2 API 逐一發送（隱私保護）
```

### 重要設計原則（2026-04-02 更新）
- **發信只有一條路徑**：數據收集完成 → workflow_run → daily-send.yml
- **不可加備份觸發**：backup cron、Worker auto dispatch、本機 crontab/LaunchAgent 會搶發舊數據
- **本機觸發器已全部停用**：crontab run_auto.sh 已移除，LaunchAgent 已卸載（2026-04-02）
- **email_sender.py 內建 dedup**：send_report_email() 自帶 D1 防重發（fail-closed，學自股票量化系統）
- **不可在美股收盤前手動觸發數據收集**：會收到前一天的過期數據
- **防重發必須 fail-closed**：查詢失敗預設「不發」，寧可漏發不可重發
- **等待邏輯上限**：根據實際流程計算（05:00 到 07:30 = 2.5h），設 3h 上限
- **報告絕不能出現英文**：翻譯失敗的標題一律丟棄，中文比例 < 30% 的不顯示
- **報告絕不能混簡體字**：所有文字經 opencc（s2twp）轉換，零洩漏

### 發信方式
- **Gmail OAuth2 API**（不是 SMTP，跟股票量化系統共用同一套）
- Secrets: `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` / `GMAIL_USER`
- 收件人: `EMAIL_TO`（逗號分隔，目前 2 人測試，正式 34 人在 recipients.json）
- 逐一發送，每位收件人只看到自己的地址

### Cloudflare 監控架構（純監控，不觸發發信）
- **D1 資料庫**：`macro-report-db`（UUID: `26fc7949-e2b4-4b30-b317-3ccc165d967d`）
  - 表 `send_log`：記錄每次發送（report_date, recipient, status, sent_at, pdf_size）
- **Worker**：`macro-report-monitor`（`https://macro-report-monitor.stock-quant.workers.dev`）
  - Cron: 每天 UTC 02:00（台北 10:00）純監控檢查，**不觸發任何 dispatch**
  - `GET /status`：查看今天發送記錄
  - `GET /check`：檢查狀態（只回報，不動作）
  - `POST /record`：workflow 發完信後記錄到 D1（需 X-API-Key）
- **GitHub Secrets**：`MONITOR_RECORD_KEY`（Worker 記錄端點的 API Key）

### Kimi AI 新聞增強（2026-04-02 升級）
- **模組**：`modules/kimi_enhancer.py`
- **API**：Moonshot API（`moonshot-v1-auto`），Secret: `MOONSHOT_API_KEY`，max_tokens: 2000
- **功能**：
  1. **所有 8 個新聞板塊**都用 Kimi 生成專業中文敘事摘要（不再限前 4 個）
  2. 報告末尾「十二、總結分析」— 三段式（今日重點/核心驅動/明日關注）
- **Fallback**：Kimi 失敗時退回規則引擎模板，不影響報告生成
- **簡繁轉換**：使用 `opencc`（s2twp 台灣偏好），徹底取代字典對照表
- **簡體版生成**：`_to_simplified()` 用 opencc（tw2sp）繁→簡，生成 `_sc.html`
- **用詞規則**：客觀陳述、不帶稱呼、不用套話、署名「僅供參考」

### 數據抓取三層防護（2026-04-02 建成）
- **第一層**：yfinance 重試 5 次，間隔 5 秒
- **第二層**：Yahoo Finance HTTP API 備用數據源
- **第三層**：exchange_calendars 判斷休市
  - 確認休市 → 表格顯示「休市」
  - 非休市但抓取失敗 → 不顯示（避免錯誤數據）
  - **絕不使用前一天數據**

### 郵件附件（2026-04-02 升級）
- 每封信附兩個 PDF：`繁體.pdf` + `簡體.pdf`
- 繁體版：opencc s2twp（台灣用語偏好）
- 簡體版：opencc tw2sp（繁→簡）

### ReportLab PDF 升級（開發中）
- **檔案**：`modules/pdf_report_generator.py`（初版，尚未切換）
- **目標**：取代 Chrome headless，pixel-perfect 排版控制
- **狀態**：基礎框架完成，缺儀表盤圖/美林時鐘圖，**必須超越 HTML 版才能切換**

### 熱門股量化評分系統（2026-03-31 建成）
- **三層篩選**：放量門檻（硬篩）→ 量化驗證 → 複合排名
- **複合分數**：量能 30% + 量化評分 40% + 動量 30%
- **數據來源**：
  1. 股票量化系統 API（D1，~4000+ 支指數成分股）
  2. 即時評分 fallback（yfinance，對 API 未覆蓋的股票即時算分）
- **即時評分維度**：技術面信號 + Z-Score 均值回歸 + F-Score + 分析師目標價
- **顯示邏輯**：匹配率 ≥ 50% 顯示量化欄位，否則回退成交量欄位
- **force_send**：`workflow_dispatch` 支援 `force_send=true` 跳過防重發

### 待完成
- [ ] **34 人名單上線**：等品質確認穩定後切換
- [ ] **報告存 R2**：PDF 歷史存檔
- [ ] **數據存 D1**：取代 git commit JSON

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

## 新聞品質控制（2026-04-02 升級，參考投行晨報標準）
1. 垃圾過濾：正則黑名單
2. 評分制分類：標題 3 分、描述 1 分，最佳匹配
3. **來源分級篩選**：Tier-1（Bloomberg/Reuters）1 分即入選；Tier-2 需 2 分；Tier-3 需 3 分
4. 敘事摘要：Kimi AI 生成（所有板塊），fallback 用 why_it_matters 模板
5. **摘要不截斷**：移除 150 字硬截斷，殘缺句子自動清理
6. 翻譯：數據收集階段預翻譯存入 `title_zh`，報告生成時優先用 + opencc 後處理
7. **英文過濾**：翻譯結果中文比例 < 30% 的一律丟棄不顯示
8. **無股票代碼標籤**：新聞卡片不顯示 ticker tag

## Email 格式
- **純文字正文**（投行風格，不用 HTML 美工）
- 包含：市場總覽 / 中文新聞標題 / 指數亮點 / 加密貨幣 / 經濟日曆
- **兩個 PDF 附件**：繁體版 + 簡體版

## PDF 版面規則
- Chrome headless 的 `page-break-inside: avoid` 對超過半頁的元素無效
- 正解：縮減內容高度（如刪除冗餘恐貪儀表 SVG）
- 小表格用 `sub-section-block` 防切斷
- 用函數參數傳入數據，不要字串搜尋插入 HTML
- 每次改版面必須生成 PDF 目視確認

## 關鍵檔案
- `scripts/generate_full_report.py` — 主報告生成（1200+ 行進階版，不可回退）
- `modules/html_report_generator.py` — HTML 模板引擎
- `modules/hot_stocks.py` — 熱門股偵測 + 量化評分整合 + 即時評分 fallback
- `modules/email_sender.py` — Email 摘要生成
- `modules/news_collector.py` — 新聞收集
- `modules/kimi_enhancer.py` — Kimi AI 新聞摘要 + 報告總結 + opencc 簡繁轉換
- `modules/market_data.py` — 市場數據收集（三層防護 + 休市判斷）
- `modules/pdf_report_generator.py` — ReportLab PDF 引擎（開發中）
- `modules/email_template_v2.py` — Goldman 風格 HTML 模板（備用，本機 run_auto.sh 用）
- `recipients.json` — 34 人完整收件名單
