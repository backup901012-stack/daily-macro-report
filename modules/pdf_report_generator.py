#!/usr/bin/env python3
"""
ReportLab 原生 PDF 報告引擎
取代 Chrome headless HTML→PDF，提供投行級排版品質
"""
import os
import json
import math
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, CondPageBreak, KeepTogether, HRFlowable, Image
)
from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import Drawing, Rect, Circle, Line, String, Wedge, Group
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================================
# 常數
# ============================================================
PAGE_W, PAGE_H = A4  # 595 x 842 pt
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 15 * mm
MARGIN_LR = 15 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_LR  # ~511 pt

# 顏色
PRIMARY = colors.HexColor('#1a365d')
SECONDARY = colors.HexColor('#2c3e50')
ACCENT = colors.HexColor('#e67e22')
GREEN = colors.HexColor('#27ae60')
RED = colors.HexColor('#e74c3c')
ORANGE = colors.HexColor('#e67e22')
BLUE = colors.HexColor('#3498db')
GRAY = colors.HexColor('#95a5a6')
LIGHT_GRAY = colors.HexColor('#f8f9fa')
BORDER_GRAY = colors.HexColor('#dee2e6')
WHITE = colors.white
BLACK = colors.HexColor('#1a1a2e')

# 方向顏色
DIR_COLORS = {
    '利空': RED,
    '利多': GREEN,
    '中性': BLUE,
}

# ============================================================
# 字體註冊
# ============================================================
_font_registered = False

def _register_fonts():
    global _font_registered
    if _font_registered:
        return
    # 嘗試多個字體路徑
    font_paths = [
        '/usr/share/fonts/truetype/noto/NotoSansCJKtc-Regular.ttf',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                if fp.endswith('.ttc'):
                    pdfmetrics.registerFont(TTFont('CJK', fp, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont('CJK', fp))
                _font_registered = True
                print(f'  ✓ 字體: {os.path.basename(fp)}')
                return
            except Exception as e:
                print(f'  ⚠️ 字體 {fp} 載入失敗: {e}')
    # fallback
    print('  ⚠️ 無 CJK 字體，使用 Helvetica')
    _font_registered = True


def _font():
    return 'CJK' if pdfmetrics.getFont('CJK', None) else 'Helvetica'


def _get_font():
    """取得可用的字體名稱"""
    try:
        pdfmetrics.getFont('CJK')
        return 'CJK'
    except:
        return 'Helvetica'


# ============================================================
# 樣式
# ============================================================
def _build_styles():
    f = _get_font()
    styles = {}
    styles['title'] = ParagraphStyle('Title', fontName=f, fontSize=16, leading=22,
        textColor=PRIMARY, spaceAfter=4*mm, spaceBefore=2*mm, alignment=TA_LEFT)
    styles['section'] = ParagraphStyle('Section', fontName=f, fontSize=14, leading=20,
        textColor=PRIMARY, spaceBefore=6*mm, spaceAfter=3*mm, borderWidth=0)
    styles['subsection'] = ParagraphStyle('SubSection', fontName=f, fontSize=11, leading=16,
        textColor=SECONDARY, spaceBefore=4*mm, spaceAfter=2*mm)
    styles['body'] = ParagraphStyle('Body', fontName=f, fontSize=9.5, leading=15,
        textColor=SECONDARY, spaceAfter=2*mm, alignment=TA_JUSTIFY)
    styles['small'] = ParagraphStyle('Small', fontName=f, fontSize=8, leading=12,
        textColor=GRAY, spaceAfter=1*mm)
    styles['card_title'] = ParagraphStyle('CardTitle', fontName=f, fontSize=11, leading=15,
        textColor=BLACK, spaceAfter=1*mm)
    styles['card_body'] = ParagraphStyle('CardBody', fontName=f, fontSize=9, leading=14,
        textColor=SECONDARY, spaceAfter=1*mm, alignment=TA_JUSTIFY)
    styles['metric_big'] = ParagraphStyle('MetricBig', fontName=f, fontSize=22, leading=28,
        alignment=TA_CENTER, spaceAfter=1*mm)
    styles['metric_label'] = ParagraphStyle('MetricLabel', fontName=f, fontSize=8, leading=11,
        textColor=GRAY, alignment=TA_CENTER)
    styles['metric_sub'] = ParagraphStyle('MetricSub', fontName=f, fontSize=8.5, leading=12,
        alignment=TA_CENTER)
    styles['footer'] = ParagraphStyle('Footer', fontName=f, fontSize=7.5, leading=11,
        textColor=GRAY, alignment=TA_CENTER)
    styles['summary_title'] = ParagraphStyle('SummaryTitle', fontName=f, fontSize=10, leading=15,
        textColor=PRIMARY, spaceBefore=2*mm, spaceAfter=1*mm)
    styles['summary_body'] = ParagraphStyle('SummaryBody', fontName=f, fontSize=9.5, leading=16,
        textColor=SECONDARY, spaceAfter=2*mm, alignment=TA_JUSTIFY)
    return styles


# ============================================================
# 輔助元件
# ============================================================

class SectionTitle(Flowable):
    """章節標題（帶底部彩色線）"""
    def __init__(self, text, color=ACCENT, width=CONTENT_W):
        Flowable.__init__(self)
        self.text = text
        self.color = color
        self.width = width
        self.height = 28

    def draw(self):
        self.canv.setFont(_get_font(), 14)
        self.canv.setFillColor(PRIMARY)
        self.canv.drawString(0, 10, self.text)
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(2.5)
        self.canv.line(0, 4, self.width, 4)


class ColoredBox(Flowable):
    """帶左側色條的文字框"""
    def __init__(self, content_paras, border_color=PRIMARY, bg_color=LIGHT_GRAY, width=CONTENT_W, padding=12):
        Flowable.__init__(self)
        self.content_paras = content_paras  # list of (text, style)
        self.border_color = border_color
        self.bg_color = bg_color
        self.box_width = width
        self.padding = padding
        # 計算高度
        self._built = []
        total_h = padding * 2
        for text, style in content_paras:
            p = Paragraph(text, style)
            pw, ph = p.wrap(width - padding * 2 - 5, 1000)
            self._built.append((p, ph))
            total_h += ph + 2
        self.height = total_h
        self.width = width

    def draw(self):
        c = self.canv
        # 背景
        c.setFillColor(self.bg_color)
        c.roundRect(5, 0, self.box_width - 5, self.height, 4, fill=1, stroke=0)
        # 左側色條
        c.setFillColor(self.border_color)
        c.rect(0, 0, 5, self.height, fill=1, stroke=0)
        # 內容
        y = self.height - self.padding
        for p, ph in self._built:
            p.drawOn(c, self.padding + 5, y - ph)
            y -= ph + 2


def _chg_color(val):
    """漲跌顏色"""
    if val is None or val == 0:
        return GRAY
    return GREEN if val > 0 else RED


def _fmt_chg(val, suffix='%'):
    """格式化漲跌"""
    if val is None:
        return '—'
    return f'{val:+.2f}{suffix}'


def _fmt_price(val, decimals=2):
    """格式化價格"""
    if val is None:
        return '—'
    if abs(val) >= 10000:
        return f'{val:,.{decimals}f}'
    return f'{val:.{decimals}f}'


def _trend_arrow(val):
    """趨勢箭頭"""
    if val is None or val == 0:
        return '—'
    if val > 1:
        return '▲▲'
    if val > 0:
        return '▲'
    if val < -1:
        return '▼▼'
    return '▼'


def _badge_text(text, color):
    """生成彩色標籤的 HTML"""
    return f'<font color="white"><b> {text} </b></font>'


# ============================================================
# 表格建構
# ============================================================

def _build_market_table(data_dict, columns, col_widths=None):
    """建構市場數據表格

    columns: [(display_name, data_key, formatter, align), ...]
    """
    if not data_dict:
        return []

    f = _get_font()
    header = [Paragraph(f'<b>{c[0]}</b>', ParagraphStyle('th', fontName=f, fontSize=8, leading=11, textColor=SECONDARY, alignment=TA_CENTER if i > 0 else TA_LEFT)) for i, c in enumerate(columns)]
    rows = [header]

    for name, d in data_dict.items():
        if not isinstance(d, dict):
            continue
        row = []
        for i, (col_name, key, formatter, align) in enumerate(columns):
            val = d.get(key, name if key == '_name' else None)
            if key == '_name':
                val = name
            text = formatter(val) if formatter else str(val or '—')

            # 漲跌顏色
            color = SECONDARY
            if key in ('change_pct', 'change', 'ytd_pct') and isinstance(val, (int, float)):
                color = _chg_color(val)
            elif key == 'cross' and val:
                color = GREEN if '黃金' in str(val) else RED if '死亡' in str(val) else GRAY

            style = ParagraphStyle('td', fontName=f, fontSize=8.5, leading=12,
                textColor=color, alignment=TA_LEFT if i == 0 else TA_RIGHT)
            row.append(Paragraph(text, style))
        rows.append(row)

    if not col_widths:
        n = len(columns)
        first_w = CONTENT_W * 0.18
        rest_w = (CONTENT_W - first_w) / (n - 1)
        col_widths = [first_w] + [rest_w] * (n - 1)

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), SECONDARY),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, BORDER_GRAY),
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#eee')),
        ('LINEBELOW', (0, -1), (-1, -1), 1, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#fafbfc')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return [t, Spacer(1, 3*mm)]


# ============================================================
# 章節生成器
# ============================================================

def _gen_cover(date_str, executive_summary=''):
    """封面"""
    f = _get_font()
    elements = []

    # 頂部色帶
    d = Drawing(CONTENT_W, 120)
    d.add(Rect(0, 0, CONTENT_W, 120, fillColor=PRIMARY, strokeColor=None))
    # 標題文字
    d.add(String(25, 75, '每日宏觀資訊綜合早報', fontName=f, fontSize=26, fillColor=WHITE))
    d.add(String(25, 52, 'Daily Macro Market Briefing', fontName=f, fontSize=12, fillColor=colors.HexColor('#8899aa')))
    d.add(String(25, 30, f'{date_str}  ｜  綜合早報', fontName=f, fontSize=10, fillColor=colors.HexColor('#aabbcc')))
    elements.append(d)
    elements.append(Spacer(1, 6*mm))

    return elements


def _gen_snapshot_box(raw_data, styles):
    """市場快照框（封面下方）"""
    md = raw_data.get('market_data', {})
    sd = raw_data.get('sentiment_data', {})
    f = _get_font()

    us = md.get('us_indices', {})
    sp = us.get('S&P 500', {})
    nq = us.get('納斯達克', {})

    comm = md.get('commodities', {})
    gold = comm.get('黃金', {})
    oil = comm.get('原油(WTI)', {})

    forex = md.get('forex', {})
    dxy = forex.get('美元指數', {})

    bonds = md.get('bonds', {})
    us10y = bonds.get('美國10年期', {})

    crypto = md.get('crypto', {})
    btc = crypto.get('Bitcoin', {})
    eth = crypto.get('Ethereum', {})

    fg = sd.get('fear_greed', {})
    vix = sd.get('vix', {})

    lines = []
    # 股市
    sp_chg = sp.get('change_pct', 0)
    nq_chg = nq.get('change_pct', 0)
    sp_c = '#27ae60' if sp_chg > 0 else '#e74c3c'
    nq_c = '#27ae60' if nq_chg > 0 else '#e74c3c'
    lines.append(f'<b>股市：</b>S&P 500 <font color="{sp_c}">{sp_chg:+.2f}%</font>，納斯達克 <font color="{nq_c}">{nq_chg:+.2f}%</font>')

    # 商品
    gold_chg = gold.get('change_pct', 0)
    oil_chg = oil.get('change_pct', 0)
    gc = '#27ae60' if gold_chg > 0 else '#e74c3c'
    oc = '#27ae60' if oil_chg > 0 else '#e74c3c'
    lines.append(f'<b>商品：</b>黃金 <font color="{gc}">{gold_chg:+.2f}%</font>  ｜  原油(WTI) <font color="{oc}">{oil_chg:+.2f}%</font>')

    # 外匯
    dxy_chg = dxy.get('change_pct', 0)
    dc = '#27ae60' if dxy_chg > 0 else '#e74c3c'
    lines.append(f'<b>外匯：</b>美元指數 {dxy.get("current", "—")} (<font color="{dc}">{dxy_chg:+.2f}%</font>)')

    # 加密
    btc_chg = btc.get('change_pct', 0)
    bc = '#27ae60' if btc_chg > 0 else '#e74c3c'
    lines.append(f'<b>加密：</b>BTC ${btc.get("current", 0):,.0f} (<font color="{bc}">{btc_chg:+.2f}%</font>)')

    # 焦點
    ne = raw_data.get('news_events', [])
    if ne:
        lines.append(f'<b>焦點事件：</b>{ne[0].get("title", "")}')

    content = [(l, ParagraphStyle('snap', fontName=f, fontSize=9, leading=15, textColor=SECONDARY)) for l in lines]

    return ColoredBox(content, border_color=PRIMARY, bg_color=colors.HexColor('#f0f7ff'), padding=10)


def _gen_executive_summary(text, styles):
    """市場綜述框"""
    if not text:
        return []
    f = _get_font()
    content = [
        (f'<b>市場綜述 Executive Summary</b>', ParagraphStyle('es_t', fontName=f, fontSize=10, leading=14, textColor=PRIMARY)),
        (text, ParagraphStyle('es_b', fontName=f, fontSize=9.5, leading=15, textColor=SECONDARY)),
    ]
    return [Spacer(1, 2*mm), ColoredBox(content, border_color=PRIMARY, bg_color=colors.HexColor('#f0f7ff'), padding=10), Spacer(1, 4*mm)]


def _gen_news_section(news_events, styles):
    """宏觀重點新聞"""
    if not news_events:
        return []

    f = _get_font()
    elements = []
    elements.append(SectionTitle('一、宏觀重點新聞'))
    elements.append(Spacer(1, 2*mm))

    headlines = [e for e in news_events if e.get('is_headline')]
    briefs = [e for e in news_events if not e.get('is_headline')]

    for i, event in enumerate(headlines, 1):
        direction = event.get('market_direction', '中性')
        impact = event.get('impact_level', '中')
        border_color = DIR_COLORS.get(direction, BLUE)
        narrative = event.get('narrative', '')
        title = event.get('title', '')
        source = event.get('source_info', '')
        affected = event.get('affected_markets', '')
        head_lines = event.get('headlines', [])[:4]
        data_pts = event.get('data_points', [])
        tickers = event.get('related_tickers', [])[:5]

        # 影響/方向標籤
        impact_color = '#c0392b' if impact == '高' else '#e67e22'
        dir_label = {'利空': '▼ 利空', '利多': '▲ 利多', '中性': '— 中性'}.get(direction, '— 中性')
        dir_color = '#e74c3c' if direction == '利空' else '#27ae60' if direction == '利多' else '#3498db'

        card_parts = []

        # 標題行
        title_text = f'<b>{i}. {title}</b>  <font color="{impact_color}" size="7"><b>[{impact}影響]</b></font>  <font color="{dir_color}" size="7"><b>[{dir_label}]</b></font>'
        card_parts.append((title_text, ParagraphStyle('nt', fontName=f, fontSize=11, leading=16, textColor=BLACK)))

        # 來源
        card_parts.append((f'{source}  ｜  影響範圍：{affected}', ParagraphStyle('ns', fontName=f, fontSize=7.5, leading=10, textColor=GRAY)))

        # 敘事摘要
        if narrative:
            card_parts.append((narrative, ParagraphStyle('nn', fontName=f, fontSize=9.5, leading=15, textColor=SECONDARY)))

        # 重點標題
        if head_lines:
            hl_text = '<br/>'.join([f'• {h}' for h in head_lines])
            card_parts.append((f'<font size="7" color="#95a5a6"><b>HEADLINES</b></font><br/>{hl_text}',
                ParagraphStyle('nh', fontName=f, fontSize=8.5, leading=13, textColor=SECONDARY)))

        # 數據
        if data_pts:
            dp_text = '  ｜  '.join(data_pts)
            card_parts.append((f'<font size="7" color="#95a5a6"><b>MARKET DATA</b></font>  {dp_text}',
                ParagraphStyle('nd', fontName=f, fontSize=8.5, leading=12, textColor=SECONDARY)))

        # Tickers
        if tickers:
            tk_text = '  '.join([f'<font color="#4a4a8a" size="7"><b>[{t}]</b></font>' for t in tickers])
            card_parts.append((tk_text, ParagraphStyle('ntk', fontName=f, fontSize=7.5, leading=10, textColor=colors.HexColor('#4a4a8a'))))

        box = ColoredBox(card_parts, border_color=border_color, bg_color=LIGHT_GRAY, padding=12)
        elements.append(box)
        elements.append(Spacer(1, 3*mm))

    # 其他要聞
    if briefs:
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph('<b>其他要聞</b>', ParagraphStyle('bh', fontName=f, fontSize=11, leading=16, textColor=BLACK, spaceBefore=2*mm, spaceAfter=2*mm)))
        for event in briefs:
            direction = event.get('market_direction', '中性')
            border_color = DIR_COLORS.get(direction, GRAY)
            title = event.get('title', '')
            narrative = event.get('narrative', '')[:150]
            dir_label = {'利空': '▼ 利空', '利多': '▲ 利多', '中性': '— 中性'}.get(direction, '')
            dir_color = '#e74c3c' if direction == '利空' else '#27ae60' if direction == '利多' else '#95a5a6'

            parts = [
                (f'<b>{title}</b>  <font color="{dir_color}" size="7"><b>[{dir_label}]</b></font>  <font color="#aaa" size="7">{event.get("source_info","")}</font>',
                 ParagraphStyle('bt', fontName=f, fontSize=10, leading=14, textColor=BLACK)),
            ]
            if narrative:
                parts.append((narrative, ParagraphStyle('bn', fontName=f, fontSize=8.5, leading=13, textColor=SECONDARY)))

            box = ColoredBox(parts, border_color=border_color, bg_color=LIGHT_GRAY, padding=8)
            elements.append(KeepTogether([box, Spacer(1, 2*mm)]))

    return elements


def _gen_index_section(market_data, technical_levels, index_analysis, styles):
    """全球指數表現"""
    f = _get_font()
    elements = []
    elements.append(SectionTitle('二、全球指數表現'))

    cols = [
        ('指數', '_name', None, TA_LEFT),
        ('收盤價', 'current', lambda v: _fmt_price(v, 2), TA_RIGHT),
        ('昨日漲跌', 'change', lambda v: _fmt_chg(v, ''), TA_RIGHT),
        ('昨日漲跌幅', 'change_pct', lambda v: _fmt_chg(v), TA_RIGHT),
        ('年初至今(%)', 'ytd_pct', lambda v: _fmt_chg(v) if v else '—', TA_RIGHT),
    ]
    cw = [CONTENT_W*0.20, CONTENT_W*0.20, CONTENT_W*0.20, CONTENT_W*0.20, CONTENT_W*0.20]

    for region, label in [('asia_indices', '亞洲市場'), ('europe_indices', '歐洲市場'), ('us_indices', '美國市場')]:
        data = market_data.get(region, {})
        if not data:
            continue
        elements.append(Paragraph(f'<b>{label}</b>', ParagraphStyle('r', fontName=f, fontSize=10, leading=14, textColor=SECONDARY, spaceBefore=3*mm, spaceAfter=1*mm)))

        # 摘要文字
        chgs = [(n, d.get('change_pct', 0)) for n, d in data.items() if isinstance(d, dict)]
        if chgs:
            best = max(chgs, key=lambda x: x[1])
            worst = min(chgs, key=lambda x: x[1])
            elements.append(Paragraph(
                f'{label}表現最佳：{best[0]}（{best[1]:+.2f}%），最弱：{worst[0]}（{worst[1]:+.2f}%）',
                ParagraphStyle('rs', fontName=f, fontSize=8, leading=12, textColor=GRAY, spaceAfter=1*mm)
            ))

        elements.extend(_build_market_table(data, cols, cw))

    # 技術面
    if technical_levels:
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph('<b>主要指數技術面關鍵位</b>', ParagraphStyle('tt', fontName=f, fontSize=10, leading=14, textColor=SECONDARY, spaceAfter=1*mm)))
        tech_cols = [
            ('指數', '_name', None, TA_LEFT),
            ('收盤', 'current', lambda v: _fmt_price(v, 0), TA_RIGHT),
            ('50MA', 'ma50', lambda v: _fmt_price(v, 0), TA_RIGHT),
            ('200MA', 'ma200', lambda v: _fmt_price(v, 0) if v else 'N/A', TA_RIGHT),
            ('RSI(14)', 'rsi', lambda v: f'{v:.1f}' if v else '—', TA_RIGHT),
            ('距52W高', 'pct_from_high', lambda v: _fmt_chg(v), TA_RIGHT),
            ('均線交叉', 'cross', lambda v: v or '—', TA_CENTER),
        ]
        tcw = [CONTENT_W*0.16, CONTENT_W*0.12, CONTENT_W*0.12, CONTENT_W*0.12, CONTENT_W*0.12, CONTENT_W*0.14, CONTENT_W*0.22]
        elements.extend(_build_market_table(technical_levels, tech_cols, tcw))

    return elements


def _gen_bonds_section(bonds_data, yield_curve_analysis, styles):
    """債券殖利率"""
    f = _get_font()
    elements = []
    elements.append(SectionTitle('三、債券・殖利率'))

    cols = [
        ('債券', '_name', None, TA_LEFT),
        ('殖利率', 'current', lambda v: f'{v:.3f}%' if v else '—', TA_RIGHT),
        ('變動', 'change', lambda v: _fmt_chg(v, ''), TA_RIGHT),
        ('變動幅度', 'change_pct', lambda v: _fmt_chg(v), TA_RIGHT),
    ]
    cw = [CONTENT_W*0.30, CONTENT_W*0.23, CONTENT_W*0.23, CONTENT_W*0.24]
    elements.extend(_build_market_table(bonds_data, cols, cw))

    if yield_curve_analysis:
        content = [
            ('<b>殖利率曲線分析</b>', ParagraphStyle('yca_t', fontName=f, fontSize=10, leading=14, textColor=colors.HexColor('#6c5ce7'))),
            (yield_curve_analysis, ParagraphStyle('yca_b', fontName=f, fontSize=9, leading=14, textColor=SECONDARY)),
        ]
        elements.append(ColoredBox(content, border_color=colors.HexColor('#6c5ce7'), bg_color=colors.HexColor('#f5f0ff'), padding=10))
        elements.append(Spacer(1, 3*mm))

    return elements


def _gen_forex_section(forex_data, styles):
    """外匯市場"""
    f = _get_font()
    elements = []
    elements.append(SectionTitle('四、外匯市場'))

    cols = [
        ('貨幣對', '_name', None, TA_LEFT),
        ('匯率', 'current', lambda v: _fmt_price(v, 4), TA_RIGHT),
        ('漲跌', 'change', lambda v: _fmt_chg(v, ''), TA_RIGHT),
        ('漲跌幅', 'change_pct', lambda v: _fmt_chg(v), TA_RIGHT),
    ]
    cw = [CONTENT_W*0.30, CONTENT_W*0.23, CONTENT_W*0.23, CONTENT_W*0.24]
    elements.extend(_build_market_table(forex_data, cols, cw))
    return elements


def _gen_commodities_section(commodities_data, styles):
    """大宗商品"""
    f = _get_font()
    elements = []
    elements.append(SectionTitle('五、大宗商品'))

    cols = [
        ('商品', '_name', None, TA_LEFT),
        ('價格', 'current', lambda v: f'${_fmt_price(v, 2)}', TA_RIGHT),
        ('漲跌', 'change', lambda v: _fmt_chg(v, ''), TA_RIGHT),
        ('漲跌幅', 'change_pct', lambda v: _fmt_chg(v), TA_RIGHT),
    ]
    cw = [CONTENT_W*0.30, CONTENT_W*0.23, CONTENT_W*0.23, CONTENT_W*0.24]
    elements.extend(_build_market_table(commodities_data, cols, cw))
    return elements


def _gen_crypto_section(crypto_data, styles):
    """加密貨幣"""
    f = _get_font()
    elements = []
    elements.append(SectionTitle('六、加密貨幣'))

    cols = [
        ('幣種', '_name', None, TA_LEFT),
        ('價格', 'current', lambda v: f'${_fmt_price(v, 2)}', TA_RIGHT),
        ('漲跌幅', 'change_pct', lambda v: _fmt_chg(v), TA_RIGHT),
    ]
    cw = [CONTENT_W*0.40, CONTENT_W*0.30, CONTENT_W*0.30]
    elements.extend(_build_market_table(crypto_data, cols, cw))
    return elements


def _gen_sentiment_section(sentiment_data, clock_data, historical_context, styles):
    """市場情緒指標"""
    f = _get_font()
    elements = []
    elements.append(PageBreak())
    elements.append(SectionTitle('七、市場情緒指標'))

    fg = sentiment_data.get('fear_greed', {})
    vix = sentiment_data.get('vix', {})
    us10y = sentiment_data.get('us10y', {})
    dxy = sentiment_data.get('dxy', {})

    fg_score = fg.get('score', 50)
    fg_rating = '極度恐懼' if fg_score < 25 else '恐懼' if fg_score < 45 else '中性' if fg_score < 55 else '貪婪' if fg_score < 75 else '極度貪婪'
    fg_color = RED if fg_score < 25 else ORANGE if fg_score < 45 else colors.HexColor('#f1c40f') if fg_score < 55 else GREEN

    vix_val = vix.get('value', 0) if 'error' not in vix else 0
    vix_chg = vix.get('change', 0)

    # 四格指標卡
    metrics = [
        ('CNN 恐懼與貪婪', f'{fg_score:.1f}', fg_rating, fg_color),
        ('VIX 恐慌指數', f'{vix_val:.2f}' if vix_val else 'N/A', f'{vix_chg:+.2f} ({vix.get("change_pct",0):+.1f}%)' if vix_val else '', RED if vix_val > 25 else GREEN),
        ('美10Y殖利率', f'{us10y.get("yield", 0):.3f}%', f'{us10y.get("change", 0):+.4f}', SECONDARY),
        ('美元指數 DXY', f'{dxy.get("value", 0):.2f}', '—', SECONDARY),
    ]

    card_data = []
    for label, value, sub, color in metrics:
        card_data.append([
            Paragraph(f'<font size="7" color="#999">{label}</font><br/><font size="18" color="{color.hexval()}">{value}</font><br/><font size="7" color="#999">{sub}</font>',
                ParagraphStyle('mc', fontName=f, fontSize=9, leading=14, alignment=TA_CENTER))
        ])

    metric_table = Table([card_data[0] + card_data[1] + card_data[2] + card_data[3]],
        colWidths=[CONTENT_W/4]*4)
    metric_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(metric_table)
    elements.append(Spacer(1, 4*mm))

    # 恐貪歷史比較
    fg_prev = fg.get('previous_close', 0) or 0
    fg_1w = fg.get('previous_1_week', 0) or 0
    fg_1m = fg.get('previous_1_month', 0) or 0
    fg_1y = fg.get('previous_1_year', 0) or 0

    hist_header = [Paragraph(f'<b>{h}</b>', ParagraphStyle('hh', fontName=f, fontSize=8, leading=11, textColor=SECONDARY, alignment=TA_CENTER if i > 0 else TA_LEFT))
        for i, h in enumerate(['指標', '當前', '前日', '一週前', '一月前', '一年前'])]
    hist_row = [
        Paragraph('恐懼與貪婪', ParagraphStyle('hr', fontName=f, fontSize=8.5, leading=12, textColor=SECONDARY)),
    ]
    for v in [fg_score, fg_prev, fg_1w, fg_1m, fg_1y]:
        c = RED if v < 25 else ORANGE if v < 45 else GREEN
        hist_row.append(Paragraph(f'<font color="{c.hexval()}">{v:.1f}</font>', ParagraphStyle('hv', fontName=f, fontSize=8.5, leading=12, alignment=TA_CENTER)))

    hist_table = Table([hist_header, hist_row], colWidths=[CONTENT_W*0.18] + [CONTENT_W*0.164]*5)
    hist_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, BORDER_GRAY),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(hist_table)
    elements.append(Spacer(1, 4*mm))

    # 美林時鐘
    if clock_data and clock_data.get('phase') != 'Unknown':
        phase_cn = clock_data.get('phase_cn', '未知')
        confidence = clock_data.get('confidence', '弱')
        growth = '↓' if clock_data.get('growth_direction') == 'down' else '↑'
        inflation = '↑' if clock_data.get('inflation_direction') == 'up' else '↓'

        content = [
            (f'<b>經濟週期指示器：{phase_cn}</b>', ParagraphStyle('cl_t', fontName=f, fontSize=10, leading=14, textColor=ACCENT)),
            (f'增長方向：{growth}  ｜  通膨方向：{inflation}  ｜  信號強度：{confidence}', ParagraphStyle('cl_b', fontName=f, fontSize=9, leading=13, textColor=SECONDARY)),
        ]
        elements.append(ColoredBox(content, border_color=ACCENT, bg_color=colors.HexColor('#fff8f0'), padding=10))
        elements.append(Spacer(1, 3*mm))

    # 歷史情境
    if historical_context:
        hc_parts = []
        for k, v in historical_context.items():
            if isinstance(v, str) and v:
                hc_parts.append(v)
        if hc_parts:
            content = [
                ('<b>歷史情境參考</b>', ParagraphStyle('hc_t', fontName=f, fontSize=9, leading=13, textColor=RED)),
            ]
            for p in hc_parts:
                content.append((p, ParagraphStyle('hc_b', fontName=f, fontSize=8.5, leading=13, textColor=SECONDARY)))
            elements.append(ColoredBox(content, border_color=RED, bg_color=colors.HexColor('#fff5f5'), padding=8))

    return elements


def _gen_fund_flows_section(fund_flows, styles):
    """全球資金流向"""
    f = _get_font()
    elements = []
    elements.append(SectionTitle('八、全球資金流向'))

    etf_flows = fund_flows.get('etf_flows', [])
    if not etf_flows:
        elements.append(Paragraph('資金流向數據暫缺', styles['small']))
        return elements

    # 表格
    header = ['國家/地區', 'ETF', '當日', '近一週', '近一月', '年初至今']
    rows = [header]
    for ef in etf_flows:
        rows.append([
            ef.get('country', ''),
            ef.get('etf', ''),
            ef.get('daily_flow_str', '—'),
            ef.get('weekly_flow_str', '—'),
            ef.get('monthly_flow_str', '—'),
            ef.get('ytd_flow_str', '—'),
        ])

    cw = [CONTENT_W*0.16, CONTENT_W*0.10, CONTENT_W*0.16, CONTENT_W*0.16, CONTENT_W*0.16, CONTENT_W*0.16]
    t = Table(rows, colWidths=cw, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
        ('FONTNAME', (0, 0), (-1, -1), f),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, BORDER_GRAY),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor('#eee')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#fafbfc')]),
    ]

    # 顏色標記正負
    for ri, row in enumerate(rows[1:], 1):
        for ci in range(2, 6):
            val = row[ci]
            if isinstance(val, str) and ('+' in val):
                style_cmds.append(('TEXTCOLOR', (ci, ri), (ci, ri), GREEN))
            elif isinstance(val, str) and ('-' in val):
                style_cmds.append(('TEXTCOLOR', (ci, ri), (ci, ri), RED))

    t.setStyle(TableStyle(style_cmds))
    elements.append(t)
    elements.append(Spacer(1, 3*mm))

    return elements


def _gen_hot_stocks_section(hot_stocks, stock_analysis, styles):
    """熱門股票"""
    f = _get_font()
    elements = []
    elements.append(SectionTitle('十、當日熱門股票'))

    for market, data in hot_stocks.items():
        if not isinstance(data, dict):
            continue
        inflow = data.get('inflow', [])
        outflow = data.get('outflow', [])
        if not inflow and not outflow:
            continue

        elements.append(Paragraph(f'<b>{market}</b>', ParagraphStyle('ms', fontName=f, fontSize=10, leading=14, textColor=SECONDARY, spaceBefore=3*mm, spaceAfter=1*mm)))

        for direction, stocks, label in [(inflow, inflow, '資金流入'), (outflow, outflow, '資金流出')]:
            if not stocks:
                continue
            elements.append(Paragraph(f'<font color="#999" size="8"><b>{label}</b></font>', ParagraphStyle('dl', fontName=f, fontSize=8, leading=11, textColor=GRAY, spaceAfter=1*mm)))

            header = ['股票', '代碼', '現價', '漲跌%', '量比']
            rows = [header]
            for s in stocks[:8]:
                chg = s.get('change_pct', 0)
                rows.append([
                    s.get('name', '')[:8],
                    s.get('symbol', ''),
                    _fmt_price(s.get('current'), 2),
                    _fmt_chg(chg),
                    f'{s.get("volume_ratio", 0):.1f}x' if s.get('volume_ratio') else '—',
                ])

            cw = [CONTENT_W*0.22, CONTENT_W*0.20, CONTENT_W*0.18, CONTENT_W*0.20, CONTENT_W*0.20]
            t = Table(rows, colWidths=cw, repeatRows=1)
            style_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
                ('FONTNAME', (0, 0), (-1, -1), f),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('LINEBELOW', (0, 0), (-1, 0), 1, BORDER_GRAY),
                ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor('#eee')),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ]
            # 漲跌顏色
            for ri in range(1, len(rows)):
                chg_val = stocks[ri-1].get('change_pct', 0)
                c = GREEN if chg_val > 0 else RED if chg_val < 0 else GRAY
                style_cmds.append(('TEXTCOLOR', (3, ri), (3, ri), c))

            t.setStyle(TableStyle(style_cmds))
            elements.append(t)
            elements.append(Spacer(1, 2*mm))

    return elements


def _gen_calendar_section(calendar_events, fred_data, styles):
    """經濟日曆 + FRED"""
    f = _get_font()
    elements = []
    elements.append(SectionTitle('十一、本週經濟日曆 + FRED'))

    if calendar_events:
        header = ['日期', '事件', '國家', '重要性', '說明']
        rows = [header]
        for e in calendar_events[:10]:
            rows.append([
                e.get('date', ''),
                e.get('event', ''),
                e.get('country', ''),
                e.get('importance', ''),
                (e.get('description', '') or '')[:40],
            ])

        cw = [CONTENT_W*0.12, CONTENT_W*0.22, CONTENT_W*0.10, CONTENT_W*0.10, CONTENT_W*0.46]
        t = Table(rows, colWidths=cw, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
            ('FONTNAME', (0, 0), (-1, -1), f),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, 0), 1, BORDER_GRAY),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor('#eee')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(t)

    return elements


def _gen_summary_section(ai_summary, styles):
    """總結分析"""
    if not ai_summary:
        return []

    f = _get_font()
    elements = []
    elements.append(SectionTitle('十二、總結分析 Daily Summary'))

    # 解析三段
    summary_html = ai_summary.replace('【今日重點】', '<b><font color="#1a365d">【今日重點】</font></b><br/>')
    summary_html = summary_html.replace('【核心驅動】', '<br/><br/><b><font color="#2d6a4f">【核心驅動】</font></b><br/>')
    summary_html = summary_html.replace('【明日關注】', '<br/><br/><b><font color="#c2185b">【明日關注】</font></b><br/>')
    summary_html = summary_html.replace('\n', '<br/>')

    content = [
        (summary_html, ParagraphStyle('sum', fontName=f, fontSize=9.5, leading=16, textColor=SECONDARY)),
        ('<font color="#aaa" size="7">— 僅供參考</font>', ParagraphStyle('disc', fontName=f, fontSize=7, leading=10, textColor=GRAY, alignment=TA_RIGHT)),
    ]
    elements.append(ColoredBox(content, border_color=PRIMARY, bg_color=LIGHT_GRAY, padding=14))
    elements.append(Spacer(1, 4*mm))

    return elements


def _gen_footer(date_str, styles):
    """名片 + 聲明"""
    f = _get_font()
    elements = []
    elements.append(Spacer(1, 4*mm))

    # 名片
    card_content = [
        ('<b>何宣逸</b>', ParagraphStyle('fn', fontName=f, fontSize=9, leading=13, textColor=SECONDARY)),
        ('副總裁 ｜ 私人財富管理部<br/>華泰金融控股（香港）有限公司<br/>電話：+852 3658 6180 ｜ 手機：+852 6765 0336 / +86 130 0329 5233<br/>電郵：jamieho@htsc.com<br/>地址：香港皇后大道中99號中環中心69樓',
         ParagraphStyle('fc', fontName=f, fontSize=7.5, leading=11, textColor=GRAY)),
        ('<font size="6" color="#aaa">華泰證券股份有限公司全資附屬公司 (SSE: 601688; SEHK: 6886; LSE: HTSC)</font>',
         ParagraphStyle('fx', fontName=f, fontSize=6, leading=9, textColor=GRAY)),
    ]
    elements.append(ColoredBox(card_content, border_color=PRIMARY, bg_color=LIGHT_GRAY, padding=10))
    elements.append(Spacer(1, 3*mm))

    # 聲明
    disclaimer = [
        (f'<b>報告製作時間</b>：{datetime.now().strftime("%Y-%m-%d %H:%M")} (UTC+8)<br/>'
         '<b>資料來源</b>：Yahoo Finance、Polygon.io、S&P Global、CNBC、Investing.com、CNN Fear &amp; Greed Index<br/>'
         '資金流向數據基於ETF Chaikin Money Flow (CMF) × 成交量計算<br/><br/>'
         '<i>本報告僅供參考，不構成任何投資建議。投資有風險，入市需謹慎。</i>',
         ParagraphStyle('disc', fontName=f, fontSize=7, leading=10, textColor=GRAY)),
    ]
    elements.append(ColoredBox(disclaimer, border_color=BORDER_GRAY, bg_color=WHITE, padding=8))

    return elements


# ============================================================
# 主函數
# ============================================================

def generate_pdf_report(raw_data, output_path, ai_summary=None):
    """生成完整 PDF 報告

    Args:
        raw_data: 完整的 raw_data dict（從 JSON 載入）
        output_path: PDF 輸出路徑
        ai_summary: Kimi 生成的總結文字（可選）

    Returns:
        str: PDF 檔案路徑
    """
    _register_fonts()
    styles = _build_styles()

    date_str = raw_data.get('report_date', datetime.now().strftime('%Y-%m-%d'))
    md = raw_data.get('market_data', {})
    news_events = raw_data.get('news_events', [])
    sentiment_data = raw_data.get('sentiment_data', {})
    clock_data = raw_data.get('clock_data', {})
    fund_flows = raw_data.get('fund_flows', {})
    hot_stocks = raw_data.get('hot_stocks', {})
    technical_levels = raw_data.get('technical_levels', {})
    calendar_events = raw_data.get('calendar_events', [])
    fred_data = raw_data.get('fred_data', {})
    historical_context = raw_data.get('historical_context', {})
    executive_summary = raw_data.get('executive_summary', '')
    yield_curve_analysis = raw_data.get('yield_curve_analysis', '')
    index_analysis = raw_data.get('index_analysis', '')
    stock_analysis = raw_data.get('stock_analysis', '')
    sector_analysis = raw_data.get('sector_analysis', '')

    # 頁首頁尾
    def _header_footer(canvas, doc):
        canvas.saveState()
        f = _get_font()
        # 頁首
        canvas.setFont(f, 7)
        canvas.setFillColor(GRAY)
        canvas.drawString(MARGIN_LR, PAGE_H - 12*mm, f'{date_str}')
        canvas.drawRightString(PAGE_W - MARGIN_LR, PAGE_H - 12*mm, f'每日宏觀資訊綜合早報 | {date_str}')
        canvas.setStrokeColor(BORDER_GRAY)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_LR, PAGE_H - 13*mm, PAGE_W - MARGIN_LR, PAGE_H - 13*mm)
        # 頁尾
        canvas.drawCentredString(PAGE_W / 2, 10*mm, f'{doc.page}')
        canvas.restoreState()

    def _first_page(canvas, doc):
        """封面不顯示頁首"""
        canvas.saveState()
        canvas.setFont(_get_font(), 7)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(PAGE_W / 2, 10*mm, f'{doc.page}')
        canvas.restoreState()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        leftMargin=MARGIN_LR,
        rightMargin=MARGIN_LR,
    )

    # 建構所有元素
    elements = []

    # 封面
    elements.extend(_gen_cover(date_str, executive_summary))
    elements.append(_gen_snapshot_box(raw_data, styles))
    elements.extend(_gen_executive_summary(executive_summary, styles))

    # 第一段：發生了什麼
    elements.extend(_gen_news_section(news_events, styles))
    elements.append(CondPageBreak(50*mm))
    elements.extend(_gen_index_section(md, technical_levels, index_analysis, styles))

    # 第二段：為什麼
    elements.append(CondPageBreak(40*mm))
    elements.extend(_gen_bonds_section(md.get('bonds', {}), yield_curve_analysis, styles))
    elements.append(CondPageBreak(40*mm))
    elements.extend(_gen_forex_section(md.get('forex', {}), styles))
    elements.append(CondPageBreak(40*mm))
    elements.extend(_gen_commodities_section(md.get('commodities', {}), styles))
    elements.append(CondPageBreak(40*mm))
    elements.extend(_gen_crypto_section(md.get('crypto', {}), styles))
    elements.extend(_gen_sentiment_section(sentiment_data, clock_data, historical_context, styles))

    # 第三段：錢怎麼流
    elements.append(CondPageBreak(50*mm))
    elements.extend(_gen_fund_flows_section(fund_flows, styles))
    elements.append(CondPageBreak(50*mm))
    elements.extend(_gen_hot_stocks_section(hot_stocks, stock_analysis, styles))

    # 第四段：往前看
    elements.append(CondPageBreak(40*mm))
    elements.extend(_gen_calendar_section(calendar_events, fred_data, styles))

    # 總結分析（名片前）
    if ai_summary:
        elements.append(CondPageBreak(60*mm))
        elements.extend(_gen_summary_section(ai_summary, styles))

    # 名片 + 聲明
    elements.extend(_gen_footer(date_str, styles))

    # 生成 PDF
    doc.build(elements, onFirstPage=_first_page, onLaterPages=_header_footer)
    print(f'✅ ReportLab PDF: {output_path} ({os.path.getsize(output_path):,} bytes)')
    return output_path
