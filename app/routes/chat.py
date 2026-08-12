import json
import uuid
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.wordlist import WordList
from app.models.word import Word
from app.models.chat_session import ChatSession
from app.services.ai_service import AIService, AIServiceError
from app.services.security import (
    INJECTION_ERROR_MESSAGE,
    MAX_FIELD_LENGTH,
    MAX_MESSAGE_LENGTH,
    MAX_WORD_COUNT,
    has_prompt_injection,
    validate_chat_history,
)

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat")
@login_required
def chat_page():
    """チャット画面を表示する。"""
    return render_template("chat.html")


@chat_bp.route("/api/chat/session", methods=["POST"])
@login_required
def create_session():
    """新しいヒアリングセッションを作成し、最初の質問を返す。"""
    session = ChatSession(
        user_id=current_user.id if current_user.is_authenticated else None,
        session_key=uuid.uuid4().hex,
        messages=[],
        collected_data={},
    )
    db.session.add(session)
    db.session.commit()

    try:
        ai = AIService()
        result = ai.analyze_and_respond(
            messages=[{"role": "user", "content": "こんにちは"}],
            collected_data={},
        )
        reply = result["message_to_user"] or "学習目標を教えてください。"
        session.append_message("assistant", reply)
        session.collected_data = result["collected_data"]
        db.session.commit()
    except AIServiceError:
        reply = "こんにちは！あなたに最適な単語帳を作成します。まず、学習目標を教えてください。（例: TOEIC 800点、英検準1級、海外営業で使う英語など）"
        session.append_message("assistant", reply)
        db.session.commit()

    return jsonify({
        "session_key": session.session_key,
        "message": reply,
        "collected_data": session.collected_data,
    })


@chat_bp.route("/api/chat/message", methods=["POST"])
@login_required
def send_message():
    """ユーザーの発言をAIに渡し、応答と収集データの更新を返す。"""
    data = request.get_json(silent=True) or {}
    session_key = data.get("session_key", "")
    user_message = data.get("message", "").strip()

    if not session_key or not user_message:
        return jsonify({"error": "セッションキーとメッセージが必要です。"}), 400

    if len(user_message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            "error": f"メッセージが長すぎます（最大{MAX_MESSAGE_LENGTH}文字）。"
        }), 400
    if has_prompt_injection(user_message):
        return jsonify({"error": INJECTION_ERROR_MESSAGE}), 400

    session = ChatSession.query.filter_by(session_key=session_key).first()
    if not session:
        return jsonify({"error": "セッションが見つかりません。"}), 404

    session.append_message("user", user_message)

    try:
        ai = AIService()
        result = ai.analyze_and_respond(
            messages=session.messages or [],
            collected_data=session.collected_data or {},
        )
    except AIServiceError as e:
        return jsonify({"error": str(e)}), 500

    reply = result["message_to_user"] or "もう少し詳しく教えてください。"
    session.append_message("assistant", reply)
    session.collected_data = result["collected_data"]

    cd = session.collected_data or {}
    required = ["goal", "level", "weak_points", "count"]
    if all(cd.get(k) for k in required):
        session.status = "completed"

    db.session.commit()

    return jsonify({
        "message": reply,
        "collected_data": session.collected_data,
        "summary": result.get("summary"),
        "next_question": result.get("next_question"),
        "status": session.status,
        "session_key": session.session_key,
    })


@chat_bp.route("/api/chat/session/<session_key>", methods=["GET"])
@login_required
def get_session(session_key: str):
    """セッションの状態を取得する（途中再開・修正用）。"""
    session = ChatSession.query.filter_by(session_key=session_key).first()
    if not session:
        return jsonify({"error": "セッションが見つかりません。"}), 404
    if session.user_id and session.user_id != current_user.id:
        return jsonify({"error": "このセッションにアクセスできません。"}), 403

    return jsonify({
        "session_key": session.session_key,
        "messages": session.messages or [],
        "collected_data": session.collected_data or {},
        "status": session.status,
    })


@chat_bp.route("/api/chat/session/<session_key>", methods=["PUT"])
@login_required
def update_session(session_key: str):
    """収集データを直接修正する（途中修正機能）。"""
    data = request.get_json(silent=True) or {}
    session = ChatSession.query.filter_by(session_key=session_key).first()
    if not session:
        return jsonify({"error": "セッションが見つかりません。"}), 404
    if session.user_id and session.user_id != current_user.id:
        return jsonify({"error": "このセッションにアクセスできません。"}), 403

    current = dict(session.collected_data or {})
    for key in ("goal", "level", "weak_points", "count", "other_requests"):
        if key not in data:
            continue
        value = data[key]
        if key == "count":
            try:
                value = int(value)
            except (TypeError, ValueError):
                return jsonify({"error": "countは数値で指定してください。"}), 400
            if not 1 <= value <= MAX_WORD_COUNT:
                return jsonify({
                    "error": f"countは1〜{MAX_WORD_COUNT}の範囲で指定してください。"
                }), 400
        else:
            value = str(value).strip()
            if len(value) > MAX_FIELD_LENGTH:
                return jsonify({
                    "error": f"{key}が長すぎます（最大{MAX_FIELD_LENGTH}文字）。"
                }), 400
            if has_prompt_injection(value):
                return jsonify({"error": INJECTION_ERROR_MESSAGE}), 400
        current[key] = value

    session.collected_data = current
    required = ["goal", "level", "weak_points", "count"]
    if all(current.get(k) for k in required):
        session.status = "completed"
    else:
        session.status = "collecting"
    db.session.commit()

    return jsonify({"collected_data": session.collected_data, "status": session.status})


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
            "other_requests": "例文多め",
            "count": 20,
            "chat_history": [{"role": "user", "content": "..."}, ...]
        }
    """
    data = request.get_json(silent=True) or {}
    goal = data.get("goal", "").strip()
    level = data.get("level", "").strip()
    weak_points = data.get("weak_points", "").strip()
    other_requests = data.get("other_requests", "").strip()
    chat_history = data.get("chat_history", [])

    try:
        count = int(data.get("count", 20))
    except (TypeError, ValueError):
        return jsonify({"error": "countは数値で指定してください。"}), 400
    count = min(max(count, 1), MAX_WORD_COUNT)

    if not goal:
        return jsonify({"error": "学習目標を入力してください。"}), 400

    # 長さ・インジェクション検証
    for field_name, value in (
        ("goal", goal),
        ("level", level),
        ("weak_points", weak_points),
        ("other_requests", other_requests),
    ):
        if len(value) > MAX_FIELD_LENGTH:
            return jsonify({
                "error": f"{field_name}が長すぎます（最大{MAX_FIELD_LENGTH}文字）。"
            }), 400
        if has_prompt_injection(value):
            return jsonify({"error": INJECTION_ERROR_MESSAGE}), 400

    ok, msg = validate_chat_history(chat_history)
    if not ok:
        return jsonify({"error": msg}), 400

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
            other_requests=other_requests,
        )
    except AIServiceError as e:
        return jsonify({"error": str(e)}), 500

    words = result.get("words", [])
    if not words:
        return jsonify({
            "error": "AIの出力を検証できませんでした。",
            "details": result.get("errors", []),
        }), 502

    wordlist = WordList(
        user_id=current_user.id,
        title=result.get("title", "マイ単語帳"),
        goal=goal,
        level=level,
        weak_points=weak_points,
    )
    db.session.add(wordlist)
    db.session.flush()

    for w in words:
        word = Word(
            wordlist_id=wordlist.id,
            word=w.get("word", ""),
            meaning=w.get("meaning", ""),
            example=w.get("example", ""),
            example_ja=w.get("example_ja", ""),
            note=w.get("note", ""),
            reason=w.get("reason", ""),
            difficulty=w.get("difficulty", ""),
            category=w.get("category", ""),
        )
        db.session.add(word)
        db.session.flush()  # word.id を取得
        w["id"] = word.id

    current_user.increment_generation()
    db.session.commit()

    return jsonify({
        "wordlist_id": wordlist.id,
        "title": wordlist.title,
        "words": words,
        "errors": result.get("errors", []),
        "remaining": current_user.get_monthly_limit() - current_user.monthly_generation_count,
    })


@chat_bp.route("/api/wordlists/<int:wordlist_id>/words", methods=["POST"])
@login_required
def add_word(wordlist_id: int):
    """単語帳に単語を追加する。"""
    wordlist = WordList.query.filter_by(
        id=wordlist_id, user_id=current_user.id
    ).first_or_404()

    data = request.get_json(silent=True) or {}
    word_text = (data.get("word") or "").strip()
    if not word_text:
        return jsonify({"error": "単語を入力してください。"}), 400

    word = Word(
        wordlist_id=wordlist.id,
        word=word_text,
        meaning=(data.get("meaning") or "").strip(),
        example=(data.get("example") or "").strip(),
        example_ja=(data.get("example_ja") or "").strip(),
        note=(data.get("note") or "").strip(),
        reason=(data.get("reason") or "").strip(),
        difficulty=(data.get("difficulty") or "").strip(),
        category=(data.get("category") or "").strip(),
    )
    db.session.add(word)
    db.session.commit()
    return jsonify({"id": word.id, "word": word.word}), 201


@chat_bp.route("/api/wordlists/<int:wordlist_id>/words/<int:word_id>", methods=["PUT"])
@login_required
def edit_word(wordlist_id: int, word_id: int):
    """単語を編集する。"""
    word = Word.query.join(WordList).filter(
        Word.id == word_id,
        WordList.id == wordlist_id,
        WordList.user_id == current_user.id,
    ).first_or_404()

    data = request.get_json(silent=True) or {}
    for key in ("word", "meaning", "example", "example_ja", "note", "reason", "difficulty", "category"):
        if key in data:
            setattr(word, key, (data[key] or "").strip())
    db.session.commit()
    return jsonify({"ok": True})


@chat_bp.route("/api/wordlists/<int:wordlist_id>/words/<int:word_id>", methods=["DELETE"])
@login_required
def delete_word(wordlist_id: int, word_id: int):
    """単語を削除する。"""
    word = Word.query.join(WordList).filter(
        Word.id == word_id,
        WordList.id == wordlist_id,
        WordList.user_id == current_user.id,
    ).first_or_404()
    db.session.delete(word)
    db.session.commit()
    return jsonify({"ok": True})
