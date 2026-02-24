import requests
import pandas as pd
import os
import json
from datetime import datetime, timedelta

CACHE_PATH = "cache/tse_tickers.json"
NIKKEI225_CACHE_PATH = "cache/nikkei225_tickers.json"
CACHE_TTL_DAYS = 7  # 銘柄リストは週1回更新で十分

# JPX公式の上場銘柄一覧URL
JPX_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"


def _is_cache_valid() -> bool:
    if not os.path.exists(CACHE_PATH):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(CACHE_PATH))
    return datetime.now() - mtime < timedelta(days=CACHE_TTL_DAYS)


def fetch_tse_tickers(market: str = "all") -> list:
    """
    JPXから東証上場銘柄のティッカーリストを取得する
    market: "all"（全市場）/ "prime"（プライム）/ 
            "standard"（スタンダード）/ "growth"（グロース）
    """
    if _is_cache_valid():
        print("[キャッシュ] 銘柄リストを読み込みました")
        with open(CACHE_PATH, encoding="utf-8") as f:
            all_tickers = json.load(f)
    else:
        print("[取得中] JPXから上場銘柄一覧をダウンロードしています...")
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(JPX_URL, headers=headers, timeout=30)
        response.raise_for_status()

        # Excelファイルを読み込む
        from io import BytesIO
        df = pd.read_excel(BytesIO(response.content), header=0)

        # 列名を確認して銘柄コードを取得
        # JPXのExcelは「コード」列に証券コードが入っている
        code_col = [c for c in df.columns if 'コード' in str(c)][0]
        market_col = [c for c in df.columns if '市場' in str(c)][0]

        # yfinance用に「XXXX.T」形式に変換
        df['ticker'] = df[code_col].astype(str).str.zfill(4) + '.T'
        df['market_name'] = df[market_col].astype(str)

        # キャッシュ用に全銘柄を保存
        ticker_data = df[['ticker', 'market_name']].to_dict('records')
        os.makedirs("cache", exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(ticker_data, f, ensure_ascii=False)

        all_tickers = ticker_data
        print(f"[完了] {len(all_tickers)} 件の銘柄を取得しました")

    # 日経225の場合は別ソースから取得
    if market == "nikkei225":
        return _fetch_nikkei225_tickers()

    # 市場フィルタ
    market_map = {
        "prime": "プライム",
        "standard": "スタンダード",
        "growth": "グロース",
    }

    if market == "all":
        return [t['ticker'] for t in all_tickers]
    else:
        keyword = market_map.get(market, "")
        filtered = [t['ticker'] for t in all_tickers
                    if keyword in t['market_name']]
        print(f"[フィルタ] {market}市場：{len(filtered)} 件")
        return filtered


def _fetch_nikkei225_tickers() -> list:
    """Wikipediaから日経225構成銘柄を取得する"""
    cache_path = NIKKEI225_CACHE_PATH
    if os.path.exists(cache_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if datetime.now() - mtime < timedelta(days=CACHE_TTL_DAYS):
            print("[キャッシュ] 日経225銘柄リストを読み込みました")
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)

    print("[取得中] 日経225構成銘柄を取得しています...")
    from urllib.parse import quote
    from io import StringIO
    url = "https://ja.wikipedia.org/wiki/" + quote("日経平均株価")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text))
        # 「銘柄コード」列を持つテーブルから証券コードを集める
        tickers = []
        for t in tables:
            cols = [str(c) for c in t.columns]
            code_cols = [c for c in cols if 'コード' in c]
            if code_cols:
                code_col = code_cols[0]
                for code in t[code_col]:
                    if pd.notna(code):
                        try:
                            tickers.append(str(int(code)).zfill(4) + '.T')
                        except (ValueError, TypeError):
                            continue
        # 重複除去
        tickers = list(dict.fromkeys(tickers))
        print(f"[完了] 日経225：{len(tickers)} 件")
    except Exception as e:
        print(f"[エラー] Wikipedia取得失敗: {e}")
        print("[フォールバック] JPX銘柄リストの大型株上位225件を使用します")
        # フォールバック：キャッシュ済みのプライム市場銘柄を使う
        tickers = fetch_tse_tickers(market="prime")[:225]

    os.makedirs("cache", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(tickers, f, ensure_ascii=False)

    return tickers


if __name__ == "__main__":
    tickers = fetch_tse_tickers(market="prime")
    print(f"プライム市場：{len(tickers)} 件")
    print("先頭10件:", tickers[:10])