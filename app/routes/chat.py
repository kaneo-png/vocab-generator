import json
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.wordlist import WordList
from app.models.word import Word
from app.models.chat_session import ChatSession
from app.services.ai_service import AIService, AIServiceError

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

    # AIに最初の質問を生成させる
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
    except AIServiceError as e:
        # AI呼び出し失敗時はデフォルトの最初の質問で継続
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

    session = ChatSession.query.filter_by(session_key=session_key).first()
    if not session:
        return jsonify({"error": "セッションが見つかりません。"}), 404

    # ユーザー発言を履歴に追加
    session.append_message("user", user_message)

    try:
        ai = AIService()
        result = ai.analyze_and_respond(
            messages=session.messages or [],
            collected_data=session.collected_data or {},
        )
    except AIServiceError as e:
        return jsonify({"error": str(e)}), 500

    # AI応答を履歴に追加
    reply = result["message_to_user"] or "もう少し詳しく教えてください。"
    session.append_message("assistant", reply)
    session.collected_data = result["collected_data"]

    # 5項目が揃ったら completed にする
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
        if key in data:
            current[key] = data[key]

    session.collected_data = current
    # 修正後に必須項目が揃えば completed にする
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