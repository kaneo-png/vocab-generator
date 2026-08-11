from app.extensions import db


class Word(db.Model):
    """単語帳に含まれる個々の単語エントリ。"""

    __tablename__ = "words"

    id = db.Column(db.Integer, primary_key=True)
    wordlist_id = db.Column(
        db.Integer, db.ForeignKey("wordlists.id"), nullable=False, index=True
    )
    word = db.Column(db.String(255), nullable=False)
    meaning = db.Column(db.Text, nullable=False)      # 日本語訳
    example = db.Column(db.Text, nullable=True)       # 例文
    example_ja = db.Column(db.Text, nullable=True)    # 例文の日本語訳
    note = db.Column(db.Text, nullable=True)          # 補足（語源、類義語など）
    reason = db.Column(db.Text, nullable=True)        # 選定理由（ユーザーの目標・苦手と紐づけ）
    difficulty = db.Column(db.String(2), nullable=True)  # 難易度（A1〜C2）
    category = db.Column(db.String(100), nullable=True)  # 分野（例: ビジネス形容詞）

    def __repr__(self) -> str:
        return f"<Word {self.word} (list={self.wordlist_id})>"
