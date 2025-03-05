import os
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml
from dotenv import load_dotenv

from app.nav import MenuButtons
from app.pages.account import get_roles

SUBMITTION_DB_PATH = "./database/submissions.db"

with open("competition_setting.yaml", "r") as file:
    config = yaml.safe_load(file)
OPTIMIZATION_DIRECTION = config["competition"]["optimization_direction"]


def create_leaderboard_table(df):
    # 順位とSubmit回数の最大値を取得
    max_rank = df["順位"].max()
    max_submit = df["Submit回数"].max()

    # 列幅を動的に設定
    rank_width = max(60, len(str(max_rank)) * 10)  # 最小幅60、文字数に応じて増加
    submit_width = max(60, len(str(max_submit)) * 10)  # 最小幅60、文字数に応じて増加
    team_width = 200  # チーム名用の固定幅
    score_width = 100  # スコア用の固定幅

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
                columnwidth=[
                    rank_width,
                    team_width,
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


def get_leaderboard():
    conn = sqlite3.connect(SUBMITTION_DB_PATH)

    if OPTIMIZATION_DIRECTION == "max":
        query = """
        WITH user_best_scores AS (
            SELECT 
                s.user_id,
                MAX(s.public_score) as best_score,
                COUNT(*) as submit_count
            FROM submissions s
            GROUP BY s.user_id
        )
        SELECT 
            tu.team_name,
            MAX(ubs.best_score) as best_score,
            COUNT(DISTINCT tu.user_id) as member_count,
            SUM(ubs.submit_count) as submit_count,
            GROUP_CONCAT(u.username, ', ') as team_members
        FROM team_users tu
        JOIN users u ON tu.user_id = u.user_id
        JOIN user_best_scores ubs ON u.user_id = ubs.user_id
        GROUP BY tu.team_name
        HAVING best_score IS NOT NULL
        ORDER BY best_score DESC
        """
    else:  # min
        query = """
        WITH user_best_scores AS (
            SELECT 
                s.user_id,
                MIN(s.public_score) as best_score,
                COUNT(*) as submit_count
            FROM submissions s
            GROUP BY s.user_id
        )
        SELECT 
            tu.team_name,
            MIN(ubs.best_score) as best_score,
            COUNT(DISTINCT tu.user_id) as member_count,
            SUM(ubs.submit_count) as submit_count,
            GROUP_CONCAT(u.username, ', ') as team_members
        FROM team_users tu
        JOIN users u ON tu.user_id = u.user_id
        JOIN user_best_scores ubs ON u.user_id = ubs.user_id
        GROUP BY tu.team_name
        HAVING best_score IS NOT NULL
        ORDER BY best_score ASC
        """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # 順位を付ける
    df["順位"] = range(1, len(df) + 1)

    # カラム名を変更
    df = df.rename(
        columns={
            "team_name": "チーム名",
            "best_score": "Public スコア",
            "member_count": "メンバー数",
            "submit_count": "Submit回数",
            "team_members": "チームメンバー",
        }
    )

    # スコアを小数点以下4桁に丸める
    df["Public スコア"] = df["Public スコア"].round(3)
    # カラムの順序を変更
    df = df[["順位", "チーム名", "Public スコア", "Submit回数"]]

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
