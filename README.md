# minikaggle

## 概要
ローカルでKaggleのようなコンペティションを開催するためのツールです。

## 環境構築
uvを利用しているので、以下の手順で環境構築を行ってください。
https://docs.astral.sh/uv/guides/install-python/

.competition_setting.yamlと.authenticator_config.yaml
を参考にしてcompetition_setting.yamlとauthenticator_config.yamlを作成してください。
competition_setting.yamlはコンペティションの設定を行うファイルです。
特にコンペティションのtargetの列の名前の設定`answer_column`の設定は必須です。
authenticator_config.yamlは認証ファイルです。こちらは特に触ることはないですが、ユーザーごとに管理者権限を与えたい場合に利用します。

## データの準備
test.csvデータを用意してください。
必要な列名
- answer_column(targetになります)
- is_public(0 or 1)
この2つの列名があるtest.csvをcompetitionディレクトリの直下に配置してください。

## 使い方
以下のコマンドを実行してください。
```bash
uv run streamlit run app/main.py --server.port 15000
```

これで、http://localhost:15000 にアクセスすることで、minikaggleを利用することができます。

Describe your project here.
Thanks for this repository
https://github.com/fsmosca/sample-streamlit-authenticator/tree/main