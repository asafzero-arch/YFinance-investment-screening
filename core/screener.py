import yaml
import time
from core.data_fetcher import fetch_stock_info
from core.scorer import calc_value_score
from core.tse_tickers import fetch_tse_tickers


def load_config() -> dict:
    with open('config/thresholds.yaml', encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_screening(preset='value', limit=10, market='prime', max_scan=50):
    config = load_config()
    weights = config['scoring']
    thresholds = config['japan']

    tickers = fetch_tse_tickers(market=market)
    tickers = tickers[:max_scan]
    print(f"[スキャン開始] {len(tickers)} 件をスクリーニングします...")

    results = []
    for i, ticker in enumerate(tickers, 1):
        try:
            print(f"  ({i}/{len(tickers)}) {ticker} を確認中...", end="\r")
            info = fetch_stock_info(ticker)

            market_cap = info.get('marketCap', 0) or 0
            per = info.get('trailingPE', 0) or 0
            pbr = info.get('priceToBook', 0) or 0

            if market_cap < thresholds['min_market_cap']:
                continue
            if per <= 0:
                continue

            if preset == 'high-dividend':
                div = info.get('dividendYield', 0) or 0
                if div > 1:
                    div /= 100
                if div < 0.03:
                    continue
            elif preset == 'growth':
                growth = info.get('revenueGrowth', 0) or 0
                if growth < 0.10:
                    continue
            else:
                if per > thresholds['max_per']:
                    continue
                if pbr > thresholds['max_pbr']:
                    continue

            score = calc_value_score(info, weights)

            results.append({
                'ticker': ticker,
                'name': info.get('longName', ticker),
                'score': score,
                'per': round(per, 2) if per else None,
                'pbr': round(pbr, 2) if pbr else None,
                'dividend': info.get('dividendYield'),
                'roe': info.get('returnOnEquity'),
                'market_cap': market_cap,
            })

            time.sleep(0.3)

        except Exception as e:
            print(f"\n[スキップ] {ticker}: {e}")
            continue

    print(f"\n[完了] {len(results)} 件がフィルタを通過しました")
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]
