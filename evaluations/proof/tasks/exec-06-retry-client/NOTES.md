# exec-06-retry-client: fairness notes

The solver never sees this file, the grader, the exemplars or `impls/`.

## What the task is

Add retries to an existing HTTP client wrapper as six architecture decision records settle them, and deliver a test file that proves the rules hold. The grader checks the client directly, then runs the delivered tests against the delivered client, a correct reference client and eight faulty clients.

## Why it is harder than the tasks it replaces

The replaced tasks gave one function and a complete numbered specification. Here the rules are spread over records with four different statuses:

- 0001 (Accepted) fixes the interface, the letter case of header names and how the clock may be read.
- 0002 (Rejected) and 0006 (Proposed) describe behavior that must not be built. The README still describes 0002.
- 0003 (Accepted, amended by 0005) sets the retry rules. 0005 replaces its attempt limit and extends its `Retry-After` rule.
- 0004 (Accepted) narrows 0003 by method.
- 0005 (Accepted, amends 0003) adds 429, the 30 second limit and the deadline.

Several checks need two records at once: a `Retry-After` of 60 on a 504 is retried after 0.5 seconds (0003 ignores the header there, so the limit in 0005 never applies), and the deadline is compared against the `Retry-After` delay. The visible tests pass on the untouched starter and say nothing about retries. Nothing in the prompt says which rules are easy to break.

The second deliverable is a proof. A happy-path test file passes on the delivered client and still fails the task, because it does not fail on the faulty clients. A test file tied to the solver's own internals fails on the reference client.

## What the bad exemplar does

It is the version of a solver who stops reading at 0004. The client implements 0003 and 0004 as written: four attempts, no retry of a 429, any `Retry-After` waited for, no deadline. Its test file has five happy-path tests, one of which asserts four attempts. It passes `test_client.py`.

## The clients in `impls/`

`reference.py` follows the accepted records and is built another way than the good exemplar. It reads the clock after every attempt, with or without a deadline, which 0001 allows. It accepts three things outside the interface that a test file may do without harm: missing headers, a header value that is not a string and a lower-case method. Each other file is `reference.py` with one rule broken, named in its first line. `diff impls/reference.py impls/<name>.py` shows the change.

## Hidden checks and the sentence each follows from

| Check | Stated rule | Where |
|---|---|---|
| a success makes one attempt and no sleep | "Every other response is final, whatever its status: `send` returns it at once." "It never calls `sleep` before the first attempt or after the last one." | 0003, decisions 1 and 5 |
| 502 503 504 and a transport error are retried | "An attempt is a retryable failure when the transport raises `TransportError`, or returns a response with status 502, 503 or 504." | 0003, decision 1 |
| 429 is retried | "A response with status 429 is a retryable failure, in addition to those in 0003." | 0005, decision 2 |
| other statuses are returned at once | "Every other response is final, whatever its status: `send` returns it at once." Checked with 301, 400, 404, 408, 500 and 501 | 0003, decision 1 |
| at most three attempts are made | "`send` makes at most 3 attempts. This replaces the limit in 0003." | 0005, decision 1 |
| delays are 0.5 then 1 second | "0.5 before attempt 2, 1 before attempt 3", and "calls `sleep` exactly once before each retry, with the delay in seconds as its argument". 0006 is Proposed, and "A record is in force only while its status is Accepted." | 0003, decisions 3 and 5; `README.md` |
| no sleep follows the last attempt | "It never calls `sleep` before the first attempt or after the last one." | 0003, decision 5 |
| the last response is returned when attempts run out | "It returns that attempt's `Response` object as it is" | 0003, decision 6 |
| the last transport error is raised when attempts run out | "or raises the `TransportError` object that attempt raised. It never raises an error of its own." | 0003, decision 6 |
| every call starts over with the same delays | "Each call to `send` counts its own attempts. Nothing carries over from one call to the next." | 0003, decision 2 |
| PUT DELETE and HEAD are retried | "A request whose method is GET, HEAD, PUT or DELETE is retried as 0003 decides." | 0004, decision 1 |
| POST without a key gets one attempt | "Without that header the request gets exactly one attempt: what that attempt produces ends the call, and `sleep` is not called." Checked with POST and PATCH | 0004, decision 2 |
| POST with a key is retried | "A request with any other method, such as POST or PATCH, is retried only when it carries an `Idempotency-Key` header." | 0004, decision 2 |
| the key header name may be in any letter case | "Header names are compared without regard to letter case." | 0001, decision 5 |
| every attempt gets the caller's request unchanged | "Every attempt passes the caller's `Request` object itself to `transport.send`. The client does not copy it, and does not change it or its headers." | 0004, decisions 3 and 4 |
| Retry-After on a 503 replaces the delay | "the client waits that many seconds in place of the computed delay" | 0003, decision 4 |
| Retry-After on a 429 replaces the delay | "`Retry-After` on a 429 is treated exactly as 0003 treats it on a 503." | 0005, decision 2 |
| the Retry-After name may be in lower case | "`Retry-After`, `retry-after` and `RETRY-AFTER` name the same header." | 0001, decision 5 |
| Retry-After that is not a whole number is ignored | "Any other value, such as an HTTP date, `1.5`, `-1` or an empty string, is ignored as if the header were absent." Checked with exactly those four | 0003, decision 4 |
| Retry-After of 0 sleeps 0 seconds | "A whole number is one or more ASCII digits and nothing else, such as `0`", and `sleep` is called "also when the delay is 0" | 0003, decisions 4 and 5 |
| Retry-After on other statuses has no effect | "`Retry-After` on any response other than a 503 is ignored in the same way." 0005 extends it to a 429 only, and its limit applies to "a `Retry-After` value that the client would wait for" | 0003, decision 4; 0005, decisions 2 and 3 |
| Retry-After above 30 is not retried | "When a `Retry-After` value that the client would wait for is greater than 30, the client does not retry. `send` returns that response at once and does not call `sleep`." | 0005, decision 3 |
| Retry-After of exactly 30 is retried | "A value of exactly 30 is waited for." | 0005, decision 3 |
| the computed delay follows the attempt number | "It depends only on n, not on how long any earlier wait was." | 0003, decision 3 |
| a deadline stops the retries | "When elapsed + delay is greater than `deadline`, the client does not retry and does not call `sleep`. `send` ends as 0003 decides when it gives up." "The first attempt is always made." | 0005, decision 4 |
| a retry that ends exactly at the deadline is made | "When elapsed + delay is equal to `deadline` or less, the retry goes ahead." | 0005, decision 4 |
| the time attempts take counts toward the deadline | "The start is the reading of `clock` when `send` is called, before the first attempt." "The time the attempts took counts, as well as the time slept." The grader's clock starts at 1000: "Its origin is arbitrary." | 0005, decision 4; 0001, decision 2 |
| the deadline is checked against the Retry-After delay | "once its delay is known (computed, or taken from `Retry-After`)" | 0005, decision 4 |
| tests pass on the delivered client | "It must pass on your client" | `prompt.md` |
| tests pass on a reference client | "and on any other client that follows the accepted records. So it may use only the public interface those records define". "Callers and tests use nothing else from the module." "It may read `clock` any number of times, whatever arguments `send` was given." | `prompt.md`; 0001, decisions 1 and 6 |
| tests catch a fourth attempt | "It must fail on a client that breaks any one retry rule of the accepted records." The rule: at most 3 attempts | `prompt.md`; 0005, decision 1 |
| tests catch a POST retried without a key | The same sentence. The rule: without the header, exactly one attempt | `prompt.md`; 0004, decision 2 |
| tests catch a retried 500 | The same sentence. The rule: every other response is final | `prompt.md`; 0003, decision 1 |
| tests catch a sleep after the last attempt | The same sentence. The rule: never `sleep` after the last attempt | `prompt.md`; 0003, decision 5 |
| tests catch a Retry-After ignored on a 429 | The same sentence. The rule: `Retry-After` on a 429 is treated exactly as on a 503 | `prompt.md`; 0005, decision 2 |
| tests catch a retry after a Retry-After above 30 | The same sentence. The rule: above 30, no retry | `prompt.md`; 0005, decision 3 |
| tests catch an ignored deadline | The same sentence. The rule: past the deadline, no retry | `prompt.md`; 0005, decision 4 |
| tests catch a changed request on a retry | The same sentence. The rule: every attempt passes the caller's `Request` object itself | `prompt.md`; 0004, decision 4 |

A `tests catch` check passes only when the delivered tests pass on the reference client and fail on the faulty one. Tests that fail on a correct client would otherwise catch everything.

Every number in the grader's scripts is a multiple of 0.25, so each sum of a clock reading and a delay is exact in binary floating point, however the client arranges the comparison.

The 8 second cap on the computed delay (0003, decision 3) cannot be reached in 3 attempts. No check depends on it.

`variants/exec-06-retry-client.py` holds one plausible mistake per rule, in the client or in the test file. `test_bench.py` checks that each fails exactly the checks it lists.

The grader runs the delivered tests against the delivered client, the reference and the eight faulty clients side by side. The prompt states the limit that applies to each run: "It must be deterministic and finish in a few seconds. A run is stopped after 30 seconds."
