"""プロンプトインジェクション対策。

AIへ送信する入力の検証・サニタイズを行い、
無料LLMプロキシ化やシステムプロンプト抽出などの悪用を防ぐ。
"""
import re

# ---- 長さ制限 ----
MAX_MESSAGE_LENGTH = 2000   # チャットメッセージの最大長
MAX_FIELD_LENGTH = 500      # goal / level / weak_points / other_requests の最大長
MAX_WORD_COUNT = 100        # 生成単語数の上限
ALLOWED_ROLES = {"user", "assistant"}

# ---- インジェクションパターン ----
# 明確な注入攻撃のみを検出する（通常の学習会話で誤検知しないよう保守的に設定）
INJECTION_PATTERNS = [
    # --- 英語パターン ---
    re.compile(
        r"\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|messages?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(disregard|forget|override)\s+(all\s+)?(previous|prior|above)?\s*(instructions?|prompts?)\b", re.IGNORECASE),
    re.compile(r"\b(system|developer)\s+prompts?\b", re.IGNORECASE),
    re.compile(r"\breveal?\s+(your|the)\s+(system|developer)\s+prompts?\b", re.IGNORECASE),
    re.compile(r"\b(override|replace|change|modify)\s+(your|the|these)\s+(system|developer|instructions?|rules?)\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\s+(an?|the)\b", re.IGNORECASE),
    re.compile(r"\bignore\s+(the|your|these)\s+(system|instructions?|rules?)\b", re.IGNORECASE),
    # --- 日本語パターン ---
    re.compile(r"(上記|これまで|今までの|すべての|最初の).{0,10}(指示|命令|ルール|プロンプト|設定).{0,15}(無視|無効|変更|破棄|忘れ|やめ)"),
    re.compile(r"(指示|命令|ルール).{0,10}(無視|無効|変更).{0,10}(して|する|で|下さい|ください)"),
    re.compile(r"(システムプロンプト|開発者指示|内部設定|あなたの設定).{0,15}(教え|出力|表示|見せ|漏ら|開示)"),
    re.compile(r"(システムプロンプト|内部指示).{0,10}(何|内容|全文)"),
    re.compile(r"あなたは今から.{0,20}(になって|として行動)"),
]


# 検出用のメッセージ
INJECTION_ERROR_MESSAGE = "不適切な内容が検出されました。メッセージを修正してください。"


def detect_prompt_injection(text: str) -> list:
    """インジェクションパターンに一致する箇所のリストを返す（一致がなければ空リスト）。"""
    if not text:
        return []
    text = text.strip()
    matched = []
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            matched.append(pattern.pattern)
    return matched


def has_prompt_injection(text: str) -> bool:
    """インジェクションパターンが含まれるかを判定する。"""
    return bool(detect_prompt_injection(text))


def validate_chat_history(messages) -> tuple:
    """
    チャット履歴のロールと内容を検証する。

    system/developer ロールを許可しない（システムプロンプト乗っ取り防止）。
    長すぎるメッセージやインジェクションも拒否する。

    Returns:
        (ok: bool, error_message: str)
    """
    if not isinstance(messages, list):
        return False, "チャット履歴の形式が不正です。"

    for m in messages:
        if not isinstance(m, dict):
            return False, "チャット履歴の形式が不正です。"
        role = m.get("role", "")
        if role not in ALLOWED_ROLES:
            return False, f"不正なメッセージロールが含まれています: '{role}'"

        content = m.get("content", "")
        if not isinstance(content, str):
            return False, "メッセージ内容の形式が不正です。"
        if len(content) > MAX_MESSAGE_LENGTH:
            return False, f"メッセージが長すぎます（最大{MAX_MESSAGE_LENGTH}文字）。"
        if has_prompt_injection(content):
            return False, INJECTION_ERROR_MESSAGE

    return True, ""
