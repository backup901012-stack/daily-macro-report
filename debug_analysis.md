# 根本原因分析 - 排序變化 + KOSPI 消失

## 問題 1: KOSPI 消失

根因在 `fetch_batch()` 函數（第 163-170 行）：
```python
def fetch_batch(symbols_dict):
    results = {}
    for name, symbol in symbols_dict.items():
        data = fetch_quote(symbol, name)
        if data:          # <-- 如果 fetch_quote 返回 None，就跳過
            results[name] = data
    return results
```

KOSPI (`^KS11`) 的 `fetch_quote` 返回了 `None`，所以被跳過了。
可能原因：韓國市場週末 API 返回的數據不足 2 個有效交易日。

## 問題 2: 排序變化

原始數據（raw_data JSON）的 dict key 順序是 Python dict 插入順序，與 ASIA_INDICES 定義順序一致。
3/20: ['日經225', '台灣加權', '香港恆生', '上證綜指', '深證成指', '韓國KOSPI', '澳洲ASX200']
3/23: ['日經225', '台灣加權', '香港恆生', '上證綜指', '深證成指', '澳洲ASX200']

但 HTML 報告中的排序不同（從截圖看是按跌幅排序），所以排序邏輯在 HTML 渲染階段。
需要檢查 html_report_generator.py 中的排序邏輯。
