import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """アプリケーション設定。環境変数から読み込む。"""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # DBはinstance/フォルダ配下の絶対パスで指定
    # （相対パスだとマイグレーションとアプリ実行時で参照先がズレるため）
    _base_dir = Path(__file__).resolve().parent
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{_base_dir / 'instance' / 'vocab_generator.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # DeepSeek API (OpenAI互換)
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    # DeepSeekのJSONモード（response_format=json_object）を使用するか。
    # 対応していないエンドポイントを使う場合は環境変数で無効化できる。
    DEEPSEEK_JSON_MODE = (
        os.environ.get("DEEPSEEK_JSON_MODE", "true").lower() in ("1", "true", "yes")
    )

    # Stripe
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    # Checkout後のリダイレクト先（未設定ならurl_forで自動生成）
    STRIPE_SUCCESS_URL = os.environ.get("STRIPE_SUCCESS_URL", "")
    STRIPE_CANCEL_URL = os.environ.get("STRIPE_CANCEL_URL", "")

    # プラン設定 (Stripe Price ID)
    STRIPE_PRICE_AD_FREE = os.environ.get("STRIPE_PRICE_AD_FREE", "")
    STRIPE_PRICE_PREMIUM = os.environ.get("STRIPE_PRICE_PREMIUM", "")

    # プランごとの月間生成回数制限
    FREE_MONTHLY_LIMIT = 3
    AD_FREE_MONTHLY_LIMIT = 10
    PREMIUM_MONTHLY_LIMIT = 9999