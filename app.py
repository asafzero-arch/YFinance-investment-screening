import streamlit as st
import sys
import pandas as pd
from datetime import datetime
sys.path.insert(0, '.')
from core.screener import run_screening
from core.stock_lookup import search_ticker
from core.stock_detail import get_stock_details, format_currency, format_percentage
from core.watchlist_manager import (
    add_to_watchlist, get_watchlist, remove_from_watchlist,
    get_user_id, update_memo
)

# ─────────── ページ設定 ───────────
st.set_page_config(
    page_title="日本株スクリーニング",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────── カスタムCSS ───────────
st.markdown("""
<style>
/* ── 全体 ── */
.block-container { padding-top: 1.5rem; }

/* ── カード風コンテナ ── */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f8f9fd 0%, #ffffff 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 14px 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
    transition: transform .15s, box-shadow .15s;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,.10);
}
div[data-testid="stMetric"] label {
    font-size: 0.78rem !important;
    color: #64748b;
    text-transform: none;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    font-weight: 700;
}

/* ── タブ ── */
button[data-baseweb="tab"] {
    font-size: 1rem !important;
    font-weight: 600;
    padding: 10px 20px !important;
}

/* ── ランキングバッジ ── */
.rank-badge {
    display: inline-block;
    width: 28px; height: 28px;
    line-height: 28px;
    border-radius: 50%;
    text-align: center;
    font-weight: 800;
    font-size: .85rem;
    color: #fff;
    margin-right: 6px;
}
.rank-1 { background: linear-gradient(135deg, #f59e0b, #d97706); }
.rank-2 { background: linear-gradient(135deg, #94a3b8, #64748b); }
.rank-3 { background: linear-gradient(135deg, #b45309, #92400e); }

/* ── スコアバー ── */
.score-bar-bg {
    background: #e2e8f0;
    border-radius: 6px;
    height: 10px;
    width: 100%;
    overflow: hidden;
}
.score-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width .4s ease;
}

/* ── 結果カード ── */
.result-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,.05);
    transition: box-shadow .15s;
}
.result-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,.08);
}

/* ── サイドバー ── */
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
}
section[data-testid="stSidebar"] hr {
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# ─────────── Session State 初期化 ───────────
for key, default in {
    'screening_results': None,
    'screening_df': None,
    'screening_display_df': None,
    'screening_preset': None,
    'screening_market': None,
    'selected_ticker': None,
    'selected_name': None,
    'search_results': None,
    'last_query': None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────── ヘルパー関数 ───────────
def score_color(score):
    """スコアに応じた色を返す"""
    if score >= 70:
        return "#16a34a"   # green
    elif score >= 50:
        return "#2563eb"   # blue
    elif score >= 30:
        return "#d97706"   # amber
    return "#dc2626"       # red


def score_bar_html(score, max_score=100):
    pct = min(score / max_score * 100, 100)
    color = score_color(score)
    return (
        f'<div class="score-bar-bg">'
        f'<div class="score-bar-fill" style="width:{pct}%;background:{color}"></div>'
        f'</div>'
    )


def format_dividend_display(x):
    if x and x <= 1:
        return f"{round(x * 100, 2)}%"
    elif x:
        return f"{round(x, 2)}%"
    return "-"


def format_market_cap_display(x):
    if x:
        return f"{round(x / 100000000):,}億円"
    return "-"


def navigate_to_detail(ticker, name):
    """スクリーニング結果から個別株詳細へ遷移"""
    st.session_state.selected_ticker = ticker
    st.session_state.selected_name = name


def render_stock_detail(ticker, name):
    """個別株の詳細情報を描画する共通関数"""
    with st.spinner("詳細情報を取得中..."):
        details = get_stock_details(ticker)

    # ── ヘッダーとウォッチリスト追加 ──
    header_col, action_col = st.columns([3, 1])
    with header_col:
        st.markdown(f"### {name}")
        st.caption(f"ティッカー: {ticker}")
    with action_col:
        with st.expander("⭐ ウォッチリストに追加", expanded=False):
            memo = st.text_input("メモ（任意）", key=f"memo_{ticker}", placeholder="例：決算後に再確認")
            if st.button("追加する", key=f"add_{ticker}", type="primary", use_container_width=True):
                success, message = add_to_watchlist(
                    ticker=ticker,
                    company_name=name,
                    score=details['score'],
                    pbr=details['financial_metrics']['pbr'],
                    per=details['financial_metrics']['per'],
                    dividend=details['financial_metrics']['dividend_yield'],
                    memo=memo
                )
                if success:
                    st.success(message)
                else:
                    st.warning(message)

    st.divider()

    # ── 基本指標 ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        score = details['score']
        st.metric("バリュースコア", f"{score:.1f} / 100")
        st.markdown(score_bar_html(score), unsafe_allow_html=True)
    with col2:
        price = details['basic_info']['current_price']
        st.metric("株価", format_currency(price, details['basic_info']['currency']))
    with col3:
        mcap = details['basic_info']['market_cap']
        st.metric("時価総額", format_currency(mcap, details['basic_info']['currency']))
    with col4:
        sector = details['basic_info']['sector']
        st.metric("セクター", sector if sector != '-' else '不明')

    # ── 財務指標（2段） ──
    st.subheader("📊 財務指標")
    metrics = details['financial_metrics']

    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    with r1c1:
        val = metrics['per']
        st.metric("PER", f"{val:.2f}" if val else "-",
                  delta="割安" if val and val < 15 else None,
                  delta_color="normal" if val and val < 15 else "off")
    with r1c2:
        val = metrics['pbr']
        st.metric("PBR", f"{val:.2f}" if val else "-",
                  delta="割安" if val and val < 1 else None,
                  delta_color="normal" if val and val < 1 else "off")
    with r1c3:
        st.metric("ROE", format_percentage(metrics['roe']))
    with r1c4:
        st.metric("配当利回り", format_percentage(metrics['dividend_yield']))

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    with r2c1:
        st.metric("売上成長率", format_percentage(metrics['revenue_growth']))
    with r2c2:
        st.metric("利益率", format_percentage(metrics['profit_margin']))
    with r2c3:
        st.metric("52週高値", f"¥{metrics['52w_high']:,.0f}" if metrics['52w_high'] else "-")
    with r2c4:
        st.metric("52週安値", f"¥{metrics['52w_low']:,.0f}" if metrics['52w_low'] else "-")

    # ── 株価チャート ──
    if not details['price_history'].empty:
        st.subheader("📈 株価チャート（過去1年）")
        st.line_chart(details['price_history']['Close'])

    # ── 配当履歴 ──
    if not details['dividend_history'].empty:
        st.subheader("💵 配当履歴（過去5年）")
        div_df = pd.DataFrame({
            '日付': details['dividend_history'].index.strftime('%Y-%m-%d'),
            '配当金': details['dividend_history'].values
        })
        st.dataframe(div_df, width="stretch", hide_index=True)
    else:
        st.info("配当データがありません")


# ─────────── サイドバー ───────────
with st.sidebar:
    st.markdown("## 📊 日本株スクリーニング")
    st.caption("yfinance データに基づくスコアリングツール")
    st.divider()

    st.markdown("##### スコアリング配点")
    scoring_data = {
        "指標": ["PER", "PBR", "配当利回り", "ROE", "売上成長率"],
        "配点": [25, 25, 20, 15, 15],
    }
    st.dataframe(
        pd.DataFrame(scoring_data),
        width="stretch",
        hide_index=True,
        height=215,
    )

    st.divider()
    st.markdown("##### プリセット説明")
    st.markdown("""
    - **💰 バリュー** — PER・PBR が低く割安な銘柄
    - **💵 高配当** — 配当利回り重視
    - **📈 成長** — 売上成長率が高い銘柄
    """)

    st.divider()
    st.caption(f"あなたの ID: `{get_user_id()}`")
    st.caption("データソース: Yahoo Finance (yfinance)")


# ─────────── メインタイトル ───────────
st.title("📊 日本株スクリーニング")

# タブ作成
tab1, tab2, tab3 = st.tabs(["🔍 スクリーニング", "📈 個別株検索", "⭐ ウォッチリスト"])

# ==================== タブ1: スクリーニング ====================
with tab1:
    # ── 設定パネル ──
    with st.container():
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
        progress_bar = st.progress(0, text="銘柄リストを取得中...")
        status_placeholder = st.empty()

        with st.spinner(f'{max_scan}件の銘柄をスキャン中...'):
            progress_bar.progress(10, text="スキャン実行中...")
            results = run_screening(
                preset=preset,
                limit=limit,
                market=market,
                max_scan=max_scan
            )
            progress_bar.progress(90, text="結果を整理中...")

        progress_bar.progress(100, text="完了！")
        progress_bar.empty()

        # 結果をセッションに保存
        st.session_state.screening_results = results
        st.session_state.screening_preset = preset
        st.session_state.screening_market = market

        if results:
            df = pd.DataFrame(results)
            df['dividend_display'] = df['dividend'].apply(format_dividend_display)
            df['market_cap_display'] = df['market_cap'].apply(format_market_cap_display)
            st.session_state.screening_df = df

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
            st.session_state.screening_display_df = display_df

    # ── 結果表示（セッションから復元）──
    results = st.session_state.screening_results
    if results is None:
        st.info("上の条件を設定して「スクリーニング実行」を押してください。")
    elif not results:
        st.warning("該当する銘柄が見つかりませんでした。条件を変えて再実行してください。")
    else:
        df = st.session_state.screening_df
        display_df = st.session_state.screening_display_df
        saved_preset = st.session_state.screening_preset
        saved_market = st.session_state.screening_market

        st.success(f"✅ {len(results)} 件の銘柄が見つかりました")

        # ── TOP3 カード ──
        st.subheader("🏆 スコア TOP 3")
        top_cols = st.columns(3)
        medals = ["🥇", "🥈", "🥉"]
        rank_classes = ["rank-1", "rank-2", "rank-3"]
        for i, (idx, row) in enumerate(df.head(3).iterrows()):
            with top_cols[i]:
                score = row['score']
                st.markdown(
                    f'<div class="result-card">'
                    f'<span class="rank-badge {rank_classes[i]}">{i+1}</span> '
                    f'<strong>{row["name"][:25]}</strong><br>'
                    f'<span style="font-size:1.6rem;font-weight:800;color:{score_color(score)}">'
                    f'{score}点</span>'
                    f'{score_bar_html(score)}'
                    f'<br><small>PER {row["per"]}　PBR {row["pbr"]}　'
                    f'配当 {display_df.iloc[i]["配当利回り"]}</small>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if st.button(f"📈 詳細を見る", key=f"top_{row['ticker']}"):
                    navigate_to_detail(row['ticker'], row['name'])
                    st.rerun()

        # ── 全データテーブル ──
        st.subheader("📋 全結果")
        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
                "スコア": st.column_config.ProgressColumn(
                    "スコア",
                    min_value=0,
                    max_value=100,
                    format="%d 点",
                ),
            },
        )

        # ── 個別詳細へのジャンプ ──
        st.markdown("##### 銘柄を選んで詳細を見る")
        detail_col1, detail_col2 = st.columns([3, 1])
        with detail_col1:
            selected = st.selectbox(
                "銘柄を選択",
                options=list(zip(df['ticker'], df['name'])),
                format_func=lambda x: f"{x[1]} ({x[0]})",
                label_visibility="collapsed",
            )
        with detail_col2:
            if st.button("📈 詳細ページへ", use_container_width=True):
                navigate_to_detail(selected[0], selected[1])
                st.rerun()

        # ── CSV ダウンロード ──
        csv = display_df.to_csv(index=False, encoding='utf-8-sig')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv,
            file_name=f"screening_{saved_preset}_{saved_market}_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )

# ==================== タブ2: 個別株検索 ====================
with tab2:
    # セッションから遷移してきた場合
    pre_ticker = st.session_state.selected_ticker
    pre_name = st.session_state.selected_name

    if pre_ticker:
        st.info(f"📌 {pre_name} ({pre_ticker}) の詳細を表示中")
        if st.button("✕ 検索に戻る"):
            st.session_state.selected_ticker = None
            st.session_state.selected_name = None
            st.rerun()
        render_stock_detail(pre_ticker, pre_name)
    else:
        st.markdown("会社名またはティッカーコードで個別株を検索")

        # 検索ボックス
        query = st.text_input(
            "🔎 銘柄を検索",
            placeholder="例：トヨタ、7203、7203.T",
            help="会社名の一部またはティッカーコードを入力してください"
        )

        if query:
            # キャッシュ検索結果をセッションに保持
            if query != st.session_state.last_query:
                with st.spinner("検索中..."):
                    search_res = search_ticker(query)
                st.session_state.search_results = search_res
                st.session_state.last_query = query
            else:
                search_res = st.session_state.search_results

            if not search_res:
                st.warning(f"「{query}」に該当する銘柄が見つかりませんでした。")
            elif len(search_res) == 1:
                ticker, name = search_res[0]
                render_stock_detail(ticker, name)
            else:
                # 複数ヒット → selectbox で選択
                st.info(f"{len(search_res)}件の候補が見つかりました。")
                chosen = st.selectbox(
                    "銘柄を選択してください",
                    options=search_res,
                    format_func=lambda x: f"{x[1]} ({x[0]})",
                )
                if chosen:
                    render_stock_detail(chosen[0], chosen[1])

# ==================== タブ3: ウォッチリスト ====================
with tab3:
    st.markdown("### ⭐ あなたのウォッチリスト")

    # ウォッチリスト取得
    watchlist = get_watchlist()

    if watchlist.empty:
        # 改善された空状態
        st.markdown(
            '<div class="result-card" style="text-align:center;padding:40px">'
            '<p style="font-size:2.5rem;margin-bottom:8px">⭐</p>'
            '<p style="font-size:1.1rem;font-weight:600;margin-bottom:4px">'
            'ウォッチリストは空です</p>'
            '<p style="color:#64748b">「個別株検索」タブから気になる銘柄を追加しましょう。</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.success(f"📌 {len(watchlist)} 件の銘柄を監視中")

        # 表示用に整形
        display_columns = ['ticker', 'company_name', 'score', 'per', 'pbr', 'dividend', 'added_date', 'memo']
        display_df = watchlist[display_columns].copy()
        display_df.columns = ['ティッカー', '会社名', 'スコア', 'PER', 'PBR', '配当利回り', '登録日時', 'メモ']

        st.dataframe(display_df, width="stretch", hide_index=True)

        # ── 銘柄操作 ──
        st.divider()
        op_col1, op_col2 = st.columns(2)

        with op_col1:
            st.markdown("##### 📝 メモ編集")
            memo_ticker = st.selectbox(
                "銘柄を選択",
                options=watchlist['ticker'].tolist(),
                format_func=lambda x: f"{watchlist[watchlist['ticker']==x]['company_name'].values[0]} ({x})",
                key="memo_edit_select",
            )
            current_memo = watchlist[watchlist['ticker'] == memo_ticker]['memo'].values[0] if memo_ticker else ""
            new_memo = st.text_input("新しいメモ", value=current_memo, key="new_memo_input")
            if st.button("💾 メモを保存", use_container_width=True):
                success, message = update_memo(memo_ticker, new_memo)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        with op_col2:
            st.markdown("##### 🗑️ 銘柄の削除")
            ticker_to_remove = st.selectbox(
                "削除する銘柄を選択",
                options=watchlist['ticker'].tolist(),
                format_func=lambda x: f"{watchlist[watchlist['ticker']==x]['company_name'].values[0]} ({x})",
                key="remove_select",
            )

            st.warning("この操作は元に戻せません。", icon="⚠️")
            if st.button("🗑️ 削除する", type="secondary", use_container_width=True):
                success, message = remove_from_watchlist(ticker_to_remove)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        # ── 詳細ジャンプ ──
        st.divider()
        st.markdown("##### 🔎 詳細を見る")
        jump_ticker = st.selectbox(
            "銘柄を選択して詳細へ",
            options=watchlist['ticker'].tolist(),
            format_func=lambda x: f"{watchlist[watchlist['ticker']==x]['company_name'].values[0]} ({x})",
            key="jump_select",
        )
        if st.button("📈 個別株詳細へ", use_container_width=True):
            name = watchlist[watchlist['ticker'] == jump_ticker]['company_name'].values[0]
            navigate_to_detail(jump_ticker, name)
            st.rerun()

# ─────────── フッター ───────────
st.divider()
foot_col1, foot_col2 = st.columns([3, 1])
with foot_col1:
    st.caption("⚠️ 本ツールは情報提供のみを目的としています。投資判断は自己責任でお願いします。")
    st.caption("データソース: Yahoo Finance (yfinance)")
with foot_col2:
    st.caption(f"最終アクセス: {datetime.now().strftime('%Y-%m-%d %H:%M')}")