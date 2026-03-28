#!/usr/bin/env python3
"""
FRED 聯準會經濟數據模組
負責獲取：
1. 關鍵利率與殖利率（聯邦基金利率、殖利率曲線、高收益利差）
2. 通脹指標（盈虧平衡通脹率、CPI）
3. 貨幣與流動性（Fed資產負債表、逆回購）
4. 勞動與經濟（初領失業金、失業率）
5. 金融狀況指數（NFCI、STLFSI）
"""
import os
import requests
from datetime import datetime


FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred/series/observations'

# ==================== FRED 系列定義 ====================

FRED_SERIES = {
    'rates_yields': {
        'label': '關鍵利率與殖利率',
        'series': {
            'FEDFUNDS': '聯邦基金有效利率',
            'DFF': '聯邦基金日利率',
            'T10Y2Y': '10Y-2Y 殖利率利差',
            'T10Y3M': '10Y-3M 殖利率利差',
            'BAMLH0A0HYM2': 'ICE BofA 高收益利差',
        },
    },
    'inflation': {
        'label': '通脹指標',
        'series': {
            'T5YIE': '5年盈虧平衡通脹率',
            'T10YIE': '10年盈虧平衡通脹率',
            'CPIAUCSL': 'CPI 消費者物價指數',
        },
    },
    'money_liquidity': {
        'label': '貨幣與流動性',
        'series': {
            'WALCL': 'Fed 資產負債表（總資產）',
            'RRPONTSYD': '隔夜逆回購（日）',
        },
    },
    'labor_economy': {
        'label': '勞動與經濟',
        'series': {
            'ICSA': '初領失業金人數（週）',
            'UNRATE': '失業率',
        },
    },
    'financial_conditions': {
        'label': '金融狀況指數',
        'series': {
            'NFCI': '芝加哥聯儲金融狀況指數',
            'STLFSI4': '聖路易聯儲金融壓力指數',
        },
    },
}

# All series IDs flattened for convenience
ALL_SERIES_IDS = []
for cat in FRED_SERIES.values():
    ALL_SERIES_IDS.extend(cat['series'].keys())


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ==================== 核心 API 函數 ====================

def fetch_fred_series(series_id, limit=5):
    """
    Fetch latest observations from FRED.

    Args:
        series_id: FRED series identifier (e.g. 'T10Y2Y')
        limit: Number of recent observations to fetch

    Returns:
        List of {'date': str, 'value': float|None} dicts, newest first.
        Returns empty list on error.
    """
    if not FRED_API_KEY:
        log(f"    ⚠ FRED_API_KEY 未設定，跳過 {series_id}")
        return []

    params = {
        'series_id': series_id,
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': limit,
    }

    try:
        resp = requests.get(FRED_BASE_URL, params=params, timeout=10)
        if resp.status_code != 200:
            log(f"    ✗ {series_id}: HTTP {resp.status_code}")
            return []

        data = resp.json()
        observations = data.get('observations', [])

        results = []
        for obs in observations:
            val = obs.get('value', '.')
            results.append({
                'date': obs.get('date', ''),
                'value': float(val) if val not in ('.', '') else None,
            })
        return results

    except requests.exceptions.Timeout:
        log(f"    ✗ {series_id}: 請求超時")
        return []
    except Exception as e:
        log(f"    ✗ {series_id}: {e}")
        return []


# ==================== 分類數據函數 ====================

def get_fred_macro_snapshot():
    """
    Get all key macro indicators in one call, organized by category.

    Returns:
        Dict with categories as keys, each containing series data:
        {
            'rates_yields': {
                'label': '關鍵利率與殖利率',
                'data': {
                    'FEDFUNDS': {'name': '...', 'latest': {...}, 'history': [...]},
                    ...
                }
            },
            ...
        }
    """
    if not FRED_API_KEY:
        log("  ⚠ FRED_API_KEY 未設定，無法獲取 FRED 數據")
        return {}

    log("  獲取 FRED 宏觀經濟快照...")
    snapshot = {}

    for category_key, category_info in FRED_SERIES.items():
        cat_label = category_info['label']
        cat_data = {}

        for series_id, series_name in category_info['series'].items():
            observations = fetch_fred_series(series_id, limit=5)

            if observations:
                latest = observations[0]
                prev = observations[1] if len(observations) > 1 else None

                change = None
                change_pct = None
                if (latest['value'] is not None and prev is not None
                        and prev['value'] is not None and prev['value'] != 0):
                    change = round(latest['value'] - prev['value'], 6)
                    change_pct = round(change / abs(prev['value']) * 100, 4)

                cat_data[series_id] = {
                    'name': series_name,
                    'latest_date': latest['date'],
                    'latest_value': latest['value'],
                    'prev_value': prev['value'] if prev else None,
                    'change': change,
                    'change_pct': change_pct,
                    'history': observations,
                }

                val_str = f"{latest['value']}" if latest['value'] is not None else 'N/A'
                chg_str = f" ({change:+.4f})" if change is not None else ''
                log(f"    ✓ {series_id} ({series_name}): {val_str}{chg_str}")
            else:
                cat_data[series_id] = {
                    'name': series_name,
                    'latest_date': None,
                    'latest_value': None,
                    'prev_value': None,
                    'change': None,
                    'change_pct': None,
                    'history': [],
                }

        snapshot[category_key] = {
            'label': cat_label,
            'data': cat_data,
        }

    return snapshot


def get_fed_balance_sheet_trend():
    """
    Get Fed balance sheet (WALCL) recent trend with weekly data.

    Returns:
        Dict with trend info:
        {
            'latest_date': str,
            'latest_value': float (millions USD),
            'latest_value_trillion': float,
            'week_change': float,
            'week_change_pct': float,
            'month_trend': [{'date': str, 'value': float}, ...],
        }
    """
    if not FRED_API_KEY:
        log("  ⚠ FRED_API_KEY 未設定，跳過 Fed 資產負債表趨勢")
        return {}

    log("  獲取 Fed 資產負債表趨勢...")
    observations = fetch_fred_series('WALCL', limit=8)

    if not observations:
        return {}

    # Filter out None values
    valid_obs = [o for o in observations if o['value'] is not None]
    if not valid_obs:
        return {}

    latest = valid_obs[0]
    prev = valid_obs[1] if len(valid_obs) > 1 else None

    week_change = None
    week_change_pct = None
    if prev and prev['value']:
        week_change = round(latest['value'] - prev['value'], 0)
        week_change_pct = round(week_change / prev['value'] * 100, 4)

    result = {
        'latest_date': latest['date'],
        'latest_value': latest['value'],
        'latest_value_trillion': round(latest['value'] / 1_000_000, 4),
        'week_change': week_change,
        'week_change_pct': week_change_pct,
        'month_trend': valid_obs,
    }

    log(f"    ✓ Fed 資產負債表: ${result['latest_value_trillion']:.2f}T"
        f" (週變化: {week_change:+,.0f}M)" if week_change is not None else
        f"    ✓ Fed 資產負債表: ${result['latest_value_trillion']:.2f}T")

    return result


# ==================== 主函數 ====================

def collect_fred_data():
    """
    Main entry: collect all FRED data for the daily macro report pipeline.

    Returns:
        Dict with all FRED macro data:
        {
            'snapshot': {...},           # All series organized by category
            'balance_sheet_trend': {...}, # Fed balance sheet weekly trend
            'metadata': {
                'source': 'FRED',
                'timestamp': str,
                'api_key_set': bool,
            }
        }
    """
    log("開始收集 FRED 聯準會經濟數據...")

    api_key_set = bool(FRED_API_KEY)
    if not api_key_set:
        log("  ⚠ FRED_API_KEY 環境變數未設定，所有 FRED 數據將為空")
        log("  ⚠ 請至 https://fred.stlouisfed.org/docs/api/api_key.html 申請免費 API Key")

    snapshot = get_fred_macro_snapshot()
    balance_sheet = get_fed_balance_sheet_trend()

    # Summary count
    total_series = 0
    fetched_series = 0
    for cat in snapshot.values():
        for sid, sdata in cat.get('data', {}).items():
            total_series += 1
            if sdata.get('latest_value') is not None:
                fetched_series += 1

    log(f"  FRED 數據收集完成: {fetched_series}/{total_series} 系列成功")

    return {
        'snapshot': snapshot,
        'balance_sheet_trend': balance_sheet,
        'metadata': {
            'source': 'FRED (Federal Reserve Economic Data)',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'api_key_set': api_key_set,
            'series_fetched': fetched_series,
            'series_total': total_series,
        },
    }


if __name__ == '__main__':
    import json
    data = collect_fred_data()
    output_path = os.path.join(os.path.dirname(__file__), '..', 'reports', 'fred_data_test.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    log("FRED 數據測試輸出完成")
