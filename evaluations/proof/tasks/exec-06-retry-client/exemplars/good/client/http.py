"""HTTP client wrapper for our services. The decisions behind it are in docs/adr."""
from collections import namedtuple

Request = namedtuple('Request', 'method url headers body')
Response = namedtuple('Response', 'status headers body')

MAX_ATTEMPTS = 3
RETRY_STATUSES = (429, 502, 503, 504)
RETRY_AFTER_STATUSES = (429, 503)
MAX_RETRY_AFTER = 30
REPEATABLE_METHODS = ('GET', 'HEAD', 'PUT', 'DELETE')


class TransportError(Exception):
    """The transport could not complete an attempt: connection refused, reset or timed out."""


def header(headers, name):
    """The value of a header, whatever letter case its name is written in, or None."""
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def backoff(attempt):
    """The computed wait before this attempt: 0.5 s before the second, doubling, at most 8 s."""
    return min(0.5 * 2 ** (attempt - 2), 8.0)


def wait_before(attempt, response):
    """Seconds to wait before this attempt, or None when the response is final.
    `response` is None when the attempt before it raised TransportError."""
    if response is None:
        return backoff(attempt)
    if response.status not in RETRY_STATUSES:
        return None
    if response.status in RETRY_AFTER_STATUSES:
        value = header(response.headers, 'Retry-After')
        if value is not None and value.isascii() and value.isdigit():
            return int(value) if int(value) <= MAX_RETRY_AFTER else None
    return backoff(attempt)


class Client:
    def __init__(self, transport, sleep, clock):
        self._transport = transport
        self._sleep = sleep
        self._clock = clock

    def send(self, request, deadline=None):
        """Send the request, retrying as docs/adr 0003, 0004 and 0005 decide.
        Returns the last attempt's response or raises its TransportError."""
        start = self._clock()
        repeatable = (request.method in REPEATABLE_METHODS
                      or header(request.headers, 'Idempotency-Key') is not None)
        attempt = 0
        while True:
            attempt += 1
            try:
                response, error = self._transport.send(request), None
            except TransportError as exc:
                response, error = None, exc
            delay = wait_before(attempt + 1, response) if repeatable and attempt < MAX_ATTEMPTS else None
            if delay is not None and deadline is not None and self._clock() - start + delay > deadline:
                delay = None
            if delay is None:
                if error is not None:
                    raise error
                return response
            self._sleep(delay)
