# exec-03-limiter-tests: fairness notes

The solver never sees this file, the grader, `impls/` or the exemplars.

## What the task is

Write `test_limiter.py` for a rate limiter that is correct today and is about to be rewritten. The solver writes no production code. The grader runs the delivered tests with 16 files in turn in place of `limiter/window.py`: the shipped file, three other correct implementations, and twelve faulty ones. The tests must exit 0 on the four correct files and non-zero on each faulty one.

## Why it is harder than the tasks it replaces

The replaced tasks gave a complete numbered specification of one function, and the solver's own generated tests were enough to audit an implementation of it. Here the tests are the deliverable. No run against the shipped file can show that they are complete, because the shipped file is correct and every test passes on it. The solver has to ask, for each rule, what a break of it would look like and whether a test would see it. Several of the faulty files differ from the shipped one only at a boundary or when two rules meet. The tests can also fail the other way: an assertion on anything `SPEC.md` leaves open passes today and fails on a correct rewrite.

Nothing in the prompt says which rules are easy to break or which freedoms a rewrite will use.

## What the bad exemplar does

It is the file a quick solver writes: one limiter, the happy path of each method, one expiry check, an error message matched by regex and a look at the private `_hits` dict. It passes on the shipped file. It fails the three rewrite checks and lets eight faulty files through.

## Hidden checks and the sentence each follows from

| Check | Stated rule | Where |
|---|---|---|
| passes on the shipped implementation | "`limiter/window.py` is a rate limiter. It implements `SPEC.md` correctly" and "it passes when it exits 0" | `prompt.md` |
| passes on a correct rewrite with other error text and internals | "The text of an error message, and whether the exception is `ValueError` itself or a subclass of it." and "Every attribute, method and module-level name other than the API above." | `SPEC.md`, Not specified |
| passes on a correct rewrite that returns float waits | "Whether `retry_after` returns an int or a float. Its 0 may be `0.0`." This file also keeps hits that left the window until the key is next written, which shows only under "What happens after the clock returns a time earlier than one it returned before." | `SPEC.md`, Not specified |
| passes on a correct rewrite that reads the clock twice in a call | "How many times a call reads the clock. The constructor may read it too." | `SPEC.md`, Not specified |
| catches a limit of 0 that is accepted | "`limit` is an int greater than 0." "Any other `limit` or `window` raises `ValueError`." | `SPEC.md`, rule 1 |
| catches one hit more than the limit | "returns `True` when the key has at most `limit - cost` hits in the window" "Otherwise it returns `False`." | `SPEC.md`, rule 2 |
| catches a hit that still counts at exactly t + window | "From exactly `t + window` on it is not." | `SPEC.md`, rule 3 |
| catches a denied call that moves recorded hits | "it does not move or remove a hit already recorded" | `SPEC.md`, rule 4 |
| catches a denied call that records part of its cost | "A call to `allow` that returns `False` changes nothing. It records no hit" | `SPEC.md`, rule 4 |
| catches a cost above the limit that returns False | "`cost` is an int from 1 to `limit`, both included. Any other `cost` raises `ValueError`" | `SPEC.md`, rule 5 |
| catches keys compared as text | "Two keys are the same key exactly when they are equal (`==`)." | `SPEC.md`, rule 6 |
| catches remaining that counts hits outside the window | "`remaining(key)` returns `limit` minus the number of the key's hits in the window" | `SPEC.md`, rule 7 |
| catches retry_after that waits for the newest hit | "that time is `t + window`, where `t` is the time of the `k`-th oldest of those hits" | `SPEC.md`, rule 8 |
| catches retry_after that waits only for the oldest hit | "With `n` hits in the window, `k = n - (limit - cost)` of them must leave it first." | `SPEC.md`, rule 8 |
| catches reset that forgets every key | "`reset(key)` forgets every hit of that key, and no hit of any other key." | `SPEC.md`, rule 9 |
| catches limiters on one clock that share hits | "Each `Limiter` is independent of every other `Limiter`, even when they share a clock." | `SPEC.md`, rule 10 |

The prompt states the two obligations the checks apply: "It must pass against the current implementation and against any other correct implementation of `SPEC.md`", and "It must fail, exiting non-zero, against an implementation that breaks any one numbered rule of `SPEC.md`".

## What catches each faulty file

Each faulty file is the shipped file with one edit and nothing else changed. `diff workspace/limiter/window.py impls/faulty_<name>.py` shows the edit. Each can be caught through the public API alone. The good exemplar does it with one test per fault, and no other test of the good exemplar fails on that file.

| File | The smallest sequence that catches it |
|---|---|
| `faulty_limit_zero.py` | `Limiter(0, 10, clock)` does not raise. |
| `faulty_extra_hit.py` | With a limit of 3, the fourth `allow` returns `True`. |
| `faulty_boundary.py` | Limit 2 with two hits at time 3 and a window of 10. At time 13 the key is still full. |
| `faulty_denied_restarts.py` | Fill the key at time 0. A denied call at time 4 makes `retry_after` 10, not 6. A denial at the instant of the hits shows nothing. |
| `faulty_denied_partial.py` | Limit 4 with 2 hits. A denied `allow(key, 4)` leaves `remaining` at 0, not 2. A denial on a full key shows nothing. |
| `faulty_cost_above_limit.py` | With a limit of 3, `allow(key, 4)` returns `False` and does not raise. |
| `faulty_keys_as_text.py` | Hits for `1` and `1.0` land on two keys, and hits for `1` count against `'1'`. Keys that are all different strings show nothing. |
| `faulty_remaining_stale.py` | Limit 3 with two hits at time 0. At time 11 `remaining` is still 1. It is right again once `allow` or `retry_after` has run for the key. |
| `faulty_retry_newest.py` | Limit 3 with hits at 0, 2 and 4. At time 5 `retry_after(key)` is 9, not 5. Hits recorded at one instant show nothing. |
| `faulty_retry_oldest.py` | The same hits. `retry_after(key, 2)` is 5, not 7. The default cost shows nothing. |
| `faulty_reset_all.py` | Hits on `a` and `b`. After `reset('a')`, `remaining('b')` is back at the limit. |
| `faulty_shared_clock.py` | Two limiters built on one clock object. A hit on one counts on the other. Limiters with a clock each show nothing. |

## What keeps the correct files correct

| File | How it differs from the shipped file |
|---|---|
| `correct_deque.py` | A deque of expiry times per key. Keys with no hit in the window are dropped. It raises `LimiterError`, a subclass of `ValueError`, with messages that share no word with the shipped ones. |
| `correct_blocks.py` | One (time, hits) entry per allowed call. `retry_after` always returns a float. Only `allow` drops entries that left the window, so the two files differ after the clock is turned back. |
| `correct_reads.py` | `allow` and `retry_after` are built on `remaining`, so one call may read the clock twice. |

The three rewrites differ from the shipped file only where the Not specified section of `SPEC.md` says an implementation is free. In everything else they agree with it, including inputs the rules do not single out: a NaN or infinite window, a `bool` where an int is asked for, keyword arguments, float times that are not exact in binary. All four compute a wait as `(t + window) - now`, so results are equal bit for bit. Two scripts compared the rewrites with the shipped file on Python 3.9 and 3.15: 3,000 random call sequences, and a fixed list of unusual calls. The scripts were not kept. The random sequences found no difference.

The unusual calls found one difference that the rules did not cover, and `SPEC.md` now lists it as not specified. `reset` with an unhashable key raises `TypeError` in the shipped file once any key has been used, and returns `None` in the rewrites while they hold no key, because `dict.pop` does not hash the key when the dict is empty. `allow`, `remaining` and `retry_after` raise `TypeError` for an unhashable key in all four files.

No file in `impls/` says in its text whether it is correct or faulty. All carry the shipped docstring, so a test file that reads the source of `limiter/window.py` finds no label in it.

The grader runs the 16 files side by side on first use. Run one after another, a test file that takes four seconds would outlast the harness's 60 second limit on a grader, though the prompt allows it.

`variants/exec-03-limiter-tests.py` holds one plausible mistake per check. `test_bench.py` checks that each fails exactly the checks it lists.
