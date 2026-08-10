from flask import Blueprint, jsonify, Response, abort
from flask_login import login_required, current_user
from app.models.wordlist import WordList
from app.services.csv_service import CSVService

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/wordlists/<int:wordlist_id>/csv")
@login_required
def download_csv(wordlist_id: int):
    """指定した単語帳をAnki互換CSVとしてダウンロードする。"""
    wordlist = WordList.query.filter_by(
        id=wordlist_id, user_id=current_user.id
    ).first_or_404()

    words = [
        {
            "word": w.word,
            "meaning": w.meaning,
            "example": w.example,
            "example_ja": w.example_ja,
            "note": w.note,
        }
        for w in wordlist.words.all()
    ]

    csv_content = CSVService.to_anki_csv(words)

    filename = f"{wordlist.title}.csv"
    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@api_bp.route("/api/wordlists/<int:wordlist_id>")
@login_required
def get_wordlist(wordlist_id: int):
    """単語帳の詳細をJSONで返す。"""
    wordlist = WordList.query.filter_by(
        id=wordlist_id, user_id=current_user.id
    ).first_or_404()

    return jsonify({
        "id": wordlist.id,
        "title": wordlist.title,
        "goal": wordlist.goal,
        "level": wordlist.level,
        "weak_points": wordlist.weak_points,
        "created_at": wordlist.created_at.isoformat(),
        "words": [
            {
                "word": w.word,
                "meaning": w.meaning,
                "example": w.example,
                "example_ja": w.example_ja,
                "note": w.note,
            }
            for w in wordlist.words.all()
        ],
    })