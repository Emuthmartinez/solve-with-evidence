# 0005: Retry budget

- Status: Accepted, amends 0003
- Date: 2025-06-23

## Context

The June outage of the billing API showed four problems with 0003. Four attempts per call multiplied the load on an upstream that was already down. The upstream answered some calls with `Retry-After: 600`, and workers slept for ten minutes while holding a job. A rate-limited call (429) was not retried, so jobs failed that one more attempt would have saved. Callers had no way to say how long a call may take.

## Decision

1. **Attempt limit.** `send` makes at most 3 attempts. This replaces the limit in 0003.
2. **429.** A response with status 429 is a retryable failure, in addition to those in 0003. `Retry-After` on a 429 is treated exactly as 0003 treats it on a 503.
3. **Long `Retry-After`.** When a `Retry-After` value that the client would wait for is greater than 30, the client does not retry. `send` returns that response at once and does not call `sleep`. A value of exactly 30 is waited for.
4. **Deadline.** `send` takes an optional second parameter: `send(request, deadline=None)`. `deadline` is the number of seconds the caller allows for the whole call. `None` means no deadline.
   - The start is the reading of `clock` when `send` is called, before the first attempt. The first attempt is always made.
   - Before each retry, once its delay is known (computed, or taken from `Retry-After`), the elapsed time is the reading of `clock` at that moment minus the start. The time the attempts took counts, as well as the time slept.
   - When elapsed + delay is greater than `deadline`, the client does not retry and does not call `sleep`. `send` ends as 0003 decides when it gives up.
   - When elapsed + delay is equal to `deadline` or less, the retry goes ahead.
   - The delay is never shortened to fit the deadline, and an attempt in progress is never cut short.

## Consequences

- With no deadline, the longest a call waits between attempts is 30 seconds, twice.
- A call can end after the deadline, by at most the time its last attempt took.
