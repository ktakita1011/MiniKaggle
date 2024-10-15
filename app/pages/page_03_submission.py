import os
import sqlite3

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from streamlit import session_state as ss

from app.nav import MenuButtons
from app.pages.account import get_roles

# .env ファイルから環境変数をロード
load_dotenv(".env")
SUBMITTION_DB_PATH = "./data/submissions.db"

if "authentication_status" not in ss:
    st.switch_page("./pages/account.py")


# メトリックを計算する関数（この例ではMSEを使用）
def calculate_metric(predictions, actual):
    return ((predictions - actual) ** 2).mean()


def create_table():
    conn = sqlite3.connect("./data/submissions.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS submissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user TEXT,
                  team TEXT,
                  public_score REAL,
                  private_score REAL)""")
    conn.commit()
    conn.close()


def insert_submission(user, team, public_score, private_score):
    conn = sqlite3.connect("./data/submissions.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO submissions (user, team, public_score, private_score) VALUES (?, ?, ?, ?)",
        (user, team, public_score, private_score),
    )
    conn.commit()
    conn.close()


def show():
    MenuButtons(get_roles())
    st.title("提出ページ")
    st.write("ここで結果を提出できます。")

    # データベーステーブルの作成
    create_table()

    # ユーザー情報入力
    user = st.text_input("ユーザー名")
    team = st.text_input("チーム名")

    # ファイルアップロード
    file = st.file_uploader("結果ファイルをアップロード", type=["csv"])

    if file is not None:
        st.success("ファイルがアップロードされました！")

        # CSVファイルの読み込み
        df = pd.read_csv(file)

        # 実際のデータ（この例では、これも提供されると仮定）
        actual_data = pd.read_csv("actual_data.csv")

        # Public scoreとPrivate scoreの計算
        public_mask = actual_data["is_public"] == 1
        private_mask = actual_data["is_public"] == 0

        public_score = calculate_metric(
            df.loc[public_mask, "prediction"], actual_data.loc[public_mask, "actual"]
        )
        private_score = calculate_metric(
            df.loc[private_mask, "prediction"], actual_data.loc[private_mask, "actual"]
        )

        st.write(f"Public Score: {public_score}")
        st.write(f"Private Score: {private_score}")

        if st.button("提出"):
            # データベースに結果を保存
            insert_submission(user, team, public_score, private_score)
            st.info("結果が提出されました")

    # 提出履歴の表示
    st.subheader("提出履歴")
    conn = sqlite3.connect("./data/submissions.db")
    history = pd.read_sql_query("SELECT * FROM submissions", conn)

    # 環境変数に基づいてprivate_scoreを表示/非表示
    if os.environ.get("VISIBLE_PRIVATE_SCORE", "False").lower() != "true":
        history = history.drop("private_score", axis=1)

    st.dataframe(history)
    conn.close()


if __name__ == "__main__":
    show()
