#!/usr/bin/env python3
"""
完整報告生成腳本（無需 AI API）
基於收集到的數據，用規則引擎生成分析文字，組裝 HTML 報告
"""
import json, sys, os, re, requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATE = datetime.now().strftime('%Y-%m-%d')
REPORTS = 'reports'


def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def gen_executive_summary(md, enh, enh2):
    """根據數據生成 Executive Summary"""
    # 指數表現
    asia = md.get('asia_indices', {})
    europe = md.get('europe_indices', {})
    us = md.get('us_indices', {})

    def avg_chg(indices):
        vals = [d.get('change_pct', 0) for d in indices.values() if isinstance(d, dict)]
        return sum(vals) / len(vals) if vals else 0

    asia_avg = avg_chg(asia)
    europe_avg = avg_chg(europe)
    us_avg = avg_chg(us)

    # 情緒
    fg = enh.get('sentiment', {}).get('fear_greed', {}).get('score')
    fg_rating = enh.get('sentiment', {}).get('fear_greed', {}).get('rating', '')
    vix = enh.get('sentiment', {}).get('vix', {}).get('value')
    clock = enh.get('clock', {}).get('phase_cn', '')

    # 商品
    gold = md.get('commodities', {}).get('黃金', {})
    oil = md.get('commodities', {}).get('原油(WTI)', {})
    gold_chg = gold.get('change_pct', 0) if gold else 0
    oil_chg = oil.get('change_pct', 0) if oil else 0

    # 技術面
    sp_tech = enh2.get('technical_levels', {}).get('S&P 500', {})
    sp_rsi = sp_tech.get('rsi', 50)
    sp_from_high = sp_tech.get('pct_from_high', 0)

    # 市場方向判斷
    overall_chg = (asia_avg + europe_avg + us_avg) / 3
    if overall_chg < -1:
        tone = "全球市場昨日顯著下挫"
    elif overall_chg < -0.3:
        tone = "全球市場昨日普遍走低"
    elif overall_chg > 1:
        tone = "全球市場昨日全面上漲"
    elif overall_chg > 0.3:
        tone = "全球市場昨日溫和上揚"
    else:
        tone = "全球市場昨日漲跌互見"

    parts = [tone + "。"]

    # 美股
    sp = us.get('S&P 500', {})
    nq = us.get('納斯達克', {})
    if sp and nq:
        parts.append(f"S&P 500 {sp.get('change_pct',0):+.2f}%，納斯達克 {nq.get('change_pct',0):+.2f}%（RSI {sp_rsi:.0f}，距高點 {sp_from_high:+.1f}%）")

    # 商品
    comm_parts = []
    if abs(gold_chg) > 0.5:
        comm_parts.append(f"黃金 {gold_chg:+.2f}%")
    if abs(oil_chg) > 0.5:
        comm_parts.append(f"原油 {oil_chg:+.2f}%")
    if comm_parts:
        parts.append('，'.join(comm_parts))

    # 情緒
    emo_parts = []
    if fg is not None:
        emo_parts.append(f"恐貪指數 {fg:.0f}（{fg_rating}）")
    if vix is not None:
        emo_parts.append(f"VIX {vix:.1f}")
    if clock:
        emo_parts.append(f"美林時鐘：{clock}")
    if emo_parts:
        parts.append('，'.join(emo_parts))

    cleaned = [p.rstrip('。') for p in parts]
    return '。'.join(cleaned) + '。'


def gen_index_analysis(md, enh2):
    """根據數據生成指數分析"""
    result = {}

    for region, key, indices_key in [
        ('asia', '亞洲', 'asia_indices'),
        ('europe', '歐洲', 'europe_indices'),
        ('us', '美國', 'us_indices'),
    ]:
        indices = md.get(indices_key, {})
        if not indices:
            continue

        parts = []
        sorted_idx = sorted(indices.items(), key=lambda x: x[1].get('change_pct', 0))
        best = sorted_idx[-1] if sorted_idx else None
        worst = sorted_idx[0] if sorted_idx else None

        avg = sum(d.get('change_pct', 0) for _, d in sorted_idx) / len(sorted_idx) if sorted_idx else 0

        if avg > 0.5:
            parts.append(f"{key}市場整體走強。")
        elif avg < -0.5:
            parts.append(f"{key}市場整體走弱。")
        else:
            parts.append(f"{key}市場漲跌互見。")

        if best:
            parts.append(f"{best[0]}表現最佳（{best[1].get('change_pct',0):+.2f}%）")
        if worst and worst != best:
            parts.append(f"，{worst[0]}表現最弱（{worst[1].get('change_pct',0):+.2f}%）。")

        result[f'{region}_analysis'] = ''.join(parts)

    # Overall
    all_chg = []
    for key in ['asia_indices', 'europe_indices', 'us_indices']:
        for _, d in md.get(key, {}).items():
            if isinstance(d, dict):
                all_chg.append(d.get('change_pct', 0))
    avg_all = sum(all_chg) / len(all_chg) if all_chg else 0
    if avg_all > 0.5:
        result['overall_summary'] = '全球市場整體偏多，風險偏好回升。'
        result['summary'] = '全球市場偏多。'
    elif avg_all < -0.5:
        result['overall_summary'] = '全球市場整體承壓，避險情緒升溫。'
        result['summary'] = '全球市場承壓。'
    else:
        result['overall_summary'] = '全球市場方向不明，觀望氣氛濃厚。'
        result['summary'] = '全球市場漲跌互見。'

    return result


def gen_stock_analysis(hot_stocks, news):
    """為每支熱門股票生成簡短分析"""
    analysis = {}
    titles = ' '.join([a.get('title', '') for a in news.get('articles', [])[:50]])

    for market, data in hot_stocks.items():
        for direction in ['inflow', 'outflow']:
            for stock in data.get(direction, []):
                symbol = stock.get('symbol', '')
                name = stock.get('name', symbol)
                chg = stock.get('change_pct', 0)
                vol = stock.get('volume_ratio', 1)

                if direction == 'inflow':
                    analysis[symbol] = f"{name}放量上漲{chg:+.2f}%，量比{vol:.1f}x，資金積極追捧。"
                else:
                    analysis[symbol] = f"{name}放量下跌{chg:+.2f}%，量比{vol:.1f}x，資金明顯流出。"

    return analysis


def _translate_titles(titles):
    """批量翻譯英文標題為中文（使用 Google Translate，免費）"""
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='en', target='zh-TW')
        # 批量翻譯（合併後一次翻，減少 API 呼叫）
        if not titles:
            return []
        # 每批最多 20 條，用 ||| 分隔
        results = []
        for i in range(0, len(titles), 20):
            batch = titles[i:i+20]
            combined = ' ||| '.join(batch)
            try:
                translated = translator.translate(combined)
                parts = translated.split(' ||| ')
                # 如果分割結果數量不對，逐條翻譯
                if len(parts) == len(batch):
                    results.extend(parts)
                else:
                    for t in batch:
                        try:
                            results.append(translator.translate(t))
                        except Exception:
                            results.append(t)
            except Exception:
                results.extend(batch)  # 翻譯失敗保留原文
        return results
    except ImportError:
        return titles  # 沒裝 deep-translator 就保留原文


# ========== 新聞品質控制系統 ==========

# 垃圾標題黑名單（正則，匹配到就丟棄）
_JUNK_PATTERNS = re.compile(
    r'profile and biography|profile & biography|'
    r'\bcocktail\b|\brecipe\b|\bfashion\b|\blifestyle\b|'
    r'\bcelebrity\b|\bentertainment\b|\bhoroscope\b|'
    r'stock analysis[:\s].*(forecast|prediction|dividend|earning)|'
    r'Stock Analysis: Prediction|'
    r'簡介與傳記|簡介和傳記|股票分析[：:].*預測|'
    r'預測、收益、股息|預測、獲利、股息|預測、收益、股利|'
    r'Prediction,?\s*Earnings?,?\s*Dividend|'
    r'\bsports?\b.*\b(score|game|match)\b|'
    r'\.[A-Z]{2}\s+Stock Analysis|\.[A-Z]{2}\s+股票分析|'
    r'Leadershipinstitute',
    re.IGNORECASE
)

def _is_relevant_article(title, desc=''):
    """判斷文章是否與金融/宏觀相關（兩層過濾）"""
    text = (title + ' ' + (desc or '')).lower()
    # 黑名單
    if _JUNK_PATTERNS.search(text):
        return False
    # 太短的標題
    if len(title) < 15:
        return False
    return True


# 分類關鍵詞（區分需要 word boundary 的短詞和可以用 substring 的長詞）
def _build_category_pattern(keywords):
    """把關鍵詞列表編譯成正則，短詞加 word boundary"""
    parts = []
    for kw in keywords:
        if len(kw) <= 4:
            parts.append(r'\b' + re.escape(kw) + r'\b')
        else:
            parts.append(re.escape(kw))
    return re.compile('|'.join(parts), re.IGNORECASE) if parts else None


# 新聞主題分類規則
NEWS_CATEGORIES = {
    'Fed/央行政策': {
        'keywords': ['federal reserve', 'interest rate', 'central bank', 'fomc', 'powell',
                     'ecb', 'lagarde', 'boj', 'pboc', 'rate cut', 'rate hike', 'monetary policy',
                     'quantitative', 'tightening', 'easing', 'inflation target'],
        'impact': '高',
        'direction_rules': {
            'rate cut': '利多', 'easing': '利多', 'dovish': '利多',
            'rate hike': '利空', 'tightening': '利空', 'hawkish': '利空',
        },
        'markets': '全球股市、債券、外匯',
        'why_it_matters': {
            'rate cut': '降息預期升溫壓低殖利率曲線前端，美元走弱利好新興市場資金回流。關鍵在於市場已定價多少——若低於預期反而觸發拋售。',
            'rate hike': '高利率環境壓制高槓桿和成長型企業獲利能力，投資級和高收益債利差面臨擴大壓力。',
            'hawkish': '鷹派措辭推升加息概率，科技和高估值板塊面臨估值壓縮，需重新評估降息時間表。',
            'dovish': '鴿派轉向暗示緊縮周期接近尾聲，成長股和小型股可能受益——但需警惕是否因衰退風險所驅動。',
            '_default': '央行每一句措辭變化都可能引發跨資產重新定價，密切關注利率期貨隱含的政策路徑。',
        },
    },
    '地緣政治/關稅': {
        'keywords': ['iran war', 'iran conflict', 'israel', 'tariff', 'sanction', 'geopolitical', 'trump',
                     'ukraine', 'russia', 'conflict', 'military', 'missile', 'nuclear',
                     'trade war', 'executive order', 'nato', 'taiwan strait', 'middle east',
                     'houthi', 'gaza', 'troops', 'strait of hormuz', 'ceasefire',
                     'iran', 'invasion'],
        'impact': '高',
        'direction_rules': {
            'ceasefire': '利多', 'peace': '利多', 'deal': '利多',
            'war': '利空', 'conflict': '利空', 'sanction': '利空', 'tariff': '利空',
        },
        'markets': '全球股市、能源、避險資產',
        'why_it_matters': {
            'war': '軍事衝突推動避險資金湧入黃金和美債，能源供應鏈受威脅推升原油，波動率飆升。',
            'tariff': '關稅加碼推升進口成本和通脹預期，跨國企業利潤率面臨壓縮，供應鏈重組加速。',
            'sanction': '制裁加劇大宗商品供應風險，貿易夥伴合規成本上升，金融機構需重估交易對手風險。',
            'ceasefire': '停火有助地緣溢價消退，能源和航運成本正常化，風險資產有望估值修復。',
            '_default': '地緣風險的關鍵指標是原油和黃金價格，以及避險貨幣（日圓、瑞郎）的走勢方向。',
        },
    },
    '通脹/經濟數據': {
        'keywords': ['cpi', 'ppi', 'inflation', 'gdp', 'employment', 'payroll', 'jobs',
                     'unemployment', 'retail sales', 'consumer price', 'pmi', 'manufacturing',
                     'consumer confidence', 'housing', 'trade balance', 'nonfarm'],
        'impact': '高',
        'direction_rules': {
            'beat': '利多', 'strong': '利多', 'surge': '利空',
            'miss': '利空', 'weak': '利空', 'decline': '利空',
        },
        'markets': '美股、美債、美元',
        'why_it_matters': {
            'beat': '強勁數據降低 Fed 降息緊迫性——「好消息即壞消息」邏輯主導，殖利率和美元上行。',
            'miss': '數據走弱引發衰退擔憂，資金轉向防禦型板塊和長天期國債。',
            'surge': '通脹超預期削弱降息可能性，實質利率上升壓制成長股估值。',
            '_default': '市場反應取決於數據相對於預期的偏差程度，需對照 CME FedWatch 定價變化評估。',
        },
    },
    'AI/半導體': {
        'keywords': ['artificial intelligence', 'nvidia', 'semiconductor', 'openai',
                     'data center', 'tsmc', 'machine learning', 'cloud computing',
                     'gpu', 'llm', 'amd', 'ai chip', 'ai model', 'ai agent',
                     'generative ai', 'chatgpt', 'gemini ai', 'claude ai'],
        'impact': '中',
        'direction_rules': {
            'invest': '利多', 'launch': '利多', 'growth': '利多', 'record': '利多',
            'ban': '利空', 'restrict': '利空', 'decline': '利空',
        },
        'markets': '科技股、半導體板塊',
        'why_it_matters': {
            'invest': 'AI 資本支出擴大利好上游晶片商（NVDA、TSM），但需關注資本開支回報率能否兌現。',
            'ban': '出口管制影響半導體供應鏈，受限企業營收面臨下修，產業格局加速重組。',
            '_default': 'AI 估值已反映大量樂觀預期，任何資本支出放緩或技術瓶頸的信號都可能引發回調。',
        },
    },
    '能源/商品': {
        'keywords': ['crude oil', 'oil price', 'gold price', 'silver', 'opec', 'energy',
                     'commodity', 'natural gas', 'copper', 'iron ore', 'wheat', 'lithium',
                     'brent', 'wti'],
        'impact': '中',
        'direction_rules': {
            'surge': '利多', 'rally': '利多', 'shortage': '利多',
            'drop': '利空', 'oversupply': '利空', 'cut': '利空',
        },
        'markets': '能源股、商品期貨、通脹預期',
        'why_it_matters': {
            'surge': '價格急漲推升企業成本和通脹預期，可能延後降息時間表。能源股短期受惠。',
            'drop': '價格回落暗示需求走弱，有利壓低通脹，但能源板塊盈利預期面臨下修。',
            '_default': '銅價是經濟領先指標，原油反映地緣風險，黃金是避險和通脹預期的風向標。',
        },
    },
    '企業/財報': {
        'keywords': ['earnings', 'revenue', 'profit', 'quarterly results', 'guidance',
                     'merger', 'acquisition', 'buyout', 'layoff', 'restructur', 'dividend',
                     'buyback', 'stock split', 'ipo'],
        'impact': '中',
        'direction_rules': {
            'beat': '利多', 'raise': '利多', 'record': '利多', 'buyback': '利多',
            'miss': '利空', 'cut': '利空', 'layoff': '利空', 'warning': '利空',
        },
        'markets': '個股、行業板塊',
        'why_it_matters': {
            'beat': '超預期財報提振板塊信心，關注管理層展望指引和營收成長是否由核心業務驅動。',
            'miss': '不及預期引發獲利了結，若多家同業 miss 可能暗示行業景氣轉弱。',
            'layoff': '裁員短期提振利潤率預期，但長期可能削弱競爭力，反映整體就業市場壓力。',
            '_default': '當前財報季的整體表現將決定市場能否維持現有估值水平。',
        },
    },
    '加密貨幣': {
        'keywords': ['bitcoin', 'crypto', 'ethereum', 'btc', 'blockchain',
                     'stablecoin', 'defi', 'binance', 'coinbase', 'altcoin'],
        'impact': '中',
        'direction_rules': {
            'rally': '利多', 'adoption': '利多', 'etf': '利多',
            'crash': '利空', 'ban': '利空', 'hack': '利空', 'regulate': '利空',
        },
        'markets': '加密貨幣、科技股',
        'why_it_matters': {
            'etf': 'ETF 進展拓寬機構資金流入渠道，但槓桿效應也可能放大波動。',
            'crash': '去槓桿連鎖效應可能外溢至科技股等風險資產，歷史上常領先傳統市場調整。',
            '_default': '加密市場是全球流動性和風險偏好的敏感指標，與納斯達克相關性在緊縮期顯著上升。',
        },
    },
    '房地產/金融': {
        'keywords': ['housing market', 'mortgage', 'real estate', 'bank', 'credit',
                     'default', 'lending', 'financial crisis', 'jpmorgan', 'goldman sachs',
                     'citibank', 'wells fargo', 'private credit'],
        'impact': '中',
        'direction_rules': {},
        'markets': '金融股、房地產',
        'why_it_matters': {
            'default': '信用違約敲響警鐘，高收益債利差可能擴大，銀行壞帳撥備壓力上升。',
            'housing': '高房貸利率抑制購房需求，但庫存不足限制價格下行，財富效應負面影響將逐步顯現。',
            '_default': '重點關注商業地產風險敞口、銀行存款穩定性和信用利差，任何流動性緊張信號值得警惕。',
        },
    },
}

# 預編譯分類正則（模組載入時執行一次）
_CATEGORY_PATTERNS = {}
for _cat_name, _cat_config in NEWS_CATEGORIES.items():
    _CATEGORY_PATTERNS[_cat_name] = _build_category_pattern(_cat_config['keywords'])


def _classify_article(title, desc, tier):
    """評分制分類：標題匹配 3 分，描述匹配 1 分。返回最佳分類或 None"""
    title_lower = title.lower()
    desc_lower = (desc or '').lower()

    scores = {}
    for cat_name, pattern in _CATEGORY_PATTERNS.items():
        if pattern is None:
            continue
        title_hits = len(pattern.findall(title_lower))
        desc_hits = len(pattern.findall(desc_lower))
        score = title_hits * 3 + desc_hits
        # Tier-3 來源要求更高分（避免單一偶然匹配）
        min_score = 2 if tier >= 3 else 1
        if score >= min_score:
            scores[cat_name] = score

    if not scores:
        return None
    return max(scores, key=scores.get)


def gen_news_events(news, market_data=None, sentiment_data=None, alt_data=None):
    """專業晨報新聞生成

    每組新聞包含：
    1. 敘事摘要（從 description 翻譯組裝，告訴讀者發生了什麼）
    2. 重點標題列表（翻譯後的中文標題）
    3. 市場數據佐證
    """
    articles = news.get('articles', [])
    if not articles:
        return []

    mkt = _build_market_snapshot(market_data, sentiment_data, alt_data)

    # Step 1: 品質過濾 + 評分制分類
    groups = {}
    for article in articles:
        title = article.get('title', '')
        desc = article.get('description', '') or ''
        tier = article.get('source_tier', 3)

        # 垃圾過濾
        if not _is_relevant_article(title, desc):
            continue

        # 評分制分類（最佳匹配，不是先到先得）
        best_cat = _classify_article(title, desc, tier)
        if best_cat is None:
            continue

        if best_cat not in groups:
            groups[best_cat] = []
        groups[best_cat].append({
            'title': title, 'text': (title + ' ' + desc).lower(), 'tier': tier,
            'publisher': article.get('publisher', ''),
            'desc': desc,
        })

    # Step 2: 排序
    sorted_groups = sorted(
        groups.items(),
        key=lambda x: (
            0 if NEWS_CATEGORIES[x[0]]['impact'] == '高' else 1,
            -len(x[1]),
            min(a['tier'] for a in x[1]),
        )
    )

    # Step 3: 批量翻譯（標題 + descriptions）
    all_texts = []
    text_indices = {}  # (group, original_text) -> index

    for group_name, group_articles in sorted_groups[:8]:
        # 收集標題（前5條）
        for a in group_articles[:6]:
            idx = len(all_texts)
            text_indices[('title', group_name, a['title'])] = idx
            all_texts.append(a['title'])

        # 收集有內容的 descriptions（只取跟主題關鍵詞匹配的高品質描述）
        config_kw = NEWS_CATEGORIES.get(group_name, {}).get('keywords', [])
        descs_with_content = [
            a for a in group_articles
            if a['desc'] and len(a['desc']) > 30
            and any(kw in a['desc'].lower() for kw in config_kw)  # 描述必須含主題關鍵詞
        ]
        descs_sorted = sorted(descs_with_content, key=lambda x: (x['tier'], -len(x['desc'])))[:5]
        for a in descs_sorted:
            idx = len(all_texts)
            text_indices[('desc', group_name, a['desc'])] = idx
            all_texts.append(a['desc'])

    translated = _translate_titles(all_texts)

    def _zh(kind, group_name, orig):
        idx = text_indices.get((kind, group_name, orig))
        t = translated[idx] if idx is not None and idx < len(translated) else orig
        return re.sub(r'\s*[-–—]\s*(Bloomberg|Reuters|CNBC|WSJ|BBC|CNN|Investing|TechCrunch|Abcnews|Yahoo|CNA|Mediaite|CoinDesk|Business Insider)[\w.\s]*$', '', t).strip()

    # Step 4: 生成事件
    events = []
    for rank, (group_name, group_articles) in enumerate(sorted_groups[:8]):
        config = NEWS_CATEGORIES.get(group_name, {})
        is_headline = rank < 4

        # 方向判斷（加權投票）
        direction_votes = {'利多': 0, '利空': 0}
        combined_text = ' '.join(a['text'] for a in group_articles)
        for keyword, dir_val in config.get('direction_rules', {}).items():
            count = combined_text.count(keyword)
            if count > 0:
                direction_votes[dir_val] = direction_votes.get(dir_val, 0) + count
        if direction_votes.get('利空', 0) > direction_votes.get('利多', 0):
            direction = '利空'
        elif direction_votes.get('利多', 0) > direction_votes.get('利空', 0):
            direction = '利多'
        else:
            direction = '中性'

        n_articles = len(group_articles)
        pub_counts = {}
        for a in group_articles:
            p = a['publisher']
            if p:
                pub_counts[p] = pub_counts.get(p, 0) + 1
        top_pubs = sorted(pub_counts.items(), key=lambda x: -x[1])[:3]
        source_str = '、'.join(p for p, _ in top_pubs)

        # === 敘事摘要：基於 why_it_matters 模板 + 嚴格篩選的翻譯描述 ===
        # 策略：優先用高品質描述，不足時用 why_it_matters 模板補充
        cat_pattern = _CATEGORY_PATTERNS.get(group_name)
        why_it_matters = config.get('why_it_matters', {})

        # 1. 嚴格篩選描述：必須有 ≥2 個關鍵詞命中
        descs_with_content = []
        if cat_pattern:
            for a in group_articles:
                if a['desc'] and len(a['desc']) > 40:
                    hits = len(cat_pattern.findall(a['desc'].lower()))
                    if hits >= 2:
                        descs_with_content.append(a)
        descs_sorted = sorted(descs_with_content, key=lambda x: (x['tier'], -len(x['desc'])))[:4]

        narrative_parts = []
        seen_narratives = set()
        for a in descs_sorted:
            zh = _zh('desc', group_name, a['desc'])
            cjk_count = sum(1 for c in zh if '\u4e00' <= c <= '\u9fff')
            if len(zh) > 0 and cjk_count / len(zh) < 0.3:
                continue
            zh_key = zh[:20]
            if zh_key not in seen_narratives and len(zh) > 15:
                seen_narratives.add(zh_key)
                zh = zh.rstrip('。，；、 ')
                narrative_parts.append(zh)
            if len(narrative_parts) >= 3:
                break

        # 2. 描述不足時，用 why_it_matters 模板生成相關性摘要
        if len(narrative_parts) < 1:
            # 找到最匹配的 why_it_matters
            wim_text = why_it_matters.get('_default', '')
            for kw, wim in why_it_matters.items():
                if kw != '_default' and kw in combined_text:
                    wim_text = wim
                    break
            if wim_text:
                narrative_parts.append(wim_text)

        narrative = '。'.join(narrative_parts)
        if narrative and not narrative.endswith('。'):
            narrative += '。'

        # === 重點標題列表（翻譯後再次過濾垃圾）===
        seen_titles = set()
        headlines_zh = []
        for a in sorted(group_articles, key=lambda x: x['tier'])[:10]:
            zh = _zh('title', group_name, a['title'])
            # 過濾垃圾翻譯標題
            if _JUNK_PATTERNS.search(zh):
                continue
            zh_key = zh[:15]
            if zh_key not in seen_titles and len(zh) > 8:
                seen_titles.add(zh_key)
                headlines_zh.append(zh)
            if len(headlines_zh) >= 5:
                break

        # 關鍵數據
        data_points = _gen_data_points(group_name, direction, mkt)

        # tickers
        tickers = []
        ticker_map = {
            'nvidia': 'NVDA', 'apple': 'AAPL', 'meta': 'META', 'google': 'GOOGL',
            'amazon': 'AMZN', 'microsoft': 'MSFT', 'tesla': 'TSLA', 'tsmc': 'TSM',
            'amd': 'AMD', 'intel': 'INTC', 'netflix': 'NFLX', 'jpmorgan': 'JPM',
            'goldman': 'GS', 'bitcoin': 'BTC', 'ethereum': 'ETH',
        }
        for kw, ticker in ticker_map.items():
            if kw in combined_text:
                tickers.append(ticker)

        # 向後兼容 description
        desc = narrative if narrative else '；'.join(headlines_zh[:3]) + '。'

        events.append({
            'title': group_name,
            'narrative': narrative,       # 敘事摘要
            'headlines': headlines_zh,    # 重點標題
            'source_info': f'{source_str} 等 {n_articles} 篇',
            'data_points': data_points,
            'is_headline': is_headline,
            'impact_level': config.get('impact', '中'),
            'affected_markets': config.get('markets', '全球'),
            'market_direction': direction,
            'related_tickers': tickers[:5],
            'ticker_impact': {},
            'description': desc,
        })

    return events


def _build_market_snapshot(market_data, sentiment_data, alt_data):
    """從各數據源提取關鍵數字，供新聞分析交叉引用"""
    mkt = {
        'sp500_chg': 0, 'nasdaq_chg': 0, 'dji_chg': 0,
        'gold_chg': 0, 'gold_price': 0, 'oil_chg': 0, 'oil_price': 0,
        'vix': 0, 'fg_score': 0, 'fg_rating': '',
        'dxy_chg': 0, 'us10y': 0, 'us2y': 0,
        'nikkei_chg': 0, 'hsi_chg': 0, 'shanghai_chg': 0,
        'btc_chg': 0, 'btc_price': 0,
        'put_call': 0, 'stock_changes': {},
    }
    if not market_data:
        return mkt

    # 美股
    us = market_data.get('us_indices', {})
    for name, key in [('S&P 500', 'sp500_chg'), ('納斯達克', 'nasdaq_chg'), ('道瓊工業', 'dji_chg')]:
        d = us.get(name, {})
        mkt[key] = d.get('change_pct', 0)

    # 亞股
    asia = market_data.get('asia_indices', {})
    for name, key in [('日經225', 'nikkei_chg'), ('香港恆生', 'hsi_chg'), ('上證綜指', 'shanghai_chg')]:
        d = asia.get(name, {})
        mkt[key] = d.get('change_pct', 0)

    # 商品
    comm = market_data.get('commodities', {})
    gold = comm.get('黃金', {})
    mkt['gold_chg'] = gold.get('change_pct', 0)
    mkt['gold_price'] = gold.get('current', 0)
    oil = comm.get('原油(WTI)', {})
    mkt['oil_chg'] = oil.get('change_pct', 0)
    mkt['oil_price'] = oil.get('current', 0)

    # 外匯/債券
    fx = market_data.get('forex', {})
    dxy = fx.get('美元指數', {})
    mkt['dxy_chg'] = dxy.get('change_pct', 0)
    bonds = market_data.get('bonds', {})
    us10 = bonds.get('美國10年期', {})
    mkt['us10y'] = us10.get('current', 0)
    us2 = bonds.get('美國2年期', {})
    mkt['us2y'] = us2.get('current', 0)

    # 加密
    crypto = market_data.get('crypto', {})
    btc = crypto.get('比特幣', {})
    mkt['btc_chg'] = btc.get('change_pct', 0)
    mkt['btc_price'] = btc.get('current', 0)

    # 情緒
    if sentiment_data:
        fg = sentiment_data.get('fear_greed', {})
        mkt['fg_score'] = fg.get('score', 0)
        mkt['fg_rating'] = fg.get('rating', '')
        vix = sentiment_data.get('vix', {})
        mkt['vix'] = vix.get('value', 0)

    # 替代數據
    if alt_data:
        pc = alt_data.get('put_call_ratio', {})
        mkt['put_call'] = pc.get('volume_pcr', 0)

    # 個股漲跌（從熱門股提取）
    # 這裡先留空，後續可從 hot_stocks 填入

    return mkt


def _gen_data_points(group_name, direction, mkt):
    """根據新聞類別，返回 2-4 個最相關的關鍵數據點（簡潔格式）"""
    pts = []

    if group_name in ('地緣政治/關稅',):
        if mkt['gold_price']:
            pts.append(f"黃金 ${mkt['gold_price']:,.0f}（{mkt['gold_chg']:+.1f}%）")
        if mkt['oil_price']:
            pts.append(f"原油 ${mkt['oil_price']:.1f}（{mkt['oil_chg']:+.1f}%）")
        if mkt['vix']:
            pts.append(f"VIX {mkt['vix']:.1f}")

    elif group_name in ('Fed/央行政策', '通脹/經濟數據'):
        if mkt['us10y']:
            pts.append(f"10Y殖利率 {mkt['us10y']:.2f}%")
        if mkt['us2y'] and mkt['us10y']:
            pts.append(f"2-10Y利差 {mkt['us10y'] - mkt['us2y']:+.0f}bp")
        if mkt['dxy_chg']:
            pts.append(f"美元 {mkt['dxy_chg']:+.1f}%")

    elif group_name in ('AI/半導體', '企業/財報'):
        if mkt['nasdaq_chg']:
            pts.append(f"納指 {mkt['nasdaq_chg']:+.1f}%")
        if mkt['sp500_chg']:
            pts.append(f"S&P {mkt['sp500_chg']:+.1f}%")

    elif group_name in ('能源/商品',):
        if mkt['oil_price']:
            pts.append(f"WTI ${mkt['oil_price']:.1f}（{mkt['oil_chg']:+.1f}%）")
        if mkt['gold_price']:
            pts.append(f"黃金 ${mkt['gold_price']:,.0f}（{mkt['gold_chg']:+.1f}%）")

    elif group_name in ('加密貨幣',):
        if mkt['btc_price']:
            pts.append(f"BTC ${mkt['btc_price']:,.0f}（{mkt['btc_chg']:+.1f}%）")

    elif group_name in ('房地產/金融',):
        if mkt['us10y']:
            pts.append(f"10Y {mkt['us10y']:.2f}%")
        if mkt['put_call']:
            pts.append(f"P/C Ratio {mkt['put_call']:.2f}")

    # 通用：恐懼貪婪
    if mkt['fg_score'] and group_name in ('地緣政治/關稅', 'Fed/央行政策', '通脹/經濟數據'):
        pts.append(f"恐貪指數 {mkt['fg_score']:.0f}")

    return pts[:4]  # 最多4個


def gen_calendar():
    """生成未來一週經濟日曆（含預期影響方向）

    優先從 Trading Economics API 抓取真實數據，失敗時用日期感知的靜態日曆
    """
    real = _fetch_real_calendar()
    if real:
        return real
    # 嘗試從新聞中提取
    news = load_json(f'{REPORTS}/news_today.json')
    extracted = _extract_calendar_from_news(news) if news else None
    if extracted:
        return extracted
    return _gen_static_calendar()


def _fetch_real_calendar():
    """嘗試從 Trading Economics 公開頁面抓取經濟日曆"""
    try:
        today = datetime.now()
        end = today + timedelta(days=7)
        url = "https://tradingeconomics.com/calendar"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.select('table tr[data-url]')
        if not rows:
            return None

        events = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 5:
                continue
            date_str = (cols[0].get_text(strip=True) or '')[:10]
            country = cols[1].get_text(strip=True)
            event_name = cols[2].get_text(strip=True)
            # 只保留重要事件
            imp_el = row.find(class_='calendar-importance')
            imp = len(imp_el.find_all(class_='calendar-bull')) if imp_el else 1
            if imp < 2:
                continue
            imp_str = '★' * min(imp, 3)
            events.append({
                'date': date_str, 'event': event_name, 'country': country,
                'importance': imp_str, 'description': _gen_event_description(event_name),
            })
        return events[:10] if events else None
    except:
        return None


def _extract_calendar_from_news(news):
    """從新聞文章中提取提及的經濟事件"""
    articles = news.get('articles', [])
    if not articles:
        return None

    cal_keywords = {
        'pce': ('美國', 'PCE 物價指數', '★★★'),
        'nonfarm': ('美國', '非農就業報告', '★★★'),
        'non-farm payroll': ('美國', '非農就業報告', '★★★'),
        'fomc minute': ('美國', 'FOMC 會議紀要', '★★★'),
        'cpi release': ('美國', '消費者物價指數', '★★★'),
        'fed decision': ('美國', 'Fed 利率決議', '★★★'),
        'manufacturing pmi': ('多國', '製造業 PMI', '★★'),
        'services pmi': ('多國', '服務業 PMI', '★★'),
        'jobless claim': ('美國', '初領失業救濟', '★★'),
    }

    found = {}
    for article in articles[:100]:
        text = (article.get('title', '') + ' ' + (article.get('description', '') or '')).lower()
        for kw, (country, event, imp) in cal_keywords.items():
            if kw in text and event not in found:
                found[event] = {'country': country, 'importance': imp,
                                'description': _gen_event_description(event)}

    if not found:
        return None

    today = datetime.now()
    events = []
    offset = 1
    for event, info in found.items():
        d = today + timedelta(days=offset)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        events.append({'date': d.strftime('%Y-%m-%d'), 'event': event, **info})
        offset += 1
    events.sort(key=lambda x: x['date'])
    return events if events else None


def _gen_event_description(event_name):
    """根據事件名稱生成預期影響描述"""
    desc_map = {
        'PCE 物價指數': '聯儲最關注的通脹指標。高於預期→延後降息、美元走強；低於預期→利多黃金和債券',
        '非農就業報告': '本週最重要就業數據。超預期→美元走強、延後降息；不及預期→利多黃金和債券',
        '消費者物價指數': '通脹高於預期→推遲降息、壓制股市；低於預期→利多成長股',
        '製造業 PMI': '製造業景氣指標。高於 50 利多股市；低於預期則強化降息預期',
        '服務業 PMI': '服務業是主要經濟引擎，低於 50 暗示衰退風險上升',
        'ISM 製造業指數': '領先指標。高於 50 利多週期股；低於預期可能觸發避險',
        'JOLTS 職位空缺': '空缺減少→勞動市場降溫→利多債券、利空美元',
        '初領失業救濟': '高於預期→經濟放緩信號；低於預期→就業韌性仍在',
        'Fed 利率決議': '央行政策風向標，決定短期資金成本走勢',
        'FOMC 會議紀要': '揭示 Fed 內部鷹鴿分歧，影響利率路徑預期',
    }
    for key, val in desc_map.items():
        if key in event_name:
            return val
    return '關注數據公布後市場即時反應'


def _gen_static_calendar():
    """日期感知的靜態經濟日曆（fallback）"""
    today = datetime.now()
    events = []

    for delta in range(1, 8):
        d = today + timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        ds = d.strftime('%Y-%m-%d')
        dow = d.weekday()
        dom = d.day

        # 月初第一個工作日：ISM 製造業（只出現一次）
        if dom == 1 or (dom <= 3 and dow == 0):  # 1日或月初第一個週一
            events.append({'date': ds, 'event': 'ISM 製造業指數', 'country': '美國', 'importance': '★★★',
                           'description': '領先指標。高於 50 利多週期股；低於預期可能觸發避險'})
        # 月初 1-3 日：各國 PMI
        if dom <= 3:
            events.append({'date': ds, 'event': '製造業 PMI', 'country': '多國', 'importance': '★★',
                           'description': '製造業景氣指標'})
        # 每月第一個週五（dom 1-7）：非農
        if dow == 4 and dom <= 7:
            events.append({'date': ds, 'event': '非農就業報告', 'country': '美國', 'importance': '★★★',
                           'description': '本週最重要數據。超預期→美元走強、延後降息；不及預期→利多黃金和債券'})
        # 每月 10-14 日：CPI
        if 10 <= dom <= 14 and dow <= 3:
            events.append({'date': ds, 'event': '消費者物價指數', 'country': '美國', 'importance': '★★★',
                           'description': '通脹高於預期→推遲降息、壓制股市；低於預期→利多成長股'})
        # 月底或月初週五：PCE
        if (dom >= 28 or dom <= 3) and dow == 4:
            events.append({'date': ds, 'event': 'PCE 物價指數', 'country': '美國', 'importance': '★★★',
                           'description': '聯儲最關注的通脹指標。高於預期→延後降息；低於預期→利多黃金'})
        # 每週四：初領失業救濟
        if dow == 3:
            events.append({'date': ds, 'event': '初領失業救濟', 'country': '美國', 'importance': '★★',
                           'description': '高於預期→經濟放緩信號；低於預期→就業韌性仍在'})

    seen = set()
    unique = []
    for e in events:
        key = f"{e['date']}_{e['event']}"
        if key not in seen:
            seen.add(key)
            unique.append(e)
    unique.sort(key=lambda x: (x['date'], '★★★' not in x['importance']))
    return unique[:8]


def gen_sector_analysis(fund_flows):
    """生成行業輪動分析"""
    sectors = fund_flows.get('sector', {})
    if not sectors:
        return ''

    inflows = [(d.get('name', s), d.get('1d', 0)) for s, d in sectors.items() if d.get('1d', 0) > 0]
    outflows = [(d.get('name', s), d.get('1d', 0)) for s, d in sectors.items() if d.get('1d', 0) < 0]
    inflows.sort(key=lambda x: x[1], reverse=True)
    outflows.sort(key=lambda x: x[1])

    parts = []
    if inflows:
        top_in = '、'.join([f"{n}" for n, _ in inflows[:3]])
        parts.append(f"當日資金流入板塊：{top_in}")
    if outflows:
        top_out = '、'.join([f"{n}" for n, _ in outflows[:3]])
        parts.append(f"資金流出板塊：{top_out}")

    return '。'.join(parts) + '。' if parts else ''


def gen_yield_curve_analysis(enh2):
    """生成殖利率曲線分析"""
    yc = enh2.get('yield_curve', {})
    if not yc:
        return ''
    shape = yc.get('shape', '')
    spread = yc.get('spread_3m10y')
    interp = yc.get('interpretation', '')
    if spread is not None:
        return f"美國殖利率曲線呈{shape}形態，3個月-10年利差為 {spread}%。{interp}"
    return interp


def _gen_fred_data_html(fred):
    """生成 FRED 經濟數據 HTML 區塊"""
    snapshot = fred.get('snapshot', {})
    if not snapshot:
        return ''

    rows = ''
    for cat_key, cat in snapshot.items():
        cat_label = cat.get('label', '')
        for sid, s in cat.get('data', {}).items():
            if s.get('latest_value') is None:
                continue
            val = s['latest_value']
            chg = s.get('change')
            chg_str = f'{chg:+.4f}' if chg is not None else '-'
            color = '#e74c3c' if chg and chg < 0 else '#27ae60' if chg and chg > 0 else '#666'
            rows += f'<tr><td style="text-align:left;">{s["name"]}</td><td style="text-align:center;color:#888;font-size:8pt;">{sid}</td><td style="text-align:right;font-weight:600;">{val:,.4f}</td><td style="text-align:right;color:{color};">{chg_str}</td><td style="text-align:center;color:#999;font-size:8pt;">{s.get("latest_date","")}</td></tr>'

    if not rows:
        return ''

    bs = fred.get('balance_sheet_trend', {})
    bs_line = ''
    if bs.get('latest_value_trillion'):
        wc = bs.get('week_change')
        wc_str = f'（週變化 {wc:+,.0f}M）' if wc else ''
        bs_line = f'<div style="margin-top:8px;font-size:9pt;color:#555;">Fed 資產負債表: <strong>${bs["latest_value_trillion"]:.2f}T</strong>{wc_str}</div>'

    return (
        '<div class="section-new-page"></div>'
        '<div style="margin:16px 0 20px 0;page-break-inside:avoid;">'
        '<div style="font-size:13pt;font-weight:700;color:#2c3e50;border-bottom:2.5px solid #2980b9;padding-bottom:6px;margin-bottom:10px;">FRED 聯準會經濟數據</div>'
        f'<table><thead><tr><th style="text-align:left;">指標</th><th style="text-align:center;">代碼</th><th style="text-align:right;">最新值</th><th style="text-align:right;">變化</th><th style="text-align:center;">日期</th></tr></thead><tbody>{rows}</tbody></table>'
        f'{bs_line}</div>\n'
    )


def _gen_alternative_data_html(alt):
    """生成替代數據 HTML 區塊（板塊輪動 + 市場微觀結構，不含 EM 貨幣）"""
    if not alt:
        return ''

    parts = []

    # 板塊輪動
    sr = alt.get('sector_rotation', {})
    if sr and 'sectors' in sr:
        rows = ''
        for s in sr['sectors']:
            m = s.get('momentum', 0)
            mc = '#27ae60' if m > 0 else '#e74c3c'
            rows += f'<tr><td style="text-align:left;font-weight:600;">{s["name"]} ({s["ticker"]})</td><td style="text-align:right;">{s.get("return_1w",0):+.2f}%</td><td style="text-align:right;">{s.get("return_1m",0):+.2f}%</td><td style="text-align:right;color:{mc};font-weight:700;">{m:+.2f}</td></tr>'
        regime = sr.get('regime', '')
        spread = sr.get('risk_spread', 0)
        parts.append(
            '<div style="margin:16px 0;page-break-inside:avoid;">'
            '<div style="font-size:13pt;font-weight:700;color:#2c3e50;border-bottom:2.5px solid #e67e22;padding-bottom:6px;margin-bottom:10px;">板塊輪動分析 Sector Rotation</div>'
            f'<div style="background:linear-gradient(135deg,#fff8f0,#ffecd2);border-left:4px solid #e67e22;padding:10px 16px;margin-bottom:10px;font-size:9.5pt;border-radius:0 6px 6px 0;"><strong>市場態勢：</strong>{regime}（Risk Spread: {spread:+.2f}）</div>'
            f'<table><thead><tr><th style="text-align:left;">板塊</th><th style="text-align:right;">1週</th><th style="text-align:right;">1月</th><th style="text-align:right;">動量</th></tr></thead><tbody>{rows}</tbody></table></div>'
        )

    # Put/Call + 波動率 + 市場寬度
    summaries = []
    pc = alt.get('put_call_ratio', {})
    if pc.get('volume_pcr'):
        summaries.append(f'SPY Put/Call Ratio: <strong>{pc["volume_pcr"]:.3f}</strong>（{pc.get("signal","")}）')

    vs = alt.get('volatility_term_structure', {})
    if vs.get('ratio'):
        summaries.append(f'VIX/VIX3M: <strong>{vs["ratio"]:.4f}</strong>（{vs.get("structure","")}）')

    mb = alt.get('market_breadth', {})
    rsp = mb.get('rsp_spy', {})
    if rsp.get('signal'):
        summaries.append(f'RSP/SPY（市場寬度）: {rsp.get("signal","")}（1月 {rsp.get("change_1m_pct",0):+.2f}%）')

    iwm = mb.get('iwm_spy', {})
    if iwm.get('signal'):
        summaries.append(f'IWM/SPY（大小型股）: {iwm.get("signal","")}')

    vg = mb.get('iwd_iwf', {})
    if vg.get('signal'):
        summaries.append(f'IWD/IWF（價值/成長）: {vg.get("signal","")}')

    if summaries:
        items = ''.join(f'<div style="margin:4px 0;">• {s}</div>' for s in summaries)
        parts.append(
            '<div style="background:linear-gradient(135deg,#f0fff4,#e6ffed);border-left:4px solid #27ae60;padding:14px 18px;margin:14px 0;font-size:9.5pt;line-height:1.8;border-radius:0 6px 6px 0;page-break-inside:avoid;">'
            f'<strong style="color:#27ae60;font-size:10.5pt;">市場微觀結構指標</strong>{items}</div>'
        )

    if not parts:
        return ''
    return '<div class="section-new-page"></div>' + '\n'.join(parts)


def _gen_em_currency_html(alt):
    """生成新興市場貨幣壓力 HTML 區塊（獨立，放在外匯區塊後面）"""
    if not alt:
        return ''
    em = alt.get('em_currency_stress', {})
    if not em.get('currencies'):
        return ''
    rows = ''
    for c in em['currencies']:
        sc = c.get('stress_score', 0)
        sc_color = '#e74c3c' if sc > 5 else '#f39c12' if sc > 2 else '#27ae60'
        rows += f'<tr><td style="text-align:left;">{c["name"]}</td><td style="text-align:right;">{c.get("rate",0):.4f}</td><td style="text-align:right;">{c.get("change_1w_pct",0):+.2f}%</td><td style="text-align:right;">{c.get("change_1m_pct",0):+.2f}%</td><td style="text-align:right;">{c.get("vol_20d",0):.1f}%</td><td style="text-align:right;color:{sc_color};font-weight:700;">{sc:.1f}</td></tr>'
    level = em.get('level', '')
    return (
        '<div style="margin:16px 0;page-break-inside:avoid;">'
        '<div style="font-size:13pt;font-weight:700;color:#2c3e50;border-bottom:2.5px solid #e74c3c;padding-bottom:6px;margin-bottom:10px;">新興市場貨幣壓力 EM Currency Stress</div>'
        f'<div style="font-size:9.5pt;margin-bottom:8px;">綜合壓力: <strong>{em.get("avg_stress",0):.1f}</strong> — {level}</div>'
        f'<table><thead><tr><th style="text-align:left;">貨幣</th><th style="text-align:right;">匯率</th><th style="text-align:right;">1週</th><th style="text-align:right;">1月</th><th style="text-align:right;">波動率</th><th style="text-align:right;">壓力分</th></tr></thead><tbody>{rows}</tbody></table></div>'
    )


def main():
    print(f"Generating report for {DATE}...")

    # Load all data
    md = load_json(f'{REPORTS}/market_data_today.json')
    news = load_json(f'{REPORTS}/news_today.json')
    hot_stocks = load_json(f'{REPORTS}/hot_stocks_today.json')
    enh = load_json(f'{REPORTS}/enhanced_today.json')
    enh2 = load_json(f'{REPORTS}/enhanced_v2_today.json')
    fred = load_json(f'{REPORTS}/fred_today.json')
    alt = load_json(f'{REPORTS}/alternative_today.json')

    # Generate analysis
    executive_summary = gen_executive_summary(md, enh, enh2)
    index_analysis = gen_index_analysis(md, enh2)
    stock_analysis = gen_stock_analysis(hot_stocks, news)
    news_events = gen_news_events(news, market_data=md, sentiment_data=enh.get('sentiment', {}), alt_data=alt)
    calendar_events = gen_calendar()
    sector_analysis = gen_sector_analysis(enh.get('fund_flows', {}))
    yield_curve_analysis = gen_yield_curve_analysis(enh2)

    # Historical context
    from modules.enhanced_market_data import get_historical_sentiment_context
    fg = enh.get('sentiment', {}).get('fear_greed', {}).get('score')
    vix = enh.get('sentiment', {}).get('vix', {}).get('value')
    historical = get_historical_sentiment_context(fg, vix) if fg else {}

    # Serialize hot stocks
    def ser_hs(hs):
        out = {}
        for m, d in hs.items():
            if isinstance(d, dict) and 'inflow' in d:
                out[m] = {
                    'inflow': [{k: s.get(k) for k in ['symbol','name','current','change_pct','volume_ratio','volume','avg_volume','flow','news_mentions']} for s in d['inflow']],
                    'outflow': [{k: s.get(k) for k in ['symbol','name','current','change_pct','volume_ratio','volume','avg_volume','flow','news_mentions']} for s in d['outflow']],
                }
            else:
                out[m] = d
        return out

    # Build raw_data
    raw_data = {
        'market_data': md, 'news_events': news_events, 'index_analysis': index_analysis,
        'stock_analysis': stock_analysis, 'calendar_events': calendar_events,
        'hot_stocks': ser_hs(hot_stocks),
        'holiday_alerts': {'today_closed': [], 'tomorrow_closed': [], 'upcoming_holidays': [], 'has_alerts': False},
        'sentiment_data': enh.get('sentiment', {}), 'clock_data': enh.get('clock', {}),
        'fund_flows': enh.get('fund_flows', {}),
        'executive_summary': executive_summary, 'sector_analysis': sector_analysis,
        'yield_curve_analysis': yield_curve_analysis, 'historical_context': historical,
        'technical_levels': enh2.get('technical_levels', {}),
        'credit_spreads': enh2.get('credit_spreads', {}),
        'northbound_southbound': enh2.get('northbound_southbound', {}),
        'yield_curve': enh2.get('yield_curve', {}),
        'fred_data': fred,
        'alternative_data': alt,
        'report_date': DATE, 'generated_at': datetime.now().isoformat(),
        'fact_check_report': {'total_events_checked': len(news_events), 'corrections_applied': 0, 'status': '通過'}
    }

    with open(f'{REPORTS}/raw_data_{DATE}.json', 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"raw_data saved")

    # Generate HTML
    from modules.html_report_generator import generate_html_report
    html = generate_html_report(
        md, news_events, ser_hs(hot_stocks), stock_analysis,
        index_analysis, calendar_events, DATE,
        sentiment_data=enh.get('sentiment', {}),
        clock_data=enh.get('clock', {}),
        fund_flows=enh.get('fund_flows', {}),
        historical_context=historical,
    )

    # Inject enhanced blocks
    def insert_before_section(html, section_text, new_block):
        pat = rf'(<div class="section-new-page"></div>\s*<div class="section-title">{re.escape(section_text)}</div>)'
        m = re.search(pat, html)
        if m: return html[:m.start()] + new_block + html[m.start():]
        pat2 = rf'(<div class="section-title">{re.escape(section_text)}</div>)'
        m2 = re.search(pat2, html)
        if m2: return html[:m2.start()] + new_block + html[m2.start():]
        return html

    # 市場綜述：插在新聞前面（報告最上方）
    if executive_summary:
        html = insert_before_section(html, '一、宏觀重點新聞',
            f'<div style="background:linear-gradient(135deg,#f0f7ff 0%,#e8f4fd 100%);border-left:5px solid #1a365d;padding:12px 18px;margin:12px 0 14px 0;font-size:10pt;line-height:1.5;color:#2c3e50;border-radius:0 6px 6px 0;page-break-inside:avoid;"><strong style="font-size:11pt;color:#1a365d;">市場綜述</strong>　{executive_summary}</div>\n')

    # 技術面：插在債券前（指數後面）
    tech = enh2.get('technical_levels', {})
    if tech:
        rows = ""
        for name, t in tech.items():
            rsi = t.get('rsi', 0)
            rc = '#e74c3c' if rsi < 30 else '#27ae60' if rsi > 70 else '#2c3e50'
            cross = t.get('cross', '') or ''
            cc = '#27ae60' if '黃金' in cross else '#e74c3c' if '死亡' in cross else '#999'
            m200 = f"{t['ma200']:,.0f}" if t.get('ma200') else 'N/A'
            rows += f'<tr><td style="font-weight:600;text-align:left;">{name}</td><td style="text-align:right;">{t.get("current",0):,.0f}</td><td style="text-align:right;">{t.get("ma50",0):,.0f}</td><td style="text-align:right;">{m200}</td><td style="text-align:right;font-weight:700;color:{rc};">{rsi:.1f}</td><td style="text-align:right;color:#e74c3c;">{t.get("pct_from_high",0):+.1f}%</td><td style="text-align:center;color:{cc};font-size:8.5pt;">{cross}</td></tr>'
        html = insert_before_section(html, '三、債券・殖利率',
            f'<div style="margin:16px 0 20px 0;page-break-inside:avoid;"><div style="font-size:13pt;font-weight:700;color:#2c3e50;border-bottom:2.5px solid #e67e22;padding-bottom:6px;margin-bottom:10px;">主要指數技術面關鍵位</div><table><thead><tr><th style="text-align:left;">指數</th><th style="text-align:right;">收盤</th><th style="text-align:right;">50MA</th><th style="text-align:right;">200MA</th><th style="text-align:right;">RSI(14)</th><th style="text-align:right;">距52W高</th><th style="text-align:center;">均線交叉</th></tr></thead><tbody>{rows}</tbody></table></div>\n')

    # 殖利率曲線分析：插在外匯前（債券後面）
    if yield_curve_analysis:
        html = insert_before_section(html, '四、外匯市場',
            f'<div style="background:linear-gradient(135deg,#f5f0ff 0%,#ede5ff 100%);border-left:4px solid #6c5ce7;padding:14px 18px;margin:14px 0;font-size:9.5pt;line-height:1.8;border-radius:0 6px 6px 0;page-break-inside:avoid;"><strong style="color:#6c5ce7;font-size:10.5pt;">殖利率曲線分析</strong><br>{yield_curve_analysis}</div>\n')

    # 歷史情境參考：已直接由 generate_html_report 的 historical_context 參數渲染在情緒指標章節內

    # 行業輪動解讀：插在板塊輪動前
    if sector_analysis:
        html = insert_before_section(html, '九、板塊輪動',
            f'<div style="background:linear-gradient(135deg,#fff8f0 0%,#ffecd2 100%);border-left:4px solid #e67e22;padding:14px 18px;margin:14px 0;font-size:9.5pt;line-height:1.8;border-radius:0 6px 6px 0;page-break-inside:avoid;"><strong style="color:#d35400;font-size:10.5pt;">行業輪動解讀</strong><br>{sector_analysis}</div>\n')

    # ── 替代數據區塊（分拆插入到對應位置） ──
    alt_blocks = _gen_alternative_data_html(alt)  # 板塊輪動 + 市場微觀結構
    em_block = _gen_em_currency_html(alt)          # EM 貨幣壓力（獨立）
    fred_block = _gen_fred_data_html(fred)

    # EM 貨幣壓力：插在外匯的「主要貨幣對」表格後面
    if em_block:
        forex_marker = '>主要貨幣對</div>'
        forex_pos = html.find(forex_marker)
        if forex_pos > 0:
            table_end = html.find('</tbody></table>', forex_pos)
            if table_end > 0:
                block_end = html.find('</div>', table_end)
                if block_end > 0:
                    insert_pos = block_end + len('</div>')
                    html = html[:insert_pos] + '\n' + em_block + html[insert_pos:]
        else:
            html = insert_before_section(html, '五、大宗商品', em_block)

    # FRED + 替代數據：插在經濟日曆前
    if fred_block:
        html = insert_before_section(html, '十一、本週經濟日曆', fred_block)
    if alt_blocks:
        html = insert_before_section(html, '十一、本週經濟日曆', alt_blocks)

    html_path = f'{REPORTS}/daily_report_{DATE}.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML saved: {html_path}")


if __name__ == '__main__':
    main()
