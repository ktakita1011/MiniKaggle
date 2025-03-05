import sqlite3

import polars as pl
import streamlit as st


# データベースから全ユーザーを取得する関数
def get_all_users():
    conn = sqlite3.connect("./database/users.db")
    c = conn.cursor()
    c.execute("SELECT username, email FROM users")
    users = c.fetchall()
    conn.close()
    return users


# Streamlitアプリケーション
def show():
    st.title("登録ユーザー一覧")

    # データベースからユーザー情報を取得
    users = get_all_users()

    if users:
        # ユーザー情報をPolars DataFrameに変換
        df = pl.DataFrame(
            {
                "ユーザー名": [user[0] for user in users],
                "メールアドレス": [user[1] for user in users],
            }
        )

        # ユーザー情報をテーブルとして表示
        st.write("登録されているユーザー:")
        st.dataframe(df)
    else:
        st.write("登録されているユーザーはいません。")


if __name__ == "__main__":
    show()
