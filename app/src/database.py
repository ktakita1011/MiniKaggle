import logging
import os
import sqlite3

import pandas as pd
from dotenv import load_dotenv

from app.src.logger_config import get_logger

load_dotenv(".env")
logger = get_logger(__name__)

FINAL_SUBMISSION_DB_PATH = "./database/final_submissions.db"
SUBMITTION_DB_PATH = "./database/submissions.db"
OPTIMIZATION_DIRECTION = os.environ.get("OPTIMIZATION_DIRECTION", "min").lower()


def create_tables():
    # メイン提出データベースのテーブル作成
    conn_main = sqlite3.connect(SUBMITTION_DB_PATH)
    c_main = conn_main.cursor()

    # 最終提出データベースのテーブル作成
    conn_final = sqlite3.connect(FINAL_SUBMISSION_DB_PATH)
    c_final = conn_final.cursor()

    # Users テーブル (メインデータベースのみ)
    c_main.execute("""CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE)""")

    # Teams テーブル (メインデータベースのみ)
    c_main.execute("""CREATE TABLE IF NOT EXISTS teams
                     (team_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      team_name TEXT UNIQUE)""")

    # Submissions テーブル (メインデータベースのみ)
    c_main.execute("""CREATE TABLE IF NOT EXISTS submissions
                     (submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      team_id INTEGER,
                      filename TEXT,
                      public_score REAL,
                      private_score REAL,
                      timestamp TEXT,
                      user_submission_id INTEGER,
                      FOREIGN KEY (user_id) REFERENCES users(user_id),
                      FOREIGN KEY (team_id) REFERENCES teams(team_id))""")

    # Final Submissions テーブル (最終提出データベースのみ)
    c_final.execute("""CREATE TABLE IF NOT EXISTS final_submissions
                     (submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      team_id INTEGER,
                      filename TEXT,
                      public_score REAL,
                      private_score REAL,
                      timestamp TEXT,
                      user_submission_id INTEGER)""")

    conn_main.commit()
    conn_final.commit()
    conn_main.close()
    conn_final.close()


# def create_final_submission_table():
#     conn = sqlite3.connect(FINAL_SUBMISSION_DB_PATH)
#     cursor = conn.cursor()
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS final_submissions
#     (submission_id INTEGER PRIMARY KEY,
#      user_id INTEGER,
#      team_id INTEGER,
#      filename TEXT,
#      public_score REAL,
#      private_score REAL,
#      timestamp TEXT,
#      FOREIGN KEY (user_id) REFERENCES users(user_id),
#      FOREIGN KEY (team_id) REFERENCES teams(team_id))
#     """)
#     conn.commit()
#     conn.close()


def get_or_create_user_id(username):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    if result:
        user_id = result[0]
    else:
        c.execute("INSERT INTO users (username) VALUES (?)", (username,))
        user_id = c.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_or_create_team_id(team_name):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT team_id FROM teams WHERE team_name = ?", (team_name,))
    result = c.fetchone()
    if result:
        team_id = result[0]
    else:
        c.execute("INSERT INTO teams (team_name) VALUES (?)", (team_name,))
        team_id = c.lastrowid
    conn.commit()
    conn.close()
    return team_id


def insert_submission(
    user_id, team_id, public_score, private_score, timestamp, filename
):
    query = """
    INSERT INTO submissions (user_id, team_id, filename, public_score, private_score, timestamp, user_submission_id)
    VALUES (:user_id, :team_id, :filename, :public_score, :private_score, :timestamp,
            (SELECT COALESCE(MAX(user_submission_id), 0) + 1 FROM submissions WHERE user_id = :user_id))
    """
    data = {
        "user_id": user_id,
        "team_id": team_id,
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
        SELECT users.username, {agg_func}(submissions.public_score) as best_public_score
        FROM submissions
        JOIN users ON submissions.user_id = users.user_id
        GROUP BY users.user_id
        ORDER BY best_public_score {'ASC' if OPTIMIZATION_DIRECTION == 'min' else 'DESC'}
    """)
    user_leaderboard = pd.DataFrame(
        c.fetchall(), columns=["username", "best_public_score"]
    )

    # チームごとの最高スコア
    c.execute(f"""
        SELECT teams.team_name, {agg_func}(submissions.public_score) as best_public_score
        FROM submissions
        JOIN teams ON submissions.team_id = teams.team_id
        GROUP BY teams.team_id
        ORDER BY best_public_score {'ASC' if OPTIMIZATION_DIRECTION == 'min' else 'DESC'}
    """)
    team_leaderboard = pd.DataFrame(c.fetchall(), columns=["team", "best_public_score"])

    conn.close()
    return user_leaderboard, team_leaderboard


def get_submission_count(user_id, date):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT COUNT(*) FROM submissions
        WHERE user_id = ? AND DATE(timestamp) = DATE(?)
    """,
        (user_id, date),
    )
    count = c.fetchone()[0]
    conn.close()
    return count


def select_final_submissions(user_id, limit=2):
    conn_original = sqlite3.connect(SUBMITTION_DB_PATH)
    query = """
    SELECT submissions.*, users.username, teams.team_name 
    FROM submissions 
    JOIN users ON submissions.user_id = users.user_id
    JOIN teams ON submissions.team_id = teams.team_id
    WHERE submissions.user_id = ? 
    ORDER BY public_score DESC, timestamp DESC
    LIMIT ?
    """
    final_submissions = pd.read_sql_query(query, conn_original, params=(user_id, limit))
    conn_original.close()

    conn_final = sqlite3.connect(FINAL_SUBMISSION_DB_PATH)
    cursor = conn_final.cursor()

    cursor.execute("DELETE FROM final_submissions WHERE user_id = ?", (user_id,))

    for _, submission in final_submissions.iterrows():
        cursor.execute(
            """
        INSERT INTO final_submissions 
        (user_id, team_id, filename, public_score, private_score, timestamp, user_submission_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                submission["user_id"],
                submission["team_id"],
                submission["filename"],
                submission["public_score"],
                submission["private_score"],
                submission["timestamp"],
                submission["user_submission_id"],
            ),
        )

    conn_final.commit()
    conn_final.close()

    return final_submissions


def get_user_submissions(user_id):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    query = """
    SELECT s.submission_id, s.user_id, s.team_id, s.filename, s.public_score, s.private_score, s.timestamp,
           u.username, t.team_name, s.user_submission_id
    FROM submissions s
    JOIN users u ON s.user_id = u.user_id
    JOIN teams t ON s.team_id = t.team_id
    WHERE s.user_id = ? 
    ORDER BY s.public_score DESC, s.timestamp DESC
    """
    submissions = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    return submissions


def update_final_submissions(user_id, selected_ids):
    conn_original = sqlite3.connect(SUBMITTION_DB_PATH)
    conn_final = sqlite3.connect(FINAL_SUBMISSION_DB_PATH)

    query = """
    SELECT submissions.*, users.username, teams.team_name 
    FROM submissions 
    JOIN users ON submissions.user_id = users.user_id
    JOIN teams ON submissions.team_id = teams.team_id
    WHERE submissions.submission_id IN ({})
    """.format(",".join(["?"] * len(selected_ids)))
    final_submissions = pd.read_sql_query(query, conn_original, params=selected_ids)

    cursor = conn_final.cursor()

    cursor.execute("DELETE FROM final_submissions WHERE user_id = ?", (user_id,))

    for _, submission in final_submissions.iterrows():
        cursor.execute(
            """
        INSERT INTO final_submissions 
        (submission_id, user_id, team_id, filename, public_score, private_score, timestamp, user_submission_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                submission["submission_id"],
                submission["user_id"],
                submission["team_id"],
                submission["filename"],
                submission["public_score"],
                submission["private_score"],
                submission["timestamp"],
                submission["user_submission_id"],
            ),
        )

    conn_final.commit()
    conn_original.close()
    conn_final.close()


def get_total_submission_count(user_id):
    conn = sqlite3.connect(SUBMITTION_DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT COUNT(*) FROM submissions
        WHERE user_id = ?
    """,
        (user_id,),
    )
    count = c.fetchone()[0]
    conn.close()
    return count
