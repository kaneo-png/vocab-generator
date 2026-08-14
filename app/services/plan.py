"""プラン定義と機能アクセス制御。

プランごとの利用可能機能と月間生成上限を一元管理する。
"""

# プランごとの利用可能機能
PLAN_FEATURES = {
    "free": {"chat", "csv"},
    "ad_free": {"chat", "csv", "edit", "master", "pronunciation"},
    "premium": {"chat", "csv", "edit", "master", "pronunciation", "advanced"},
}

# プランごとの月間生成上限
PLAN_MONTHLY_LIMITS = {
    "free": 3,
    "ad_free": 10,
    "premium": 9999,
}

# ゲスト（未ログイン）の生成上限（合計）
GUEST_GENERATION_LIMIT = 2


class FeatureRequiredError(Exception):
    """必要なプラン機能を持たない場合に発生。"""


def has_feature(plan: str, feature: str) -> bool:
    """指定プランが機能を利用できるかを判定する。"""
    return feature in PLAN_FEATURES.get(plan or "free", set())


def require_feature(plan: str, feature: str):
    """機能が必要なのに無い場合は例外を投げる。"""
    if not has_feature(plan, feature):
        raise FeatureRequiredError(feature)


def monthly_limit(plan: str) -> int:
    """プランに応じた月間生成上限を返す。"""
    return PLAN_MONTHLY_LIMITS.get(plan, PLAN_MONTHLY_LIMITS["free"])
