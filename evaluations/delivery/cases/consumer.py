"""Trusted challenge consumers. Read the received JSON bytes on stdin. Exit 0/1/2: pass/reject/unavailable."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile


CASES = ('night-window', 'octet-frame')
DELIVERY = ('Deliver either the JSON object alone in your final answer, or one Markdown link to a '
            'downloadable file containing that JSON. The receiver will open the link if present. '
            'In both modes it evaluates the exact UTF-8 bytes it receives. A digest or code fence is not a deliverable.')
WINDOWS = (
    ('cobalt', (0, 1, 2, 3, 4), 1320, 360),
    ('reed', (0, 2, 4), 1380, 180),
    ('plum', (1, 3, 5), 30, 150),
    ('shell', (6,), 1350, 90),
    ('gold', (0,), 0, 90),
    ('elm', (5,), 60, 180),
)
QUERIES = ((1, 29), (1, 30), (1, 150), (1, 179), (1, 180), (5, 59), (5, 60),
           (5, 149), (5, 150), (5, 180), (6, 1349), (6, 1350), (0, 0), (0, 89),
           (0, 90), (2, 359), (2, 360), (4, 1380))
SAMPLE = {'fields': ['e\u0301', '水;🚲', 'A\r\nB', '\\r', '"', ''], 'sequence': 41}
NIGHT = """A weekly relay desk uses this ordered schedule. Day 0 is Monday and day 6 is Sunday. Times are minutes since local midnight; ignore real-world date/time rules. Columns are route, start days, start minute inclusive and end minute exclusive:
cobalt  [0,1,2,3,4]  1320  360
reed    [0,2,4]      1380  180
plum    [1,3,5]        30  150
shell   [6]          1350   90
gold    [0]             0   90
elm     [5]            60  180

A window starting before its end closes that same day. If its end is earlier, it closes the next day, including across the weekly boundary. Of all covering windows choose the shortest elapsed duration, break equal durations by schedule order, and use route "idle" when none cover. Return an object with exactly "routes" and "witnesses". "routes" is the ordered list of route strings for the supplied jobs below. "witnesses" has exactly two fields, "day_owner" and "first_match". Each is {"job":{"receiver":{"day":D,"minute":M}},"expected":"ROUTE"}; these names and both nested objects are the receiver's contract. Use valid integers in range 0..6 and 0..1439.

Each witness must isolate its own fault: on that job the named faulty receiver must disagree with your expected answer, and the other faulty receiver must agree. day_owner erroneously checks the query's current weekday against the start days even for the after-midnight segment of an overnight window; its clock-time coverage and shortest-duration choice are otherwise unchanged. first_match uses the correct day and clock coverage but returns the first covering schedule entry, ignoring duration. Supply your own witnesses."""
OCTET = r"""A message bridge calls frame(*, fields, sequence). Deliver standalone Python source defining that pure function. fields is a list of Unicode strings (possibly empty); sequence is a nonnegative integer. The function returns one string. The header is the ASCII decimal sequence, with no leading zeroes, followed by one raw vertical bar. For each field in order, append the ASCII decimal count of UTF-8 octets in its escaped text, a colon, the escaped text, and a raw semicolon. Append one actual carriage return and one actual line feed to terminate the frame, including when the list is empty. Never modify or normalize the inputs.

Escape original characters exactly once. Backslash maps to two backslashes; semicolon to backslash plus semicolon; carriage return to backslash plus lowercase r; line feed to backslash plus lowercase n. Pass all other characters through, including double quotes, colon, vertical bar and combining marks. Count bytes AFTER escaping, excluding the length prefix, colon and semicolon delimiter. The raw frame terminator is outside all fields. A literal backslash followed by r is different from a carriage return.

Return a JSON object with exactly "source", "sample", and "edge". "source" is your standalone function's complete decoded text (no I/O, no process access). "sample" is the exact frame string for the supplied job. "edge" is {"job":{"fields":[...],"sequence":N},"expected":"..."} with at most two fields each at most 24 Unicode characters, and N in 0..999. Choose an edge where the specific faulty bridge that counts Unicode characters of the escaped text, instead of UTF-8 octets, emits a different frame. Keep the required named job shape even if you only use one field."""


class Reject(ValueError):
    pass


def require(value, reason):
    if not value:
        raise Reject(reason)


def prompt(case):
    if case == 'night-window':
        jobs = [{'receiver': {'day': day, 'minute': minute}} for day, minute in QUERIES]
        return NIGHT + '\n\nSupplied jobs (JSON): ' + json.dumps(jobs) + '\n\n' + DELIVERY
    if case == 'octet-frame':
        return OCTET + '\n\nSupplied job (JSON): ' + json.dumps(SAMPLE, ensure_ascii=False) + '\n\n' + DELIVERY
    raise KeyError(case)


def decode(raw):
    def pairs(rows):
        obj = dict(rows)
        require(len(rows) == len(obj), 'duplicate JSON property')
        return obj
    def constant(_):
        raise Reject('invalid JSON numeric constant')
    require(len(raw) <= 131072, 'payload too large')
    obj = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    # Escaped unpaired surrogates are not valid text for this receiver.
    json.dumps(obj, ensure_ascii=False).encode('utf-8')
    return obj


def keys(value, expected, reason):
    require(type(value) is dict and value.keys() == set(expected), reason)


def route(day, minute, fault=None):
    query = day * 1440 + minute
    covering = []
    for i, (name, days, start, end) in enumerate(WINDOWS):
        duration = (end - start) % 1440
        if fault == 'day_owner':
            active = day in days and (start <= minute < end if end > start else minute >= start or minute < end)
        else:
            active = any((query - (d * 1440 + start)) % (7 * 1440) < duration for d in days)
        if active:
            covering.append((duration, i, name))
    if not covering:
        return 'idle'
    return covering[0][2] if fault == 'first_match' else min(covering)[2]


def check_night(obj):
    keys(obj, ('routes', 'witnesses'), 'top-level keys must be routes and witnesses')
    require(obj['routes'] == [route(d, m) for d, m in QUERIES], 'incorrect supplied routes')
    names = ('day_owner', 'first_match')
    keys(obj['witnesses'], names, 'missing named witness')
    for name, other in (names, names[::-1]):
        w = obj['witnesses'][name]
        keys(w, ('job', 'expected'), 'witness requires job and expected')
        keys(w['job'], ('receiver',), 'job requires a named receiver')
        j = w['job']['receiver']
        keys(j, ('day', 'minute'), 'receiver requires day and minute')
        d, m = j['day'], j['minute']
        require(type(d) is int and 0 <= d < 7 and type(m) is int and 0 <= m < 1440, 'invalid clock input')
        expected = route(d, m)
        require(w['expected'] == expected, 'incorrect expected route')
        require(route(d, m, name) != expected == route(d, m, other), 'witness does not isolate ' + name)


def frame_ref(job, fault=False):
    tokens = [str(job['sequence']), '|']
    replacements = {'\\': '\\\\', ';': '\\;', '\r': '\\r', '\n': '\\n'}
    for value in job['fields']:
        escaped = ''.join(replacements.get(ch, ch) for ch in value)
        tokens.extend([str(len(escaped) if fault else len(escaped.encode('utf-8'))), ':', escaped, ';'])
    return ''.join(tokens) + '\r\n'


def probes():
    edges = [[], [''], ['', ''], ['\n', '\\n', '\r', '\\r', '\r\n'], ['é', 'e\u0301', '🧪', ';\\'], [':|', '"', '\x00']]
    jobs = [{'fields': a, 'sequence': i} for i, a in enumerate(edges)]
    rng = random.Random(9833461)
    chars = ['a', 'é', '水', '🧪', ';', '\\', '\r', '\n', 'r', 'n', '\u0301', '"', ':', '|']
    for _ in range(36):
        fields = [''.join(rng.choices(chars, k=rng.randrange(9))) for _ in range(rng.randrange(5))]
        jobs.append({'fields': fields, 'sequence': rng.randrange(100000)})
    return jobs


def calculator():
    configured = os.environ.get('SOLVE_EVAL_CALCULATOR')
    if configured:
        path = Path(configured)
        if not path.is_file():
            raise RuntimeError('configured sealed macOS evaluator unavailable')
        return path.resolve()
    for parent in Path(__file__).resolve().parents:
        p = parent / 'evaluations/hard/runner/calculate.py'
        if p.is_file():
            return p
    raise RuntimeError('set SOLVE_EVAL_CALCULATOR to the sealed macOS evaluator')


def execute(source, jobs):
    require(type(source) is str and 0 < len(source.encode()) <= 32768, 'missing or oversized source')
    code = ("space = {'__name__':'__candidate__'}\n"
            f"exec(compile({source!r}, '<received source>', 'exec'),space)\n"
            f"jobs = {jobs!r}\n"
            "results = []\n"
            "for original in jobs:\n"
            "    job = json.loads(json.dumps(original))\n"
            "    value = space['frame'](**job)\n"
            "    results.append([job == original, value if type(value) is str else None])\n"
            "print(json.dumps(results,ensure_ascii=True))\n")
    if sys.platform != 'darwin':
        raise RuntimeError('sealed evaluator requires macOS')
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            p = subprocess.run([sys.executable, '-I', '-B', '-S', str(calculator())], input=code.encode(),
                               cwd='/', env={'LC_ALL':'C'}, stdout=out, stderr=err, timeout=6)
        except subprocess.TimeoutExpired as exc:
            raise Reject('received source timed out') from exc
        if p.returncode:
            err.seek(0)
            diagnostic = err.read(65536)
            if b'Could not isolate calculator' in diagnostic:
                raise RuntimeError('sealed evaluator unavailable')
            raise Reject('received source failed to compile or run')
        out.seek(0)
        actual = json.loads(out.read(65536))
    require(actual == [[True, frame_ref(j)] for j in jobs], 'received function failed a fixture or mutated its input')


def check_octet(obj):
    keys(obj, ('source', 'sample', 'edge'), 'top-level keys must be source, sample and edge')
    require(obj['sample'] == frame_ref(SAMPLE), 'sample frame differs from required wire text')
    w = obj['edge']
    keys(w, ('job', 'expected'), 'edge requires job and expected')
    j = w['job']
    keys(j, ('fields', 'sequence'), 'edge.job requires named fields and sequence')
    require(type(j['sequence']) is int and 0 <= j['sequence'] <= 999, 'invalid sequence in edge')
    require(type(j['fields']) is list and len(j['fields']) <= 2 and
            all(type(v) is str and len(v) <= 24 for v in j['fields']), 'invalid fields in edge')
    require(w['expected'] == frame_ref(j) != frame_ref(j, True), 'edge must expose the specified byte-length fault')
    execute(obj['source'], [SAMPLE, j, *probes()])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prompt', action='store_true')
    ap.add_argument('case', choices=CASES)
    args = ap.parse_args()
    if args.prompt:
        print(prompt(args.case))
        return 0
    raw = sys.stdin.buffer.read(131073)
    try:
        obj = decode(raw)
        (check_night if args.case == 'night-window' else check_octet)(obj)
    except (ValueError, UnicodeError, RecursionError) as e:
        print(f'rejected: {e}', file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f'unavailable: {e}', file=sys.stderr)
        return 2
    print('accepted sha256=' + hashlib.sha256(raw).hexdigest(), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
