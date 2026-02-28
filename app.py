import streamlit as st
import sys
import pandas as pd
from datetime import datetime
sys.path.insert(0, '.')
from core.screener import run_screening
from core.stock_lookup import search_ticker
from core.stock_detail import get_stock_details, format_currency, format_percentage

st.set_page_config(
    page_title="日本株スクリーニング",
    page_icon="📊",
    layout="wide"
)

st.title("📊 日本株スクリーニング")

# タブ作成
tab1, tab2 = st.tabs(["🔍 スクリーニング", "📈 個別株検索"])

# ==================== タブ1: スクリーニング ====================
with tab1:
    st.markdown("yfinanceデータに基づく個別株検索＆スコアリングツール")
    
    # 設定をタブ内に配置（4列レイアウト）
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        preset = st.selectbox(
            "スクリーニング種類",
            options=["value", "high-dividend", "growth"],
            format_func=lambda x: {
                "value": "💰 割安株（バリュー）",
                "high-dividend": "💵 高配当",
                "growth": "📈 成長株"
            }[x]
        )
    
    with col2:
        market = st.selectbox(
            "対象市場",
            options=["prime", "standard", "growth", "all"],
            format_func=lambda x: {
                "prime": "プライム市場",
                "standard": "スタンダード市場",
                "growth": "グロース市場",
                "all": "全市場"
            }[x]
        )
    
    with col3:
        limit = st.number_input(
            "表示件数",
            min_value=5,
            max_value=50,
            value=10,
            step=5
        )
    
    with col4:
        max_scan = st.number_input(
            "スキャン件数",
            min_value=50,
            max_value=500,
            value=100,
            step=50,
            help="この件数まで銘柄をチェックします。多いほど時間がかかります。"
        )
    
    # 実行ボタン
    if st.button("🔍 スクリーニング実行", type="primary", use_container_width=True):
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

# ==================== タブ2: 個別株検索 ====================
with tab2:
    st.markdown("会社名またはティッカーコードで個別株を検索")
    
    # 検索ボックス
    query = st.text_input(
        "🔎 銘柄を検索",
        placeholder="例：トヨタ、7203、7203.T",
        help="会社名の一部またはティッカーコードを入力してください"
    )
    
    if query:
        with st.spinner("検索中..."):
            results = search_ticker(query)
        
        if not results:
            st.warning(f"「{query}」に該当する銘柄が見つかりませんでした。")
        elif len(results) == 1:
            # 1件のみヒット → 直接詳細を表示
            ticker, name = results[0]
            st.info(f"📌 {name} ({ticker})")
            
            with st.spinner("詳細情報を取得中..."):
                details = get_stock_details(ticker)
            
            # 基本情報とスコア
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("バリュースコア", f"{details['score']:.2f} / 100")
            with col2:
                price = details['basic_info']['current_price']
                st.metric("株価", format_currency(price, details['basic_info']['currency']))
            with col3:
                mcap = details['basic_info']['market_cap']
                st.metric("時価総額", format_currency(mcap, details['basic_info']['currency']))
            with col4:
                sector = details['basic_info']['sector']
                st.metric("セクター", sector if sector != '-' else '不明')
            
            # 財務指標
            st.subheader("📊 財務指標")
            metrics = details['financial_metrics']
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("PER", f"{metrics['per']:.2f}" if metrics['per'] else "-")
                st.metric("PBR", f"{metrics['pbr']:.2f}" if metrics['pbr'] else "-")
            with col2:
                st.metric("ROE", format_percentage(metrics['roe']))
                st.metric("配当利回り", format_percentage(metrics['dividend_yield']))
            with col3:
                st.metric("売上成長率", format_percentage(metrics['revenue_growth']))
                st.metric("利益率", format_percentage(metrics['profit_margin']))
            with col4:
                st.metric("52週高値", f"¥{metrics['52w_high']:,.0f}" if metrics['52w_high'] else "-")
                st.metric("52週安値", f"¥{metrics['52w_low']:,.0f}" if metrics['52w_low'] else "-")
            
            # 株価チャート
            if not details['price_history'].empty:
                st.subheader("📈 株価チャート（過去1年）")
                st.line_chart(details['price_history']['Close'])
            
            # 配当履歴
            if not details['dividend_history'].empty:
                st.subheader("💵 配当履歴（過去5年）")
                div_df = pd.DataFrame({
                    '日付': details['dividend_history'].index.strftime('%Y-%m-%d'),
                    '配当金': details['dividend_history'].values
                })
                st.dataframe(div_df, use_container_width=True, hide_index=True)
            else:
                st.info("配当データがありません")
        
        else:
            # 複数ヒット → 選択肢を表示
            st.info(f"{len(results)}件の候補が見つかりました。銘柄を選択してください：")
            
            for ticker, name in results:
                if st.button(f"{name} ({ticker})", key=ticker):
                    st.rerun()

# フッター
st.markdown("---")
st.caption("⚠️ このアプリに基づいて損失出しても責めないでね。。")
st.caption("データソース: yfinance (Yahoo Finance)")