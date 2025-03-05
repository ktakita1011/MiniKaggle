import os
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml
from dotenv import load_dotenv

from app.pages.account import get_roles

SUBMISSION_DB_PATH = "./database/submissions.db"
FINAL_SUBMISSION_DB_PATH = "./database/final_submissions.db"

with open("competition_setting.yaml", "r") as file:
    config = yaml.safe_load(file)
OPTIMIZATION_DIRECTION = config["competition"]["optimization_direction"]


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

    if OPTIMIZATION_DIRECTION == "max":
        compare = lambda x: x.idxmax()
        best_n = lambda df, col, n: df.nlargest(n, col)
    elif OPTIMIZATION_DIRECTION == "min":
        compare = lambda x: x.idxmin()
        best_n = lambda df, col, n: df.nsmallest(n, col)
    else:
        raise ValueError("OPTIMIZATION_DIRECTION must be either 'max' or 'min'")

    for _, user in users_df.iterrows():
        user_id = user["user_id"]
        user_final_submissions = final_submissions_df[
            final_submissions_df["user_id"] == user_id
        ]
        user_submissions = submissions_df[submissions_df["user_id"] == user_id]

        submission_count = len(user_submissions)

        if submission_count == 0:
            continue  # 提出がない場合はスキップ

        if len(user_final_submissions) == 2:
            for submission in user_final_submissions.to_dict("records"):
                submission["submission_count"] = submission_count
                leaderboard_data.append(submission)
        elif len(user_final_submissions) == 1:
            final_submission = user_final_submissions.iloc[0].to_dict()
            final_submission["submission_count"] = submission_count
            leaderboard_data.append(final_submission)

            other_submissions = user_submissions[
                user_submissions["submission_id"] != final_submission["submission_id"]
            ]
            if len(other_submissions) > 0:
                best_other_submission = other_submissions.loc[
                    compare(other_submissions["public_score"])
                ].to_dict()
                best_other_submission["submission_count"] = submission_count
                leaderboard_data.append(best_other_submission)
        else:
            best_submissions = best_n(user_submissions, "public_score", 2)
            for submission in best_submissions.to_dict("records"):
                submission["submission_count"] = submission_count
                leaderboard_data.append(submission)

    return pd.DataFrame(leaderboard_data)


def create_optimized_public_score_leaderboard(users_df, submissions_df):
    """OPTIMIZATION_DIRECTIONに基づいて最適化されたpublic_scoreのリーダーボードを作成する"""
    leaderboard_data = []

    if OPTIMIZATION_DIRECTION == "max":
        compare = lambda df, col: df[col].idxmax()
        sort_ascending = False
        rank_ascending = False
    elif OPTIMIZATION_DIRECTION == "min":
        compare = lambda df, col: df[col].idxmin()
        sort_ascending = True
        rank_ascending = True
    else:
        raise ValueError("OPTIMIZATION_DIRECTION must be either 'max' or 'min'")

    for _, user in users_df.iterrows():
        user_id = user["user_id"]
        user_submissions = submissions_df[submissions_df["user_id"] == user_id]

        submission_count = len(user_submissions)

        if submission_count > 0:
            # 提出がある場合、最適なpublic_scoreを持つものを選ぶ
            best_submission = user_submissions.loc[
                compare(user_submissions, "public_score")
            ].to_dict()
            best_submission["submission_count"] = submission_count
            leaderboard_data.append(best_submission)

    if len(leaderboard_data) == 0:
        print("No submissions found for public_score leaderboard")
        st.warning("No submissions found for public_score leaderboard")
        return pd.DataFrame()
    # public_scoreでソート
    leaderboard_df = (
        pd.DataFrame(leaderboard_data)
        .sort_values("public_score", ascending=sort_ascending)
        .reset_index(drop=True)
    )

    # ランクを追加
    leaderboard_df["rank"] = (
        leaderboard_df["public_score"]
        .rank(method="min", ascending=rank_ascending)
        .astype(int)
    )

    return leaderboard_df


def get_team_name_user_df():
    conn_main = sqlite3.connect(SUBMISSION_DB_PATH)
    c_main = conn_main.cursor()
    c_main.execute("SELECT user_id, team_name FROM team_users")
    team_users_df = pd.DataFrame(c_main.fetchall(), columns=["user_id", "team_name"])
    conn_main.close()
    return team_users_df


def generate_leaderboard():
    users_df, submissions_df, final_submissions_df = fetch_data_from_db()
    team_users_df = get_team_name_user_df()

    leaderboard_df = prepare_leaderboard_data(
        users_df, submissions_df, final_submissions_df
    )
    public_leaderboard_df = create_optimized_public_score_leaderboard(
        users_df=users_df, submissions_df=submissions_df
    )

    # ユーザー名とチーム名を追加
    leaderboard_df = leaderboard_df.merge(
        users_df[["user_id", "username"]], on="user_id", how="left"
    ).merge(team_users_df, on="user_id", how="left")

    if OPTIMIZATION_DIRECTION == "max":
        leaderboard = (
            leaderboard_df.groupby("user_id")
            .agg(
                {
                    "username": "first",
                    "team_name": "first",
                    "public_score": "max",
                    "private_score": "max",
                    "submission_count": "max",
                    "timestamp": "min",  # 最も早いタイムスタンプを取得
                }
            )
            .reset_index()
        )
        leaderboard = leaderboard.sort_values(
            ["private_score", "timestamp"], ascending=[False, True]
        )
    else:  # min
        leaderboard = (
            leaderboard_df.groupby("user_id")
            .agg(
                {
                    "username": "first",
                    "team_name": "first",
                    "public_score": "min",
                    "private_score": "min",
                    "submission_count": "max",
                    "timestamp": "min",  # 最も早いタイムスタンプを取得
                }
            )
            .reset_index()
        )
        leaderboard = leaderboard.sort_values(
            ["private_score", "timestamp"], ascending=[True, True]
        )

    leaderboard["順位"] = range(1, len(leaderboard) + 1)

    # public_leaderboard_dfの順位を取得
    public_ranks = public_leaderboard_df.set_index("user_id")["rank"].to_dict()

    # 順位変動を計算
    leaderboard["public_rank"] = leaderboard["user_id"].map(public_ranks)
    leaderboard["順位変動"] = leaderboard["public_rank"] - leaderboard["順位"]

    leaderboard = leaderboard.rename(
        columns={
            "username": "ユーザー",
            "team_name": "チーム名",
            "public_score": "Public スコア",
            "private_score": "Private スコア",
            "submission_count": "提出回数",
        }
    )
    leaderboard["Public スコア"] = leaderboard["Public スコア"].round(3)
    leaderboard["Private スコア"] = leaderboard["Private スコア"].round(3)
    leaderboard = leaderboard[
        [
            "順位変動",
            "順位",
            "チーム名",
            "Private スコア",
            "Public スコア",
            "提出回数",
        ]
    ]

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


def create_leaderboard_table(df):
    """リーダーボードテーブルを作成する"""

    # 順位変動カラムを最初に移動
    df = df[["順位変動"] + [col for col in df.columns if col != "順位変動"]]

    max_rank = df["順位"].max()

    # 列幅を動的に設定
    rank_width = max(60, len(str(max_rank)) * 10)  # 最小幅60、文字数に応じて増加
    submit_width = 60  # 最小幅60、文字数に応じて増加
    team_width = 200  # チーム名用の固定幅
    score_width = 60  # スコア用の固定幅
    submit_count = 60

    # 順位変動に基づいて色を設定
    rank_change_colors = []
    for change in df["順位変動"]:
        if change > 0:
            rank_change_colors.append("green")
        elif change < 0:
            rank_change_colors.append("red")
        else:
            rank_change_colors.append("black")

    # 順位変動の表示を調整
    rank_change_display = []
    for change in df["順位変動"]:
        if change > 0:
            rank_change_display.append(f"+{change}")
        elif change < 0:
            rank_change_display.append(str(change))
        else:
            rank_change_display.append("-")

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
                    values=[
                        rank_change_display if col == "順位変動" else df[col]
                        for col in df.columns
                    ],
                    fill_color=[
                        ["#E6F0FF" if i % 2 == 0 else "white" for i in range(len(df))]
                    ],
                    align="center",
                    font=dict(
                        color=[rank_change_colors] + ["black"] * (len(df.columns) - 1),
                        size=14,
                    ),
                ),
                columnwidth=[
                    rank_width,
                    rank_width,
                    team_width,
                    score_width,
                    score_width,
                    submit_width,
                ],  # 動的に列幅を設定
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        height=800,
    )

    return fig


if __name__ == "__main__":
    display_leaderboard()
