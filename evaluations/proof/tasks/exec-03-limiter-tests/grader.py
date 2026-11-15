import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, tests_pass

HERE = Path(__file__).resolve().parent
# Each of these keeps every rule of SPEC.md, so the delivered tests must exit 0 against it.
CORRECT = [
    ('passes on the shipped implementation', HERE / 'workspace/limiter/window.py'),
    ('passes on a correct rewrite with other error text and internals', HERE / 'impls/correct_deque.py'),
    ('passes on a correct rewrite that returns float waits', HERE / 'impls/correct_blocks.py'),
    ('passes on a correct rewrite that reads the clock twice in a call', HERE / 'impls/correct_reads.py'),
]
# Each of these is the shipped file with one rule broken, so the delivered tests must exit non-zero against it.
FAULTY = [
    ('catches a limit of 0 that is accepted', HERE / 'impls/faulty_limit_zero.py'),
    ('catches one hit more than the limit', HERE / 'impls/faulty_extra_hit.py'),
    ('catches a hit that still counts at exactly t + window', HERE / 'impls/faulty_boundary.py'),
    ('catches a denied call that moves recorded hits', HERE / 'impls/faulty_denied_restarts.py'),
    ('catches a denied call that records part of its cost', HERE / 'impls/faulty_denied_partial.py'),
    ('catches a cost above the limit that returns False', HERE / 'impls/faulty_cost_above_limit.py'),
    ('catches keys compared as text', HERE / 'impls/faulty_keys_as_text.py'),
    ('catches remaining that counts hits outside the window', HERE / 'impls/faulty_remaining_stale.py'),
    ('catches retry_after that waits for the newest hit', HERE / 'impls/faulty_retry_newest.py'),
    ('catches retry_after that waits only for the oldest hit', HERE / 'impls/faulty_retry_oldest.py'),
    ('catches reset that forgets every key', HERE / 'impls/faulty_reset_all.py'),
    ('catches limiters on one clock that share hits', HERE / 'impls/faulty_shared_clock.py'),
]
OUTCOMES = {}


def passes(implementation):
    """Whether the delivered tests exit 0 with this file in place of limiter/window.py. The first
    call runs every implementation, side by side: one after another, a test file that takes a few
    seconds would cost that sixteen times and outlast the harness's limit on the grader."""
    if not OUTCOMES:
        files = [file for _, file in CORRECT + FAULTY]
        with ThreadPoolExecutor(8) as pool:
            runs = pool.map(lambda file: tests_pass('test_limiter.py', {'limiter/window.py': file.read_text()}), files)
            OUTCOMES.update(zip(files, runs))
    return OUTCOMES[implementation]


CHECKS = ([(name, lambda _, file=file: passes(file)) for name, file in CORRECT]
          + [(name, lambda _, file=file: not passes(file)) for name, file in FAULTY])

if __name__ == '__main__':
    main(CHECKS, 'limiter.window')
