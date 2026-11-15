# limiter

`limiter/window.py` rate-limits API callers by key. `SPEC.md` is its contract.

It keeps one list entry per hit and scans the key's list on every call. That is too slow at the limits we now sell, so it will be rewritten for speed. The rewrite must keep to `SPEC.md`. Nothing else about the current code is promised.
