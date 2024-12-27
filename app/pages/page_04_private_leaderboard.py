import os
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from app.pages.account import get_roles

SUBMISSION_DB_PATH = "./database/submissions.db"
FINAL_SUBMISSION_DB_PATH = "./database/final_submissions.db"

# 環境変数の読み込み
load_dotenv()
OPTIMIZATION_DIRECTION = os.getenv("OPTIMIZATION_DIRECTION", "max").lower()


def check_admin():
    roles = get_roles()
    if (
        "authentication_status" not in st.session_state
        or not st.session_state["authentication_status"]
    ):
        st.error("このページにアクセスするにはログインが必要です。")
        st.stop()

    if "username" not in st.session_state:
        st.error("ユーザー情報が見つかりません。")
        st.stop()

    username = st.session_state["username"]
    if username not in roles or roles[username] != "admin":
        st.error("このページにアクセスする権限がありません。")
        st.stop()


def fetch_data_from_db():
    """データベースから必要なデータを取得する"""
    conn_main = sqlite3.connect(SUBMISSION_DB_PATH)
    conn_final = sqlite3.connect(FINAL_SUBMISSION_DB_PATH)

    users_df = pd.read_sql_query("SELECT * FROM users", conn_main)
    submissions_df = pd.read_sql_query("SELECT * FROM submissions", conn_main)
    final_submissions_df = pd.read_sql_query(
        "SELECT * FROM final_submissions", conn_final
    )

    conn_main.close()
    conn_final.close()

    return users_df, submissions_df, final_submissions_df


def prepare_leaderboard_data(users_df, submissions_df, final_submissions_df):
    """リーダーボード用のデータを準備する"""
    leaderboard_data = []

    for user_id in users_df["user_id"]:
        user_final_submissions = final_submissions_df[
            final_submissions_df["user_id"] == user_id
        ]
        user_submissions = submissions_df[submissions_df["user_id"] == user_id]

        if len(user_final_submissions) == 2:
            leaderboard_data.extend(user_final_submissions.to_dict("records"))
        elif len(user_final_submissions) == 1:
            final_submission = user_final_submissions.iloc[0]
            leaderboard_data.append(final_submission.to_dict())

            other_submissions = user_submissions[
                user_submissions["submission_id"] != final_submission["submission_id"]
            ]
            if len(other_submissions) > 0:
                best_other_submission = other_submissions.loc[
                    other_submissions["public_score"].idxmax()
                ]
                leaderboard_data.append(best_other_submission.to_dict())
        elif len(user_submissions) > 0:
            best_submissions = user_submissions.nlargest(2, "public_score")
            leaderboard_data.extend(best_submissions.to_dict("records"))

    return pd.DataFrame(leaderboard_data)


def create_leaderboard_table(df):
    """リーダーボードテーブルを作成する"""
    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=list(df.columns),
                    fill_color="#FD8E72",
                    align="center",
                    font=dict(color="black", size=16),
                ),
                cells=dict(
                    values=[df[col] for col in df.columns],
                    fill_color=[
                        ["#E6F0FF" if i % 2 == 0 else "white" for i in range(len(df))]
                    ],
                    align="center",
                    font=dict(color="black", size=14),
                ),
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        height=800,
    )

    return fig


def generate_leaderboard():
    users_df, submissions_df, final_submissions_df = fetch_data_from_db()
    leaderboard_df = prepare_leaderboard_data(
        users_df, submissions_df, final_submissions_df
    )

    # ユーザー名を追加
    leaderboard_df = leaderboard_df.merge(
        users_df[["user_id", "username"]], on="user_id", how="left"
    )

    if OPTIMIZATION_DIRECTION == "max":
        leaderboard = (
            leaderboard_df.groupby("user_id")
            .agg({"username": "first", "public_score": "max", "private_score": "max"})
            .reset_index()
        )
        leaderboard = leaderboard.sort_values("private_score", ascending=False)
    else:  # min
        leaderboard = (
            leaderboard_df.groupby("user_id")
            .agg({"username": "first", "public_score": "min", "private_score": "min"})
            .reset_index()
        )
        leaderboard = leaderboard.sort_values("private_score", ascending=True)

    leaderboard["順位"] = range(1, len(leaderboard) + 1)
    leaderboard = leaderboard.rename(
        columns={
            "username": "ユーザー",
            "public_score": "Public スコア",
            "private_score": "Private スコア",
        }
    )
    leaderboard["Public スコア"] = leaderboard["Public スコア"].round(3)
    leaderboard["Private スコア"] = leaderboard["Private スコア"].round(3)
    leaderboard = leaderboard[["順位", "ユーザー", "Private スコア", "Public スコア"]]

    return leaderboard


def display_leaderboard():
    check_admin()  # admin権限チェック

    st.title("🏆 リーダーボード   🏆")
    st.write(
        f"現在のPrivate Scoreに基づくリーダーボードです。(最適化方向: {'最大化' if OPTIMIZATION_DIRECTION == 'max' else '最小化'})"
    )

    leaderboard = generate_leaderboard()

    items_per_page = 20
    num_pages = (len(leaderboard) - 1) // items_per_page + 1

    page = 1
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    fig = create_leaderboard_table(leaderboard.iloc[start_idx:end_idx])
    leaderboard_chart = st.plotly_chart(fig, use_container_width=True)

    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input("ページ", min_value=1, max_value=num_pages, value=1)
        st.write(f"ページ {page}/{num_pages}")

    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    fig = create_leaderboard_table(leaderboard.iloc[start_idx:end_idx])
    leaderboard_chart.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    display_leaderboard()
