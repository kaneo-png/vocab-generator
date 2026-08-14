from flask import Blueprint, jsonify, Response
from flask_login import login_required, current_user
from urllib.parse import quote
from app.extensions import db
from app.models.wordlist import WordList
from app.services.csv_service import CSVService
from app.services.guest import is_guest_wordlist_owner

api_bp = Blueprint("api", __name__)


def _word_to_dict(w) -> dict:
    """WordモデルをJSON用の辞書に変換する。"""
    return {
        "id": w.id,
        "word": w.word,
        "meaning": w.meaning,
        "example": w.example,
        "example_ja": w.example_ja,
        "note": w.note,
        "reason": w.reason,
        "difficulty": w.difficulty,
        "category": w.category,
    }


def _get_wordlist_for_request(wordlist_id: int):
    """単語帳を取得し、アクセス権（所有者 or ゲストセッション）を検証する。"""
    wordlist = db.session.get(WordList, wordlist_id)
    if not wordlist:
        return None, jsonify({"error": "単語帳が見つかりません。"}), 404

    if wordlist.user_id is not None:
        if not current_user.is_authenticated or wordlist.user_id != current_user.id:
            return None, jsonify({"error": "この単語帳にアクセスできません。"}), 403
    else:
        if not is_guest_wordlist_owner(wordlist_id):
            return None, jsonify({"error": "この単語帳にアクセスできません。"}), 403
    return wordlist, None, None


@api_bp.route("/api/wordlists/<int:wordlist_id>/csv")
def download_csv(wordlist_id: int):
    """指定した単語帳をAnki互換CSVとしてダウンロードする。"""
    wordlist, error_response, status = _get_wordlist_for_request(wordlist_id)
    if error_response:
        return error_response, status

    words = [_word_to_dict(w) for w in wordlist.words.all()]
    csv_content = CSVService.to_anki_csv(words)

    filename = f"{wordlist.title}.csv"
    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                # ASCIIフォールバック + 日本語対応（RFC 5987）
                f"attachment; filename=wordlist_{wordlist.id}.csv; "
                f"filename*=UTF-8''{quote(filename)}"
            )
        },
    )


@api_bp.route("/api/wordlists/<int:wordlist_id>")
def get_wordlist(wordlist_id: int):
    """単語帳の詳細をJSONで返す。"""
    wordlist, error_response, status = _get_wordlist_for_request(wordlist_id)
    if error_response:
        return error_response, status

    return jsonify({
        "id": wordlist.id,
        "title": wordlist.title,
        "goal": wordlist.goal,
        "level": wordlist.level,
        "weak_points": wordlist.weak_points,
        "created_at": wordlist.created_at.isoformat() if wordlist.created_at else None,
        "words": [_word_to_dict(w) for w in wordlist.words.all()],
    })
