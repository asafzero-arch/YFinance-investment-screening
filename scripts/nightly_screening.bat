@echo off
REM 毎晩の自動スクリーニング実行バッチ
cd /d "C:\Users\hidmi\OneDrive\Documents\YFinance\investment-screening"

echo [%date% %time%] 夜間スクリーニング開始 >> logs\nightly.log

echo === value スクリーニング ===
python scripts/screening.py --preset value --market prime --max-scan 100 --limit 20 >> logs\nightly.log 2>&1

echo === high-dividend スクリーニング ===
python scripts/screening.py --preset high-dividend --market prime --max-scan 100 --limit 20 >> logs\nightly.log 2>&1

echo === growth スクリーニング ===
python scripts/screening.py --preset growth --market prime --max-scan 100 --limit 20 >> logs\nightly.log 2>&1

echo [%date% %time%] 夜間スクリーニング完了 >> logs\nightly.log
