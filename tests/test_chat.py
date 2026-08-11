import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_create_session(logged_in_client):
    """セッション作成APIが動作する。"""
    res = logged_in_client.post("/api/chat/session")
    assert res.status_code == 200
    data = res.get_json()
    assert data["session_key"]
    assert data["message"]


def test_get_session(logged_in_client):
    """作成したセッションを取得できる。"""
    create = logged_in_client.post("/api/chat/session")
    session_key = create.get_json()["session_key"]

    res = logged_in_client.get(f"/api/chat/session/{session_key}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["session_key"] == session_key
    assert "messages" in data
    assert "collected_data" in data


def test_update_session(logged_in_client):
    """収集データを修正できる。"""
    create = logged_in_client.post("/api/chat/session")
    session_key = create.get_json()["session_key"]

    res = logged_in_client.put(
        f"/api/chat/session/{session_key}",
        json={"goal": "TOEIC 900点", "level": "中級"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["collected_data"]["goal"] == "TOEIC 900点"
    assert data["collected_data"]["level"] == "中級"


def test_message_requires_key(logged_in_client):
    """セッションキーなしのメッセージ送信は400。"""
    res = logged_in_client.post("/api/chat/message", json={"message": "こんにちは"})
    assert res.status_code == 400


def test_message_with_unknown_session(logged_in_client):
    """存在しないセッションキーは404。"""
    res = logged_in_client.post(
        "/api/chat/message", json={"session_key": "nonexistent", "message": "こんにちは"}
    )
    assert res.status_code == 404
