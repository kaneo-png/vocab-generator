from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """ユーザー。プラン情報と月間生成回数を保持する。"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # プラン: free / ad_free / premium
    plan = db.Column(db.String(20), nullable=False, default="free")
    # 月間生成回数（プラン制限の判定に使用）
    monthly_generation_count = db.Column(db.Integer, nullable=False, default=0)
    # カウント対象の月（YYYY-MM形式）
    generation_month = db.Column(db.String(7), nullable=False, default="")
    # Stripe Customer ID（サブスク管理・解約時に使用）
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    # メール認証
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    verification_token = db.Column(db.String(64), nullable=True)
    verification_token_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    wordlists = db.relationship(
        "WordList", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_monthly_limit(self) -> int:
        """プランに応じた月間生成回数上限を返す。"""
        from app.services.plan import monthly_limit

        return monthly_limit(self.plan)

    def has_feature(self, feature: str) -> bool:
        """プランで指定機能を利用できるかを判定する。"""
        from app.services.plan import has_feature as _has_feature

        return _has_feature(self.plan, feature)

    def is_generation_allowed(self) -> tuple:
        """生成可否とエラーメッセージを返す（メール認証 + 月間上限）。

        Returns:
            (ok: bool, error_message: str, extra: dict)
        """
        if not self.email_verified:
            return False, "メール認証が完了していません。確認メールから認証してください。", {
                "verification_required": True,
            }
        if not self.can_generate():
            return False, "今月の生成回数上限に達しました。プランをアップグレードしてください。", {
                "limit_reached": True,
            }
        return True, "", {}

    def can_generate(self) -> bool:
        """今月の生成回数が上限に達していないか判定。"""
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        if self.generation_month != current_month:
            # 月が変わったらリセット
            self.generation_month = current_month
            self.monthly_generation_count = 0
        return self.monthly_generation_count < self.get_monthly_limit()

    def increment_generation(self) -> None:
        """生成回数を1増やす。月が変わっていればリセットしてから。"""
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        if self.generation_month != current_month:
            self.generation_month = current_month
            self.monthly_generation_count = 0
        self.monthly_generation_count += 1

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.plan})>"


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))