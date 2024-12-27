import streamlit as st
from streamlit import session_state as ss

# アプリケーションの設定
st.set_page_config(
    page_title="MiniKaggleCompetition",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.nav import MenuButtons
from app.pages.account import get_roles
from app.src.database import create_tables

create_tables()

if "authentication_status" not in ss:
    st.switch_page("./pages/account.py")


MenuButtons(get_roles())
st.header("Home page")


# Protected content in home page.
if ss.authentication_status:
    st.write("This content is only accessible for logged in users.")
else:
    st.write("Please log in on login page.")
