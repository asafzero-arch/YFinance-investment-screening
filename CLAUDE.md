# Investment Screening Tool

## プロジェクト概要
yfinanceを使って東証上場銘柄の割安株をスクリーニングするツール。

## アーキテクチャ
- Skills層（.claude/commands/）→ Core層（core/）→ Data層（core/data_fetcher.py）の3層分離
- yfinanceのEquityQueryで東証全銘柄をバルク取得
- キャッシュはcache/に24時間TTLで保存
- 閾値設定はconfig/thresholds.yamlで一元管理

## スクリーニングロジック
バリュースコア100点満点：
- PER：25点（低いほど高得点）
- PBR：25点（低いほど高得点）
- 配当利回り：20点（高いほど高得点）
- ROE：15点（高いほど高得点）
- 売上成長率：15点（高いほど高得点）

## yfinanceの注意事項
- 東証銘柄のティッカーは末尾に「.T」が必要（例：7203.T）
- 配当利回りが1を超える値で返る場合は100で割って正規化する
- ETFは売上履歴が空リストで返るのでbool()でチェックする

## モジュール構成
- core/data_fetcher.py：yfinance唯一の窓口。ここ以外でyfinanceを直接呼ばない
- core/screener.py：EquityQueryとスコアリングのロジック
- core/scorer.py：バリュースコアの計算
- scripts/screening.py：CLIエントリーポイント
- config/thresholds.yaml：スクリーニング閾値