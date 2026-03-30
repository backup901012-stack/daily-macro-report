# 待辦事項

## 優先處理（自動化卡關）

### 1. Gmail SMTP 認證失敗
- **問題**: GitHub Actions 上 Gmail App Password 認證失敗（535 BadCredentials）
- **已嘗試**: 含空格/不含空格/舊密碼，全部失敗
- **可能原因**:
  - App Password 產生後可能需要等幾分鐘才生效
  - Google 可能封鎖了 GitHub Actions 的 IP 範圍
  - 需要確認是用 `backup901012@gmail.com` 帳號產生的 App Password
- **解決方向**:
  - [ ] 重新產生 App Password，截圖確認
  - [ ] 如果 Gmail 持續失敗，考慮改用其他郵件服務（SendGrid / Mailgun 免費方案）
  - [ ] 或用 GitHub Actions 把 PDF 上傳到某處，手動下載

### 2. Anthropic 雲端 Trigger 無法使用
- **問題**: Anthropic 雲端環境封鎖外部 API（403 Tunnel），yfinance/requests 都不能用
- **結論**: 放棄此方案，改用 GitHub Actions
- **Trigger ID**: `trig_01Q2SvyHMpC4U7SfEnqMABBW`（可到 https://claude.ai/code/scheduled 停用或刪除）

---

## GitHub Actions 狀態
- **Workflow**: `.github/workflows/daily-report.yml`
- **排程**: UTC 23:00 週日到週四（= 台北 07:00 週一到週五）
- **所有步驟都成功，只剩 Email 發送失敗**:
  - ✓ Checkout repo
  - ✓ Install dependencies
  - ✓ Collect market data（39 標的）
  - ✓ Collect news（450+ 篇）
  - ✓ Scan hot stocks（2,300+ 支）
  - ✓ Collect enhanced data（情緒/美林時鐘/資金流向/技術面）
  - ✓ Generate AI analysis and report
  - ✓ Generate PDF（2.3 MB）
  - ✗ Send email（Gmail 認證失敗）

---

## 報告品質改善（次優先）

### 3. AI 分析品質提升
- 目前 GitHub Actions 用規則引擎（`scripts/generate_full_report.py`）生成分析文字
- 品質不如 Claude 手動分析
- **解決方向**:
  - [ ] 取得 Anthropic API Key 後，改用 Claude API 做分析
  - [ ] 或在 workflow 中加入 `claude -p` 步驟（需要研究 GitHub Actions 上能否跑 Claude CLI）

### 4. PDF 版面優化
- 第4頁空白問題仍存在
- 部分熱門股票缺少分析文字（規則引擎只能生成簡單描述）
- 表格 header 風格可以再調整
- Executive Summary 手動注入的方式不夠優雅，應該改進 html_report_generator.py 原生支援

### 5. 美股熱門股票
- 動態門檻已加入程式碼但未實測
- 需要在 GitHub Actions 上確認是否能正常篩出美股

### 6. html_report_generator.py 原生支援新區塊
- 目前 Executive Summary、技術面、殖利率曲線等是用 HTML 注入方式
- 應該改成 generate_html_report() 函數原生支援這些參數
- 減少外部注入的維護成本

---

## 已完成

- [x] 從 GitHub clone 原始 repo
- [x] 移除 Manus 沙盒依賴（market_data.py → 純 yfinance）
- [x] 新增 enhanced_market_data.py 模組
- [x] 新增亞洲新聞來源（Nikkei Asia + SCMP）
- [x] 動態門檻回退（hot_stocks.py）
- [x] CSS 視覺優化（表格/資金流向顏色/消除空白頁）
- [x] Chrome headless PDF 生成（解決中文亂碼）
- [x] generate_pdf.py 支援 Chrome + WeasyPrint fallback
- [x] 建立新 GitHub repo（macro-daily-report-claude）
- [x] 設定 GitHub Actions workflow
- [x] 設定 GitHub Secrets
- [x] SYSTEM_LOGIC_BACKUP.md 完整邏輯備檔
- [x] CHANGELOG_2026-03-27.md 改版記錄
