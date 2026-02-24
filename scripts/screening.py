import sys
import argparse
import csv
import os
from datetime import datetime
sys.path.insert(0, '.')
from core.screener import run_screening


def format_value(value, digits=2):
    if value is None:
        return '-'
    if isinstance(value, float):
        return f"{round(value, digits)}"
    return f"{value}"


def format_dividend(value):
    if value is None:
        return '-'
    if value > 1:
        value /= 100
    return f"{round(value * 100, 2)}%"


def format_market_cap(value):
    if value is None:
        return '-'
    return f"{round(value / 100000000)}億円"


def save_to_csv(results, preset, market):
    """結果をCSVファイルに保存する"""
    os.makedirs('results', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"results/screening_{preset}_{market}_{timestamp}.csv"

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # ヘッダー
        writer.writerow(['順位', 'ティッカー', '会社名', 'スコア',
                         'PER', 'PBR', '配当利回り', '時価総額'])
        # データ
        for i, r in enumerate(results, 1):
            div = r['dividend']
            if div is not None and div > 1:
                div /= 100
            div_str = f"{round(div * 100, 2)}%" if div else '-'

            writer.writerow([
                i,
                r['ticker'],
                r['name'],
                r['score'],
                r['per'] or '-',
                r['pbr'] or '-',
                div_str,
                f"{round(r['market_cap'] / 100000000)}億円" if r['market_cap'] else '-'
            ])

    print(f"\n[保存完了] {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description='東証割安株スクリーニング')
    parser.add_argument('--preset', default='value',
                        choices=['value', 'high-dividend', 'growth'])
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--market', default='prime',
                        choices=['prime', 'standard', 'growth', 'all', 'nikkei225'])
    parser.add_argument('--max-scan', type=int, default=100)
    parser.add_argument('--no-save', action='store_true',
                        help='CSV自動保存を無効にする')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  東証割安株スクリーニング｜{args.market}市場｜{args.preset}")
    print(f"{'='*60}\n")

    results = run_screening(
        preset=args.preset,
        limit=args.limit,
        market=args.market,
        max_scan=args.max_scan
    )

    if not results:
        print("該当する銘柄が見つかりませんでした。")
        return

    print(f"\n{'順位':<4} {'ティッカー':<10} {'会社名':<30} {'スコア':<8} "
          f"{'PER':<8} {'PBR':<8} {'配当':<8} {'時価総額'}")
    print('-' * 90)

    for i, r in enumerate(results, 1):
        name = r['name'][:28] if r['name'] else '-'
        print(f"{i:<4} {r['ticker']:<10} {name:<30} "
              f"{format_value(r['score']):<8} "
              f"{format_value(r['per']):<8} "
              f"{format_value(r['pbr']):<8} "
              f"{format_dividend(r['dividend']):<8} "
              f"{format_market_cap(r['market_cap'])}")

    print(f"\n合計 {len(results)} 件")

    # 毎回CSVログとして自動保存（--no-saveで無効化可能）
    if not args.no_save:
        save_to_csv(results, args.preset, args.market)


if __name__ == '__main__':
    main()
