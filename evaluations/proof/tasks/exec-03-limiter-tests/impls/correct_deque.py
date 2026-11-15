"""Sliding-window rate limiter. SPEC.md is the contract."""
from collections import deque


class LimiterError(ValueError):
    pass


def _whole(value):
    return isinstance(value, int) and not isinstance(value, bool)


class Limiter:
    def __init__(self, limit, window, clock):
        if not _whole(limit) or limit < 1:
            raise LimiterError('rejected: first argument')
        if not (_whole(window) or isinstance(window, float)) or not window > 0:
            raise LimiterError('rejected: second argument')
        self._max = limit
        self._span = window
        self._tick = clock
        self._expiring = {}  # key -> deque of the times its hits leave the window, soonest first

    def allow(self, key, cost=1):
        self._require(cost)
        now, leaving = self._live(key)
        if len(leaving) + cost > self._max:
            return False
        self._expiring.setdefault(key, deque()).extend([now + self._span] * cost)
        return True

    def remaining(self, key):
        return self._max - len(self._live(key)[1])

    def retry_after(self, key, cost=1):
        self._require(cost)
        now, leaving = self._live(key)
        blocked = len(leaving) + cost - self._max
        return leaving[blocked - 1] - now if blocked > 0 else 0

    def reset(self, key):
        self._expiring.pop(key, None)

    def _require(self, cost):
        if not _whole(cost) or cost < 1 or cost > self._max:
            raise LimiterError('rejected: amount')

    def _live(self, key):
        """The current time and the key's expiry times that are still ahead of it."""
        now = self._tick()
        leaving = self._expiring.get(key, ())
        while leaving and not now < leaving[0]:
            leaving.popleft()
        if not leaving:
            self._expiring.pop(key, None)
        return now, leaving
