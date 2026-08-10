# パーソナライズ単語帳ジェネレーター

英語学習者向けの「パーソナライズ単語帳ジェネレーター」Webアプリ。
ユーザーとチャットで対話し、目標・レベル・苦手分野を聞き出した上で、
最適な英単語リストを生成し、Anki互換のCSVでダウンロードできるサービス。

## 技術スタック

- **フロントエンド**: HTML, CSS, JavaScript
- **バックエンド**: Python Flask
- **AI API**: DeepSeek API (OpenAI互換)
- **データベース**: SQLite (開発段階)
- **決済**: Stripe
- **広告**: Google AdSenseプレースホルダー

## ディレクトリ構造

```
vocab-generator/
├── run.py                      # アプリ起動エントリポイント
├── requirements.txt            # Python依存パッケージ
├── .env.example                # 環境変数テンプレート
├── config.py                   # 環境変数から設定を読み込む
├── app/
│   ├── __init__.py             # Flaskアプリファクトリ
│   ├── extensions.py           # db / migrate / login_manager
│   ├── models/                 # SQLAlchemyモデル
│   │   ├── user.py             # ユーザー（プラン情報含む）
│   │   ├── wordlist.py         # 生成した単語帳
│   │   └── word.py             # 単語エントリ
│   ├── routes/                 # ルーティング（Blueprint）
│   │   ├── auth.py             # 登録/ログイン/ログアウト
│   │   ├── main.py             # トップページ/ダッシュボード
│   │   ├── chat.py             # チャット対話・単語帳生成
│   │   ├── billing.py          # プラン選択・Stripe決済
│   │   └── api.py              # CSVダウンロード等のAPI
│   ├── services/               # ビジネスロジック
│   │   ├── ai_service.py       # DeepSeek API呼び出し
│   │   ├── csv_service.py      # Anki互換CSV生成
│   │   └── billing_service.py  # Stripe決済・プラン管理
│   ├── templates/              # Jinja2テンプレート
│   └── static/                 # CSS / JS
├── migrations/                 # Alembicマイグレーション
└── tests/                      # pytest
```

## セットアップ

```bash
# 1. 依存パッケージのインストール
pip install -r requirements.txt

# 2. 環境変数の設定
cp .env.example .env
# .env に DEEPSEEK_API_KEY 等を設定

# 3. データベースの初期化
flask db init
flask db migrate -m "initial migration"
flask db upgrade

# 4. 開発サーバー起動
python run.py
```

## 料金プラン

| プラン | 料金 | 広告 | 生成回数/月 |
|--------|------|------|------------|
| free | 無料 | あり | 3回 |
| ad_free | 月額10円 | なし | 10回 |
| premium | 月額500円 | なし | 無制限 |

## マイグレーション方針

- **Flask-Migrate（Alembic）** を採用
- モデル変更時: `flask db migrate -m "変更内容"` → `flask db upgrade`
- マイグレーション履歴は `migrations/` にコミットして共有
- 開発初期はSQLite、本番はPostgreSQLへ切替可能（`DATABASE_URL` で制御）

## テスト

```bash
pytest
```
