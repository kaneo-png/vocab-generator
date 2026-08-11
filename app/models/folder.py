from datetime import datetime, timezone
from app.extensions import db

# ===== フォルダ・単語帳・学習履歴 =====


class Folder(db.Model):
    """ユーザーのフォルダ（単語帳の整理用）。"""

    __tablename__ = "folders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    wordbooks = db.relationship("Wordbook", backref="folder", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Folder {self.name}>"


class Wordbook(db.Model):
    """単語帳（1回のAI選定結果）。"""

    __tablename__ = "wordbooks"

    id = db.Column(db.Integer, primary_key=True)
    folder_id = db.Column(
        db.Integer, db.ForeignKey("folders.id"), nullable=True, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    exam_id = db.Column(
        db.Integer, db.ForeignKey("exams.id"), nullable=True, index=True
    )
    title = db.Column(db.String(255), nullable=False)
    target_words_count = db.Column(db.Integer, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    words = db.relationship(
        "WordbookWord", backref="wordbook", lazy="dynamic", cascade="all, delete-orphan",
        order_by="WordbookWord.sort_order"
    )

    def __repr__(self) -> str:
        return f"<Wordbook {self.title}>"


class WordbookWord(db.Model):
    """単語帳に含まれる単語（マスター単語への参照）。"""

    __tablename__ = "wordbook_words"

    id = db.Column(db.Integer, primary_key=True)
    wordbook_id = db.Column(
        db.Integer, db.ForeignKey("wordbooks.id"), nullable=False, index=True
    )
    word_master_id = db.Column(
        db.Integer, db.ForeignKey("word_master.id"), nullable=False, index=True
    )
    selection_reason = db.Column(db.Text, nullable=True)  # AI選定理由
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    db.UniqueConstraint("wordbook_id", "word_master_id")

    word = db.relationship("WordMaster")

    def __repr__(self) -> str:
        return f"<WordbookWord wb={self.wordbook_id} wm={self.word_master_id}>"


class UserWordHistory(db.Model):
    """ユーザー単語学習履歴（累積）。"""

    __tablename__ = "user_word_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    word_master_id = db.Column(
        db.Integer, db.ForeignKey("word_master.id"), nullable=False, index=True
    )
    review_count = db.Column(db.Integer, nullable=False, default=0)
    correct_count = db.Column(db.Integer, nullable=False, default=0)
    incorrect_count = db.Column(db.Integer, nullable=False, default=0)
    mastery_score = db.Column(db.Float, nullable=False, default=0.0)  # 0.0〜1.0
    last_reviewed_at = db.Column(db.DateTime, nullable=True)
    db.UniqueConstraint("user_id", "word_master_id")

    word = db.relationship("WordMaster")

    def __repr__(self) -> str:
        return f"<UserWordHistory user={self.user_id} wm={self.word_master_id}>"
