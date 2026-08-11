import re

# ハルシネーション防止・データ品質チェック用のバリデーション

ALLOWED_DIFFICULTIES = {"A1", "A2", "B1", "B2", "C1", "C2"}

# 英単語として妥当な文字列か（英字・ハイフン・アポストロフィのみ）
_WORD_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z\-']*$")


def validate_word(word: str) -> tuple[bool, str]:
    """単語が実在しそうな英単語の形式かを検証する。"""
    word = (word or "").strip()
    if not word:
        return False, "単語が空です。"
    if not _WORD_PATTERN.match(word):
        return False, f"「{word}」は英単語の形式ではありません（英字・ハイフン・アポストロフィのみ）。"
    return True, ""


def validate_difficulty(difficulty: str) -> tuple[bool, str]:
    """難易度がA1〜C2の範囲かを検証する。"""
    difficulty = (difficulty or "").strip().upper()
    if difficulty and difficulty not in ALLOWED_DIFFICULTIES:
        return False, f"難易度は {', '.join(sorted(ALLOWED_DIFFICULTIES))} のいずれかにしてください。"
    return True, ""


def validate_reason(reason: str) -> tuple[bool, str]:
    """選定理由が含まれているか検証する。"""
    reason = (reason or "").strip()
    if len(reason) < 10:
        return False, "選定理由（reason）が短すぎます。ユーザーの目標と紐づけた理由を記入してください。"
    return True, ""


def sanitize_wordlist(words: list) -> tuple[list, list]:
    """
    AIから返された単語リストを検証・整形する。

    Returns:
        (valid_words, errors): 有効な単語リストと、除外された単語のエラーメッセージ
    """
    valid_words = []
    errors = []
    seen_words = set()

    for i, w in enumerate(words):
        word = (w.get("word") or "").strip()

        # 英単語形式チェック
        ok, msg = validate_word(word)
        if not ok:
            errors.append(f"#{i+1}: {msg}")
            continue

        # 重複チェック
        lower = word.lower()
        if lower in seen_words:
            errors.append(f"#{i+1}: 「{word}」は重複しています。")
            continue
        seen_words.add(lower)

        # 難易度チェック（空なら補完しない＝後でカテゴリだけチェック）
        difficulty = (w.get("difficulty") or "").strip().upper()
        ok, msg = validate_difficulty(difficulty)
        if not ok:
            errors.append(f"#{i+1}: {msg}")
            difficulty = ""

        # 選定理由の存在チェック（必須）
        reason = (w.get("reason") or "").strip()
        ok, msg = validate_reason(reason)
        if not ok:
            errors.append(f"#{i+1}: {msg}")
            # reasonが無い単語も許容せず除外
            continue

        valid_words.append({
            "word": word,
            "meaning": (w.get("meaning") or "").strip(),
            "example": (w.get("example") or "").strip(),
            "example_ja": (w.get("example_ja") or "").strip(),
            "note": (w.get("note") or "").strip(),
            "reason": reason,
            "difficulty": difficulty,
            "category": (w.get("category") or "").strip(),
        })

    return valid_words, errors
