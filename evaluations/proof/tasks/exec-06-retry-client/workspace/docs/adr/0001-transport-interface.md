# 0001: Transport interface and injected time

- Status: Accepted
- Date: 2025-01-14

## Context

Every service used to call `urllib` directly, each with its own error handling. We want one wrapper, so that behavior such as retries can later be added in one place. Its tests must never touch the network or wait for real time.

## Decision

1. `client/http.py` defines `Client`, `Request`, `Response` and `TransportError`. Together with the methods named below, they are the whole public interface. Callers and tests use nothing else from the module.
2. `Client(transport, sleep, clock)` takes three collaborators under these names. All three are required. There are no defaults.
   - `transport.send(request)` makes one HTTP attempt. It returns a `Response`, or raises `TransportError` when the attempt could not be completed (connection refused, reset, timed out).
   - `sleep(seconds)` waits. `seconds` is a number, 0 or more.
   - `clock()` returns the current time in seconds. Its origin is arbitrary. Only the difference between two readings means anything.
3. `Client.send(request)` returns the `Response` object the transport returned, as it is.
4. `Request(method, url, headers, body)` and `Response(status, headers, body)` are records with those fields in that order. `method` is an upper-case string such as `'GET'`. `status` is an int. `headers` is a dict from header name to value, both strings. `body` is bytes or `None`.
5. Header names are compared without regard to letter case. `Retry-After`, `retry-after` and `RETRY-AFTER` name the same header. A headers dict never holds the same header twice.
6. The client never waits or reads the time on its own. It uses only the injected `sleep` and `clock`. It may read `clock` any number of times, whatever arguments `send` was given.

## Consequences

- Production code passes `time.sleep` and `time.monotonic`.
- Tests pass fakes. A fake `sleep` records its argument and moves a fake clock forward. A fake transport can move the same clock forward to stand for a slow attempt. Such a clock gives the same answer however often it is read.
