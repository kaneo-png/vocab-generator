import json
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.wordlist import WordList
from app.models.word import Word
from app.services.ai_service import AIService, AIServiceError

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat")
@login_required
def chat_page():
    """チャット画面を表示する。"""
    return render_template("chat.html")


@chat_bp.route("/api/chat/generate", methods=["POST"])
@login_required
def generate_wordlist():
    """
    チャットで収集した情報に基づいて単語帳を生成する。

    Request JSON:
        {
            "goal": "TOEIC 800点を目指す",
            "level": "中級",
            "weak_points": "ビジネス英単語",
            "count": 20,
            "chat_history": [{"role": "user", "content": "..."}, ...]
        }
    """
    data = request.get_json(silent=True) or {}
    goal = data.get("goal", "").strip()
    level = data.get("level", "").strip()
    weak_points = data.get("weak_points", "").strip()
    count = min(int(data.get("count", 20)), 50)  # 最大50語
    chat_history = data.get("chat_history", [])

    if not goal:
        return jsonify({"error": "学習目標を入力してください。"}), 400

    # 生成回数制限チェック
    if not current_user.can_generate():
        return jsonify({
            "error": "今月の生成回数上限に達しました。プランをアップグレードしてください。",
            "limit_reached": True,
        }), 403

    try:
        ai = AIService()
        result = ai.generate_wordlist(
            goal=goal,
            level=level,
            weak_points=weak_points,
            count=count,
            chat_history=chat_history,
        )
    except AIServiceError as e:
        return jsonify({"error": str(e)}), 500

    # 単語帳をDBに保存
    wordlist = WordList(
        user_id=current_user.id,
        title=result.get("title", "マイ単語帳"),
        goal=goal,
        level=level,
        weak_points=weak_points,
    )
    db.session.add(wordlist)
    db.session.flush()  # wordlist.id を取得するため

    for w in result.get("words", []):
        word = Word(
            wordlist_id=wordlist.id,
            word=w.get("word", ""),
            meaning=w.get("meaning", ""),
            example=w.get("example", ""),
            example_ja=w.get("example_ja", ""),
            note=w.get("note", ""),
        )
        db.session.add(word)

    # 生成回数をインクリメント
    current_user.increment_generation()
    db.session.commit()

    return jsonify({
        "wordlist_id": wordlist.id,
        "title": wordlist.title,
        "words": result.get("words", []),
        "remaining": current_user.get_monthly_limit() - current_user.monthly_generation_count,
    })