"""単語マスターのシードデータ投入（公開フリーの頻出単語リストベース）。

注意: ここでは動作確認用のサンプル単語を投入する。
本番ではスクレイピング機構 or 市販の辞書データ（JMdict等）を利用する。
"""
from app.extensions import db
from app.models.word_master import WordMaster, Meaning, WordMetadata, Tag, WordTag

# (lemma, part_of_speech, cefr, difficulty, [meanings], [tags])
SAMPLE_WORDS = [
    ("acquisition", "noun", "B2", 6, ["買収、取得"], ["business", "finance"]),
    ("merge", "verb", "B2", 5, ["合併する"], ["business"]),
    ("procurement", "noun", "C1", 7, ["調達、購買"], ["business", "logistics"]),
    ("turnover", "noun", "B2", 6, ["売上高、離職率"], ["business", "hr"]),
    ("inventory", "noun", "B2", 5, ["在庫"], ["business", "logistics"]),
    ("streamline", "verb", "B2", 6, ["効率化する"], ["business"]),
    ("feasibility", "noun", "C1", 7, ["実現可能性"], ["academic", "business"]),
    ("hypothesis", "noun", "B2", 5, ["仮説"], ["academic", "science"]),
    ("paradigm", "noun", "C1", 7, ["パラダイム、考え方の枠組み"], ["academic", "humanities"]),
    ("empirical", "adj", "C1", 7, ["実証的な"], ["academic", "science"]),
    ("sustainable", "adj", "B2", 5, ["持続可能な"], ["environment", "social_issues"]),
    ("mitigate", "verb", "C1", 7, ["軽減する"], ["environment", "academic"]),
    ("biodiversity", "noun", "C1", 7, ["生物多様性"], ["environment", "science"]),
    ("legislation", "noun", "B2", 6, ["法律、立法"], ["politics", "academic"]),
    ("diplomacy", "noun", "B2", 6, ["外交"], ["politics"]),
    ("negotiate", "verb", "B1", 4, ["交渉する"], ["business", "politics"]),
    ("implement", "verb", "B2", 5, ["実施する、実装する"], ["business", "academic"]),
    ("analyze", "verb", "B1", 4, ["分析する"], ["academic", "business"]),
    ("evaluate", "verb", "B1", 4, ["評価する"], ["academic", "business"]),
    ("significant", "adj", "B1", 4, ["重要な、顕著な"], ["academic", "business"]),
]


def seed_words() -> None:
    """単語マスターにサンプル単語を投入する（冪等）。"""
    for lemma, pos, cefr, difficulty, meanings, tags in SAMPLE_WORDS:
        word = WordMaster.query.filter_by(lemma=lemma).first()
        if not word:
            word = WordMaster(
                lemma=lemma,
                part_of_speech=pos,
                source="sample-seed",
            )
            db.session.add(word)
            db.session.flush()

        # 意味の投入（なければ）
        if not word.meanings.count():
            for m in meanings:
                db.session.add(Meaning(word_master_id=word.id, meaning_ja=m))

        # メタデータ（なければ）
        if not word.word_metadata:
            db.session.add(WordMetadata(
                word_master_id=word.id,
                cefr_level=cefr,
                difficulty=difficulty,
                frequency=1.0,  # 仮の頻度
            ))

        # タグ投入
        for tag_name in tags:
            tag = Tag.query.filter_by(type="topic", name=tag_name).first()
            if not tag:
                tag = Tag(type="topic", name=tag_name)
                db.session.add(tag)
                db.session.flush()
            exists = WordTag.query.filter_by(
                word_master_id=word.id, tag_id=tag.id
            ).first()
            if not exists:
                db.session.add(WordTag(word_master_id=word.id, tag_id=tag.id))

    db.session.commit()
