# 每日宏觀資訊日報系統 — 完整邏輯備檔

> 備檔日期：2026-03-27
> 來源 Repo：https://github.com/cbe566/daily-macro-report.git

---

## 一、系統總覽

本系統為一套**全自動每日宏觀資訊綜合早報生成與發送系統**，每週一至週五自動：
1. 收集全球市場數據（股指、商品、外匯、債券、加密貨幣）
2. 收集四來源財經新聞
3. 偵測四大市場熱門股票（資金追捧/出清）
4. 用 AI（GPT-4.1-mini）分析新聞、指數漲跌原因、熱門股票
5. 新聞事實查核（雙層機制）
6. 收集增強版數據（情緒指標、美林時鐘、資金流向）
7. 生成 Markdown → HTML → PDF 報告
8. 自動 Email 群發（逐封發送，保護隱私）

---

## 二、目錄結構

```
daily-macro-report/
├── run_report.py              # 主執行腳本（收集數據 + AI 分析 + 生成 Markdown）
├── generate_pdf.py            # 從 JSON 生成 HTML+CSS → PDF（使用 WeasyPrint）
├── build_email_body.py        # 從 JSON 生成純文字郵件正文
├── run_daily.sh               # 每日執行 Shell 腳本（串連所有步驟）
├── setup_cron.sh              # Cron 排程設定（週一~五 北京時間 08:30）
├── recipients.json            # 收件人清單（群組管理）
├── send_single.py             # 發送單封 Email 工具
├── wait_send_0730.py          # 等待到 07:30 再發送的工具
├── wait_and_send.py / wait_and_send_today.py / wait_send_today.py  # 其他等待發送變體
├── fetch_index_components.py  # 抓取四大市場指數成分股（Wikipedia/TWSE/AASTOCKS）
├── cross_verify.py / cross_verify2.py / verify_*.py  # 各種數據驗證腳本
├── test_fact_checker.py       # 事實查核模組測試
├── data/
│   ├── index_components.json  # 指數成分股快取
│   └── hk_soe_stocks.json    # 港股國企股清單
├── modules/
│   ├── __init__.py
│   ├── market_data.py         # 市場數據收集（Yahoo Finance API + yfinance）
│   ├── news_collector.py      # 四來源新聞收集
│   ├── hot_stocks.py          # 熱門股票偵測（yfinance 批量掃描）
│   ├── ai_analyzer.py         # AI 分析引擎（OpenAI GPT-4.1-mini）
│   ├── report_generator.py    # Markdown 報告生成
│   ├── html_report_generator.py  # HTML+CSS 報告生成（PDF 用）
│   ├── email_sender.py        # SMTP 郵件發送
│   ├── economic_calendar.py   # 經濟日曆
│   ├── market_holidays.py     # 市場休市偵測（exchange_calendars）
│   ├── sentiment_data.py      # 市場情緒 + 美林時鐘 + 資金流向
│   └── news_fact_checker.py   # 新聞事實查核（雙層機制）
└── reports/                   # 生成的報告存放處
    ├── daily_report_YYYY-MM-DD.md
    ├── daily_report_YYYY-MM-DD.html
    ├── daily_report_YYYY-MM-DD.pdf
    └── raw_data_YYYY-MM-DD.json
```

---

## 三、主流程（run_report.py → run_daily.sh）

### 3.1 每日執行流程（run_daily.sh）

```
1. python3 run_report.py daily   → 收集數據 + AI 分析 + 生成 Markdown + 保存 JSON
2. python3 generate_pdf.py DATE  → 從 JSON 生成 HTML → PDF（WeasyPrint）
3. python3 email_sender.py send  → 讀取 JSON 生成摘要 + 附上 PDF 逐封發送
```

### 3.2 run_report.py 主流程

```python
def main():
    # 0. 偵測休市狀態（exchange_calendars）
    holiday_alerts = get_holiday_alerts()

    # 1. 收集市場數據（Yahoo Finance API + yfinance）
    market_data = collect_market_data('daily')
    # → asia_indices, europe_indices, us_indices, commodities, forex, bonds, crypto, emerging_indices

    # 2. 收集新聞（四來源）
    news_data = get_news_for_date()

    # 3. 偵測熱門股票（yfinance 批量掃描四大市場成分股）
    hot_stocks = collect_hot_stocks(news_trending_tickers)

    # 4. AI 分析（GPT-4.1-mini）
    #    4a. 歸納 5-8 條宏觀事件
    #    4b. 新聞事實查核（雙層機制）
    #    4c. 分析指數漲跌原因
    #    4d. 分析熱門股票漲跌原因
    #    4e. 分析經濟日曆
    news_events, index_analysis, stock_analysis, calendar_events, fact_check_report = run_ai_analysis(...)

    # 4.5 收集增強版數據
    enhanced_data = collect_all_enhanced_data()
    # → sentiment（CNN Fear & Greed, VIX, US10Y, DXY）
    # → clock（美林時鐘週期判斷）
    # → fund_flows（CMF 資金流向：國家/板塊/債券 ETF）

    # 5. 生成 Markdown 報告
    daily_report = generate_daily_report(...)

    # 6. 保存原始數據為 JSON（供 PDF 生成和 Email 摘要使用）
    json.dump(raw_data, ...)
```

### 3.3 報告類型

| 類型 | 命令 | 內容 |
|------|------|------|
| `daily` | `python3 run_report.py daily` | 綜合日報（全部數據） |
| `asia` | `python3 run_report.py asia` | 亞洲盤報告 |
| `europe` | `python3 run_report.py europe` | 歐洲盤報告 |
| `us` | `python3 run_report.py us` | 美洲盤報告 |
| `all` | `python3 run_report.py all` | 生成全部四份報告 |

---

## 四、各模組詳細邏輯

### 4.1 市場數據收集（modules/market_data.py）

**數據來源**：
- 主要：`data_api.ApiClient()` → Yahoo Finance API（`YahooFinance/get_stock_chart`）
- 輔助：`yfinance`（YTD 年初價格計算）

**追蹤的市場**：

| 類別 | 標的 |
|------|------|
| 亞洲指數 | 日經225, 東證指數, 台灣加權, 恆生, 上證, 深證, KOSPI, ASX200 |
| 歐洲指數 | DAX, FTSE100, CAC40, STOXX50, SMI |
| 美股指數 | S&P 500, 納斯達克, 道瓊斯, 羅素2000, 費城半導體 |
| 大宗商品 | 黃金, 白銀, WTI原油, 布蘭特原油, 銅, 天然氣 |
| 外匯 | 美元指數, EUR/USD, USD/JPY, GBP/USD, USD/CNY, USD/TWD |
| 債券 | 美國 2Y/10Y/30Y 殖利率 |
| 加密貨幣 | BTC, ETH, BNB, SOL, XRP, ADA, DOGE |
| 新興市場 | 印度SENSEX/NIFTY50, 印尼, 泰國, 馬來西亞, 菲律賓 |

**取價邏輯**（`fetch_quote`）：
1. 呼叫 Yahoo Finance API 取得 5 天日線數據
2. 用 UTC 日期去重（避免週末重複數據點）
3. 從後往前找最新有效收盤價和前一天收盤價
4. 計算漲跌幅 + YTD 漲跌幅
5. 失敗自動重試 3 次，每次間隔 2 秒

**數據結構**（每個標的）：
```json
{
  "name": "S&P 500",
  "symbol": "^GSPC",
  "current": 5667.56,
  "previous": 5612.34,
  "change": 55.22,
  "change_pct": 0.98,
  "ytd_pct": 8.45,
  "volume": 3200000000,
  "high": 5672.00,
  "low": 5610.00,
  "timestamp": 1711497600
}
```

---

### 4.2 新聞收集（modules/news_collector.py）

**四來源架構（按品質排序）**：

| 優先級 | 來源 | 取得方式 | 說明 |
|--------|------|----------|------|
| 1 | 頂級媒體 RSS | Google News RSS（site:bloomberg.com 等） | Bloomberg, Reuters, FT, WSJ, CNN Business |
| 2 | CNBC RSS | 直接 RSS feed | Top News, World, Business, Technology, Finance |
| 3 | NewsAPI.org | REST API（`NEWSAPI_KEY`） | Top Headlines + 8 主題搜尋 |
| 4 | Polygon.io | REST API（`POLYGON_API_KEY`） | 補充 ticker 關聯和情緒數據 |

**NewsAPI 搜尋主題**：股市、央行、AI/科技、大宗商品、地緣政治、財報、加密貨幣、併購/IPO

**品質控制流程**：
1. **日期過濾**：只保留目標日期（前一天）的新聞
2. **垃圾過濾**：移除律師事務所集體訴訟廣告（30+ 個 pattern）
3. **智慧去重**：標準化標題前 80 字元做去重
4. **來源分級排序**：
   - Tier-1：Bloomberg, Reuters, FT, WSJ（最高品質）
   - Tier-2：CNBC, CNN, MarketWatch, Barron's
   - Tier-3：其他來源
5. **排序規則**：來源等級 → 來源類型 → 有無 ticker 關聯

**新聞分類**（`categorize_news`）：
- central_bank、economic_data、geopolitics、tech_industry、commodities、crypto、earnings、other

**Trending Tickers 提取**：統計 Polygon.io 新聞中出現最多的前 20 個 ticker + 情緒分析

---

### 4.3 熱門股票偵測（modules/hot_stocks.py）

**v4 架構**：所有市場統一使用 yfinance 批量下載

**候選池**（從 `data/index_components.json` 載入）：
| 市場 | 成分股來源 | 數量 |
|------|-----------|------|
| 美股 | 道瓊30 + S&P 500 + NASDAQ 100（去重） | ~519 支 |
| 日股 | 日經 225 | ~226 支 |
| 台股 | 台灣 50 + 中型 100 | ~150 支 |
| 港股 | 恆生指數 + 國企股 | ~85 支 |

**批量下載參數**：
- 每批 90 支（`YF_BATCH_SIZE`）
- 批次間休息 3 秒（`YF_BATCH_DELAY`）
- 下載 1 個月日線（`YF_DOWNLOAD_PERIOD = '1mo'`）

**三層漏斗篩選**：

| 層級 | 邏輯 | 說明 |
|------|------|------|
| 第一層（硬門檻） | 量比 ≥ 1.5x + 上漲 → `inflow`（資金追捧） | 買入放量 |
| | 量比 ≥ 2.5x + 下跌 → `outflow`（資金出清） | 賣出放量 |
| 第二層（排序） | 按漲跌幅絕對值排序（大→小） | |
| 第三層（加分） | 有新聞提及的 ticker 優先（tiebreaker） | |

**量比計算**：當日成交量 / 近月平均成交量（排除最近一天）

**輸出格式**（v2）：
```json
{
  "美股": {
    "inflow": [{"symbol": "NVDA", "change_pct": 5.2, "volume_ratio": 3.1, ...}],
    "outflow": [{"symbol": "TSLA", "change_pct": -4.1, "volume_ratio": 2.8, ...}]
  },
  "日股": { ... },
  "台股": { ... },
  "港股": { ... }
}
```

每市場每方向最多顯示 **10 支**（`MAX_PER_FLOW = 10`）

---

### 4.4 AI 分析引擎（modules/ai_analyzer.py）

**模型**：`gpt-4.1-mini`（OpenAI API）

**四大分析任務**：

#### 4.4.1 宏觀新聞歸納（`analyze_macro_news`）
- 輸入：前 60 篇新聞 + 分類結果
- 輸出：5-8 條宏觀事件，JSON 格式
- 每條包含：title, description, impact_level（高/中/低）, affected_markets, market_direction（利多/利空/中性）, related_tickers, ticker_impact
- **關鍵要求**：區分「對誰利多/利空」（例如 DRAM 漲價 → 對記憶體廠利多，對下游利空）

#### 4.4.2 指數漲跌分析（`analyze_index_movements`）
- 輸入：各區域指數數據 + 宏觀事件
- 輸出：asia_analysis, europe_analysis, us_analysis, overall_summary
- 使用 `response_format={"type": "json_object"}` 確保 JSON 輸出

#### 4.4.3 熱門股票分析（`analyze_hot_stocks`）
- 輸入：每市場前 8 支熱門股票 + 相關新聞
- 輸出：每支股票 1-2 句漲跌原因分析
- **關鍵要求**：從該股票自身角度判斷利多/利空（考慮產業鏈位置）

#### 4.4.4 經濟日曆分析（`generate_economic_calendar_analysis`）
- 輸入：本週日期範圍 + 經濟相關新聞
- 輸出：經濟事件列表（date, event, country, importance, description, consensus）
- 經濟關鍵詞：CPI, GDP, PPI, NFP, Fed, ECB, BOJ, FOMC, PMI 等

---

### 4.5 新聞事實查核（modules/news_fact_checker.py）

**雙層機制**：

#### Layer 1: AI 交叉比對
- 模型：`gpt-4.1-mini`（`temperature=0.1`，更嚴謹）
- 將 AI 歸納結果與原始 60 篇新聞逐條比對
- 檢查重點：
  - 數字準確性（融資金額 vs 估值/市值 混淆是最常見錯誤）
  - 概念混淆（融資 vs 估值、營收 vs 利潤、同比 vs 環比）
  - 公司/人物名稱正確性
  - 因果關係合理性
  - related_tickers 正確性（例如 SPCE ≠ SpaceX）
  - 單位轉換（$75 billion = 750億美元）

#### Layer 2: 結構化規則檢查
- **估值合理性**：內建 17 家知名公司估值底線（例如 SpaceX ≥ $200B, Apple ≥ $2000B）
- **百分比合理性**：單日漲幅 > 100% 需要警惕
- **Ticker 正確性**：SPCE ≠ SpaceX（自動替換為 RKLB/TSLA）

**修正邏輯**：
- 高/中嚴重度問題自動修正標題和描述
- 修正記錄保存到 `fact_check_report`

---

### 4.6 增強版數據（modules/sentiment_data.py）

#### 4.6.1 市場情緒指標
| 指標 | 來源 | 說明 |
|------|------|------|
| CNN Fear & Greed Index | CNN API | 恐懼/貪婪指數（0-100） |
| VIX | yfinance `^VIX` | CBOE 波動率指數 + 1 個月高低 |
| US 10Y Yield | yfinance `^TNX` | 美國 10 年期殖利率 |
| DXY | yfinance `DX-Y.NYB` | 美元指數 |

#### 4.6.2 美林時鐘（Investment Clock）
- **增長代理**：10Y-5Y 殖利率利差的 20 日 MA 斜率
- **通脹代理**：TIP/IEF 比率的 20 日 MA 斜率
- **四象限判斷**：

| 增長 | 通脹 | 階段 | 中文 | 最佳資產 |
|------|------|------|------|----------|
| ↑ | ↓ | Recovery | 復甦期 | 股票 |
| ↑ | ↑ | Overheat | 過熱期 | 商品 |
| ↓ | ↑ | Stagflation | 滯脹期 | 現金 |
| ↓ | ↓ | Reflation | 衰退期 | 債券 |

- 信號強度：基於斜率絕對值（強/中/弱）

#### 4.6.3 全球資金流向（CMF-based）
使用 Chaikin Money Flow 邏輯，計算 ETF 層面的資金流向：

| 類別 | ETF | 期間 |
|------|-----|------|
| 國家 | SPY, VGK, EWJ, FXI, EWT, EWY, INDA, VWO | 1d, 5d, 1m, YTD |
| GICS 板塊 | XLK, XLF, XLV, XLY, XLP, XLI, XLE, XLB, XLU, XLRE, XLC | 同上 |
| 債券 | SHY, IEI, IEF, TLH, TLT, LQD, HYG, EMB, VWOB, EMLC | 同上 |
| 新興市場補充 | EIDO, VNM, THD, EWM, EPHE, EWA | 同上 |

---

### 4.7 市場休市偵測（modules/market_holidays.py）

**依賴**：`exchange_calendars` 套件

**支援交易所**：

| 市場 | 交易所代碼 | 名稱 |
|------|-----------|------|
| US | XNYS | 紐約證交所 (NYSE) |
| JP | XTKS | 東京證交所 (TSE) |
| TW | XTAI | 台灣證交所 (TWSE) |
| HK | XHKG | 香港交易所 (HKEX) |

**功能**：
1. 偵測今日各市場是否休市
2. 偵測明日（下一個工作日）是否休市
3. 列出未來 7 天內所有休市日

---

### 4.8 報告生成

#### Markdown 報告（modules/report_generator.py）
報告結構（綜合早報）：
1. **標題區**：日期、報告類型
2. **休市提醒**（如有）
3. **市場速覽**：一目了然的摘要（股市、商品、外匯、加密、焦點事件）
4. **一、各國指數表現**：亞洲/歐洲/美國（表格 + AI 分析文字）
5. **二、宏觀重點新聞**：5-8 條事件（影響程度、利多/利空、相關標的）
6. **三、商品、外匯與債券**：三個表格
7. **四、當日熱門股票**：分市場顯示資金追捧/出清（表格 + AI 分析）
8. **五、加密貨幣市場**：表格
9. **六、本週經濟日曆**：表格 + 重點關注事件詳述
10. **底部**：資料來源聲明

#### HTML+CSS PDF 報告（modules/html_report_generator.py）
- 參考 Saxo Bank / Goldman Sachs 風格
- A4 尺寸，專業排版
- 使用 **WeasyPrint** 轉換 HTML → PDF
- 額外包含：市場情緒儀表盤、美林時鐘圖表、資金流向熱力圖

---

### 4.9 郵件發送（modules/email_sender.py）

**SMTP 配置**：
- Server：smtp.gmail.com:587（STARTTLS）
- 發件人：cbe566@gmail.com（何宣逸）
- 認證：Google 應用程式密碼

**發送策略**：
- **逐封發送**（非群發）：每位收件者收到獨立信件，To 欄位只有自己
- 優點：保護隱私 + 相容企業信箱（避免被擋）

**郵件內容**：
- Subject：`每日宏觀資訊綜合早報 | YYYY-MM-DD`
- Body：自動從 `raw_data_YYYY-MM-DD.json` 生成精簡摘要
  - 休市提醒
  - 市場總覽
  - 宏觀重點新聞（前 5 條）
  - 指數表現亮點（亞洲/歐洲/美國各前 3）
  - 加密貨幣
  - 經濟日曆重點
  - "完整報告請見附件 PDF"
- 附件：`daily_report_YYYY-MM-DD.pdf`

**收件人管理**（recipients.json）：
- 群組管理（default 群組）
- 支援 To / CC / BCC
- 支援 `{name, email}` 格式
- CLI：list / add / remove / send / preview

---

### 4.10 成分股快取（fetch_index_components.py）

**來源**：
| 市場 | 來源 | 指數 |
|------|------|------|
| 美股 | Wikipedia | 道瓊30 + S&P 500 + NASDAQ 100（去重合併） |
| 日股 | Wikipedia | 日經 225 |
| 台股 | TWSE | 台灣加權指數（全部上市股票） |
| 港股 | AASTOCKS | 恆生指數 + 國企股 |

快取存放：`data/index_components.json`

---

## 五、Cron 排程

```bash
# 北京時間 08:30 = UTC 00:30，週一到週五
30 0 * * 1-5 /path/to/run_daily.sh
```

`setup_cron.sh` 會自動：
1. 生成 `run_daily.sh` 腳本
2. 移除舊的 cron 條目
3. 安裝新的 cron 條目

---

## 六、外部依賴與 API Keys

### Python 套件
- `yfinance`：Yahoo Finance 數據
- `openai`：GPT-4.1-mini AI 分析
- `weasyprint`：HTML → PDF 轉換
- `requests`：HTTP 請求
- `beautifulsoup4`：HTML 解析（爬蟲）
- `exchange_calendars`：交易所休市日曆
- `numpy` / `pandas`：數據計算
- `data_api`（`ApiClient`）：Manus 沙盒內的 Yahoo Finance API 封裝

### API Keys（環境變數）
| Key | 用途 | 備註 |
|-----|------|------|
| `NEWSAPI_KEY` | NewsAPI.org | 預設值已硬編碼：`919b1fdb80a340f2b3080464664d7178` |
| `POLYGON_API_KEY` | Polygon.io | 環境變數 |
| `OPENAI_API_KEY` | OpenAI GPT-4.1-mini | 環境變數（openai 套件自動讀取） |

### SMTP 認證
- Email：cbe566@gmail.com
- App Password：（在 email_sender.py 中硬編碼）

---

## 七、報告內容品質控制

1. **新聞品質分級**：Tier-1 > Tier-2 > Tier-3，優先展示高品質來源
2. **垃圾新聞過濾**：30+ 個正則 pattern 過濾律師事務所廣告
3. **日期嚴格過濾**：只保留目標日期的新聞
4. **AI 事實查核**：雙層機制（AI 交叉比對 + 結構化規則）
5. **利多/利空分析**：區分「對誰利多/利空」，考慮產業鏈上下游
6. **休市偵測**：自動標註休市市場，避免誤報

---

## 八、收件人名單（截至 2026-03-27）

共 33 位收件人，涵蓋：
- 華泰證券（htsc.com）多人
- Ark Wealth（arkwealth.hk）
- 安盛資本（annum.com.hk）
- TeraWise（terawisehk.com）
- 其他個人信箱

---

## 九、已知限制與注意事項

1. `data_api.ApiClient()` 是 Manus 沙盒環境專用，本地執行需要替換為直接 yfinance
2. `sys.path.append('/opt/.manus/.sandbox-runtime')` 在本地環境需移除
3. 部分路徑硬編碼為 `/home/ubuntu/daily-macro-report/`，本地需調整
4. NewsAPI 免費方案有每日請求限制
5. Polygon.io 免費方案無法取得當天數據（已改用 yfinance 解決）
6. WeasyPrint 需要系統安裝字體（Noto Sans TC/SC/JP）才能正確顯示中日文
7. Gmail 應用程式密碼需定期更新
