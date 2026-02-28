import json
import os
from core.tse_tickers import fetch_tse_tickers


def build_company_name_mapping():
    """会社名からティッカーへのマッピングを構築する"""
    cache_path = "cache/company_mapping.json"
    
    if os.path.exists(cache_path):
        with open(cache_path, encoding='utf-8') as f:
            return json.load(f)
    
    # JPXの銘柄リストから会社名マッピングを作成
    # 本来はJPXのExcelから正式な会社名を取得すべきだが、
    # 簡易版としてティッカーからyfinanceで会社名を取得する方式
    print("[構築中] 会社名マッピングを作成しています...")
    
    # ここでは事前に主要銘柄のマッピングを用意
    # 実運用ではJPXのデータから自動生成すべき
    mapping = {}
    
    os.makedirs("cache", exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    return mapping


def search_ticker(query: str) -> list:
    """
    会社名またはティッカーコードから銘柄を検索する
    
    Args:
        query: 検索文字列（例：トヨタ、7203、7203.T）
    
    Returns:
        マッチした銘柄のリスト [(ticker, company_name), ...]
    """
    import yfinance as yf
    
    query = query.strip()
    results = []
    
    # パターン1: ティッカーコード直接入力（7203 or 7203.T）
    if query.isdigit():
        ticker = f"{query}.T"
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            name = info.get('longName') or info.get('shortName') or ticker
            results.append((ticker, name))
            return results
        except:
            pass
    
    if query.endswith('.T'):
        try:
            stock = yf.Ticker(query)
            info = stock.info
            name = info.get('longName') or info.get('shortName') or query
            results.append((query, name))
            return results
        except:
            pass
    
    # パターン2: 会社名検索（部分一致）
    # JPXの銘柄リストを検索
    from core.tse_tickers import fetch_tse_tickers
    all_tickers = fetch_tse_tickers(market='all')
    
    # 上位50件のみチェック（時間短縮のため）
    for ticker in all_tickers[:50]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            name = info.get('longName') or info.get('shortName') or ''
            
            if query.lower() in name.lower() or query in ticker:
                results.append((ticker, name))
                
            if len(results) >= 10:  # 最大10件まで
                break
        except:
            continue
    
    return results


def get_ticker_from_query(query: str) -> str:
    """
    検索クエリからティッカーコードを取得する
    単一の結果が期待される場合に使用
    """
    results = search_ticker(query)
    if results:
        return results[0][0]
    return None
