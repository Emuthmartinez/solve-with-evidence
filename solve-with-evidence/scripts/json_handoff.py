"""Deliver the exact UTF-8 JSON object bytes accepted by a supplied consumer."""
import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
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


def deliver(raw, directory):
    """Publish a checked buffer once in a caller-owned recipient-visible directory."""
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink():
        raise OSError('delivery directory must not be a symbolic link')
    directory = directory.resolve(strict=True)
    digest = hashlib.sha256(raw).hexdigest()
    target = directory / (digest + '.json')
    # Stage on the same filesystem. A hard link creates the finished name atomically
    # and, unlike rename, cannot replace another publisher's file.
    with tempfile.TemporaryDirectory(prefix='.handoff-', dir=directory) as staging:
        staged = Path(staging) / 'payload'
        with staged.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        staged.chmod(0o400)
        try:
            os.link(staged, target)
        except FileExistsError:
            pass  # A retry is successful only after verifying the existing file below.

    stored = target.lstat()
    if not stat.S_ISREG(stored.st_mode) or stored.st_size != len(raw):
        raise OSError('delivery path already contains a different artifact')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(os.open(target, flags), 'rb') as received:
        if not os.path.samestat(stored, os.fstat(received.fileno())) or received.read() != raw:
            raise OSError('delivery readback differs from checked bytes')
    return {'path': str(target), 'sha256': digest, 'bytes': len(raw)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('received', type=Path, help='exact bytes received from the producer')
    parser.add_argument('--replacement', type=Path, help='one separately prepared replacement, checked only on rejection')
    parser.add_argument('--deliver-to', type=Path, metavar='DIRECTORY',
                        help='atomically publish checked bytes here and print a JSON file receipt')
    parser.add_argument('--timeout', type=int, default=20, help='positive wall-time limit for each consumer attempt')
    parser.add_argument('--unchecked', action='append', default=[], metavar='ITEM',
                        help='something the consumer does not check; listed in the receipt. Repeatable. Needs --deliver-to')
    parser.add_argument('consumer', nargs='+', help='trusted validator command after --; reads stdin; exits 0 only on acceptance, 1 on rejection')
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('timeout must be positive')
    if args.unchecked and args.deliver_to is None:
        parser.error('--unchecked needs --deliver-to: the receipt is what carries the list')
    if not all(item.strip() for item in args.unchecked):
        parser.error('each --unchecked item must say what was not checked')

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
            accepted = check(raw, consume)
            if args.deliver_to is not None:
                receipt = deliver(accepted, args.deliver_to)
                if args.unchecked:
                    # The consumer still accepted these bytes. The list travels with them.
                    receipt.update(outcome='delivered_unchecked', unchecked=args.unchecked)
                print(json.dumps(receipt), flush=True)
                return 0
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
