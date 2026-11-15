Write `solution.py` with one function:

```python
def sessionize(events: list[dict], gap_seconds: int) -> list[dict]:
```

Each event is a dict with four keys: `id` (str), `user` (str), `ts` (int, seconds) and `seq` (int). The input list is in no particular order and can hold several versions of the same event. The function groups each user's events into sessions of activity.

Rules:

1. A `gap_seconds` below 0 raises `ValueError`.
2. Events with the same `id` are versions of one event. Keep only the version with the highest `seq`. If several versions share that highest `seq`, keep the one that appears last in the input list. The kept version alone decides the event's `user` and `ts`. Discard every other version before any grouping.
3. Group the kept events by `user`. Within one user, sort the events by `ts`, and order events with equal `ts` by `id` in ascending string order (ids compare as strings, so `"10"` comes before `"9"`). Rule 6 compares users the same way.
4. Walk each user's sorted events. The first event starts a session. A later event starts a new session when its `ts` minus the previous event's `ts` is greater than `gap_seconds`. When the difference is exactly `gap_seconds` or less, the event joins the current session.
5. Each session is a dict `{"user": str, "start": int, "end": int, "ids": list[str]}`. `start` and `end` are the `ts` of its first and last event. `ids` lists its event ids in the order of rule 3.
6. Return the sessions of all users in one list, sorted by `start`, then by `user` in ascending string order.
7. An empty `events` list returns `[]`. Do not modify the input list or its dicts.

Examples:

```python
events = [
    {"id": "a", "user": "u1", "ts": 0, "seq": 1},
    {"id": "b", "user": "u1", "ts": 50, "seq": 1},
    {"id": "c", "user": "u1", "ts": 200, "seq": 1},
    {"id": "d", "user": "u2", "ts": 10, "seq": 1},
]
sessionize(events, 100)
# [{"user": "u1", "start": 0, "end": 50, "ids": ["a", "b"]},
#  {"user": "u2", "start": 10, "end": 10, "ids": ["d"]},
#  {"user": "u1", "start": 200, "end": 200, "ids": ["c"]}]

events = [
    {"id": "a", "user": "u1", "ts": 0, "seq": 1},
    {"id": "b", "user": "u1", "ts": 90, "seq": 1},
    {"id": "c", "user": "u1", "ts": 180, "seq": 1},
    {"id": "b", "user": "u1", "ts": 300, "seq": 2},
]
sessionize(events, 100)
# The seq-2 version moves "b" to 300, so nothing bridges "a" and "c" any more:
# [{"user": "u1", "start": 0, "end": 0, "ids": ["a"]},
#  {"user": "u1", "start": 180, "end": 180, "ids": ["c"]},
#  {"user": "u1", "start": 300, "end": 300, "ids": ["b"]}]

sessionize([], -1)
# raises ValueError
```

Use the Python standard library only.
