from datetime import datetime, timezone
from app.extensions import db

# ===== 試験分析レイヤー =====


class Exam(db.Model):
    """試験マスタ（TOEIC / 英検準1級 / IELTS など）。"""

    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    stats = db.relationship("ExamWordStat", backref="exam", lazy="dynamic", cascade="all, delete-orphan")
    rules = db.relationship("ExamDomainRule", backref="exam", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Exam {self.name}>"


class ExamWordStat(db.Model):
    """試験別単語統計（スクレイピング結果を格納）。"""

    __tablename__ = "exam_word_stats"

    id = db.Column(db.Integer, primary_key=True)
    word_master_id = db.Column(
        db.Integer, db.ForeignKey("word_master.id"), nullable=False, index=True
    )
    exam_id = db.Column(
        db.Integer, db.ForeignKey("exams.id"), nullable=False, index=True
    )
    frequency_score = db.Column(db.Float, nullable=True)   # 出現頻度スコア
    last_appeared = db.Column(db.String(20), nullable=True)  # 直近出現（例: 2024-01）
    domain_relevance = db.Column(db.String(50), nullable=True)  # prioritize / exclude / normal
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    db.UniqueConstraint("word_master_id", "exam_id")

    word = db.relationship("WordMaster")

    def __repr__(self) -> str:
        return f"<ExamWordStat word={self.word_master_id} exam={self.exam_id}>"


class ExamDomainRule(db.Model):
    """試験ドメインルール（人手の知見を注入）。"""

    __tablename__ = "exam_domain_rules"

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(
        db.Integer, db.ForeignKey("exams.id"), nullable=False, index=True
    )
    rule_type = db.Column(db.String(20), nullable=False)  # exclude / prioritize / deprioritize
    category = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<ExamDomainRule {self.exam_id}:{self.category}={self.rule_type}>"
