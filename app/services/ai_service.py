import json
import re
from flask import current_app
from openai import OpenAI


class AIServiceError(Exception):
    """AIサービスで発生するエラー。"""


class AIService:
    """DeepSeek API（OpenAI互換）を使って単語リストを生成する。"""

    def __init__(self):
        self.client = OpenAI(
            api_key=current_app.config["DEEPSEEK_API_KEY"],
            base_url=current_app.config["DEEPSEEK_BASE_URL"],
        )
        self.model = current_app.config["DEEPSEEK_MODEL"]

    def generate_wordlist(
        self,
        goal: str,
        level: str,
        weak_points: str,
        count: int = 20,
        chat_history: list = None,
    ) -> dict:
        """
        ユーザーの目標・レベル・苦手分野に基づいて単語リストを生成する。

        Returns:
            {
                "title": str,
                "words": [
                    {
                        "word": str,
                        "meaning": str,
                        "example": str,
                        "example_ja": str,
                        "note": str
                    }
                ]
            }
        """
        if not current_app.config["DEEPSEEK_API_KEY"]:
            raise AIServiceError("DEEPSEEK_API_KEY が設定されていません。")

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            goal=goal, level=level, weak_points=weak_points, count=count
        )

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4000,
            )
            content = response.choices[0].message.content
            return self._parse_response(content)
        except Exception as e:
            raise AIServiceError(f"AI API呼び出しに失敗しました: {e}")

    def _build_system_prompt(self) -> str:
        return (
            "あなたは英語学習の専門家です。ユーザーの目標・レベル・苦手分野に基づいて、"
            "最適な英単語リストを生成してください。\n"
            "必ず以下のJSON形式で返してください。JSON以外のテキストは含めないでください。\n"
            "{\n"
            '  "title": "単語帳のタイトル",\n'
            '  "words": [\n'
            "    {\n"
            '      "word": "英単語",\n'
            '      "meaning": "日本語訳",\n'
            '      "example": "英語の例文",\n'
            '      "example_ja": "例文の日本語訳",\n'
            '      "note": "補足説明（語源・類義語・使い分けなど）"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "単語はユーザーのレベルに合わせて選び、苦手分野を重点的にカバーしてください。"
        )

    def _build_user_prompt(
        self, goal: str, level: str, weak_points: str, count: int
    ) -> str:
        return (
            f"【学習目標】\n{goal}\n\n"
            f"【英語レベル】\n{level}\n\n"
            f"【苦手分野】\n{weak_points}\n\n"
            f"上記の情報に基づいて、{count}個の英単語リストを生成してください。"
        )

    def _parse_response(self, content: str) -> dict:
        """AIのレスポンスからJSONを抽出してパースする。"""
        # コードブロックで囲まれている場合に対応
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # JSONが壊れている場合、最初の { から最後の } までを抽出
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise AIServiceError("AIのレスポンスからJSONを抽出できませんでした。")
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                raise AIServiceError("AIのレスポンスのJSONパースに失敗しました。")

        if "words" not in data or not isinstance(data["words"], list):
            raise AIServiceError("AIのレスポンスにwords配列が含まれていません。")

        return data