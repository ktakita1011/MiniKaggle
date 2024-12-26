import os
import sqlite3

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from app.nav import MenuButtons
from app.pages.account import get_roles

SUBMITTION_DB_PATH = "./database/submissions.db"

# 環境変数の読み込み
load_dotenv()
OPTIMIZATION_DIRECTION = os.getenv("OPTIMIZATION_DIRECTION", "max").lower()


def get_leaderboard():
    conn = sqlite3.connect(SUBMITTION_DB_PATH)

    if OPTIMIZATION_DIRECTION == "max":
        query = """
        SELECT username, MAX(public_score) as best_score
        FROM submissions
        GROUP BY username
        ORDER BY best_score DESC
        """
    else:  # min
        query = """
        SELECT username, MIN(public_score) as best_score
        FROM submissions
        GROUP BY username
        ORDER BY best_score ASC
        """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # 順位を付ける
    df["順位"] = range(1, len(df) + 1)

    # カラム名を変更
    df = df.rename(columns={"username": "ユーザー", "best_score": "スコア"})

    # カラムの順序を変更
    df = df[["順位", "ユーザー", "スコア"]]

    return df


def show():
    MenuButtons(get_roles())
    st.title("リーダーボード")
    st.write(
        f"現在のPublic Scoreに基づくリーダーボードです。(最適化方向: {'最大化' if OPTIMIZATION_DIRECTION == 'max' else '最小化'})"
    )

    leaderboard = get_leaderboard()

    # ページネーション
    items_per_page = 50  # 1ページあたりの表示数
    num_pages = (len(leaderboard) - 1) // items_per_page + 1
    page = st.number_input("ページ", min_value=1, max_value=num_pages, value=1)
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page

    # リーダーボードの表示（ページネーション適用）
    st.table(leaderboard.iloc[start_idx:end_idx])

    st.write(f"ページ {page}/{num_pages}")

    # ユーザーの順位検索
    st.subheader("ユーザー検索")
    username = st.text_input("ユーザー名を入力してください")
    if username:
        user_rank = leaderboard[leaderboard["ユーザー"] == username]
        if not user_rank.empty:
            st.success(
                f"{username}さんの順位: {user_rank['順位'].values[0]}位 (スコア: {user_rank['スコア'].values[0]:.4f})"
            )
        else:
            st.warning(f"{username}さんの記録が見つかりません。")


if __name__ == "__main__":
    show()
