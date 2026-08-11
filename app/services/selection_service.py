"""単語選定ロジック。

フロー:
1. 試験特定 → exam_id
2. 候補抽出: exam_word_stats から頻度>0の単語を取得
3. ドメインルール適用: excludeカテゴリ除外、prioritizeを優先マーク
4. 既習除外: ユーザーの全wordbooksに存在する単語を除外
5. 苦手補正: user_word_history の mastery_score 低い単語を優先
6. AI選定: 候補をDeepSeekに渡し50語を選定
"""
import json
from flask import current_app
from app.extensions import db
from app.models.word_master import WordMaster, Meaning, Tag, WordTag
from app.models.exam import Exam, ExamWordStat, ExamDomainRule
from app.models.folder import Folder, Wordbook, WordbookWord, UserWordHistory
from app.services.ai_service import AIService, AIServiceError


class SelectionServiceError(Exception):
    """選定サービスで発生するエラー。"""


class SelectionService:
    """試験分析に基づく単語選定。"""

    def __init__(self, user):
        self.user = user

    def select_words(self, exam_id: int, count: int = 50, weak_points: str = "") -> dict:
        """
        指定試験・ユーザーに最適な単語を選定する。

        Returns:
            {
                "title": str,
                "exam_id": int,
                "words": [{"word_master_id", "lemma", "meaning_ja", "reason", ...}]
            }
        """
        exam = Exam.query.get(exam_id)
        if not exam:
            raise SelectionServiceError("試験が見つかりません。")

        # 1. 候補抽出（頻度>0）
        candidates = self._extract_candidates(exam_id)
        if not candidates:
            raise SelectionServiceError(
                f"{exam.name}の候補単語が登録されていません。`flask scrape-exam` でデータを投入してください。"
            )

        # 2. ドメインルール適用
        candidates = self._apply_domain_rules(exam_id, candidates)

        # 3. 既習除外
        learned_ids = self._get_learned_word_ids()
        candidates = [c for c in candidates if c["word_master_id"] not in learned_ids]
        if not candidates:
            raise SelectionServiceError(
                "既習の単語が多く、新規候補がありません。他の試験を選ぶか、既習単語を含めて生成してください。"
            )

        # 4. 苦手補正（mastery_score 低い単語を優先）
        weak_ids = self._get_weak_word_ids()
        for c in candidates:
            c["is_weak"] = c["word_master_id"] in weak_ids

        # 5. AI選定
        ai = AIService()
        selected = self._ai_select(
            exam=exam,
            candidates=candidates,
            count=min(count, 200),
            weak_points=weak_points,
        )
        return selected

    def _extract_candidates(self, exam_id: int) -> list:
        """試験別の候補単語リストを抽出する。"""
        stats = (
            ExamWordStat.query.filter_by(exam_id=exam_id)
            .filter(ExamWordStat.frequency_score > 0)
            .order_by(ExamWordStat.frequency_score.desc())
            .limit(500)
            .all()
        )
        candidates = []
        for stat in stats:
            word = stat.word
            if not word:
                continue
            meaning = ""
            if word.meanings.count():
                meaning = word.meanings.first().meaning_ja
            # タグ取得
            tags = [wt.tag.name for wt in word.tags.all() if wt.tag]
            candidates.append({
                "word_master_id": word.id,
                "lemma": word.lemma,
                "meaning_ja": meaning,
                "frequency_score": stat.frequency_score or 0,
                "tags": tags,
            })
        return candidates

    def _apply_domain_rules(self, exam_id: int, candidates: list) -> list:
        """ドメインルールを適用する。"""
        rules = ExamDomainRule.query.filter_by(exam_id=exam_id).all()
        exclude_categories = {r.category for r in rules if r.rule_type == "exclude"}
        prioritize_categories = {r.category for r in rules if r.rule_type == "prioritize"}

        filtered = []
        for c in candidates:
            # 除外カテゴリに一致する単語はスキップ
            if exclude_categories & set(c["tags"]):
                continue
            c["is_prioritized"] = bool(prioritize_categories & set(c["tags"]))
            filtered.append(c)
        return filtered

    def _get_learned_word_ids(self) -> set:
        """ユーザーの既習単語IDを取得する。"""
        wordbooks = Wordbook.query.filter_by(user_id=self.user.id).all()
        ids = set()
        for wb in wordbooks:
            for ww in wb.words.all():
                ids.add(ww.word_master_id)
        return ids

    def _get_weak_word_ids(self) -> set:
        """ユーザーの苦手単語IDを取得する（mastery_score が 0.4 未満）。"""
        histories = (
            UserWordHistory.query.filter_by(user_id=self.user.id)
            .filter(UserWordHistory.mastery_score < 0.4)
            .all()
        )
        return {h.word_master_id for h in histories}

    def _ai_select(self, exam: Exam, candidates: list, count: int, weak_points: str) -> dict:
        """DeepSeekに候補を渡して最適な単語を選定させる。"""
        ai = AIService()
        system_prompt = (
            "あなたは英単語学習のエキスパートです。\n"
            "与えられた候補単語リストから、指定されたユーザーに最適な単語を厳選してください。\n"
            f"目標試験: {exam.name}\n"
            f"ユーザー苦手分野: {weak_points or '特になし'}\n\n"
            "要件:\n"
            "- 選定した各単語に選定理由（reason）を40字以内で付与すること\n"
            "- ユーザーの苦手分野を重点的にカバーすること\n"
            "- 意味カテゴリが偏らないよう分散させること\n"
            "- is_prioritized=True の単語を優先的に選ぶこと\n"
            "- is_weak=True の単語を優先的に選ぶこと\n"
            "- 必ず実在する単語のみを選ぶこと\n"
            "必ず以下のJSON形式で返してください。\n"
            "{\n"
            '  "title": "単語帳タイトル",\n'
            '  "words": [\n'
            "    {\n"
            '      "word_master_id": 数字,\n'
            '      "reason": "選定理由",\n'
            "    }\n"
            "  ]\n"
            "}\n"
        )

        # 候補をプロンプトに整形（頻度上位200語に制限）
        limited = candidates[:200]
        candidate_text = "\n".join(
            f"id={c['word_master_id']} | {c['lemma']} | {c['meaning_ja']} | "
            f"freq={c['frequency_score']:.0f} | tags={','.join(c['tags'])} | "
            f"prioritized={c.get('is_prioritized', False)} | weak={c.get('is_weak', False)}"
            for c in limited
        )
        user_prompt = (
            f"候補単語リスト（{len(limited)}語）:\n{candidate_text}\n\n"
            f"この中から {count} 語を選んでください。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = ai.client.chat.completions.create(
                model=ai.model,
                messages=messages,
                temperature=0.4,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            result = ai._parse_response(content)
        except Exception as e:
            raise SelectionServiceError(f"AI選定に失敗しました: {e}")

        # 選定された単語をマージ
        selected_words = []
        cand_map = {c["word_master_id"]: c for c in candidates}
        for w in result.get("words", [])[:count]:
            wm_id = int(w.get("word_master_id", 0))
            cand = cand_map.get(wm_id)
            if not cand:
                continue
            selected_words.append({
                "word_master_id": wm_id,
                "lemma": cand["lemma"],
                "meaning_ja": cand["meaning_ja"],
                "reason": w.get("reason", ""),
                "tags": cand["tags"],
            })

        return {
            "title": result.get("title", f"{exam.name}対策 単語帳"),
            "exam_id": exam.id,
            "words": selected_words,
        }
