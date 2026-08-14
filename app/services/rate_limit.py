"""シンプルなインメモリ・レート制限。

単一プロセス・単一ワーカーでの動作を想定（開発/小規模ベータ用）。
複数ワーカー構成で運用する場合は Redis 等の共有ストレージを使う
ライブラリ（Flask-Limiter等）への移行が必要。
"""
import time
from collections import defaultdict
from threading import Lock


class RateLimitExceeded(Exception):
    """レート制限を超えた場合に発生。"""


class SimpleRateLimiter:
    """キー（IP等）ごとに一定時間内の試行回数を制限する。"""

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts = defaultdict(list)
        self._lock = Lock()

    def hit(self, key: str) -> None:
        """試行を記録し、制限を超えていれば例外を投げる。"""
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            attempts = [t for t in self._attempts[key] if t > cutoff]
            if len(attempts) >= self.max_attempts:
                self._attempts[key] = attempts
                raise RateLimitExceeded(
                    f"試行回数が多すぎます。{self.window_seconds // 60}分後に再試行してください。"
                )
            attempts.append(now)
            self._attempts[key] = attempts

    def reset(self, key: str) -> None:
        """成功時にカウンタをリセットする。"""
        with self._lock:
            self._attempts.pop(key, None)


# ログイン試行: IPあたり5分間に5回まで
login_rate_limiter = SimpleRateLimiter(max_attempts=5, window_seconds=300)
