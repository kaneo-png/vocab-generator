import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.validation import (
    validate_word,
    validate_difficulty,
    validate_reason,
    sanitize_wordlist,
)


def test_validate_word_valid():
    ok, _ = validate_word("meticulous")
    assert ok
    ok, _ = validate_word("well-known")
    assert ok
    ok, _ = validate_word("don't")
    assert ok


def test_validate_word_invalid():
    # 日本語・数字・記号を含む単語は弾く
    ok, _ = validate_word("りんご")
    assert not ok
    ok, _ = validate_word("word123")
    assert not ok
    ok, _ = validate_word("")
    assert not ok


def test_validate_difficulty():
    for d in ("A1", "B2", "C1"):
        ok, _ = validate_difficulty(d)
        assert ok
    ok, _ = validate_difficulty("D3")
    assert not ok
    ok, _ = validate_difficulty("")
    assert ok


def test_validate_reason():
    ok, _ = validate_reason("TOEIC頻出でビジネスメールでよく使われるため")
    assert ok
    ok, _ = validate_reason("短い")
    assert not ok


def test_sanitize_wordlist_deduplicates():
    words = [
        {"word": "Apple", "meaning": "りんご", "reason": "日常生活で頻出のため"},
        {"word": "apple", "meaning": "りんご(重複)", "reason": "重複テスト"},
        {"word": "banana", "meaning": "バナナ", "reason": "果物の中でも最もよく使われる基本単語のため"},
    ]
    valid, errors = sanitize_wordlist(words)
    assert len(valid) == 2  # 重複は除外
    assert len(errors) == 1


def test_sanitize_wordlist_removes_invalid():
    words = [
        {"word": "犬", "meaning": "犬", "reason": "日本語のため除外される"},
        {"word": "valid", "meaning": "有効", "reason": "正しい英語形式を持ち意味も明確な単語のため", "difficulty": "B2"},
    ]
    valid, errors = sanitize_wordlist(words)
    assert len(valid) == 1
    assert valid[0]["word"] == "valid"
    assert valid[0]["difficulty"] == "B2"


def test_sanitize_wordlist_requires_reason():
    words = [{"word": "example", "meaning": "例", "reason": ""}]
    valid, errors = sanitize_wordlist(words)
    assert len(valid) == 0  # reason がない単語は除外
    assert len(errors) == 1
