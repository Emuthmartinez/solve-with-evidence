# 0006: Jitter on retry delays

- Status: Proposed
- Date: 2025-09-02

## Context

When an upstream recovers, every worker that failed at the same moment retries at the same moment, 0.5 seconds later and again 1 second after that. The upstream sees its load arrive in spikes.

## Proposal

Multiply each computed delay by a random factor between 0.5 and 1.5. A `Retry-After` value is used as it is.

## Open questions

- The client would need an injected source of randomness, or its tests stop being exact.
- We have no measurement yet that shows the spikes hurt. The load test is planned for the next quarter.

No decision has been made.
