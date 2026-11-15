"""Sliding-window rate limiter. SPEC.md is the contract."""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


class Limiter:
    def __init__(self, limit, window, clock):
        if not _is_int(limit) or limit <= 0:
            raise ValueError(f'limit must be an int greater than 0: {limit!r}')
        if not (_is_int(window) or isinstance(window, float)) or not window > 0:
            raise ValueError(f'window must be a number greater than 0: {window!r}')
        self._limit = limit
        self._window = window
        self._clock = clock
        self._hits = {}  # key -> the times of its hits, oldest first

    def allow(self, key, cost=1):
        if _is_int(cost) and cost > self._limit:
            return False
        self._check_cost(cost)
        now = self._clock()
        hits = self._live(key, now)
        if len(hits) > self._limit - cost:
            return False
        hits.extend([now] * cost)
        return True

    def remaining(self, key):
        return self._limit - len(self._live(key, self._clock()))

    def retry_after(self, key, cost=1):
        self._check_cost(cost)
        now = self._clock()
        hits = self._live(key, now)
        leaving = len(hits) - (self._limit - cost)
        if leaving <= 0:
            return 0
        return hits[leaving - 1] + self._window - now

    def reset(self, key):
        self._hits.pop(key, None)

    def _check_cost(self, cost):
        if not _is_int(cost) or not 1 <= cost <= self._limit:
            raise ValueError(f'cost must be an int from 1 to {self._limit}: {cost!r}')

    def _live(self, key, now):
        """Drop the key's hits that have left the window and return the rest."""
        hits = [t for t in self._hits.get(key, ()) if now < t + self._window]
        self._hits[key] = hits
        return hits
