"""レート制限のユニットテスト。"""
import pytest

from app.services.rate_limit import SimpleRateLimiter, RateLimitExceeded


def test_allows_within_limit():
    limiter = SimpleRateLimiter(max_attempts=3, window_seconds=60)
    # 3回まで成功
    limiter.hit("ip1")
    limiter.hit("ip1")
    limiter.hit("ip1")


def test_exceeded_raises():
    limiter = SimpleRateLimiter(max_attempts=2, window_seconds=60)
    limiter.hit("ip1")
    limiter.hit("ip1")
    with pytest.raises(RateLimitExceeded):
        limiter.hit("ip1")


def test_reset_clears_counter():
    limiter = SimpleRateLimiter(max_attempts=2, window_seconds=60)
    limiter.hit("ip1")
    limiter.hit("ip1")
    with pytest.raises(RateLimitExceeded):
        limiter.hit("ip1")
    # リセット後は再度成功する
    limiter.reset("ip1")
    limiter.hit("ip1")


def test_separate_keys():
    limiter = SimpleRateLimiter(max_attempts=1, window_seconds=60)
    limiter.hit("ip1")
    # 別キーは影響を受けない
    limiter.hit("ip2")
    with pytest.raises(RateLimitExceeded):
        limiter.hit("ip1")
