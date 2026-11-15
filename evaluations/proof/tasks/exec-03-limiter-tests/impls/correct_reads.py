"""Sliding-window rate limiter. SPEC.md is the contract."""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


class Limiter:
    def __init__(self, limit, window, clock):
        if not _is_int(limit) or limit <= 0:
            raise ValueError(f'limit must be an int greater than 0: {limit!r}')
        if not (_is_int(window) or isinstance(window, float)) or not window > 0:
            raise ValueError(f'window must be a number greater than 0: {window!r}')
        self._quota = limit
        self._period = window
        self._now = clock
        self._stamps = {}  # key -> the times of its hits in the window, oldest first; never empty

    def allow(self, key, cost=1):
        self._check(cost)
        if self.remaining(key) < cost:
            return False
        self._stamps.setdefault(key, []).extend([self._now()] * cost)
        return True

    def remaining(self, key):
        now = self._now()
        stamps = [t for t in self._stamps.get(key, ()) if now < t + self._period]
        if stamps:
            self._stamps[key] = stamps
        else:
            self._stamps.pop(key, None)
        return self._quota - len(stamps)

    def retry_after(self, key, cost=1):
        self._check(cost)
        short = cost - self.remaining(key)
        if short <= 0:
            return 0
        return self._stamps[key][short - 1] + self._period - self._now()

    def reset(self, key):
        self._stamps.pop(key, None)

    def _check(self, cost):
        if not _is_int(cost) or not 1 <= cost <= self._quota:
            raise ValueError(f'cost must be an int from 1 to {self._quota}: {cost!r}')
