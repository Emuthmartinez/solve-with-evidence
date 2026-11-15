"""The reference client with one rule broken: it sleeps once more after the last attempt when attempts run out."""
import re
from collections import namedtuple

Request = namedtuple('Request', 'method url headers body')
Response = namedtuple('Response', 'status headers body')

ATTEMPTS = 3
RETRIED = {429, 502, 503, 504}
SAFE_TO_REPEAT = {'GET', 'HEAD', 'PUT', 'DELETE'}
WHOLE_SECONDS = re.compile('[0-9]+')


class TransportError(Exception):
    """The transport could not complete an attempt: connection refused, reset or timed out."""


def carries(headers, wanted):
    return [str(value) for name, value in (headers or {}).items() if name.lower() == wanted]


def backoff(made):
    """The computed pause after this many attempts."""
    return min(0.5 * 2 ** (made - 1), 8.0)


def pause_after(response, made):
    """The pause before a retry of this response, or None when it is not retried."""
    if response.status not in RETRIED:
        return None
    if response.status in (429, 503):
        for value in carries(response.headers, 'retry-after'):
            if WHOLE_SECONDS.fullmatch(value):
                return int(value) if int(value) <= 30 else None
    return backoff(made)


def raising(error):
    def finish():
        raise error
    return finish


class Client:
    def __init__(self, transport, sleep, clock):
        self._wire = transport
        self._wait = sleep
        self._now = clock

    def send(self, request, deadline=None):
        started = self._now()
        limit = float('inf') if deadline is None else deadline
        tries = ATTEMPTS if self._repeatable(request) else 1
        for made in range(1, tries + 1):
            finish, pause = self._attempt(request, made)
            spent = self._now() - started
            if made == tries or pause is None or spent + pause > limit:
                if made == ATTEMPTS and pause is not None:
                    self._wait(pause)
                return finish()
            self._wait(pause)

    def _repeatable(self, request):
        return request.method.upper() in SAFE_TO_REPEAT or bool(carries(request.headers, 'idempotency-key'))

    def _attempt(self, request, made):
        try:
            response = self._wire.send(request)
        except TransportError as error:
            return raising(error), backoff(made)
        return (lambda: response), pause_after(response, made)
