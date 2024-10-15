import streamlit as st
from streamlit import session_state as ss


def HomeNav():
    st.sidebar.page_link("./main.py", label="Home", icon="🏠")


def LoginNav():
    st.sidebar.page_link("./pages/account.py", label="Account", icon="🔐")


def Page1Nav():
    st.sidebar.page_link("./pages/page_02_leaderbord.py", label="LB", icon="✈️")


def Page2Nav():
    st.sidebar.page_link("./pages/page_03_submission.py", label="submittion", icon="📚")


def MenuButtons(user_roles=None):
    if user_roles is None:
        user_roles = {}

    if "authentication_status" not in ss:
        ss.authentication_status = False

    # Always show the home and login navigators.
    # HomeNav()
    LoginNav()

    # Show the other page navigators depending on the users' role.
    if ss["authentication_status"]:
        # (1) Only the admin role can access page 1 and other pages.
        # In a user roles get all the usernames with admin role.
        admins = [k for k, v in user_roles.items() if v == "admin"]

        # Show page 1 if the username that logged in is an admin.
        if ss.username in admins:
            print("i am admin")

        # (2) users with user and admin roles have access to page 2.
        Page1Nav()
        Page2Nav()
