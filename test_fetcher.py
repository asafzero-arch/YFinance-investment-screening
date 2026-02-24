import sys
import yaml
sys.path.insert(0, '.')
from core.data_fetcher import fetch_stock_info
from core.scorer import calc_value_score

# 閾値設定を読み込む
with open('config/thresholds.yaml', encoding='utf-8') as f:
    config = yaml.safe_load(f)

weights = config['scoring']

# トヨタのスコアを計算
info = fetch_stock_info('7203.T')
score = calc_value_score(info, weights)

print('会社名:', info.get('longName'))
print('PER:', info.get('trailingPE'))
print('PBR:', info.get('priceToBook'))
print('ROE:', info.get('returnOnEquity'))
print('バリュースコア:', score, '/ 100')