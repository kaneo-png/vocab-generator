from flask import Flask, render_template
from config import Config
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 拡張機能の初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

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

    # エラーハンドラ
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app