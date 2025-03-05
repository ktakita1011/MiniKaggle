import streamlit as st
import streamlit_authenticator as stauth
import yaml
from streamlit import session_state as ss
from yaml.loader import SafeLoader

from app.nav import MenuButtons

CONFIG_FILENAME = "./authenticator_config.yaml"

with open(CONFIG_FILENAME) as file:
    config = yaml.load(file, Loader=SafeLoader)


def get_roles():
    """Gets user roles based on config file."""
    with open(CONFIG_FILENAME) as file:
        config = yaml.load(file, Loader=SafeLoader)

    if config is not None:
        cred = config["credentials"]
    else:
        cred = {}

    return {
        username: user_info.get("role", "user")
        for username, user_info in cred["usernames"].items()
    }


st.header("Account page")

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
    config["preauthorized"],
)

login_tab, register_tab = st.tabs(["Login", "Register"])

with login_tab:
    authenticator.login(location="main")

    if ss["authentication_status"]:
        authenticator.logout(location="main")
        st.write(f"Welcome *{ss['name']}*")

    elif ss["authentication_status"] is False:
        st.error("Username/password is incorrect")
    elif ss["authentication_status"] is None:
        st.warning("Please enter your username and password")

with register_tab:
    if not ss["authentication_status"]:
        try:
            (
                email_of_registered_user,
                username_of_registered_user,
                name_of_registered_user,
            ) = authenticator.register_user(pre_authorization=False)
            if email_of_registered_user:
                # Add role to the newly registered user
                config["credentials"]["usernames"][username_of_registered_user][
                    "role"
                ] = "user"
                st.success("User registered successfully")
        except Exception as e:
            st.error(e)

# We call below code in case of registration, reset password, etc.
with open(CONFIG_FILENAME, "w") as file:
    yaml.dump(config, file, default_flow_style=False)

# Call this late because we show the page navigator depending on who logged in.
MenuButtons(get_roles())
