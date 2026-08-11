from datetime import datetime, timezone
from app.extensions import db


class ChatSession(db.Model):
    """チャットヒアリングの会話セッション。会話履歴と収集データをJSONで保持する。"""

    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    # ログインユーザーに紐づく（未ログインのセッションのみ利用も可能にするため可空）
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )
    # フロントエンドからセッションを特定するためのキー（UUID等）
    session_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    # 会話履歴 [{"role": "user"/"assistant", "content": "..."}, ...]
    messages = db.Column(db.JSON, nullable=False, default=list)
    # 収集したヒアリング情報 {goal, level, weak_points, count, other_requests}
    collected_data = db.Column(db.JSON, nullable=False, default=dict)
    # 収集状態: collecting / completed
    status = db.Column(db.String(20), nullable=False, default="collecting")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def append_message(self, role: str, content: str) -> None:
        """会話履歴にメッセージを追加する。"""
        messages = list(self.messages or [])
        messages.append({"role": role, "content": content})
        self.messages = messages

    def is_complete(self) -> bool:
        """必要項目が全て収集できているか。"""
        return self.status == "completed"

    def __repr__(self) -> str:
        return f"<ChatSession {self.session_key} ({self.status})>"
