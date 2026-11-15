import unittest

from client.http import Client, Request, Response, TransportError


class FakeTransport:
    def __init__(self, *outcomes):
        self.outcomes = outcomes
        self.calls = 0

    def send(self, request):
        self.calls += 1
        outcome = self.outcomes[min(self.calls, len(self.outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class Retries(unittest.TestCase):
    def send(self, transport, method='GET', headers=None):
        self.sleeps = []
        client = Client(transport, self.sleeps.append, lambda: 0.0)
        return client.send(Request(method, 'https://api.test/orders', headers or {}, None))

    def test_retries_a_503_and_then_succeeds(self):
        transport = FakeTransport(Response(503, {}, b''), Response(200, {}, b'ok'))
        self.assertEqual(self.send(transport).status, 200)
        self.assertEqual(self.sleeps, [0.5])

    def test_retries_a_transport_error(self):
        transport = FakeTransport(TransportError('reset'), Response(200, {}, b'ok'))
        self.assertEqual(self.send(transport).status, 200)

    def test_gives_up_after_four_attempts(self):
        transport = FakeTransport(Response(503, {}, b''))
        self.assertEqual(self.send(transport).status, 503)
        self.assertEqual(transport.calls, 4)
        self.assertEqual(self.sleeps, [0.5, 1.0, 2.0])

    def test_honors_retry_after(self):
        transport = FakeTransport(Response(503, {'Retry-After': '7'}, b''), Response(200, {}, b'ok'))
        self.send(transport)
        self.assertEqual(self.sleeps, [7])

    def test_does_not_retry_a_post_without_a_key(self):
        transport = FakeTransport(Response(503, {}, b''), Response(200, {}, b'ok'))
        self.assertEqual(self.send(transport, 'POST').status, 503)
        self.assertEqual(transport.calls, 1)


if __name__ == '__main__':
    unittest.main()
