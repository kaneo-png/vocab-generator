from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 拡張機能の初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Blueprint登録
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.chat import chat_bp
    from app.routes.billing import billing_bp
    from app.routes.api import api_bp
    from app.routes.master import master_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(master_bp)

    # CLIコマンド登録
    from app.cli import register_commands
    register_commands(app)

    # テンプレートで利用するグローバル関数
    @app.context_processor
    def inject_globals():
        return {"STRIPE_PUBLISHABLE_KEY": app.config["STRIPE_PUBLISHABLE_KEY"]}

    return app