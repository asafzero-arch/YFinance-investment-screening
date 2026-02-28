import gspread
import pandas as pd
from datetime import datetime
import uuid
import streamlit as st

# Google SheetsのID
SHEET_KEY = "1WHdpnuYWc8owSdLNkOaHhzRAhB8xCkhrbFq2dJZan2w"


def get_user_id():
    """ブラウザからユーザーIDを取得または新規生成"""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())[:8]
    return st.session_state.user_id


def connect_to_sheet():
    """Google Sheetsに接続（サービスアカウント認証）"""
    try:
        # Streamlit secretsから認証情報を取得
        credentials = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials)
        sheet = gc.open_by_key(SHEET_KEY).sheet1
        return sheet
    except Exception as e:
        st.error(f"Google Sheets接続エラー: {str(e)}")
        return None


def add_to_watchlist(ticker, company_name, score, pbr, per, dividend, memo=""):
    """ウォッチリストに銘柄を追加"""
    user_id = get_user_id()
    added_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    try:
        sheet = connect_to_sheet()
        if sheet is None:
            return False, "Google Sheetsへの接続に失敗しました"
        
        # 既に登録済みかチェック
        all_data = sheet.get_all_values()
        for row in all_data[1:]:  # ヘッダーをスキップ
            if len(row) >= 2 and row[0] == user_id and row[1] == ticker:
                return False, f"{company_name}は既にウォッチリストに登録されています"
        
        # 新規追加
        new_row = [user_id, ticker, company_name, score, pbr, per, dividend, added_date, memo]
        sheet.append_row(new_row)
        return True, f"{company_name}をウォッチリストに追加しました"
    
    except Exception as e:
        return False, f"エラー: {str(e)}"


def get_watchlist():
    """自分のウォッチリストを取得"""
    user_id = get_user_id()
    
    try:
        sheet = connect_to_sheet()
        if sheet is None:
            return pd.DataFrame()
        
        # 全データを取得
        all_data = sheet.get_all_values()
        if len(all_data) <= 1:
            return pd.DataFrame()
        
        # DataFrameに変換
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
        
        # 自分のデータのみフィルタ
        my_data = df[df['user_id'] == user_id].copy()
        
        return my_data
    
    except Exception as e:
        st.error(f"ウォッチリスト取得エラー: {str(e)}")
        return pd.DataFrame()


def remove_from_watchlist(ticker):
    """ウォッチリストから銘柄を削除"""
    user_id = get_user_id()
    
    try:
        sheet = connect_to_sheet()
        if sheet is None:
            return False, "Google Sheetsへの接続に失敗しました"
        
        # 削除対象の行を検索
        all_data = sheet.get_all_values()
        row_to_delete = None
        
        for idx, row in enumerate(all_data[1:], start=2):  # ヘッダーをスキップ、行番号は2から
            if len(row) >= 2 and row[0] == user_id and row[1] == ticker:
                row_to_delete = idx
                break
        
        if row_to_delete:
            sheet.delete_rows(row_to_delete)
            return True, "削除しました"
        else:
            return False, "該当する銘柄が見つかりませんでした"
    
    except Exception as e:
        return False, f"エラー: {str(e)}"


def update_memo(ticker, new_memo):
    """メモを更新"""
    user_id = get_user_id()
    
    try:
        sheet = connect_to_sheet()
        if sheet is None:
            return False, "Google Sheetsへの接続に失敗しました"
        
        # 更新対象の行を検索
        all_data = sheet.get_all_values()
        
        for idx, row in enumerate(all_data[1:], start=2):
            if len(row) >= 2 and row[0] == user_id and row[1] == ticker:
                # メモ列（I列=9列目）を更新
                sheet.update_cell(idx, 9, new_memo)
                return True, "メモを更新しました"
        
        return False, "該当する銘柄が見つかりませんでした"
    
    except Exception as e:
        return False, f"エラー: {str(e)}"
