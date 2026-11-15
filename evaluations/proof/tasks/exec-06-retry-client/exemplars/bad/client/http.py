"""HTTP client wrapper for our services. The decisions behind it are in docs/adr."""
from collections import namedtuple

Request = namedtuple('Request', 'method url headers body')
Response = namedtuple('Response', 'status headers body')

MAX_ATTEMPTS = 4
RETRY_STATUSES = (502, 503, 504)
IDEMPOTENT_METHODS = ('GET', 'HEAD', 'PUT', 'DELETE')


class TransportError(Exception):
    """The transport could not complete an attempt: connection refused, reset or timed out."""


def header(headers, name):
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


class Client:
    def __init__(self, transport, sleep, clock):
        self._transport = transport
        self._sleep = sleep
        self._clock = clock

    def send(self, request):
        """Send the request, retrying as docs/adr/0003-retries.md and 0004-idempotency.md decide."""
        retryable = request.method in IDEMPOTENT_METHODS or header(request.headers, 'Idempotency-Key') is not None
        delay = 0.5
        for attempt in range(1, MAX_ATTEMPTS + 1):
            last = attempt == MAX_ATTEMPTS or not retryable
            try:
                response = self._transport.send(request)
            except TransportError:
                if last:
                    raise
                self._sleep(delay)
            else:
                if last or response.status not in RETRY_STATUSES:
                    return response
                retry_after = header(response.headers, 'Retry-After') if response.status == 503 else None
                self._sleep(int(retry_after) if retry_after and retry_after.isdigit() else delay)
            delay = min(delay * 2, 8.0)
