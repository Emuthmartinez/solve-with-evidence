"""Sliding-window rate limiter. SPEC.md is the contract."""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


class Limiter:
    def __init__(self, limit, window, clock):
        if not _is_int(limit) or limit <= 0:
            raise ValueError(f'limit must be an int greater than 0: {limit!r}')
        if not (_is_int(window) or isinstance(window, float)) or not window > 0:
            raise ValueError(f'window must be a number greater than 0: {window!r}')
        self._cap = limit
        self._width = window
        self._time = clock
        self._calls = {}  # key -> (time, hits) of each allowed call, oldest first

    def allow(self, key, cost=1):
        self._check(cost)
        now = self._time()
        calls = self._current(key, now)
        if sum(hits for _, hits in calls) + cost > self._cap:
            return False
        self._calls[key] = calls + [(now, cost)]
        return True

    def remaining(self, key):
        return self._cap - sum(hits for _, hits in self._current(key, self._time()))

    def retry_after(self, key, cost=1):
        self._check(cost)
        now = self._time()
        calls = self._current(key, now)
        over = sum(hits for _, hits in calls) + cost - self._cap
        wait = 0.0
        for at, hits in calls:
            if over <= 0:
                break
            over -= hits
            wait = float(at + self._width - now)
        return wait

    def reset(self, key):
        self._calls.pop(key, None)

    def _check(self, cost):
        if not _is_int(cost) or not 1 <= cost <= self._cap:
            raise ValueError(f'cost must be an int from 1 to {self._cap}: {cost!r}')

    def _current(self, key, now):
        return [call for call in self._calls.get(key, ()) if now < call[0] + self._width]
