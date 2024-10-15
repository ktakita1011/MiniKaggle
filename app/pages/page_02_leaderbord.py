import streamlit as st

from app.nav import MenuButtons
from app.pages.account import get_roles

SUBMITTION_DB_PATH = "./data/submissions.db"


def show():
    MenuButtons(get_roles())
    st.title("リーダーボード")
    st.write("ここにリーダーボードが表示されます。")

    # サンプルのリーダーボードデータ
    data = {
        "順位": [1, 2, 3],
        "ユーザー": ["Alice", "Bob", "Charlie"],
        "スコア": [100, 95, 90],
    }
    st.table(data)


if __name__ == "__main__":
    show()
