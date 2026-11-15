"""HTTP client wrapper for our services. The decisions behind it are in docs/adr."""
from collections import namedtuple

Request = namedtuple('Request', 'method url headers body')
Response = namedtuple('Response', 'status headers body')


class TransportError(Exception):
    """The transport could not complete an attempt: connection refused, reset or timed out."""


class Client:
    def __init__(self, transport, sleep, clock):
        self._transport = transport
        self._sleep = sleep
        self._clock = clock

    def send(self, request):
        """Make one attempt and return the transport's response."""
        return self._transport.send(request)
