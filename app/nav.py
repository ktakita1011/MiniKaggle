import streamlit as st
from streamlit import session_state as ss

from app.src.logger_config import get_cached_logger

logger = get_cached_logger(__name__)


def HomeNav():
    st.sidebar.page_link("./main.py", label="Home", icon="🏠")


def LoginNav():
    st.sidebar.page_link("./pages/account.py", label="Account", icon="🔐")


def Page1Nav():
    st.sidebar.page_link("./pages/page_02_leaderbord.py", label="LB", icon="✈️")


def Page2Nav():
    st.sidebar.page_link("./pages/page_03_submission.py", label="submittion", icon="📚")


def PrivateLBPageNav():
    st.sidebar.page_link(
        "./pages/page_04_private_leaderboard.py", label="Private_LB", icon="🔧"
    )


def MenuButtons(user_roles=None):
    if user_roles is None:
        user_roles = {}

    if "authentication_status" not in ss:
        ss.authentication_status = False

    # Always show the home and login navigators.
    HomeNav()
    LoginNav()

    # Show the other page navigators depending on the users' role.
    if ss["authentication_status"]:
        # Get all the usernames with admin role.
        admins = [k for k, v in user_roles.items() if v == "admin"]

        # Show pages accessible to all authenticated users
        Page1Nav()
        Page2Nav()

        # Show admin page only if the logged-in user is an admin
        if ss.username in admins:
            PrivateLBPageNav()
            logger.info(f"Admin page shown for user: {ss.username}")
