`limiter/window.py` is a rate limiter. It implements `SPEC.md` correctly. It will be rewritten for speed, as `README.md` explains. Before that happens, `SPEC.md` needs tests that will hold the rewrite to it.

Write `test_limiter.py` in this directory.

- It is run as `python3 test_limiter.py` from this directory, and it passes when it exits 0.
- It will be run against other implementations, each put in place of `limiter/window.py`.
- It must pass against the current implementation and against any other correct implementation of `SPEC.md`. So it may use only the API in `SPEC.md`, and it may assert only what `SPEC.md` states.
- It must fail, exiting non-zero, against an implementation that breaks any one numbered rule of `SPEC.md`.
- It must be deterministic and finish in a few seconds. A run is stopped after 30 seconds.

Use the Python standard library only. Deliver `test_limiter.py`.
