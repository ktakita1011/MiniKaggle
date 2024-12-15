import streamlit as st
from streamlit import session_state as ss

# アプリケーションの設定
st.set_page_config(
    page_title="My Streamlit App",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.nav import MenuButtons
from app.pages.account import get_roles
from app.pages.page_03_submission import create_table

create_table()

# # ログイン済みの場合、メインのアプリ機能を表示
# st.sidebar.title("Navigation")

# if st.sidebar.button("ログアウト"):
#     st.session_state["authentication_status"] = None
#     st.experimental_rerun()

# # ナビゲーション
# page_module = navigation.navigation()

# if page_module:
#     page_module.show()
# else:
#     st.title("Welcome to My Streamlit App")
#     st.write("This is the home page of our application.")
#     # ホームページの内容をここに追加


if "authentication_status" not in ss:
    st.switch_page("./pages/account.py")


MenuButtons(get_roles())
st.header("Home page")


# Protected content in home page.
if ss.authentication_status:
    st.write("This content is only accessible for logged in users.")
else:
    st.write("Please log in on login page.")
