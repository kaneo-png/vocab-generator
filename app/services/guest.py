"""ゲスト（未ログイン）セッション関連のヘルパー。"""
from flask import session
from app.extensions import db
from app.models.wordlist import WordList


def get_guest_generation_count() -> int:
    """ゲストの累計生成回数を返す。"""
    return session.get("guest_generation_count", 0)


def increment_guest_generation() -> int:
    """ゲストの生成回数を1増やし、新しい値を返す。"""
    count = session.get("guest_generation_count", 0) + 1
    session["guest_generation_count"] = count
    session.modified = True
    return count


def add_guest_wordlist(wordlist_id: int) -> None:
    """ゲストが生成した単語帳IDをセッションに記録する。"""
    ids = session.get("guest_wordlist_ids", [])
    if wordlist_id not in ids:
        ids.append(wordlist_id)
    session["guest_wordlist_ids"] = ids
    session.modified = True


def is_guest_wordlist_owner(wordlist_id: int) -> bool:
    """指定IDの単語帳がゲストセッションのものかを判定する。"""
    return wordlist_id in session.get("guest_wordlist_ids", [])


def migrate_guest_wordlists(user) -> None:
    """ゲストが生成した単語帳をアカウントへ紐付け、ゲスト状態をクリアする。"""
    ids = session.get("guest_wordlist_ids", [])
    migrated = 0
    if ids:
        for wid in ids:
            wl = db.session.get(WordList, wid)
            if wl and wl.user_id is None:
                wl.user_id = user.id
                migrated += 1
        db.session.commit()
    session.pop("guest_wordlist_ids", None)
    session.pop("guest_generation_count", None)
    session.modified = True
    return migrated
