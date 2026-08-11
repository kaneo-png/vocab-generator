"""Flask CLIコマンド定義。

- flask seed-all: 試験・ドメインルール・サンプル単語を投入
- flask scrape-exam: 指定URLから試験別頻度データを収集（プロトタイプ）
"""
import re
import time
import click
import requests
from flask import current_app
from app.extensions import db
from app.models.word_master import WordMaster, Meaning, WordMetadata, Tag, WordTag
from app.models.exam import Exam, ExamWordStat, ExamDomainRule


def register_commands(app):
    app.cli.add_command(seed_all)
    app.cli.add_command(scrape_exam)
    app.cli.add_command(fill_meanings)


@click.command("seed-all")
def seed_all():
    """試験マスタ・ドメインルール・サンプル単語を投入する。"""
    from app.seed.exam_seed import seed_exams
    from app.seed.word_seed import seed_words

    click.echo("試験データを投入中...")
    seed_exams()
    click.echo("サンプル単語を投入中...")
    seed_words()
    click.echo("✅ シード投入完了")


@click.command("scrape-exam")
@click.option("--exam-id", required=True, type=int, help="対象試験のID")
@click.option("--url", required=True, help="テキスト取得元URL")
@click.option("--limit", default=200, type=int, help="収集する上位単語数")
def scrape_exam(exam_id: int, url: str, limit: int):
    """指定URLのテキストから頻出単語を集計し exam_word_stats に格納する。

    注意: robots.txt・利用規約を必ず確認すること。
    本プロトタイプではHTMLテキストを簡易トークン化する。
    """
    exam = Exam.query.get(exam_id)
    if not exam:
        click.echo(f"試験ID {exam_id} が見つかりません")
        return

    click.echo(f"{url} からテキストを取得中...")
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "VocabGenBot/0.1"})
        resp.raise_for_status()
    except Exception as e:
        click.echo(f"取得エラー: {e}")
        return

    # BeautifulSoupで本文テキストのみ抽出（HTMLタグ・属性ノイズを除去）
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")
    # スクリプト・スタイル・引用を除去
    for tag in soup(["script", "style", "sup", "cite"]):
        tag.decompose()
    text = soup.get_text(" ")
    text = re.sub(r"[^a-zA-Z\s']", " ", text)
    words = [w.lower() for w in text.split() if len(w) > 2 and w.isalpha()]

    # ストップワード除去（頻出の機能語を除外）
    STOPWORDS = {
        "the", "and", "for", "are", "from", "with", "that", "this", "these", "those",
        "was", "were", "have", "has", "had", "will", "would", "could", "should",
        "their", "there", "they", "them", "which", "what", "when", "where", "who",
        "than", "then", "not", "but", "all", "any", "can", "its", "also", "into",
        "about", "after", "before", "between", "during", "over", "under", "such",
        "more", "most", "other", "some", "each", "both", "few", "only", "own",
        "very", "just", "because", "been", "being", "were", "was", "did", "does",
        "doing", "done", "would", "may", "might", "must", "shall", "should", "per",
        "via", "within", "without", "upon", "while", "through", "against", "among",
    }
    words = [w for w in words if w not in STOPWORDS and len(w) >= 4]

    # 頻度集計
    from collections import Counter
    freq = Counter(words)
    top_words = freq.most_common(limit)

    click.echo(f"全 {len(freq)} 種類の単語を検出。上位 {limit} 語を登録します。")

    # 登録（upsert）
    for idx, (word_str, count) in enumerate(top_words):
        word = WordMaster.query.filter_by(lemma=word_str).first()
        if not word:
            word = WordMaster(lemma=word_str, part_of_speech=None, source=f"scrape:{exam.name}")
            db.session.add(word)
            db.session.flush()

        # 意味が無ければプレースホルダ（後でAI補完 or 手動編集）
        if not word.meanings.count():
            db.session.add(Meaning(
                word_master_id=word.id,
                meaning_ja=f"（{word_str}の意味 - 要補完）",
            ))

        stat = ExamWordStat.query.filter_by(
            word_master_id=word.id, exam_id=exam.id
        ).first()
        if stat:
            # upsert: 頻度を加算
            stat.frequency_score = (stat.frequency_score or 0) + float(count)
            stat.last_appeared = time.strftime("%Y-%m")
        else:
            db.session.add(ExamWordStat(
                word_master_id=word.id,
                exam_id=exam.id,
                frequency_score=float(count),
                last_appeared=time.strftime("%Y-%m"),
                domain_relevance="normal",
            ))

    db.session.commit()
    click.echo(f"✅ {len(top_words)} 語を {exam.name} の統計に登録しました")


@click.command("fill-meanings")
@click.option("--limit", default=50, type=int, help="補完する単語数上限")
def fill_meanings(limit: int):
    """意味が未補完の単語にDeepSeekで日本語訳を付与する。"""
    from app.services.ai_service import AIService, AIServiceError

    # 意味未補完の単語を取得（"要補完" プレースホルダを含む）
    targets = (
        db.session.query(WordMaster)
        .join(Meaning, Meaning.word_master_id == WordMaster.id)
        .filter(Meaning.meaning_ja.like("%要補完%"))
        .limit(limit)
        .all()
    )
    if not targets:
        click.echo("補完対象の単語がありません。")
        return

    click.echo(f"{len(targets)} 語の意味をDeepSeekで補完します...")
    try:
        ai = AIService()
        lemmas = [w.lemma for w in targets]
        prompt = (
            "以下の英単語それぞれの日本語訳（簡潔に）をJSONで返してください。"
            "JSON形式は words 配列に lemma と meaning を持つオブジェクトの並び。"
            "単語リスト: " + ", ".join(lemmas)
        )
        resp = ai.client.chat.completions.create(
            model=ai.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )
        result = ai._parse_response(resp.choices[0].message.content)
    except Exception as e:
        click.echo(f"AI呼び出しに失敗: {e}")
        return

    word_map = {w.lemma: w for w in targets}
    updated = 0
    for item in result.get("words", []):
        lemma = item.get("lemma", "")
        meaning = item.get("meaning", "").strip()
        word = word_map.get(lemma)
        if word and meaning and "要補完" not in meaning:
            m = word.meanings.first()
            if m:
                m.meaning_ja = meaning
                updated += 1

    db.session.commit()
    click.echo(f"✅ {updated} 語の意味を補完しました")

