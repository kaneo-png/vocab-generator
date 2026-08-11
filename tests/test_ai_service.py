"""AIService._parse_response のテスト（API呼び出しは行わない）。"""

import pytest

from app.services.ai_service import AIService, AIServiceError


def test_parse_plain_json(app):
    """素のJSONがパースできる。"""
    content = (
        '{"title": "基本英単語", "words": ['
        '{"word": "apple", "meaning": "りんご", "example": "I eat an apple.", '
        '"example_ja": "私はりんごを食べます。", "note": "果物"}]}'
    )
    result = AIService()._parse_response(content)
    assert result["title"] == "基本英単語"
    assert result["words"][0]["word"] == "apple"


def test_parse_markdown_code_block(app):
    """```json で囲まれたJSONがパースできる。"""
    content = (
        "```json\n"
        '{"title": "T", "words": [{"word": "cat", "meaning": "猫"}]}\n'
        "```"
    )
    result = AIService()._parse_response(content)
    assert result["words"][0]["meaning"] == "猫"


def test_parse_markdown_code_block_without_lang(app):
    """言語指定なしのコードブロックで囲まれていてもパースできる。"""
    content = (
        "```\n"
        '{"title": "T", "words": [{"word": "cat", "meaning": "猫"}]}\n'
        "```"
    )
    result = AIService()._parse_response(content)
    assert result["words"][0]["meaning"] == "猫"


def test_parse_with_surrounding_text(app):
    """前後に余計なテキストが付いていてもパースできる。"""
    content = (
        "以下が生成結果です。\n"
        '{"title": "T", "words": [{"word": "dog", "meaning": "犬"}]}\n'
        "いかがでしょうか？"
    )
    result = AIService()._parse_response(content)
    assert result["title"] == "T"


def test_parse_trailing_commas(app):
    """末尾カンマを含む壊れたJSONを修復してパースできる。"""
    content = (
        '{"title": "T", "words": [{"word": "book", "meaning": "本", "note": "名詞",}]}'
    )
    result = AIService()._parse_response(content)
    assert result["words"][0]["word"] == "book"


def test_parse_python_literals(app):
    """Python形式のNone/TrueがJSON形式に直される。"""
    content = (
        '{"title": "T", "words": [{"word": "run", "meaning": None, "active": True}]}'
    )
    result = AIService()._parse_response(content)
    assert result["words"][0]["meaning"] is None
    assert result["words"][0]["active"] is True


def test_parse_wrapped_result(app):
    """余計なラッパーに包まれていてもwords配列を探し出す。"""
    content = '{"result": {"title": "T", "words": [{"word": "go"}]}}'
    result = AIService()._parse_response(content)
    assert result["words"][0]["word"] == "go"


def test_parse_no_words_raises(app):
    """words配列がない場合は専用エラーになる。"""
    with pytest.raises(AIServiceError, match="words配列が含まれていません"):
        AIService()._parse_response('{"title": "T", "message": "hello"}')


def test_parse_garbage_raises(app):
    """JSONを一切含まない応答はエラーになる。"""
    with pytest.raises(AIServiceError, match="JSONパースに失敗"):
        AIService()._parse_response("申し訳ありません、エラーが発生しました。")


def test_parse_empty_raises(app):
    """空の応答はエラーになる。"""
    with pytest.raises(AIServiceError, match="空でした"):
        AIService()._parse_response("")
