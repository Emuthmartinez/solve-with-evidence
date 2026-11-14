"""Pass the original UTF-8 JSON object bytes only after the supplied consumer accepts them."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


class Reject(ValueError):
    pass


def parse(raw):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise Reject('duplicate object key')
            obj[key] = value
        return obj

    def nonfinite(_):
        raise Reject('non-JSON numeric constant')

    try:
        obj = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)
    except Reject:
        raise
    except (ValueError, RecursionError) as exc:
        raise Reject('invalid UTF-8 JSON object: ' + str(exc)) from exc
    if type(obj) is not dict:
        raise Reject('expected a JSON object')
    return obj


def check(raw, consumer):
    parse(raw)
    if not consumer or consumer(raw) is not True:
        raise Reject('independent consumer did not explicitly accept the payload')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('received', type=Path, help='exact bytes received from the producer')
    parser.add_argument('--replacement', type=Path, help='one separately prepared replacement, checked only on rejection')
    parser.add_argument('--timeout', type=int, default=20, help='positive wall-time limit for each consumer attempt')
    parser.add_argument('consumer', nargs='+', help='trusted validator command after --; reads stdin; exits 0 only on acceptance, 1 on rejection')
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('timeout must be positive')

    def consume(raw):
        code = subprocess.run(args.consumer, input=raw, stdout=subprocess.DEVNULL, stderr=sys.stderr,
                              timeout=args.timeout, check=False).returncode
        if code not in (0, 1):
            raise RuntimeError(f'consumer failed (exit {code})')
        return code == 0

    for attempt, path in [('received', args.received), ('replacement', args.replacement)]:
        if path is None:
            continue
        try:
            raw = path.read_bytes()
            check(raw, consume)
        except Reject as exc:
            print(f'{attempt} rejected: {exc}', file=sys.stderr)
            continue
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            print(f'handoff unavailable: {exc}', file=sys.stderr)
            return 2
        print(f'{attempt} accepted: sha256={hashlib.sha256(raw).hexdigest()}', file=sys.stderr)
        sys.stdout.buffer.write(raw)
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
