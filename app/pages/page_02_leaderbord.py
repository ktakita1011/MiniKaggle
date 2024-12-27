import os
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from app.nav import MenuButtons
from app.pages.account import get_roles

SUBMITTION_DB_PATH = "./database/submissions.db"

# 環境変数の読み込み
load_dotenv()
OPTIMIZATION_DIRECTION = os.getenv("OPTIMIZATION_DIRECTION", "max").lower()


def create_leaderboard_table(df):
    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=list(df.columns),
                    fill_color="#FD8E72",
                    align="center",
                    font=dict(color="black", size=16),
                ),  # ヘッダーの文字色を黒に変更
                cells=dict(
                    values=[df[col] for col in df.columns],
                    fill_color=[
                        ["#E6F0FF" if i % 2 == 0 else "white" for i in range(len(df))]
                    ],
                    align="center",
                    font=dict(color="black", size=14),
                ),  # セルの文字色を黒に変更
            )
        ]
    )

    fig.update_layout(
        # title=dict(
        #     text="リーダーボード", font=dict(size=24, color="black")
        # ),  # タイトルの文字色も黒に変更
        margin=dict(l=0, r=0, t=40, b=0),
        height=800,
    )

    return fig


def get_leaderboard():
    conn = sqlite3.connect(SUBMITTION_DB_PATH)

    if OPTIMIZATION_DIRECTION == "max":
        query = """
        SELECT u.username, MAX(s.public_score) as best_score
        FROM submissions s
        JOIN users u ON s.user_id = u.user_id
        GROUP BY s.user_id
        ORDER BY best_score DESC
        """
    else:  # min
        query = """
        SELECT u.username, MIN(s.public_score) as best_score
        FROM submissions s
        JOIN users u ON s.user_id = u.user_id
        GROUP BY s.user_id
        ORDER BY best_score ASC
        """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # 順位を付ける
    df["順位"] = range(1, len(df) + 1)

    # カラム名を変更
    df = df.rename(columns={"username": "ユーザー", "best_score": "Public スコア"})

    # スコアを小数点以下4桁に丸める
    df["Public スコア"] = df["Public スコア"].round(3)
    # カラムの順序を変更
    df = df[["順位", "ユーザー", "Public スコア"]]

    return df


def show():
    MenuButtons(get_roles())
    st.title("🏆 リーダーボード 🏆")
    st.write(
        f"現在のPublic Scoreに基づくリーダーボードです。(最適化方向: {'最大化' if OPTIMIZATION_DIRECTION == 'max' else '最小化'})"
    )

    leaderboard = get_leaderboard()

    # ページネーション
    items_per_page = 20
    num_pages = (len(leaderboard) - 1) // items_per_page + 1

    # リーダーボードの表示（初期ページ）
    page = 1
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    fig = create_leaderboard_table(leaderboard.iloc[start_idx:end_idx])
    leaderboard_chart = st.plotly_chart(fig, use_container_width=True)

    # ページ切り替えを下部に配置
    st.write("")  # 空白を追加してスペースを作る
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input("ページ", min_value=1, max_value=num_pages, value=1)
        st.write(f"ページ {page}/{num_pages}")

    # ページが変更されたら、リーダーボードを更新
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    fig = create_leaderboard_table(leaderboard.iloc[start_idx:end_idx])
    leaderboard_chart.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    show()
