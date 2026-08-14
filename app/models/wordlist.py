from datetime import datetime, timezone
from app.extensions import db


class WordList(db.Model):
    """生成された単語帳。ユーザーに紐づく。"""

    __tablename__ = "wordlists"

    id = db.Column(db.Integer, primary_key=True)
    # user_idはゲスト（未ログイン）生成時はNULL
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    title = db.Column(db.String(255), nullable=False)
    goal = db.Column(db.Text, nullable=True)          # 学習目標
    level = db.Column(db.String(50), nullable=True)   # レベル（初級/中級/上級）
    weak_points = db.Column(db.Text, nullable=True)   # 苦手分野
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    words = db.relationship(
        "Word", backref="wordlist", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<WordList {self.title} (user={self.user_id})>"