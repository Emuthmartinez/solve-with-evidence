import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, tests_pass

IMPLS = Path(__file__).resolve().parent / 'impls'
TESTS, CLIENT = 'test_retries.py', 'client/http.py'
URL = 'https://api.test/orders'
ERROR = 'error'
KEY = {'Idempotency-Key': 'order-17'}


class World:
    """A transport that plays a script, with the fake sleep and clock its client is given.

    A script item is a status, a (status, Retry-After value) pair, a (status, headers) pair or
    ERROR for a TransportError. Sleeping and slow attempts move the clock, which starts away
    from zero. An attempt beyond the script raises IndexError and so fails the check."""

    def __init__(self, s, script, took=0.0):
        self.outcomes = [self.outcome(s, item) for item in script]
        self.requests, self.sleeps, self.now, self.took = [], [], 1000.0, took
        self.client = s.Client(self, self.sleep, lambda: self.now)

    @staticmethod
    def outcome(s, item):
        if item == ERROR:
            return s.TransportError('connection reset')
        status, headers = item if isinstance(item, tuple) else (item, {})
        return s.Response(status, {'Retry-After': headers} if isinstance(headers, str) else headers, b'')

    def send(self, request):
        self.requests.append(request)
        self.now += self.took
        outcome = self.outcomes[len(self.requests) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def call(self, s, request, **options):
        """Which attempt's own outcome ended the call: 1 for the first, 0 for anything else."""
        try:
            result = self.client.send(request, **options)
        except s.TransportError as exc:
            result = exc
        return next((n for n, outcome in enumerate(self.outcomes, 1) if outcome is result), 0)


def play(s, script, method='GET', headers=None, took=0.0, **options):
    """Send one request. Returns (attempts made, the sleeps, which attempt's outcome ended the call)."""
    world = World(s, script, took)
    ended = world.call(s, s.Request(method, URL, dict(headers or {}), None), **options)
    return len(world.requests), world.sleeps, ended


def success(s):
    return all(play(s, [status, 503]) == (1, [], 1) for status in (200, 201, 204))


def retryable(s):
    return all(play(s, [first, 200]) == (2, [0.5], 2) for first in (502, 503, 504, ERROR))


def too_many_requests(s):
    return play(s, [429, 200]) == (2, [0.5], 2)


def final_statuses(s):
    return all(play(s, [status, 200]) == (1, [], 1) for status in (301, 400, 404, 408, 500, 501))


def attempt_limit(s):
    return all(play(s, [first, first, first, 200])[0] == 3 for first in (503, ERROR))


def delays(s):
    return play(s, [502, 504, 200]) == (3, [0.5, 1.0], 3) and play(s, [ERROR, ERROR, 200]) == (3, [0.5, 1.0], 3)


def no_last_sleep(s):
    for last in (503, ERROR, (503, '5')):
        attempts, sleeps, _ = play(s, [503, 503, last, last])
        if len(sleeps) != attempts - 1:
            return False
    return True


def last_response(s):
    for script in ([503, 502, 504, 504], [ERROR, ERROR, 503, 503]):
        attempts, _, ended = play(s, script)
        if ended != attempts:
            return False
    return True


def last_error(s):
    for script in ([ERROR, ERROR, ERROR, ERROR], [503, ERROR, ERROR, ERROR], [ERROR, 503, ERROR, ERROR]):
        attempts, _, ended = play(s, script)
        if ended != attempts:
            return False
    return True


def fresh_calls(s):
    world = World(s, [503, 503, 200, 502, 504, 200])
    ended = [world.call(s, s.Request('GET', URL, {}, None)) for _ in range(2)]
    return ended == [3, 6] and world.sleeps == [0.5, 1.0, 0.5, 1.0]


def repeatable_methods(s):
    return all(play(s, [503, 200], method) == (2, [0.5], 2) for method in ('PUT', 'DELETE', 'HEAD'))


def post_without_key(s):
    return all(play(s, [first, 200], method) == (1, [], 1)
               for method in ('POST', 'PATCH') for first in (503, (503, '1'), ERROR))


def post_with_key(s):
    return all(play(s, [first, 200], method, KEY) == (2, [0.5], 2)
               for method in ('POST', 'PATCH') for first in (503, ERROR))


def key_letter_case(s):
    return all(play(s, [503, 200], 'POST', {name: 'order-17'}) == (2, [0.5], 2)
               for name in ('idempotency-key', 'IDEMPOTENCY-KEY', 'Idempotency-key'))


def same_request(s):
    for method, headers in (('POST', {'Accept': 'application/json', **KEY}), ('GET', {})):
        world = World(s, [503, ERROR, 200])
        request = s.Request(method, URL, dict(headers), b'{}')
        world.call(s, request)
        if (len(world.requests) != 3 or any(sent is not request for sent in world.requests)
                or (request.method, request.url, request.headers, request.body) != (method, URL, headers, b'{}')):
            return False
    return True


def retry_after_503(s):
    return play(s, [(503, '7'), 200]) == (2, [7], 2)


def retry_after_429(s):
    return play(s, [(429, '12'), 200]) == (2, [12], 2)


def retry_after_lower_case(s):
    return play(s, [(503, {'retry-after': '3'}), 200]) == (2, [3], 2)


def retry_after_not_whole(s):
    return all(play(s, [(503, value), 200]) == (2, [0.5], 2)
               for value in ('Wed, 21 Oct 2026 07:28:00 GMT', '1.5', '-1', ''))


def retry_after_zero(s):
    return play(s, [(503, '0'), 200]) == (2, [0], 2)


def retry_after_other_status(s):
    return all(play(s, [first, 200]) == (2, [0.5], 2) for first in ((502, '9'), (504, '60')))


def retry_after_long(s):
    return all(play(s, [first, 200]) == (1, [], 1) for first in ((503, '31'), (429, '600')))


def retry_after_thirty(s):
    return play(s, [(503, '30'), 200]) == (2, [30], 2)


def delay_by_attempt(s):
    return (play(s, [(503, '7'), 503, 200]) == (3, [7, 1.0], 3)
            and play(s, [503, (503, '2'), 200]) == (3, [0.5, 2], 3))


def deadline_stops(s):
    return all(play(s, [first, first, 200], deadline=1.0) == (2, [0.5], 2)
               and play(s, [first, 200], deadline=0) == (1, [], 1) for first in (503, ERROR))


def deadline_exact(s):
    return (play(s, [503, 503, 200], deadline=1.5) == (3, [0.5, 1.0], 3)
            and play(s, [503, 200], deadline=0.5) == (2, [0.5], 2))


def deadline_counts_attempts(s):
    return (play(s, [503, 200], took=2.0, deadline=2.0) == (1, [], 1)
            and play(s, [503, 200], took=2.0, deadline=3.0) == (2, [0.5], 2))


def deadline_retry_after(s):
    return (play(s, [(503, '10'), 200], deadline=5) == (1, [], 1)
            and play(s, [(503, '10'), 200], deadline=12) == (2, [10], 2))


RUNS = {}


def tests_pass_on(name):
    """Whether the delivered tests pass with this client from impls/ in place of the delivered one,
    or on the delivered client when name is None. The first call runs them all side by side: one
    after another, a test file that takes a few seconds would outlast the harness's limit on the grader."""
    if not RUNS:
        names = [None] + sorted(file.stem for file in IMPLS.glob('*.py'))
        replace = lambda name: {CLIENT: (IMPLS / f'{name}.py').read_text()} if name else None
        with ThreadPoolExecutor(8) as pool:
            RUNS.update(zip(names, pool.map(lambda name: tests_pass(TESTS, replace(name)), names)))
    return RUNS[name]


def catches(name):
    # Tests that fail on a correct client prove nothing, so a catch counts only when they pass on one.
    return lambda s: tests_pass_on('reference') and not tests_pass_on(name)


CHECKS = [
    ('a success makes one attempt and no sleep', success),
    ('502 503 504 and a transport error are retried', retryable),
    ('429 is retried', too_many_requests),
    ('other statuses are returned at once', final_statuses),
    ('at most three attempts are made', attempt_limit),
    ('delays are 0.5 then 1 second', delays),
    ('no sleep follows the last attempt', no_last_sleep),
    ('the last response is returned when attempts run out', last_response),
    ('the last transport error is raised when attempts run out', last_error),
    ('every call starts over with the same delays', fresh_calls),
    ('PUT DELETE and HEAD are retried', repeatable_methods),
    ('POST without a key gets one attempt', post_without_key),
    ('POST with a key is retried', post_with_key),
    ('the key header name may be in any letter case', key_letter_case),
    ("every attempt gets the caller's request unchanged", same_request),
    ('Retry-After on a 503 replaces the delay', retry_after_503),
    ('Retry-After on a 429 replaces the delay', retry_after_429),
    ('the Retry-After name may be in lower case', retry_after_lower_case),
    ('Retry-After that is not a whole number is ignored', retry_after_not_whole),
    ('Retry-After of 0 sleeps 0 seconds', retry_after_zero),
    ('Retry-After on other statuses has no effect', retry_after_other_status),
    ('Retry-After above 30 is not retried', retry_after_long),
    ('Retry-After of exactly 30 is retried', retry_after_thirty),
    ('the computed delay follows the attempt number', delay_by_attempt),
    ('a deadline stops the retries', deadline_stops),
    ('a retry that ends exactly at the deadline is made', deadline_exact),
    ('the time attempts take counts toward the deadline', deadline_counts_attempts),
    ('the deadline is checked against the Retry-After delay', deadline_retry_after),
    ('tests pass on the delivered client', lambda s: tests_pass_on(None)),
    ('tests pass on a reference client', lambda s: tests_pass_on('reference')),
    ('tests catch a fourth attempt', catches('four_attempts')),
    ('tests catch a POST retried without a key', catches('post_retried')),
    ('tests catch a retried 500', catches('status_500_retried')),
    ('tests catch a sleep after the last attempt', catches('sleep_after_last')),
    ('tests catch a Retry-After ignored on a 429', catches('retry_after_429_ignored')),
    ('tests catch a retry after a Retry-After above 30', catches('long_retry_after')),
    ('tests catch an ignored deadline', catches('deadline_ignored')),
    ('tests catch a changed request on a retry', catches('new_request')),
]

if __name__ == '__main__':
    main(CHECKS, 'client.http')
