# 0002: Retry everything

- Status: Rejected
- Date: 2025-02-03

## Context

The inventory API drops about one request in fifty. Callers see the failure and page the on-call.

## Proposal

`Client.send` retries every request whose attempt did not end in a 2xx response, whatever the method, up to 5 times, waiting one second between attempts.

## Decision

Rejected in review.

- It retries responses that will never change, such as a 400 or a 404.
- It repeats requests that are not safe to repeat. A retried `POST /charges` can charge a customer twice.
- A fixed wait keeps the load on an upstream that is already failing.

0003 is the replacement.
