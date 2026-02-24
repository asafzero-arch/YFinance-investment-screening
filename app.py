import streamlit as st
import sys
import pandas as pd
from datetime import datetime
sys.path.insert(0, '.')
from core.screener import run_screening

st.set_page_config(
    page_title="東証割安株スクリーニング",
    page_icon="📊",
    layout="wide"
)

st.title("📊 東証割安株スクリーニング")
st.markdown("yfinanceを使った日本株の割安銘柄検索ツール")

# サイドバーで設定
st.sidebar.header("スクリーニング設定")

preset = st.sidebar.selectbox(
    "スクリーニング種類",
    options=["value", "high-dividend", "growth"],
    format_func=lambda x: {
        "value": "💰 割安株（バリュー）",
        "high-dividend": "💵 高配当",
        "growth": "📈 成長株"
    }[x]
)

market = st.sidebar.selectbox(
    "対象市場",
    options=["prime", "standard", "growth", "all"],
    format_func=lambda x: {
        "prime": "プライム市場",
        "standard": "スタンダード市場",
        "growth": "グロース市場",
        "all": "全市場"
    }[x]
)

limit = st.sidebar.number_input(
    "表示件数",
    min_value=5,
    max_value=50,
    value=10,
    step=5
)

max_scan = st.sidebar.number_input(
    "スキャン件数",
    min_value=50,
    max_value=500,
    value=100,
    step=50,
    help="この件数まで銘柄をチェックします。多いほど時間がかかります。"
)

# 実行ボタン
if st.sidebar.button("🔍 スクリーニング実行", type="primary"):
    with st.spinner(f'{max_scan}件の銘柄をスキャン中...'):
        results = run_screening(
            preset=preset,
            limit=limit,
            market=market,
            max_scan=max_scan
        )
    
    if not results:
        st.warning("該当する銘柄が見つかりませんでした。")
    else:
        st.success(f"✅ {len(results)} 件の銘柄が見つかりました！")
        
        # 結果をDataFrameに変換
        df = pd.DataFrame(results)
        
        # 配当利回りの正規化
        df['dividend_display'] = df['dividend'].apply(
            lambda x: f"{round(x * 100, 2)}%" if x and x <= 1 
            else f"{round(x, 2)}%" if x 
            else "-"
        )
        
        # 時価総額を億円表示
        df['market_cap_display'] = df['market_cap'].apply(
            lambda x: f"{round(x / 100000000)}億円" if x else "-"
        )
        
        # 表示用DataFrame
        display_df = pd.DataFrame({
            '順位': range(1, len(df) + 1),
            'ティッカー': df['ticker'],
            '会社名': df['name'],
            'スコア': df['score'],
            'PER': df['per'],
            'PBR': df['pbr'],
            '配当利回り': df['dividend_display'],
            '時価総額': df['market_cap_display']
        })
        
        # テーブル表示
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # スコア上位3社の詳細
        st.subheader("🏆 スコアTOP3")
        cols = st.columns(3)
        for i, (idx, row) in enumerate(df.head(3).iterrows()):
            with cols[i]:
                st.metric(
                    label=f"{i+1}位: {row['name'][:20]}",
                    value=f"{row['score']}点",
                    delta=f"PER {row['per']}"
                )
                st.caption(f"配当: {display_df.iloc[i]['配当利回り']}")
        
        # CSVダウンロード
        csv = display_df.to_csv(index=False, encoding='utf-8-sig')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv,
            file_name=f"screening_{preset}_{market}_{timestamp}.csv",
            mime="text/csv"
        )

# フッター
st.markdown("---")
st.caption("⚠️ このツールの結果は投資助言ではありません。投資は自己責任で行ってください。")
st.caption("データソース: yfinance (Yahoo Finance)")
