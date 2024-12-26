import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from streamlit import session_state as ss

from app.nav import MenuButtons
from app.pages.account import get_roles

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env ファイルから環境変数をロード
load_dotenv(".env")
COMPETITION_ANSWER_COLUMN = os.environ.get("COMPETITION_ANSWER_COLUMN")
SUBMITTION_DB_PATH = "./database/submissions.db"
SUBMISSIONS_DIR = "./temp_files/uploaded_submissions"
FINAL_SUBMISSION_DB_PATH = "./database/final_submissions.db"
OPTIMIZATION_DIRECTION = os.environ.get("OPTIMIZATION_DIRECTION", "min").lower()
MAX_SUBMISSIONS = int(os.environ.get("MAX_SUBMISSIONS", 50))  # デフォルト値を50に設定

if "authentication_status" not in ss:
    st.switch_page("./pages/account.py")


# メトリックを計算する関数（この例ではMSEを使用）
def calculate_metric(predictions, actual):
    return ((predictions - actual) ** 2).mean()


def create_table():
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS submissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  team TEXT,
                  filename TEXT,
                  public_score REAL,
                  private_score REAL,
                  timestamp TEXT)""")
    conn.commit()
    conn.close()


def create_final_submission_table():
    conn = sqlite3.connect(FINAL_SUBMISSION_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS final_submissions
    (id INTEGER PRIMARY KEY,
     username TEXT,
     team TEXT,
     filename TEXT,
     public_score REAL,
     private_score REAL,
     timestamp TEXT)
    """)
    conn.commit()
    conn.close()


def insert_submission(username, team, public_score, private_score, timestamp, filename):
    query = """
    INSERT INTO submissions (username, team, filename, public_score, private_score, timestamp)
    VALUES (:username, :team, :filename, :public_score, :private_score, :timestamp)
    """
    data = {
        "username": username,
        "team": team,
        "filename": filename,
        "public_score": public_score,
        "private_score": private_score,
        "timestamp": timestamp,
    }

    try:
        with sqlite3.connect(SUBMITTION_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, data)
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return False


def get_best_scores():
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()

    agg_func = "MIN" if OPTIMIZATION_DIRECTION == "min" else "MAX"

    # ユーザーごとの最高スコア
    c.execute(f"""
        SELECT username, {agg_func}(public_score) as best_public_score
        FROM submissions
        GROUP BY username
        ORDER BY best_public_score {'ASC' if OPTIMIZATION_DIRECTION == 'min' else 'DESC'}
    """)
    user_leaderboard = pd.DataFrame(
        c.fetchall(), columns=["username", "best_public_score"]
    )

    # チームごとの最高スコア
    c.execute(f"""
        SELECT team, {agg_func}(public_score) as best_public_score
        FROM submissions
        GROUP BY team
        ORDER BY best_public_score {'ASC' if OPTIMIZATION_DIRECTION == 'min' else 'DESC'}
    """)
    team_leaderboard = pd.DataFrame(c.fetchall(), columns=["team", "best_public_score"])

    conn.close()
    return user_leaderboard, team_leaderboard


def create_user_directory(username):
    """ユーザーごとのディレクトリを作成する"""
    user_dir = os.path.join(SUBMISSIONS_DIR, username)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir


def save_submitted_csv(file, username, filename, timestamp):
    """提出されたCSVファイルを保存する"""
    user_dir = create_user_directory(username)
    save_filename = f"FILENAME_{filename}_TIMESTAMP_{timestamp}.csv"
    file_path = os.path.join(user_dir, save_filename)

    with open(file_path, "wb") as f:
        f.write(file.getvalue())

    return file_path


def get_submission_count(username, date):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT COUNT(*) FROM submissions
        WHERE username = ? AND DATE(timestamp) = DATE(?)
    """,
        (username, date),
    )
    count = c.fetchone()[0]
    conn.close()
    return count


def get_public_private_score(uploaded_submit_csv):
    # CSVファイルの読み込み
    submit_df = pd.read_csv(uploaded_submit_csv)

    # 実際のデータ（この例では、これも提供されると仮定）
    test_df = pd.read_csv("./competition/test.csv")

    # Public scoreとPrivate scoreの計算
    public_mask = test_df["is_public"] == 1
    private_mask = test_df["is_public"] == 0

    public_score = calculate_metric(
        submit_df.loc[public_mask, COMPETITION_ANSWER_COLUMN],
        test_df.loc[public_mask, COMPETITION_ANSWER_COLUMN],
    )
    private_score = calculate_metric(
        submit_df.loc[private_mask, COMPETITION_ANSWER_COLUMN],
        test_df.loc[private_mask, COMPETITION_ANSWER_COLUMN],
    )
    return public_score, private_score


def select_final_submissions(username):
    # 元のデータベースから提出を取得
    conn_original = sqlite3.connect(SUBMITTION_DB_PATH)
    query = """
    SELECT * FROM submissions 
    WHERE username = ? 
    ORDER BY public_score DESC, timestamp DESC
    LIMIT 2
    """
    final_submissions = pd.read_sql_query(query, conn_original, params=(username,))
    conn_original.close()

    # 最終提出を新しいデータベースに保存
    conn_final = sqlite3.connect(FINAL_SUBMISSION_DB_PATH)
    cursor = conn_final.cursor()

    # 既存の最終提出を削除
    cursor.execute("DELETE FROM final_submissions WHERE username = ?", (username,))

    # 新しい最終提出を挿入
    for _, submission in final_submissions.iterrows():
        cursor.execute(
            """
        INSERT INTO final_submissions 
        (username, team, public_score, private_score, timestamp) 
        VALUES (?, ?, ?, ?, ?)
        """,
            (
                submission["username"],
                submission["team"],
                submission["public_score"],
                submission["private_score"],
                submission["timestamp"],
            ),
        )

    conn_final.commit()
    conn_final.close()


def get_user_submissions(username):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    query = """
    SELECT * FROM submissions 
    WHERE username = ? 
    ORDER BY public_score DESC, timestamp DESC
    """
    submissions = pd.read_sql_query(query, conn, params=(username,))
    conn.close()
    return submissions


def update_final_submissions(username, selected_ids):
    conn_original = sqlite3.connect(SUBMITTION_DB_PATH)
    conn_final = sqlite3.connect(FINAL_SUBMISSION_DB_PATH)

    # 選択された提出を取得
    query = "SELECT * FROM submissions WHERE id IN ({})".format(
        ",".join(["?"] * len(selected_ids))
    )
    final_submissions = pd.read_sql_query(query, conn_original, params=selected_ids)

    cursor = conn_final.cursor()

    # 既存の最終提出を削除
    cursor.execute("DELETE FROM final_submissions WHERE username = ?", (username,))

    # 新しい最終提出を挿入
    for _, submission in final_submissions.iterrows():
        cursor.execute(
            """
        INSERT INTO final_submissions 
        (id, username, team, public_score, private_score, timestamp, filename) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                submission["id"],
                submission["username"],
                submission["team"],
                submission["public_score"],
                submission["private_score"],
                submission["timestamp"],
                submission["filename"],
            ),
        )

    conn_final.commit()
    conn_original.close()
    conn_final.close()


def show_final_submission_selection_and_display(username):
    st.subheader("最終提出の選択")

    submissions = get_user_submissions(username)

    if len(submissions) > 0:
        # IDの降順でソート
        submissions = submissions.sort_values("id", ascending=False)

        st.write("最大2つの提出を選択してください。")
        selected_submissions = st.multiselect(
            "最終提出として選択する提出を選んでください：",
            options=submissions.index,
            format_func=lambda x: f"ID: {submissions.loc[x, 'id']} - Score: {submissions.loc[x, 'public_score']} - Time: {submissions.loc[x, 'timestamp']} - File: {submissions.loc[x, 'filename']}",
            max_selections=2,
        )

        if st.button("最終提出を更新"):
            if len(selected_submissions) > 0:
                selected_ids = submissions.loc[selected_submissions, "id"].tolist()
                update_final_submissions(username, selected_ids)
                st.success("最終提出が更新されました。")
            else:
                st.warning("最終提出として少なくとも1つの提出を選択してください。")
    else:
        st.info("まだ提出がありません。")

    # 最終提出の表示
    st.subheader("現在の最終提出")
    conn = sqlite3.connect(FINAL_SUBMISSION_DB_PATH)
    final_submissions = pd.read_sql_query(
        "SELECT * FROM final_submissions WHERE username = ? ORDER BY id DESC",
        conn,
        params=(username,),
    )
    conn.close()

    if len(final_submissions) > 0:
        if os.environ.get("VISIBLE_PRIVATE_SCORE", "False").lower() == "true":
            final_submissions = final_submissions.drop("private_score", axis=1)
        st.dataframe(final_submissions)
    else:
        st.info("最終提出はまだ選択されていません。")


def setup_page():
    MenuButtons(get_roles())
    st.title("提出ページ")
    st.write("ここで結果を提出できます。")
    create_table()
    create_final_submission_table()


def get_best_public_score(username):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute(
        f"""
        SELECT {'MIN' if OPTIMIZATION_DIRECTION == 'min' else 'MAX'}(public_score) FROM submissions
        WHERE username = ?
    """,
        (username,),
    )
    best_score = c.fetchone()[0]
    conn.close()
    return (
        best_score
        if best_score is not None
        else (float("inf") if OPTIMIZATION_DIRECTION == "min" else float("-inf"))
    )


def handle_file_upload(username, team):
    submission_count = get_total_submission_count(username)
    st.info(f"現在の提出回数: {submission_count}/{MAX_SUBMISSIONS}")

    if "form_submitted" not in ss:
        ss.form_submitted = False

    if not ss.form_submitted:
        with st.form(key="upload_form"):
            uploaded_submit_csv = st.file_uploader(
                "結果ファイルをアップロード", type=["csv"]
            )
            submit_button = st.form_submit_button(label="提出")

        if submit_button and uploaded_submit_csv is not None:
            process_submission(username, team, uploaded_submit_csv)
    else:
        show_new_submission_button()


def get_total_submission_count(username):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT COUNT(*) FROM submissions
        WHERE username = ?
    """,
        (username,),
    )
    count = c.fetchone()[0]
    conn.close()
    return count


def process_submission(username, team, uploaded_submit_csv):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.success("ファイルがアップロードされました！")

    public_score, private_score = get_public_private_score(uploaded_submit_csv)
    st.write(f"Public Score: {public_score}")
    st.write(f"Private Score: {private_score}")

    filename = uploaded_submit_csv.name
    logger.info(f"Uploaded file name: {filename}")
    save_submitted_csv(uploaded_submit_csv, username, filename, timestamp)

    submission_count = get_total_submission_count(username)
    if submission_count >= MAX_SUBMISSIONS:
        st.error(
            f"提出回数の上限（{MAX_SUBMISSIONS}回）に達しました。これ以上の提出はできません。"
        )
    else:
        best_score = get_best_public_score(username)
        save_submission_to_database(
            username, team, public_score, private_score, timestamp, filename
        )

        if (OPTIMIZATION_DIRECTION == "min" and public_score < best_score) or (
            OPTIMIZATION_DIRECTION == "max" and public_score > best_score
        ):
            st.balloons()
            st.success(
                f"🎉 おめでとうございます！ 🎉\n新記録です！ 過去最高のPublic Scoreを更新しました！\n"
                f"前回のベストスコア: {best_score:.4f} → 新しいベストスコア: {public_score:.4f}"
            )
        elif submission_count == 0:
            st.info(
                "最初の提出おめでとうございます！これからどんどん改善していきましょう。"
            )
        else:
            st.info(
                f"現在のベストPublic Score: {best_score:.4f}\n"
                f"頑張って改善を続けましょう！"
            )


def save_submission_to_database(
    username, team, public_score, private_score, timestamp, filename
):
    success = insert_submission(
        username, team, public_score, private_score, timestamp, filename
    )
    if success:
        st.info("結果が提出されました。データベースへスコア登録されました。")
        ss.form_submitted = True
    else:
        st.error("データベースへの登録中にエラーが発生しました。")


def show_new_submission_button():
    st.success(
        "フォームが正常に送信されました。新しい提出を行うには、以下のボタンをクリックしてください。"
    )
    if st.button("新しい提出を行う"):
        ss.form_submitted = False
        st.rerun()


def display_submission_history():
    st.subheader("提出履歴")
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    history = pd.read_sql_query("SELECT * FROM submissions", conn)
    conn.close()

    if os.environ.get("VISIBLE_PRIVATE_SCORE", "False").lower() == "true":
        logger.info("Private score is invisible.")
        history = history.drop("private_score", axis=1)

    st.dataframe(history)


def show():
    setup_page()
    username = ss.username
    team = "None_Team"  # st.text_input("チーム名")

    handle_file_upload(username, team)
    display_submission_history()
    show_final_submission_selection_and_display(username)


if __name__ == "__main__":
    show()
