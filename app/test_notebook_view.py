import os
import uuid

import nbformat
import streamlit as st
from nbconvert import HTMLExporter


# ファイルをアップロードし保存する関数
def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        with open(os.path.join("uploads", uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    return False


# Jupyter NotebookをHTML形式に変換する関数
def convert_notebook_to_html(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        notebook_content = nbformat.read(f, as_version=4)

    html_exporter = HTMLExporter()
    html_exporter.template_name = "classic"

    body, _ = html_exporter.from_notebook_node(notebook_content)
    return body


# HTMLファイルを生成し、そのパスを返す関数
def generate_html_file(file_path, output_dir):
    html_content = convert_notebook_to_html(file_path)
    file_name = f"{uuid.uuid4().hex}.html"
    output_path = os.path.join(output_dir, file_name)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path


# メインアプリケーション
def main():
    st.title("Jupyter Notebook Viewer")

    # アップロードされたファイルを保存するディレクトリを作成
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    if not os.path.exists("html_files"):
        os.makedirs("html_files")

    # ファイルアップロード
    uploaded_file = st.file_uploader("Upload a Jupyter Notebook file", type="ipynb")
    if uploaded_file is not None:
        if save_uploaded_file(uploaded_file):
            st.success(f"File {uploaded_file.name} uploaded successfully!")

    # アップロードされたファイルの一覧を表示
    st.subheader("Uploaded Notebooks")
    for file in os.listdir("uploads"):
        if file.endswith(".ipynb"):
            file_path = os.path.join("uploads", file)
            html_path = generate_html_file(file_path, "html_files")
            relative_path = os.path.relpath(html_path, os.getcwd())
            link = (
                f'<a href="{relative_path}" target="_blank">View {file} in new tab</a>'
            )
            st.markdown(link, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
