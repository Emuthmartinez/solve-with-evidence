# 0004: Retries and requests that are not safe to repeat

- Status: Accepted
- Date: 2025-03-05

## Context

Two days after 0003 shipped, the payments API timed out on a `POST /charges` after it had made the charge. The client retried, and the customer was charged twice. The payments API accepts an `Idempotency-Key` header and then makes each charge once, however often the request arrives.

## Decision

1. A request whose method is GET, HEAD, PUT or DELETE is retried as 0003 decides.
2. A request with any other method, such as POST or PATCH, is retried only when it carries an `Idempotency-Key` header. The header's value is not inspected. Without that header the request gets exactly one attempt: what that attempt produces ends the call, and `sleep` is not called.
3. The client never adds, generates or changes an `Idempotency-Key`. Supplying one is the caller's job.
4. Every attempt passes the caller's `Request` object itself to `transport.send`. The client does not copy it, and does not change it or its headers.

## Consequences

- A POST without a key fails on the first dropped connection. Callers that want retries for it must send a key.
- Transports can log or sign a request once and rely on seeing the same object again.
