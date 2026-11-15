# Limiter: specification

`limiter.window.Limiter` is a sliding-window rate limiter. Each key may spend up to `limit` hits in any `window` seconds. The limiter takes the time only from the clock it is given.

## API

| Call | Returns |
|---|---|
| `Limiter(limit, window, clock)` | a limiter |
| `allow(key, cost=1)` | `True` or `False` |
| `remaining(key)` | an int |
| `retry_after(key, cost=1)` | a number of seconds |
| `reset(key)` | `None` |

Arguments may be passed by position or by the names shown.

In this document an int is an `int` that is not a `bool`, and a number is an int or a `float`.

## Rules

1. In `Limiter(limit, window, clock)`, `limit` is an int greater than 0. `window` is a number greater than 0, in seconds. `clock` is a callable that takes no argument and returns the current time in seconds as a number. Any other `limit` or `window` raises `ValueError`.
2. `allow(key, cost=1)` returns `True` when the key has at most `limit - cost` hits in the window, and it then records `cost` hits for the key at the current time. Otherwise it returns `False`.
3. A hit recorded at time `t` is in the window while the current time is less than `t + window`. From exactly `t + window` on it is not.
4. A call to `allow` that returns `False` changes nothing. It records no hit, and it does not move or remove a hit already recorded.
5. `cost` is an int from 1 to `limit`, both included. Any other `cost` raises `ValueError`, in `allow` and in `retry_after`, and the call changes nothing.
6. Keys are independent. A call for one key never changes what a call returns for another key. A key is any hashable value. Two keys are the same key exactly when they are equal (`==`).
7. `remaining(key)` returns `limit` minus the number of the key's hits in the window, as an int. It changes nothing.
8. `retry_after(key, cost=1)` returns 0 when `allow(key, cost)` would return `True` now. Otherwise it returns the number of seconds until the earliest time at which `allow(key, cost)` would return `True`, if no other call were made before then. With `n` hits in the window, `k = n - (limit - cost)` of them must leave it first. So that time is `t + window`, where `t` is the time of the `k`-th oldest of those hits, and the result is `(t + window) - now`. `retry_after` changes nothing.
9. `reset(key)` forgets every hit of that key, and no hit of any other key. Resetting a key that has no hits is not an error.
10. Each `Limiter` is independent of every other `Limiter`, even when they share a clock.

## Not specified

An implementation is free in each of these, and two correct implementations may differ:

- What happens after the clock returns a time earlier than one it returned before. The clock is trusted never to do that.
- What a call does with a key that is not hashable, or with a clock that is not as rule 1 describes.
- The text of an error message, and whether the exception is `ValueError` itself or a subclass of it.
- Whether `retry_after` returns an int or a float. Its 0 may be `0.0`.
- How many times a call reads the clock. The constructor may read it too.
- Every attribute, method and module-level name other than the API above.
