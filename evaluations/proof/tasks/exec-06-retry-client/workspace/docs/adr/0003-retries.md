# 0003: Retries

- Status: Accepted, amended by 0005
- Date: 2025-02-17

## Context

Most failures we see from upstreams are short: a dropped connection, or a gateway that answers 502, 503 or 504 for a few hundred milliseconds during a deploy. A second attempt usually succeeds. 0002 was rejected because it retried too much.

## Decision

1. **What is retried.** An attempt is one call to `transport.send`. An attempt is a retryable failure when the transport raises `TransportError`, or returns a response with status 502, 503 or 504. Every other response is final, whatever its status: `send` returns it at once.
2. **Attempt limit.** After a retryable failure the client waits and makes another attempt, up to 4 attempts in one call to `send`. Each call to `send` counts its own attempts. Nothing carries over from one call to the next.
3. **Computed delay.** The wait before attempt n is 0.5 × 2^(n − 2) seconds, and never more than 8 seconds: 0.5 before attempt 2, 1 before attempt 3, 2 before attempt 4. It depends only on n, not on how long any earlier wait was.
4. **`Retry-After`.** When the failed attempt returned a 503 with a `Retry-After` header whose value is a whole number of seconds, the client waits that many seconds in place of the computed delay. A whole number is one or more ASCII digits and nothing else, such as `0`, `7` or `120`. Any other value, such as an HTTP date, `1.5`, `-1` or an empty string, is ignored as if the header were absent. `Retry-After` on any response other than a 503 is ignored in the same way.
5. **Sleeping.** The client calls `sleep` exactly once before each retry, with the delay in seconds as its argument, also when the delay is 0. It never calls `sleep` before the first attempt or after the last one.
6. **Giving up.** When `send` makes no further attempt, it ends with what the last attempt produced. It returns that attempt's `Response` object as it is, or raises the `TransportError` object that attempt raised. It never raises an error of its own.

## Consequences

- A call can take longer than one attempt. Callers that cannot wait need a limit of their own.
- An upstream can slow our retries down by sending `Retry-After`.
