import sqlite3

import streamlit as st
from streamlit import session_state as ss

from app.nav import MenuButtons
from app.pages.account import get_roles
from app.src.database import get_or_create_user_id

# データベースのパス
SUBMITTION_DB_PATH = "./database/submissions.db"


# ユーザーのチーム情報を取得する関数
def get_user_team(user_id):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT team_id, team_name 
        FROM team_users
        WHERE user_id = ?
    """,
        (user_id,),
    )
    team = c.fetchone()
    conn.close()
    return team


# チーム名を更新する関数
def update_team_name(team_id, new_name):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "UPDATE team_users SET team_name = ? WHERE team_id = ?", (new_name, team_id)
        )
        conn.commit()
        success = True
    except sqlite3.Error:
        success = False
    finally:
        conn.close()
    return success


# 新しいチームを作成する関数
def create_new_team(user_id, team_name):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO team_users (team_name, user_id) VALUES (?, ?)",
        (team_name, user_id),
    )
    team_id = c.lastrowid
    conn.commit()
    conn.close()
    return team_id


# Streamlitアプリケーション
def show():
    MenuButtons(get_roles())
    st.title("チーム名変更")

    # ユーザーIDを取得
    user_id = get_or_create_user_id(ss.username)

    # ユーザーのチーム情報を取得
    team = get_user_team(user_id)

    if team:
        team_id, current_team_name = team
    else:
        # ユーザーがチームに所属していない場合、新しいチームを作成
        current_team_name = ss.username
        team_id = create_new_team(user_id, current_team_name)
        st.info(f"新しいチーム '{current_team_name}' を作成しました。")

    # 現在のチーム名を表示
    if "team_name" not in ss:
        ss.team_name = current_team_name
    st.write(f"現在のチーム名: {ss.team_name}")

    # 新しいチーム名の入力
    new_team_name = st.text_input("新しいチーム名", value=ss.team_name)

    # 更新ボタン
    if st.button("チーム名を更新"):
        if new_team_name and new_team_name != ss.team_name:
            success = update_team_name(team_id, new_team_name)
            if success:
                st.success(
                    f"チーム名を '{ss.team_name}' から '{new_team_name}' に更新しました。"
                )
                # セッション状態を更新して、再読み込み後も新しいチーム名が表示されるようにする
                ss.team_name = new_team_name
            else:
                st.error(
                    "チーム名の更新中にエラーが発生しました。もう一度お試しください。"
                )
        else:
            st.warning("チーム名が変更されていないか、新しい名前が入力されていません。")


if __name__ == "__main__":
    show()
