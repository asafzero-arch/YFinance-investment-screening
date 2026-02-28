import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from core.data_fetcher import fetch_stock_info
from core.scorer import calc_value_score
import yaml


def get_stock_details(ticker: str) -> dict:
    """
    個別株の詳細情報を取得する
    
    Returns:
        {
            'basic_info': {...},
            'financial_metrics': {...},
            'score': float,
            'price_history': DataFrame,
            'dividend_history': DataFrame
        }
    """
    stock = yf.Ticker(ticker)
    info = fetch_stock_info(ticker)
    
    # スコア計算
    with open('config/thresholds.yaml', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    weights = config['scoring']
    score = calc_value_score(info, weights)
    
    # 基本情報
    basic_info = {
        'ticker': ticker,
        'name': info.get('longName') or info.get('shortName') or ticker,
        'sector': info.get('sector', '-'),
        'industry': info.get('industry', '-'),
        'market_cap': info.get('marketCap'),
        'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
        'currency': info.get('currency', 'JPY'),
    }
    
    # 財務指標
    financial_metrics = {
        'per': info.get('trailingPE'),
        'pbr': info.get('priceToBook'),
        'roe': info.get('returnOnEquity'),
        'dividend_yield': info.get('dividendYield'),
        'dividend_rate': info.get('dividendRate'),
        'payout_ratio': info.get('payoutRatio'),
        'revenue': info.get('totalRevenue'),
        'revenue_growth': info.get('revenueGrowth'),
        'profit_margin': info.get('profitMargins'),
        'debt_to_equity': info.get('debtToEquity'),
        'beta': info.get('beta'),
        '52w_high': info.get('fiftyTwoWeekHigh'),
        '52w_low': info.get('fiftyTwoWeekLow'),
    }
    
    # 株価履歴（過去1年）
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        price_history = stock.history(start=start_date, end=end_date)
    except Exception as e:
        print(f"[エラー] 株価履歴取得失敗: {e}")
        price_history = pd.DataFrame()
    
    # 配当履歴
    try:
        dividend_history = stock.dividends
        if len(dividend_history) > 0:
            # 過去5年分に絞る
            five_years_ago = datetime.now() - timedelta(days=365*5)
            dividend_history = dividend_history[dividend_history.index >= five_years_ago]
    except Exception as e:
        print(f"[エラー] 配当履歴取得失敗: {e}")
        dividend_history = pd.Series()
    
    return {
        'basic_info': basic_info,
        'financial_metrics': financial_metrics,
        'score': score,
        'price_history': price_history,
        'dividend_history': dividend_history,
    }


def format_currency(value, currency='JPY'):
    """通貨フォーマット"""
    if value is None:
        return '-'
    
    if currency == 'JPY':
        if value >= 100000000:  # 1億円以上
            return f"¥{value/100000000:.1f}億"
        elif value >= 10000:
            return f"¥{value/10000:.1f}万"
        else:
            return f"¥{value:,.0f}"
    else:
        return f"${value:,.2f}"


def format_percentage(value):
    """パーセンテージフォーマット"""
    if value is None:
        return '-'
    if value > 1:  # すでにパーセント値の場合
        return f"{value:.2f}%"
    return f"{value * 100:.2f}%"
