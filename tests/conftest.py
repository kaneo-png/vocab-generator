import pytest

# プロジェクトルートを sys.path に追加する処理は pyproject.toml の
# [tool.pytest.ini_options] pythonpath で行う（Pylance の解析パスは
# .vscode/settings.json の python.analysis.extraPaths で解決）。
from app import create_app
from app.extensions import db
from app.models.user import User
from config import Config


class TestConfig(Config):
    """テスト用設定。インメモリSQLiteを使用し、実DBを壊さない。"""
    TESTING = True
    # Flask-SQLAlchemy 3.x ではエンジンは init_app() 時に作成されるため、
    # create_app() に渡す config_class 側でURIを指定する必要がある。
    # これによりテスト実行中の create_all()/drop_all() が実DB(instance/vocab_generator.db)に触れない。
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    DEEPSEEK_API_KEY = "test-key"


@pytest.fixture
def app():
    """テスト用アプリケーション。インメモリSQLiteを使用。"""
    app = create_app(TestConfig)

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
