"""マスターDBベースの単語選定・フォルダ管理API。"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.exam import Exam
from app.models.folder import Folder, Wordbook, WordbookWord
from app.models.word_master import WordMaster, Meaning
from app.services.selection_service import SelectionService, SelectionServiceError

master_bp = Blueprint("master", __name__)


@master_bp.route("/master")
@login_required
def master_page():
    """マスターDBベースの単語選定ページ。"""
    exams = Exam.query.all()
    folders = Folder.query.filter_by(user_id=current_user.id).all()
    return render_template("master.html", exams=exams, folders=folders)


@master_bp.route("/api/master/folders", methods=["GET"])
@login_required
def list_folders():
    """フォルダ一覧を取得する。"""
    folders = Folder.query.filter_by(user_id=current_user.id).all()
    return jsonify([{"id": f.id, "name": f.name, "wordbook_count": f.wordbooks.count()} for f in folders])


@master_bp.route("/api/master/folders", methods=["POST"])
@login_required
def create_folder():
    """フォルダを作成する。"""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "フォルダ名を入力してください。"}), 400
    folder = Folder(user_id=current_user.id, name=name)
    db.session.add(folder)
    db.session.commit()
    return jsonify({"id": folder.id, "name": folder.name}), 201


@master_bp.route("/api/master/folders/<int:folder_id>", methods=["DELETE"])
@login_required
def delete_folder(folder_id: int):
    """フォルダを削除する。"""
    folder = Folder.query.filter_by(id=folder_id, user_id=current_user.id).first_or_404()
    db.session.delete(folder)
    db.session.commit()
    return jsonify({"ok": True})


@master_bp.route("/api/master/generate", methods=["POST"])
@login_required
def generate_wordbook():
    """AI選定に基づいて単語帳を生成する。"""
    data = request.get_json(silent=True) or {}
    exam_id = int(data.get("exam_id", 0))
    folder_id = data.get("folder_id")
    count = min(int(data.get("count", 50)), 200)
    weak_points = (data.get("weak_points") or "").strip()

    if not exam_id:
        return jsonify({"error": "試験を選択してください。"}), 400

    try:
        service = SelectionService(current_user)
        result = service.select_words(
            exam_id=exam_id, count=count, weak_points=weak_points
        )
    except SelectionServiceError as e:
        return jsonify({"error": str(e)}), 400

    # フォルダ確認
    folder = None
    if folder_id:
        folder = Folder.query.filter_by(id=folder_id, user_id=current_user.id).first()
        if not folder:
            return jsonify({"error": "フォルダが見つかりません。"}), 404

    # 単語帳作成
    wordbook = Wordbook(
        folder_id=folder.id if folder else None,
        user_id=current_user.id,
        exam_id=exam_id,
        title=result["title"],
        target_words_count=len(result["words"]),
    )
    db.session.add(wordbook)
    db.session.flush()

    for idx, w in enumerate(result["words"]):
        db.session.add(WordbookWord(
            wordbook_id=wordbook.id,
            word_master_id=w["word_master_id"],
            selection_reason=w.get("reason", ""),
            sort_order=idx,
        ))

    db.session.commit()

    return jsonify({
        "wordbook_id": wordbook.id,
        "title": wordbook.title,
        "words": result["words"],
    }), 201


@master_bp.route("/api/master/wordbooks/<int:wordbook_id>")
@login_required
def get_wordbook(wordbook_id: int):
    """単語帳の詳細を取得する。"""
    wordbook = Wordbook.query.filter_by(id=wordbook_id, user_id=current_user.id).first_or_404()
    words = []
    for ww in wordbook.words.all():
        word = ww.word
        meaning = ""
        if word and word.meanings.count():
            meaning = word.meanings.first().meaning_ja
        words.append({
            "word": word.lemma if word else "",
            "meaning": meaning,
            "reason": ww.selection_reason,
            "word_master_id": ww.word_master_id,
        })
    return jsonify({
        "id": wordbook.id,
        "title": wordbook.title,
        "words": words,
    })


@master_bp.route("/api/master/wordbooks/<int:wordbook_id>/csv")
@login_required
def download_wordbook_csv(wordbook_id: int):
    """単語帳をAnki互換CSVで出力する。"""
    from flask import Response
    from app.services.csv_service import CSVService

    wordbook = Wordbook.query.filter_by(id=wordbook_id, user_id=current_user.id).first_or_404()
    words = []
    for ww in wordbook.words.all():
        word = ww.word
        meaning = ""
        if word and word.meanings.count():
            meaning = word.meanings.first().meaning_ja
        words.append({
            "word": word.lemma if word else "",
            "meaning": meaning,
            "reason": ww.selection_reason,
        })

    csv_content = CSVService.to_anki_csv(words)
    filename = f"{wordbook.title}.csv"
    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
