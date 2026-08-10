import csv
import io

from app.services.csv_service import CSVService


def test_to_anki_csv_basic():
    """基本的なCSV変換が正しく行われる。"""
    words = [
        {
            "word": "apple",
            "meaning": "りんご",
            "example": "I eat an apple.",
            "example_ja": "私はりんごを食べます。",
            "note": "果物",
        }
    ]

    result = CSVService.to_anki_csv(words)

    # BOM付きUTF-8
    assert result.startswith("\ufeff")

    # CSVとしてパース可能
    reader = csv.reader(io.StringIO(result.lstrip("\ufeff")))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0][0] == "apple"
    assert "りんご" in rows[0][1]
    assert "I eat an apple." in rows[0][1]
    assert "私はりんごを食べます。" in rows[0][1]
    assert "果物" in rows[0][1]


def test_to_anki_csv_multiple_words():
    """複数単語のCSV変換が正しく行われる。"""
    words = [
        {"word": "cat", "meaning": "猫", "example": "", "example_ja": "", "note": ""},
        {"word": "dog", "meaning": "犬", "example": "", "example_ja": "", "note": ""},
    ]

    result = CSVService.to_anki_csv(words)
    reader = csv.reader(io.StringIO(result.lstrip("\ufeff")))
    rows = list(reader)
    assert len(rows) == 2
    assert rows[0][0] == "cat"
    assert rows[1][0] == "dog"


def test_to_anki_csv_empty_fields():
    """空フィールドが正しく処理される。"""
    words = [
        {"word": "book", "meaning": "本", "example": "", "example_ja": "", "note": ""}
    ]

    result = CSVService.to_anki_csv(words)
    reader = csv.reader(io.StringIO(result.lstrip("\ufeff")))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0][0] == "book"
    # 例文・補足がない場合は意味のみ
    assert rows[0][1] == "本"