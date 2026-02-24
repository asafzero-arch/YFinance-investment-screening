import yfinance as yf
import json
import os
from datetime import datetime, timedelta

CACHE_DIR = "cache"
CACHE_TTL_HOURS = 24

def _cache_path(key: str) -> str:
    """キャッシュファイルのパスを返す"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe_key = str(key).replace("/", "_").replace("\\", "_")
    return os.path.join(CACHE_DIR, f"{safe_key}.json")

def _is_cache_valid(path: str) -> bool:
    """キャッシュが24時間以内かどうか確認する"""
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.now() - mtime < timedelta(hours=CACHE_TTL_HOURS)

def fetch_screener_results(preset: str = "value", limit: int = 20) -> list:
    """EquityQueryで東証銘柄をバルク取得する"""
    cache_key = f"screener_{preset}_{limit}"
    path = _cache_path(cache_key)

    if _is_cache_valid(path):
        print(f"[キャッシュ] {preset} の結果を読み込みました")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    print(f"[取得中] yfinanceから {preset} の銘柄を取得しています...")

    screener = yf.Screener()

    if preset == "high-dividend":
        screener.set_predefined_body("day_gainers")  # 暫定：後で差し替え
    else:
        screener.set_predefined_body("day_gainers")  # 暫定：後で差し替え

    screener.patch_body({
        "size": limit,
        "offset": 0,
        "region": "jp"
    })

    result = screener.response
    quotes = result.get("quotes", [])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)

    print(f"[完了] {len(quotes)} 件取得しました")
    return quotes

def fetch_stock_info(ticker: str) -> dict:
    """個別銘柄の詳細情報を取得する（例：7203.T）"""
    path = _cache_path(f"info_{ticker}")

    if _is_cache_valid(path):
        print(f"[キャッシュ] {ticker} の情報を読み込みました")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    print(f"[取得中] {ticker} の情報を取得しています...")
    stock = yf.Ticker(ticker)
    info = stock.info

    with open(path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2, default=str)

    print(f"[完了] {ticker} の情報を取得しました")
    return info