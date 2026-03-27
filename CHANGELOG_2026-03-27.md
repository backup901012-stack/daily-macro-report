# 2026-03-27 改版記錄

## 一、環境建置

### 從 GitHub Clone 下來
- Repo: `https://github.com/cbe566/daily-macro-report.git`
- Clone 到: `/Users/jamie/Desktop/Claude-每日宏觀日報/`

### 安裝 Python 依賴
```bash
pip3 install exchange_calendars weasyprint beautifulsoup4 pdfkit
brew install pango poppler
```

### 已確認可用的 API Keys
| Key | 狀態 |
|-----|------|
| NewsAPI | 已有（硬編碼在 `news_collector.py`）|
| Polygon.io | 已提供：`kMowLOQRDjo5d1ciEg2h2UV2pIydp4zT` |
| Gmail App Password | 已有（硬編碼在 `email_sender.py`）|
| OpenAI | 無 → 由 Claude 手動分析替代 |

---

## 二、程式碼改動

### 2.1 `modules/market_data.py` — 移除 Manus 沙盒依賴
- **移除**: `sys.path.append('/opt/.manus/.sandbox-runtime')`、`from data_api import ApiClient`、`client = ApiClient()`
- **改寫**: `fetch_quote()` 從 Manus API 改為純 yfinance（`yf.Ticker(symbol).history(period='5d')`）
- 取最近兩個交易日計算漲跌幅
- YTD 計算邏輯保留不變

### 2.2 `modules/hot_stocks.py` — 移除沙盒路徑 + 動態門檻
- **移除**: `sys.path.append('/opt/.manus/.sandbox-runtime')`
- **新增動態門檻回退**（在 `apply_funnel_filter()` 函數中）：
  - 原始嚴格門檻：買入 vol ≥ 1.5x + 上漲，賣出 vol ≥ 2.5x + 下跌
  - 若嚴格門檻結果為空（如美股），自動降低：
    - 買入：vol ≥ 1.2x AND 漲幅 > 1%
    - 賣出：vol ≥ 1.5x AND 跌幅 < -1%
  - 解決了美股 519 支全部被淘汰的問題

### 2.3 `modules/news_collector.py` — 新增亞洲媒體
- **新增 RSS 來源**：
  - Nikkei Asia（日經亞洲）
  - SCMP（南華早報）
- **新增來源分級**：Nikkei Asia 和 SCMP 歸為 Tier-2

### 2.4 `modules/html_report_generator.py` — 視覺優化
- **字體**: Noto Sans TC → PingFang TC（適配 macOS）
- **表格 header**: 深色背景 `#34495e` → 淺灰 `#f1f3f5` + 粗體大寫字母，更現代
- **資金流向 bar 顏色**: 藍/橘 → 綠/紅（符合金融慣例）
- **消除強制換頁**: `.section-new-page` 從 `page-break-before: always` → `auto`，消除空白頁
- **股票分析欄寬度**: 限制 `max-width: 280px`，避免表格撐爆

### 2.5 `generate_pdf.py` — Chrome 優先生成 PDF
- **新增 Chrome headless 模式**：自動偵測 Chrome 路徑，優先用 Chrome 生成 PDF
- **Fallback**: Chrome 不存在或失敗時自動回退到 WeasyPrint
- **解決中文亂碼問題**: WeasyPrint 在 macOS 上找不到中文字體 → Chrome 正確嵌入系統字體

### 2.6 `modules/enhanced_market_data.py` — 全新模組
新增增強版數據收集模組，包含 6 個功能：

| 函數 | 功能 | 數據來源 |
|------|------|----------|
| `get_northbound_southbound_flows()` | 陸港通北向/南向資金流向代理 | yfinance（FXI, KWEB, MCHI, EWH, 2800.HK）|
| `get_credit_spreads()` | 信用利差（IG/HY vs Treasury） | yfinance（LQD, HYG, IEF）|
| `get_technical_levels()` | 7 大指數技術面關鍵位（RSI, MA50, MA200, 52W 高低, 均線交叉） | yfinance |
| `get_upcoming_earnings()` | 未來 14 天重要財報日曆（22 家公司） | yfinance calendar |
| `get_historical_sentiment_context()` | 恐懼貪婪/VIX 歷史情境比較文字 | 內建規則 |
| `get_yield_curve_analysis()` | 殖利率曲線形態判斷（倒掛/平坦/正常/陡峭） | yfinance（^IRX, ^FVX, ^TNX, ^TYX）|

---

## 三、報告新增內容區塊

以下 5 個區塊是在 HTML 生成後手動注入的（因為 `html_report_generator.py` 的主函數尚未支援這些參數）：

| 區塊 | 插入位置 | 視覺風格 |
|------|----------|----------|
| **市場綜述 Executive Summary** | 第一頁，指數表前 | 藍色漸層框 + 左邊框 |
| **主要指數技術面關鍵位** | 商品表前 | 表格（RSI 超賣紅色、均線交叉綠/紅） |
| **殖利率曲線分析** | 情緒指標前 | 紫色漸層框 |
| **歷史情境參考** | 資金流向前 | 紅色漸層框 |
| **行業輪動解讀** | GICS 板塊前 | 橘色漸層框 |

---

## 四、生成的報告檔案

| 檔案 | 大小 | 說明 |
|------|------|------|
| `reports/raw_data_2026-03-27.json` | ~600KB | 完整原始數據（市場+新聞+分析+增強版） |
| `reports/daily_report_2026-03-27.html` | ~67KB | 增強版 HTML 報告 |
| `reports/daily_report_2026-03-27.pdf` | ~3.2MB | Chrome headless 生成的 PDF（11 頁） |
| `reports/daily_report_2026-03-27.md` | ~6KB | Markdown 版報告 |
| `reports/market_data_today.json` | 市場數據快取 |
| `reports/news_today.json` | 新聞數據快取（458 篇） |
| `reports/hot_stocks_today.json` | 熱門股票掃描結果 |
| `reports/enhanced_today.json` | 增強版 v1（情緒/美林時鐘/資金流向） |
| `reports/enhanced_v2_today.json` | 增強版 v2（陸港通/信用利差/技術面/殖利率曲線） |

---

## 五、報告完整內容結構（11 頁 PDF）

1. **標題 + 市場速覽快照**
2. **市場綜述 Executive Summary**（新增）
3. **一、各國指數表現**（亞洲/歐洲/美國 + AI 分析文字 + YTD 欄位）
4. **主要指數技術面關鍵位**（新增：RSI, 50/200MA, 距52W高, 均線交叉）
5. **三、商品、外匯與債券**（表格）
6. **殖利率曲線分析**（新增：曲線形態 + 2s10s 利差含義）
7. **四、市場情緒指標**（CNN Fear & Greed 儀表盤 + VIX + 美林時鐘）
8. **歷史情境參考**（新增：當前 F&G 15.6 和 VIX 29.2 的歷史對比）
9. **五、全球資金流向脈動**（14 國/地區 ETF CMF 流向）
10. **行業輪動解讀**（新增：能源流入/科技流出的分析文字）
11. **六、GICS 11 大板塊資金流向 + 債券市場資金流向**
12. **七、當日熱門股票**（港股 18 支 + 日股 7 支 + 台股 13 支，全部有 AI 分析）
13. **八、加密貨幣市場**
14. **九、本週經濟日曆**（6 事件 + 重點關注詳述）
15. **簽名檔 + 免責聲明**

---

## 六、數據收集統計

| 項目 | 數量 |
|------|------|
| 新聞來源 | 7 個（Bloomberg, Reuters, FT, WSJ, CNN, Nikkei Asia, SCMP + CNBC RSS + NewsAPI + Polygon） |
| 收集新聞 | 458 篇（Tier-1: 198, Tier-2: 65, Tier-3: 195） |
| 歸納宏觀事件 | 7 條 |
| 掃描成分股 | 2,320 支（美 519 + 日 226 + 台 1,045 + 港 530） |
| 熱門股票 | 38 支（港 18 + 台 13 + 日 7 + 美 0） |
| 股票分析 | 38 支全覆蓋 |
| 市場數據標的 | 39 個（指數/商品/外匯/債券/加密） |
| 技術面分析 | 7 大指數 |
| 資金流向 ETF | 35 個（8 國家 + 11 板塊 + 10 債券 + 6 補充） |
| 情緒指標 | CNN F&G 15.6, VIX 29.2, 美林時鐘: 滯脹期 |

---

## 七、已知問題 / 待辦

### 尚未完成
- [ ] 美股熱門股票動態門檻已加入程式碼，但今天的報告未重跑美股掃描
- [ ] `html_report_generator.py` 的 `generate_html_report()` 主函數尚未原生支援新區塊參數（目前用 HTML 注入方式）
- [ ] 自動化排程尚未設定（需 Anthropic API Key 才能自動跑 AI 分析）
- [ ] 陸港通數據目前用 ETF 代理，非真實北向/南向資金數據
- [ ] 財報日曆今天查詢結果為 0 家（可能是 yfinance calendar API 限制）

### PDF 生成注意事項
- 必須使用 Chrome headless 生成 PDF（WeasyPrint 在 macOS 上中文亂碼）
- Chrome 路徑：`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- 命令：`--headless --print-to-pdf=PATH --print-to-pdf-no-header file://HTML_PATH`

---

## 八、新建檔案清單

| 檔案 | 說明 |
|------|------|
| `SYSTEM_LOGIC_BACKUP.md` | 整套系統邏輯備檔 |
| `CHANGELOG_2026-03-27.md` | 本日改版記錄（本檔案） |
| `modules/enhanced_market_data.py` | 增強版數據收集模組（陸港通/信用利差/技術面/財報/殖利率曲線） |
