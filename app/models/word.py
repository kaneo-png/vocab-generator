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

    def __repr__(self) -> str:
        return f"<Word {self.word} (list={self.wordlist_id})>"