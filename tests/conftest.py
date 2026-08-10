import sys
import os
import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 重要: create_app() を呼ぶ前に DATABASE_URL を上書きする。
# Flask-SQLAlchemy 3.x ではエンジンは init_app() 時に作成されるため、
# アプリ作成後に config.update() でURIを変更しても実DBに接続してしまう。
# テストで実DB(instance/vocab_generator.db)を破壊しないよう、
# 環境変数で先にテスト用のインメモリDBを指定する。
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import create_app
from app.extensions import db
from app.models.user import User


@pytest.fixture
def app():
    """テスト用アプリケーション。インメモリSQLiteを使用。"""
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        DEEPSEEK_API_KEY="test-key",
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """テストクライアント。"""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """テスト用ユーザーを作成してIDを返す。"""
    user = User(email="test@example.com")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user.id


@pytest.fixture
def logged_in_client(client, test_user):
    """ログイン済みテストクライアント。"""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(test_user)
        sess["_fresh"] = True
    return client
