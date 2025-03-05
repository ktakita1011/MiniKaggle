import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import yaml
from streamlit import session_state as ss

from app.nav import MenuButtons
from app.pages.account import get_roles
from app.src.database import (
    create_tables,
    get_or_create_team_id,
    get_or_create_user_id,
    get_team_name,
    get_total_submission_count,
    get_user_submissions,
    insert_submission,
    update_final_submissions,
)
from app.src.logger_config import get_cached_logger

logger = get_cached_logger(__name__)

with open("competition_setting.yaml", "r") as file:
    config = yaml.safe_load(file)

# max_submissionsの値を取得する
max_submissions = config["competition"]["max_submissions"]
COMPETITION_ANSWER_COLUMN = "全体平面度"  # os.environ.get("COMPETITION_ANSWER_COLUMN")
SUBMISSIONS_DIR = "./temp_files/uploaded_submissions"
SUBMITTION_DB_PATH = "./database/submissions.db"
FINAL_SUBMISSION_DB_PATH = "./database/final_submissions.db"
OPTIMIZATION_DIRECTION = config["competition"]["optimization_direction"]
MAX_SUBMISSIONS = config["competition"]["max_submissions"]  # デフォルト値を50に設定
if config["competition"]["stop_final_submission_select"]:
    MAX_SUBMISSIONS = 9999
COMPETITION_TEST_CSV_PATH = "./competition/test.csv"
STOP_FINAL_SUBMISSION_SELECT = config["competition"]["stop_final_submission_select"]

if "authentication_status" not in ss:
    st.switch_page("./pages/account.py")


# メトリックを計算する関数（この例ではMSEを使用）
def calculate_metric(predictions, actual):
    if config["competition"]["metric"] == "rmse":
        mse = ((predictions - actual) ** 2).mean()
        return np.sqrt(mse)
    elif config["competition"]["metric"] == "mae":
        return np.abs(predictions - actual).mean()
    else:
        raise ValueError("Unsupported metric specified in the configuration.")


def create_user_directory(user_id):
    """ユーザーごとのディレクトリを作成する"""
    user_dir = os.path.join(SUBMISSIONS_DIR, str(user_id))
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir


def save_submitted_csv(file, user_id, filename, timestamp):
    """提出されたCSVファイルを保存する"""
    user_dir = create_user_directory(user_id)
    save_filename = f"TIMESTAMP_{timestamp}_FILENAME_{filename}_USER_ID{user_id}.csv"
    file_path = os.path.join(user_dir, save_filename)

    with open(file_path, "wb") as f:
        f.write(file.getvalue())

    return file_path


def get_public_private_score(uploaded_submit_csv):
    # CSVファイルの読み込み
    submit_df = pd.read_csv(uploaded_submit_csv)

    # 実際のデータ（この例では、これも提供されると仮定）
    test_df = pd.read_csv(COMPETITION_TEST_CSV_PATH)

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


def show_final_submission_selection_and_display(user_id):
    def format_submission(index):
        submission = submissions.loc[index]
        return (
            f"ID: {submission['user_submission_id']} - "
            f"Time: {submission['timestamp']} - "
            f"File: {submission['filename']} - "
            f"Score: {round(submission['public_score'], 4)}"
        )

    submissions = get_user_submissions(user_id)
    if STOP_FINAL_SUBMISSION_SELECT:
        st.warning("最終提出の選択は現在停止されています。")
    elif len(submissions) > 0:
        st.subheader("最終提出の選択")
        # IDの降順でソート
        submissions = submissions.sort_values("submission_id", ascending=False)

        st.write("最大2つの提出を選択してください。")
        selected_submissions = st.multiselect(
            "最終提出として選択する提出を選んでください：",
            options=submissions.index,
            format_func=format_submission,
            max_selections=2,
        )

        # 空白追加 マルチセレクトの表示が最終提出を更新の表示と被るため。
        for _ in range(5):
            st.write("")

        if st.button("最終提出を更新"):
            if len(selected_submissions) > 0:
                selected_ids = submissions.loc[
                    selected_submissions, "submission_id"
                ].tolist()
                update_final_submissions(user_id, selected_ids)
                st.success("最終提出が更新されました。")
            else:
                st.warning("最終提出として少なくとも1つの提出を選択してください。")
    else:
        st.info("まだ提出がありません。")

    # 最終提出の表示
    st.subheader("現在の最終提出")
    conn_final = sqlite3.connect(FINAL_SUBMISSION_DB_PATH)

    query = """
        SELECT user_submission_id, timestamp, filename, public_score
        FROM final_submissions
        WHERE user_id = ?
        ORDER BY timestamp DESC
    """
    final_submissions = pd.read_sql_query(query, conn_final, params=(user_id,))

    conn_final.close()

    if not final_submissions.empty:
        st.dataframe(final_submissions)
    else:
        st.info("最終提出が選択されていません。")


def setup_page():
    MenuButtons(get_roles())
    st.title("提出ページ")
    st.write("ここで結果を提出できます。")
    create_tables()


def get_best_public_score(user_id):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute(
        f"""
        SELECT {"MIN" if OPTIMIZATION_DIRECTION == "min" else "MAX"}(public_score) FROM submissions
        WHERE user_id = ?
    """,
        (user_id,),
    )
    best_score = c.fetchone()[0]
    conn.close()
    return (
        best_score
        if best_score is not None
        else (float("inf") if OPTIMIZATION_DIRECTION == "min" else float("-inf"))
    )


def handle_file_upload(user_id, team_name):
    submission_count = get_total_submission_count(user_id)
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
            process_submission(user_id, team_name, uploaded_submit_csv)
    else:
        show_new_submission_button()


def process_submission(user_id, team_name, uploaded_submit_csv):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.success("ファイルがアップロードされました！")

    public_score, private_score = get_public_private_score(uploaded_submit_csv)

    filename = uploaded_submit_csv.name
    logger.info(f"Uploaded file name: {filename}")
    save_submitted_csv(uploaded_submit_csv, user_id, filename, timestamp)

    submission_count = get_total_submission_count(user_id)

    if submission_count >= MAX_SUBMISSIONS:
        st.error(
            f"提出回数の上限（{MAX_SUBMISSIONS}回）に達しました。これ以上の提出はできません。"
        )
    else:
        best_score = get_best_public_score(user_id)
        team_id = get_or_create_team_id(team_name)
        save_submission_to_database(
            user_id, team_id, public_score, private_score, timestamp, filename
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
            st.success(
                "最初の提出おめでとうございます！これからどんどん改善していきましょう。"
            )
        else:
            st.success(
                f"提出したPublic Score: {public_score:.4f}\n"
                f"頑張って改善を続けましょう！"
            )


def save_submission_to_database(
    user_id, team_id, public_score, private_score, timestamp, filename
):
    success = insert_submission(
        user_id, team_id, public_score, private_score, timestamp, filename
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


def display_submission_history(user_id):
    st.subheader("提出履歴")
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    query = """
        SELECT s.user_id, s.timestamp, s.filename, u.username, s.public_score, s.private_score
        FROM submissions s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.user_id = ?
        ORDER BY s.timestamp DESC
    """
    # もしチーム名も表示した場合はselect文に, t.team_name を追加する
    history = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()

    if not STOP_FINAL_SUBMISSION_SELECT:
        logger.info("Private score is invisible.")
        history = history.drop("private_score", axis=1)

    if not history.empty:
        st.dataframe(history, hide_index=True)
    else:
        st.info("まだ提出履歴がありません。")


def show():
    setup_page()
    user_id = get_or_create_user_id(ss.username)
    team_id = get_or_create_team_id(user_id)
    team_name = get_team_name(team_id)

    handle_file_upload(user_id, team_name)
    display_submission_history(user_id)
    show_final_submission_selection_and_display(user_id)


if __name__ == "__main__":
    show()
