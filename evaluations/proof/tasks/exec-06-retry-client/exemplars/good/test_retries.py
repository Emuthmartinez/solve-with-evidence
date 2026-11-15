"""Tests for the retry rules of the accepted records in docs/adr: 0001, 0003, 0004 and 0005.

They use only the public interface, so they hold for any client that follows those records.
"""
import unittest

from client.http import Client, Request, Response, TransportError

URL = 'https://api.test/orders'
KEY = {'Idempotency-Key': 'order-17'}


class World:
    """A fake transport, sleep and clock for one client.

    The transport plays one outcome per attempt and repeats the last one. Sleeping and slow
    attempts move the clock, which starts away from zero because its origin is arbitrary."""

    def __init__(self, outcomes, attempt_takes=0.0):
        self.outcomes = outcomes
        self.attempt_takes = attempt_takes
        self.requests = []
        self.sleeps = []
        self.now = 500.0
        self.client = Client(self, self.sleep, self.clock)

    def send(self, request):
        self.requests.append(request)
        self.now += self.attempt_takes
        outcome = self.outcomes[min(len(self.requests), len(self.outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def clock(self):
        return self.now

    def call(self, method='GET', headers=None, **options):
        """Send one request. A raised TransportError is kept as the result."""
        self.request = Request(method, URL, dict(headers or {}), None)
        try:
            self.result = self.client.send(self.request, **options)
        except TransportError as error:
            self.result = error
        return self


def status(code, retry_after=None, name='Retry-After'):
    return Response(code, {} if retry_after is None else {name: retry_after}, b'')


def failure():
    return TransportError('connection reset')


def ok():
    return status(200)


class Retries(unittest.TestCase):
    def ended(self, world, attempts, sleeps):
        """The call made this many attempts, slept exactly like this, and ended with the last attempt's outcome."""
        self.assertEqual(len(world.requests), attempts)
        self.assertEqual(world.sleeps, sleeps)
        self.assertIs(world.result, world.outcomes[attempts - 1])

    def test_a_success_is_returned_after_one_attempt(self):
        self.ended(World([ok(), status(503)]).call(), 1, [])

    def test_retryable_failures_get_a_second_attempt(self):
        for first in (status(502), status(503), status(504), failure()):
            self.ended(World([first, ok()]).call(), 2, [0.5])

    def test_a_429_gets_a_second_attempt(self):
        self.ended(World([status(429), ok()]).call(), 2, [0.5])

    def test_other_statuses_are_final(self):
        for code in (201, 301, 400, 404, 408, 500, 501):
            self.ended(World([status(code), ok()]).call(), 1, [])

    def test_at_most_three_attempts(self):
        for outcome in (status(503), failure()):
            self.assertEqual(len(World([outcome]).call().requests), 3)

    def test_the_delay_doubles(self):
        self.ended(World([status(502), failure(), ok()]).call(), 3, [0.5, 1.0])

    def test_no_sleep_after_the_last_attempt(self):
        for outcome in (status(503), failure(), status(503, '5')):
            world = World([outcome]).call()
            self.assertEqual(len(world.sleeps), len(world.requests) - 1)

    def test_the_last_response_is_returned_when_attempts_run_out(self):
        world = World([failure(), status(502), status(504)]).call()
        self.assertIs(world.result, world.outcomes[2])

    def test_the_last_transport_error_is_raised_when_attempts_run_out(self):
        world = World([failure(), status(503), failure()]).call()
        self.assertIs(world.result, world.outcomes[2])

    def test_each_call_starts_over(self):
        world = World([status(503), status(503), ok(), status(502), status(504), ok()])
        self.assertIs(world.call().result, world.outcomes[2])
        self.assertIs(world.call().result, world.outcomes[5])
        self.assertEqual(world.sleeps, [0.5, 1.0, 0.5, 1.0])

    def test_put_delete_and_head_are_retried_without_a_key(self):
        for method in ('PUT', 'DELETE', 'HEAD'):
            self.ended(World([status(503), ok()]).call(method), 2, [0.5])

    def test_post_and_patch_without_a_key_get_one_attempt(self):
        for method in ('POST', 'PATCH'):
            for first in (status(503), status(503, '1'), failure()):
                self.ended(World([first, ok()]).call(method), 1, [])

    def test_post_and_patch_with_a_key_are_retried(self):
        for method in ('POST', 'PATCH'):
            for first in (status(503), failure()):
                self.ended(World([first, ok()]).call(method, KEY), 2, [0.5])

    def test_the_key_header_name_may_be_in_any_letter_case(self):
        for name in ('idempotency-key', 'IDEMPOTENCY-KEY'):
            self.ended(World([status(503), ok()]).call('POST', {name: 'order-17'}), 2, [0.5])

    def test_every_attempt_gets_the_request_of_the_caller_unchanged(self):
        for method, headers in (('POST', KEY), ('GET', {})):
            world = World([status(503), failure(), ok()]).call(method, headers)
            self.assertEqual(len(world.requests), 3)
            for sent in world.requests:
                self.assertIs(sent, world.request)
            self.assertEqual(world.request, Request(method, URL, headers, None))

    def test_retry_after_on_a_503_replaces_the_delay(self):
        self.ended(World([status(503, '7'), ok()]).call(), 2, [7])

    def test_retry_after_on_a_429_replaces_the_delay(self):
        self.ended(World([status(429, '12'), ok()]).call(), 2, [12])

    def test_the_retry_after_name_may_be_in_any_letter_case(self):
        for name in ('retry-after', 'RETRY-AFTER'):
            self.ended(World([status(503, '3', name), ok()]).call(), 2, [3])

    def test_retry_after_that_is_not_a_whole_number_is_ignored(self):
        for value in ('Wed, 21 Oct 2026 07:28:00 GMT', '1.5', '-1', '', '45.5'):
            self.ended(World([status(503, value), ok()]).call(), 2, [0.5])

    def test_retry_after_of_zero_sleeps_zero_seconds(self):
        self.ended(World([status(503, '0'), ok()]).call(), 2, [0])

    def test_retry_after_on_other_statuses_has_no_effect(self):
        for first in (status(502, '9'), status(504, '60')):
            self.ended(World([first, ok()]).call(), 2, [0.5])

    def test_retry_after_above_30_is_not_retried(self):
        for first in (status(503, '31'), status(429, '600')):
            self.ended(World([first, ok()]).call(), 1, [])

    def test_retry_after_of_exactly_30_is_retried(self):
        self.ended(World([status(503, '30'), ok()]).call(), 2, [30])

    def test_the_computed_delay_follows_the_attempt_number(self):
        self.ended(World([status(503, '7'), status(503), ok()]).call(), 3, [7, 1.0])
        self.ended(World([status(503), status(503, '2'), ok()]).call(), 3, [0.5, 2])

    def test_a_deadline_stops_the_retries(self):
        for first in (status(503), failure()):
            self.ended(World([status(503), first, ok()]).call(deadline=1.0), 2, [0.5])
            self.ended(World([first, ok()]).call(deadline=0), 1, [])

    def test_a_retry_that_ends_exactly_at_the_deadline_is_made(self):
        self.ended(World([status(503), status(503), ok()]).call(deadline=1.5), 3, [0.5, 1.0])

    def test_the_time_attempts_take_counts_toward_the_deadline(self):
        self.ended(World([status(503), ok()], attempt_takes=2.0).call(deadline=2.0), 1, [])
        self.ended(World([status(503), ok()], attempt_takes=2.0).call(deadline=3.0), 2, [0.5])

    def test_the_deadline_is_checked_against_the_retry_after_delay(self):
        self.ended(World([status(503, '10'), ok()]).call(deadline=5), 1, [])
        self.ended(World([status(503, '10'), ok()]).call(deadline=12), 2, [10])


if __name__ == '__main__':
    unittest.main()
