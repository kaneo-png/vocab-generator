"""CSVダウンロードの回帰テスト。

日本語の単語帳タイトルを含むCSVダウンロードが
UnicodeEncodeError（latin-1 エンコード問題）で失敗しないことを検証する。
"""

from app.extensions import db
from app.models.user import User
from app.models.wordlist import WordList
from app.models.word import Word


def _create_user_with_wordlist(app):
    """日本語タイトルの単語帳を持つユーザーを作成する。"""
    with app.app_context():
        user = User(email="csv-test@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()

        wordlist = WordList(
            user_id=user.id,
            title="英検準一級対策 必須単語",
            goal="英検準一級合格",
            level="上級",
        )
        db.session.add(wordlist)
        db.session.flush()

        db.session.add(
            Word(
                wordlist_id=wordlist.id,
                word="example",
                meaning="例",
                example="This is an example.",
            )
        )
        db.session.commit()
        return user.id, wordlist.id


def test_csv_download_with_japanese_filename(client, app):
    """日本語ファイル名のCSVが正常にダウンロードできる。"""
    user_id, wordlist_id = _create_user_with_wordlist(app)

    # ログイン
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    response = client.get(f"/api/wordlists/{wordlist_id}/csv")
    assert response.status_code == 200

    # Content-Disposition が RFC 5987 形式で日本語対応している
    disposition = response.headers.get("Content-Disposition", "")
    assert "filename*=UTF-8''" in disposition
    assert disposition.count("%") > 0  # 日本語がURLエンコードされている

    # CSV内容にBOMと単語が含まれる
    data = response.get_data()
    assert data.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    body = data.decode("utf-8-sig")
    assert "example" in body
    assert "例" in body


def test_csv_download_requires_login(client, app):
    """未ログインでは他人の単語帳CSVをダウンロードできない（403）。"""
    _, wordlist_id = _create_user_with_wordlist(app)
    response = client.get(f"/api/wordlists/{wordlist_id}/csv")
    assert response.status_code == 403


def test_csv_download_foreign_wordlist_denied(client, app):
    """他人の単語帳はダウンロードできない（403）。"""
    user_id, wordlist_id = _create_user_with_wordlist(app)

    # 別ユーザーでログイン
    other = User(email="other@example.com")
    other.set_password("password123")
    db.session.add(other)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(other.id)
        sess["_fresh"] = True

    response = client.get(f"/api/wordlists/{wordlist_id}/csv")
    assert response.status_code == 403


def test_csv_download_guest_own_wordlist_ok(client, app):
    """ゲストが自分で生成した単語帳はCSVダウンロードできる。"""
    with app.app_context():
        wl = WordList(
            user_id=None,
            title="ゲストの単語帳",
            goal="テスト",
        )
        db.session.add(wl)
        db.session.flush()
        db.session.add(Word(
            wordlist_id=wl.id, word="apple", meaning="りんご",
        ))
        db.session.commit()
        wl_id = wl.id

    # セッションにゲストの単語帳IDを記録
    with client.session_transaction() as sess:
        sess["guest_wordlist_ids"] = [wl_id]

    response = client.get(f"/api/wordlists/{wl_id}/csv")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "apple" in body


def test_csv_download_guest_foreign_wordlist_denied(client, app):
    """セッションに無いゲスト単語帳はダウンロードできない（403）。"""
    with app.app_context():
        wl = WordList(
            user_id=None,
            title="他人のゲスト単語帳",
            goal="テスト",
        )
        db.session.add(wl)
        db.session.commit()
        wl_id = wl.id

    response = client.get(f"/api/wordlists/{wl_id}/csv")
    assert response.status_code == 403
