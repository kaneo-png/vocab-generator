"""ゲスト生成・メール認証・プラン機能ゲートのテスト。"""
from unittest.mock import patch

from app.extensions import db
from app.models.user import User
from app.models.wordlist import WordList


MOCK_GENERATE_RESULT = {
    "title": "テスト単語帳",
    "words": [
        {
            "word": "apple",
            "meaning": "りんご",
            "example": "",
            "example_ja": "",
            "note": "",
            "reason": "テストのため選定",
            "difficulty": "A1",
            "category": "food",
        }
    ],
    "errors": [],
}

VALID_GENERATE = {
    "goal": "英検1級合格",
    "level": "中級",
    "weak_points": "長文読解",
    "count": 5,
}


# ===== ゲスト生成 =====

class TestGuestGeneration:
    def test_guest_can_generate_but_limited(self, client):
        """ゲストは上限まで生成でき、超えるとログインを要求される。"""
        with patch("app.services.ai_service.AIService.generate_wordlist", return_value=MOCK_GENERATE_RESULT):
            # 1回目
            res = client.post("/api/chat/generate", json=VALID_GENERATE)
            assert res.status_code == 200
            data = res.get_json()
            assert data["remaining"] == 1

            # 2回目
            res = client.post("/api/chat/generate", json=VALID_GENERATE)
            assert res.status_code == 200
            assert res.get_json()["remaining"] == 0

            # 3回目は拒否
            res = client.post("/api/chat/generate", json=VALID_GENERATE)
            assert res.status_code == 403
            data = res.get_json()
            assert data.get("login_required") is True

    def test_guest_generate_creates_guest_wordlist(self, client):
        """ゲストの生成した単語帳は user_id=None で保存される。"""
        with patch("app.services.ai_service.AIService.generate_wordlist", return_value=MOCK_GENERATE_RESULT):
            res = client.post("/api/chat/generate", json=VALID_GENERATE)
            assert res.status_code == 200
            wl_id = res.get_json()["wordlist_id"]

        with client.session_transaction() as sess:
            assert wl_id in sess.get("guest_wordlist_ids", [])

        wl = db.session.get(WordList, wl_id)
        assert wl.user_id is None


# ===== メール認証 =====

class TestEmailVerification:
    def test_register_creates_unverified_user(self, client, app):
        """登録直後は未認証で、検証トークンが発行される。"""
        res = client.post("/register", data={
            "email": "verify@example.com",
            "password": "password123",
            "confirm_password": "password123",
        }, follow_redirects=True)
        assert res.status_code == 200

        with app.app_context():
            user = User.query.filter_by(email="verify@example.com").first()
            assert user is not None
            assert user.email_verified is False
            assert user.verification_token is not None

    def test_verify_email_with_valid_token(self, client, app):
        """正しいトークンで認証が完了する。"""
        with app.app_context():
            user = User(email="verify2@example.com")
            user.set_password("password123")
            user.verification_token = "test-token-123"
            from datetime import datetime, timedelta, timezone
            user.verification_token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
            db.session.add(user)
            db.session.commit()

        res = client.get("/verify/test-token-123", follow_redirects=True)
        assert res.status_code == 200

        with app.app_context():
            user = User.query.filter_by(email="verify2@example.com").first()
            assert user.email_verified is True
            assert user.verification_token is None

    def test_verify_email_with_invalid_token(self, client):
        """不正なトークンでは認証されない。"""
        res = client.get("/verify/wrong-token", follow_redirects=True)
        assert res.status_code == 200  # ログインページへ

    def test_unverified_user_cannot_generate(self, client, app):
        """未認証ユーザーは生成できない（verification_required）。"""
        with app.app_context():
            user = User(email="unverified@example.com")
            user.set_password("password123")
            user.email_verified = False
            db.session.add(user)
            db.session.commit()
            uid = user.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(uid)
            sess["_fresh"] = True

        res = client.post("/api/chat/generate", json=VALID_GENERATE)
        assert res.status_code == 403
        data = res.get_json()
        assert data.get("verification_required") is True

    def test_verified_user_can_generate(self, client, app):
        """認証済みユーザーは生成できる。"""
        with app.app_context():
            user = User(email="verified@example.com")
            user.set_password("password123")
            user.email_verified = True
            db.session.add(user)
            db.session.commit()
            uid = user.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(uid)
            sess["_fresh"] = True

        with patch("app.services.ai_service.AIService.generate_wordlist", return_value=MOCK_GENERATE_RESULT):
            res = client.post("/api/chat/generate", json=VALID_GENERATE)
            assert res.status_code == 200


# ===== プラン機能ゲート =====

class TestPlanFeatureGate:
    def test_free_user_master_api_denied(self, logged_in_client):
        """freeユーザーはマスターAPIを利用できない（403）。"""
        res = logged_in_client.post("/api/master/folders", json={"name": "test"})
        assert res.status_code == 403

    def test_free_user_cannot_edit_word(self, client, app):
        """freeユーザーは単語編集ができない（403）。"""
        with app.app_context():
            user = User(email="free-edit@example.com")
            user.set_password("password123")
            user.plan = "free"
            db.session.add(user)
            db.session.flush()
            wl = WordList(user_id=user.id, title="リスト")
            db.session.add(wl)
            db.session.commit()
            uid, wl_id = user.id, wl.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(uid)
            sess["_fresh"] = True

        res = client.post(f"/api/wordlists/{wl_id}/words", json={"word": "test"})
        assert res.status_code == 403

    def test_ad_free_can_edit_word(self, ad_free_logged_in_client, app, test_user):
        """ad_freeユーザーは単語追加ができる。"""
        with app.app_context():
            wl = WordList(user_id=test_user, title="リスト")
            db.session.add(wl)
            db.session.commit()
            wl_id = wl.id

        res = ad_free_logged_in_client.post(
            f"/api/wordlists/{wl_id}/words",
            json={"word": "example", "meaning": "例"},
        )
        assert res.status_code == 201
