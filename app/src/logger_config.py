# logger_config.py

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import streamlit as st
from streamlit import session_state as ss

# 実行ディレクトリを取得
APP_ROOT = Path.cwd()

LOG_DIR = APP_ROOT / "logs"

LOG_DIR.mkdir(exist_ok=True)


@st.cache_resource
def get_cached_logger(name=None):
    return get_logger(name)


class StreamlitInfoFilter(logging.Filter):
    def filter(self, record):
        record.username = ss.get("username", "Unknown")
        return True


def setup_logger(name, log_file, level=logging.INFO):
    """ロガーをセットアップする関数"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # ログファイルのパスを設定
    log_path = LOG_DIR / log_file

    # ファイルハンドラーの設定（ログファイルのローテーションを行う）
    file_handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(level)

    # コンソールハンドラーの設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    # フォーマッターの設定
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - [%(username)s] - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Streamlit情報フィルターを追加
    streamlit_filter = StreamlitInfoFilter()
    file_handler.addFilter(streamlit_filter)
    console_handler.addFilter(streamlit_filter)

    # ハンドラーをロガーに追加
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# デフォルトのロガーを作成
default_logger = setup_logger("default", "app.log")


def get_logger(name=None):
    """名前付きロガーを取得する関数"""
    if name:
        return setup_logger(name, f"{name}.log")
    return default_logger
