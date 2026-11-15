import unittest

from client.http import Client, Request, Response, TransportError


class FakeTransport:
    """Plays one outcome per attempt. The last outcome repeats."""

    def __init__(self, *outcomes):
        self.outcomes = outcomes
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        outcome = self.outcomes[min(len(self.requests), len(self.outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def client(transport):
    return Client(transport, sleep=lambda seconds: None, clock=lambda: 0.0)


class Send(unittest.TestCase):
    def test_returns_the_response_of_the_transport(self):
        ok = Response(200, {'Content-Type': 'application/json'}, b'{}')
        transport = FakeTransport(ok)
        request = Request('GET', 'https://api.test/orders/7', {}, None)
        self.assertIs(client(transport).send(request), ok)
        self.assertEqual(transport.requests, [request])

    def test_returns_a_not_found_response(self):
        missing = Response(404, {}, b'')
        request = Request('GET', 'https://api.test/orders/8', {}, None)
        self.assertIs(client(FakeTransport(missing)).send(request), missing)

    def test_raises_when_the_transport_fails(self):
        transport = FakeTransport(TransportError('connection refused'))
        with self.assertRaises(TransportError):
            client(transport).send(Request('GET', 'https://api.test/orders/9', {}, None))


if __name__ == '__main__':
    unittest.main()
