import csv
import io


class CSVService:
    """単語リストをAnki互換CSVに変換する。"""

    @staticmethod
    def to_anki_csv(words: list) -> str:
        """
        単語リストをAnki互換CSV文字列に変換する。

        Ankiの基本ノートタイプ（Basic）に合わせて:
        表: 英単語
        裏: 日本語訳 + 例文 + 選定理由 + 難易度 + カテゴリ + 補足

        Args:
            words: [{"word", "meaning", "example", "example_ja", "note", "reason", "difficulty", "category"}, ...]

        Returns:
            CSV文字列（UTF-8 BOM付き）
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        for w in words:
            front = w.get("word", "").strip()
            back_parts = [w.get("meaning", "").strip()]

            if w.get("difficulty"):
                back_parts.append(f"難易度: {w['difficulty']}")
            if w.get("category"):
                back_parts.append(f"カテゴリ: {w['category']}")
            if w.get("example"):
                back_parts.append(f"例文: {w['example']}")
            if w.get("example_ja"):
                back_parts.append(f"訳: {w['example_ja']}")
            if w.get("reason"):
                back_parts.append(f"選定理由: {w['reason']}")
            if w.get("note"):
                back_parts.append(f"補足: {w['note']}")

            back = "<br>".join(back_parts)
            writer.writerow([front, back])

        # BOM付きUTF-8で返す（Excel/Ankiでの文字化け防止）
        csv_content = output.getvalue()
        return "\ufeff" + csv_content
