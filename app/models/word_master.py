from datetime import datetime, timezone
from app.extensions import db

# ===== 単語マスター系テーブル（新規: 試験分析・AI選定用） =====


class WordMaster(db.Model):
    """単語基本情報（lemma単位）。JMdict等の辞書由来のマスターデータ。"""

    __tablename__ = "word_master"

    id = db.Column(db.Integer, primary_key=True)
    lemma = db.Column(db.String(255), unique=True, nullable=False, index=True)
    part_of_speech = db.Column(db.String(50), nullable=True)  # 品詞
    pronunciation = db.Column(db.String(255), nullable=True)  # 発音記号
    source = db.Column(db.String(100), nullable=True)         # データ出典
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    meanings = db.relationship("Meaning", backref="word_master", lazy="dynamic", cascade="all, delete-orphan")
    word_metadata = db.relationship("WordMetadata", backref="word_master", uselist=False, cascade="all, delete-orphan")
    tags = db.relationship("WordTag", backref="word_master", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<WordMaster {self.lemma}>"


class Meaning(db.Model):
    """日本語意味（多義語対応のため1対多）。"""

    __tablename__ = "meanings"

    id = db.Column(db.Integer, primary_key=True)
    word_master_id = db.Column(
        db.Integer, db.ForeignKey("word_master.id"), nullable=False, index=True
    )
    meaning_ja = db.Column(db.Text, nullable=False)
    example_en = db.Column(db.Text, nullable=True)
    example_ja = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<Meaning {self.meaning_ja}>"


class WordMetadata(db.Model):
    """単語メタデータ（CEFRレベル、難易度、一般的頻度）。"""

    __tablename__ = "word_metadata"

    word_master_id = db.Column(
        db.Integer, db.ForeignKey("word_master.id"), primary_key=True
    )
    cefr_level = db.Column(db.String(2), nullable=True)   # A1〜C2
    difficulty = db.Column(db.Integer, nullable=True)      # 1〜10
    frequency = db.Column(db.Float, nullable=True)         # 一般的頻度スコア
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<WordMetadata {self.cefr_level}>"


class Tag(db.Model):
    """汎用タグ（試験以外のテーマ・品詞特性など）。"""

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)   # 例: topic / pos / theme
    name = db.Column(db.String(100), nullable=False)
    __table_args__ = (
        db.UniqueConstraint("type", "name", name="uq_tags"),
    )

    def __repr__(self) -> str:
        return f"<Tag {self.type}:{self.name}>"


class WordTag(db.Model):
    """単語とタグの中間テーブル。"""

    __tablename__ = "word_tags"

    word_master_id = db.Column(
        db.Integer, db.ForeignKey("word_master.id"), primary_key=True
    )
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id"), primary_key=True)

    tag = db.relationship("Tag", backref="word_tag_links")

    def __repr__(self) -> str:
        return f"<WordTag {self.word_master_id}:{self.tag_id}>"
