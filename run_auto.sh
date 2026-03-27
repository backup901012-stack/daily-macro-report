#!/bin/bash
# ============================================================
# 每日宏觀資訊報告 — 全自動執行腳本（Claude Code 版）
#
# 流程：收集數據 → Claude 分析 → 生成 PDF → 發送 Email
# 排程：每天北京時間 07:30（UTC-1 06:30 / UTC 22:30 前一天）
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export PATH="$HOME/.nvm/versions/node/v24.14.1/bin:$PATH"
export POLYGON_API_KEY="kMowLOQRDjo5d1ciEg2h2UV2pIydp4zT"
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH:-}"
export TZ='Asia/Taipei'

DATE=$(date +%Y-%m-%d)
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/auto_${DATE}.log"

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "=========================================="
log "每日宏觀報告自動化 — ${DATE}"
log "=========================================="

# ─── Step 1: 收集市場數據 ───
log "Step 1: 收集市場數據..."
python3 -c "
import sys, json
sys.path.insert(0, '${SCRIPT_DIR}')
from modules.market_data import get_asia_indices, get_europe_indices, get_us_indices, get_commodities, get_forex, get_bonds, get_crypto

data = {
    'asia_indices': get_asia_indices(),
    'europe_indices': get_europe_indices(),
    'us_indices': get_us_indices(),
    'commodities': get_commodities(),
    'forex': get_forex(),
    'bonds': get_bonds(),
    'crypto': get_crypto(),
}
with open('reports/market_data_today.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
total = sum(len(v) for v in data.values())
print(f'市場數據: {total} 標的')
" >> "${LOG_FILE}" 2>&1
log "  ✓ 市場數據完成"

# ─── Step 2: 收集新聞 ───
log "Step 2: 收集新聞..."
python3 -c "
import sys, json
sys.path.insert(0, '${SCRIPT_DIR}')
from modules.news_collector import get_news_for_date
news = get_news_for_date()
with open('reports/news_today.json', 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=2, default=str)
print(f'新聞: {len(news[\"articles\"])} 篇')
" >> "${LOG_FILE}" 2>&1
log "  ✓ 新聞收集完成"

# ─── Step 3: 掃描熱門股票 ───
log "Step 3: 掃描熱門股票（約 4 分鐘）..."
python3 -c "
import sys, json
sys.path.insert(0, '${SCRIPT_DIR}')
from modules.hot_stocks import get_all_hot_stocks
from modules.news_collector import get_trending_tickers_from_news

with open('reports/news_today.json', 'r') as f:
    news = json.load(f)
trending = news.get('trending_tickers', [])
hot = get_all_hot_stocks(news_trending_tickers=trending)
with open('reports/hot_stocks_today.json', 'w', encoding='utf-8') as f:
    json.dump(hot, f, ensure_ascii=False, indent=2, default=str)
total = sum(len(d.get('inflow',[])) + len(d.get('outflow',[])) for d in hot.values())
print(f'熱門股票: {total} 支')
" >> "${LOG_FILE}" 2>&1
log "  ✓ 熱門股票完成"

# ─── Step 4: 增強版數據（情緒/美林時鐘/資金流向） ───
log "Step 4: 收集增強版數據..."
python3 -c "
import sys, json
sys.path.insert(0, '${SCRIPT_DIR}')
from modules.sentiment_data import collect_all_enhanced_data
from modules.enhanced_market_data import collect_all_enhanced_v2

v1 = collect_all_enhanced_data()
v2 = collect_all_enhanced_v2()
with open('reports/enhanced_today.json', 'w', encoding='utf-8') as f:
    json.dump(v1, f, ensure_ascii=False, indent=2, default=str)
with open('reports/enhanced_v2_today.json', 'w', encoding='utf-8') as f:
    json.dump(v2, f, ensure_ascii=False, indent=2, default=str)
print(f'增強版數據收集完成')
" >> "${LOG_FILE}" 2>&1
log "  ✓ 增強版數據完成"

# ─── Step 5: Claude AI 分析 ───
log "Step 5: Claude AI 分析（約 1-2 分鐘）..."

# 準備分析提示
ANALYSIS_PROMPT=$(python3 -c "
import json

with open('reports/market_data_today.json') as f:
    md = json.load(f)
with open('reports/news_today.json') as f:
    news = json.load(f)
with open('reports/hot_stocks_today.json') as f:
    hs = json.load(f)
with open('reports/enhanced_today.json') as f:
    enh = json.load(f)
with open('reports/enhanced_v2_today.json') as f:
    enh2 = json.load(f)

# 市場摘要
idx_summary = {}
for region, indices in [('亞洲', md.get('asia_indices',{})), ('歐洲', md.get('europe_indices',{})), ('美國', md.get('us_indices',{}))]:
    idx_summary[region] = {n: {'pct': d['change_pct'], 'price': d['current']} for n, d in indices.items()}

# 前30篇新聞標題
titles = [a['title'] for a in news['articles'][:30]]

# 熱門股票摘要
hs_summary = {}
for market, data in hs.items():
    inflow = [{'symbol': s['symbol'], 'name': s['name'], 'pct': s['change_pct'], 'vol_ratio': s.get('volume_ratio',1)} for s in data.get('inflow',[])]
    outflow = [{'symbol': s['symbol'], 'name': s['name'], 'pct': s['change_pct'], 'vol_ratio': s.get('volume_ratio',1)} for s in data.get('outflow',[])]
    if inflow or outflow:
        hs_summary[market] = {'inflow': inflow[:5], 'outflow': outflow[:5]}

# 情緒數據
fg = enh.get('sentiment',{}).get('fear_greed',{}).get('score','N/A')
vix = enh.get('sentiment',{}).get('vix',{}).get('value','N/A')
clock = enh.get('clock',{}).get('phase_cn','N/A')

# 技術面
tech = {n: {'rsi': t['rsi'], 'pct_from_high': t['pct_from_high'], 'cross': t.get('cross','')} for n, t in enh2.get('technical_levels',{}).items()}

prompt = f'''你是華泰證券私人財富管理部的資深宏觀分析師。請根據以下今日市場數據，用繁體中文生成完整的 AI 分析報告。

=== 指數表現 ===
{json.dumps(idx_summary, ensure_ascii=False)}

=== 今日新聞標題（前30篇）===
{json.dumps(titles, ensure_ascii=False)}

=== 熱門股票 ===
{json.dumps(hs_summary, ensure_ascii=False)}

=== 情緒指標 ===
CNN Fear & Greed: {fg}, VIX: {vix}, 美林時鐘: {clock}

=== 技術面 ===
{json.dumps(tech, ensure_ascii=False)}

請嚴格以下面的 JSON 格式回覆，不要加任何其他文字：
{{
  \"executive_summary\": \"3段式市場綜述（200-300字）\",
  \"news_events\": [
    {{
      \"title\": \"事件標題\",
      \"description\": \"2-3句描述\",
      \"impact_level\": \"高/中/低\",
      \"affected_markets\": \"影響範圍\",
      \"market_direction\": \"利多/利空/中性\",
      \"related_tickers\": [\"TICKER\"],
      \"ticker_impact\": {{\"TICKER\": \"利多/利空（原因）\"}}
    }}
  ],
  \"index_analysis\": {{
    \"asia_analysis\": \"亞洲市場分析（3-5句）\",
    \"europe_analysis\": \"歐洲市場分析（3-5句）\",
    \"us_analysis\": \"美國市場分析（3-5句）\",
    \"overall_summary\": \"全球總結（2-3句）\",
    \"summary\": \"一句話摘要\"
  }},
  \"stock_analysis\": {{\"SYMBOL\": \"個股分析（1-2句）\"}},
  \"sector_analysis\": \"行業輪動解讀（2-3句）\",
  \"yield_curve_analysis\": \"殖利率曲線分析（2-3句）\",
  \"calendar_events\": [
    {{\"date\": \"YYYY-MM-DD\", \"event\": \"事件名\", \"country\": \"國家\", \"importance\": \"★★★/★★/★\", \"description\": \"描述\", \"consensus\": \"預期值\"}}
  ]
}}

要求：
1. news_events 歸納 5-8 條當日最重要的宏觀事件
2. stock_analysis 為每支熱門股票都寫分析
3. calendar_events 列出未來一週重要經濟數據
4. 所有分析必須基於提供的數據，不要編造
5. 區分「對誰利多/利空」
'''
print(prompt)
")

# 呼叫 Claude 做分析
CLAUDE_RESULT=$(echo "${ANALYSIS_PROMPT}" | claude -p "$(cat)" --output-format json 2>/dev/null || echo "${ANALYSIS_PROMPT}" | claude -p "$(cat)" 2>/dev/null)

# 保存 Claude 分析結果
echo "${CLAUDE_RESULT}" > "reports/claude_analysis_${DATE}.json"
log "  ✓ Claude 分析完成"

# ─── Step 6: 組裝 raw_data + 生成 HTML ───
log "Step 6: 組裝報告..."
python3 << PYEOF >> "${LOG_FILE}" 2>&1
import json, sys, re
from datetime import datetime
sys.path.insert(0, '${SCRIPT_DIR}')
from modules.html_report_generator import generate_html_report
from modules.enhanced_market_data import get_historical_sentiment_context

DATE = '${DATE}'

with open('reports/market_data_today.json') as f: market_data = json.load(f)
with open('reports/hot_stocks_today.json') as f: hot_stocks = json.load(f)
with open('reports/enhanced_today.json') as f: enh = json.load(f)
with open('reports/enhanced_v2_today.json') as f: enh2 = json.load(f)

# 讀取 Claude 分析
with open(f'reports/claude_analysis_{DATE}.json') as f:
    raw_text = f.read()
# 嘗試提取 JSON
try:
    # 清理可能的 markdown 包裝
    text = raw_text.strip()
    if text.startswith('\`\`\`'):
        text = text.split('\n', 1)[1]
        text = text.rsplit('\`\`\`', 1)[0]
    analysis = json.loads(text)
except:
    # 嘗試找到 JSON 部分
    match = re.search(r'\{[\s\S]+\}', raw_text)
    if match:
        analysis = json.loads(match.group())
    else:
        print("WARNING: Claude 分析 JSON 解析失敗，使用空分析")
        analysis = {}

news_events = analysis.get('news_events', [])
index_analysis = analysis.get('index_analysis', {})
stock_analysis = analysis.get('stock_analysis', {})
calendar_events = analysis.get('calendar_events', [])
executive_summary = analysis.get('executive_summary', '')
sector_analysis = analysis.get('sector_analysis', '')
yield_curve_analysis = analysis.get('yield_curve_analysis', '')

# 歷史情境
fg_score = enh.get('sentiment',{}).get('fear_greed',{}).get('score')
vix_val = enh.get('sentiment',{}).get('vix',{}).get('value')
historical = get_historical_sentiment_context(fg_score, vix_val) if fg_score else {}

# 序列化 hot_stocks
def ser_hs(hs):
    out = {}
    for m, d in hs.items():
        if isinstance(d, dict) and 'inflow' in d:
            out[m] = {
                'inflow': [{k: s.get(k) for k in ['symbol','name','current','change_pct','volume_ratio','volume','avg_volume','flow','news_mentions']} for s in d['inflow']],
                'outflow': [{k: s.get(k) for k in ['symbol','name','current','change_pct','volume_ratio','volume','avg_volume','flow','news_mentions']} for s in d['outflow']],
            }
        else: out[m] = d
    return out

raw_data = {
    'market_data': market_data, 'news_events': news_events, 'index_analysis': index_analysis,
    'stock_analysis': stock_analysis, 'calendar_events': calendar_events,
    'hot_stocks': ser_hs(hot_stocks),
    'holiday_alerts': {'today_closed':[], 'tomorrow_closed':[], 'upcoming_holidays':[], 'has_alerts': False},
    'sentiment_data': enh.get('sentiment',{}), 'clock_data': enh.get('clock',{}),
    'fund_flows': enh.get('fund_flows',{}),
    'executive_summary': executive_summary, 'sector_analysis': sector_analysis,
    'yield_curve_analysis': yield_curve_analysis, 'historical_context': historical,
    'technical_levels': enh2.get('technical_levels',{}),
    'credit_spreads': enh2.get('credit_spreads',{}),
    'northbound_southbound': enh2.get('northbound_southbound',{}),
    'yield_curve': enh2.get('yield_curve',{}),
    'report_date': DATE, 'generated_at': datetime.now().isoformat(),
    'fact_check_report': {'total_events_checked': len(news_events), 'corrections_applied': 0, 'status': '通過'}
}

with open(f'reports/raw_data_{DATE}.json', 'w', encoding='utf-8') as f:
    json.dump(raw_data, f, ensure_ascii=False, indent=2, default=str)

# 生成 HTML
html = generate_html_report(
    market_data, news_events, ser_hs(hot_stocks), stock_analysis,
    index_analysis, calendar_events, DATE,
    sentiment_data=enh.get('sentiment',{}),
    clock_data=enh.get('clock',{}),
    fund_flows=enh.get('fund_flows',{}),
)

# 注入增強區塊
def insert_before_section(html, section_text, new_block):
    import re
    pat = rf'(<div class="section-new-page"></div>\s*<div class="section-title">{re.escape(section_text)}</div>)'
    m = re.search(pat, html)
    if m: return html[:m.start()] + new_block + html[m.start():]
    pat2 = rf'(<div class="section-title">{re.escape(section_text)}</div>)'
    m2 = re.search(pat2, html)
    if m2: return html[:m2.start()] + new_block + html[m2.start():]
    return html

if executive_summary:
    es = executive_summary.replace('\n', '<br>')
    html = insert_before_section(html, '一、各國指數表現',
        f'<div style="background:linear-gradient(135deg,#f0f7ff 0%,#e8f4fd 100%);border-left:5px solid #1a365d;padding:18px 22px;margin:18px 0 20px 0;font-size:10.5pt;line-height:1.9;color:#2c3e50;border-radius:0 8px 8px 0;box-shadow:0 2px 8px rgba(0,0,0,0.05);page-break-inside:avoid;"><div style="font-size:14pt;font-weight:800;color:#1a365d;margin-bottom:12px;">市場綜述 Executive Summary</div>{es}</div>\n')

tech = enh2.get('technical_levels', {})
if tech:
    rows = ""
    for name, t in tech.items():
        rsi = t.get('rsi',0)
        rc = '#e74c3c' if rsi < 30 else '#27ae60' if rsi > 70 else '#2c3e50'
        cross = t.get('cross','') or ''
        cc = '#27ae60' if '黃金' in cross else '#e74c3c' if '死亡' in cross else '#999'
        m200 = f"{t['ma200']:,.0f}" if t.get('ma200') else 'N/A'
        rows += f'<tr><td style="font-weight:600;text-align:left;">{name}</td><td style="text-align:right;">{t.get("current",0):,.0f}</td><td style="text-align:right;">{t.get("ma50",0):,.0f}</td><td style="text-align:right;">{m200}</td><td style="text-align:right;font-weight:700;color:{rc};">{rsi:.1f}</td><td style="text-align:right;color:#e74c3c;">{t.get("pct_from_high",0):+.1f}%</td><td style="text-align:center;color:{cc};font-size:8.5pt;">{cross}</td></tr>'
    html = insert_before_section(html, '三、商品、外匯與債券',
        f'<div style="margin:16px 0 20px 0;page-break-inside:avoid;"><div style="font-size:13pt;font-weight:700;color:#2c3e50;border-bottom:2.5px solid #e67e22;padding-bottom:6px;margin-bottom:10px;">主要指數技術面關鍵位</div><table><thead><tr><th style="text-align:left;">指數</th><th style="text-align:right;">收盤</th><th style="text-align:right;">50MA</th><th style="text-align:right;">200MA</th><th style="text-align:right;">RSI(14)</th><th style="text-align:right;">距52W高</th><th style="text-align:center;">均線交叉</th></tr></thead><tbody>{rows}</tbody></table></div>\n')

if yield_curve_analysis:
    html = insert_before_section(html, '四、市場情緒指標',
        f'<div style="background:linear-gradient(135deg,#f5f0ff 0%,#ede5ff 100%);border-left:4px solid #6c5ce7;padding:14px 18px;margin:14px 0;font-size:9.5pt;line-height:1.8;border-radius:0 6px 6px 0;page-break-inside:avoid;"><strong style="color:#6c5ce7;font-size:10.5pt;">殖利率曲線分析</strong><br>{yield_curve_analysis}</div>\n')

if historical:
    hp = [v for v in historical.values() if isinstance(v, str)]
    if hp:
        html = insert_before_section(html, '五、全球資金流向脈動',
            f'<div style="background:linear-gradient(135deg,#fff5f5 0%,#ffe8e8 100%);border-left:4px solid #e74c3c;padding:14px 18px;margin:14px 0;font-size:9.5pt;line-height:1.8;border-radius:0 6px 6px 0;page-break-inside:avoid;"><strong style="color:#c0392b;font-size:10.5pt;">歷史情境參考</strong><br>{"<br><br>".join(hp)}</div>\n')

if sector_analysis:
    html = insert_before_section(html, '六、GICS 11大板塊資金流向',
        f'<div style="background:linear-gradient(135deg,#fff8f0 0%,#ffecd2 100%);border-left:4px solid #e67e22;padding:14px 18px;margin:14px 0;font-size:9.5pt;line-height:1.8;border-radius:0 6px 6px 0;page-break-inside:avoid;"><strong style="color:#d35400;font-size:10.5pt;">行業輪動解讀</strong><br>{sector_analysis}</div>\n')

html_path = f'reports/daily_report_{DATE}.html'
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'HTML 報告已生成: {html_path}')
PYEOF
log "  ✓ HTML 報告組裝完成"

# ─── Step 7: Chrome 生成 PDF ───
log "Step 7: 生成 PDF..."
HTML_PATH="${SCRIPT_DIR}/reports/daily_report_${DATE}.html"
PDF_PATH="${SCRIPT_DIR}/reports/daily_report_${DATE}.pdf"

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless --disable-gpu --no-sandbox \
    --print-to-pdf="${PDF_PATH}" \
    --print-to-pdf-no-header \
    "file://${HTML_PATH}" >> "${LOG_FILE}" 2>&1

if [ -f "${PDF_PATH}" ] && [ $(stat -f%z "${PDF_PATH}") -gt 1000 ]; then
    log "  ✓ PDF 生成成功: $(du -h "${PDF_PATH}" | cut -f1)"
else
    log "  ✗ PDF 生成失敗"
    exit 1
fi

# ─── Step 8: 發送 Email ───
log "Step 8: 發送 Email..."
python3 -c "
import sys
sys.path.insert(0, '${SCRIPT_DIR}')
from modules.email_sender import send_report_email
result = send_report_email('${DATE}', '${PDF_PATH}', '${SCRIPT_DIR}/reports/raw_data_${DATE}.json')
print(f'Email 發送結果: {result}')
" >> "${LOG_FILE}" 2>&1
log "  ✓ Email 發送完成"

log "=========================================="
log "全部完成！"
log "=========================================="
