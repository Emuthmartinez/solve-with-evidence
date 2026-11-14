"""Native-shell client for the independent fixture consumer. Usage: ./case-check < candidate.json."""
import json
from pathlib import Path
import sys
import time
import uuid


def main():
    spool = Path(__file__).resolve().parent / '.case-check'
    stem = uuid.uuid4().hex
    scratch = spool / (stem + '.part')
    raw = sys.stdin.buffer.read(131073)
    scratch.write_bytes(raw)
    scratch.rename(spool / (stem + '.request'))
    reply = spool / (stem + '.reply')
    until = time.monotonic() + 15
    while time.monotonic() < until:
        if reply.exists():
            data = json.loads(reply.read_bytes())
            sys.stderr.write(data['stderr'])
            sys.stdout.write(data['stdout'])
            return data['exit']
        time.sleep(.025)
    print('unavailable: host checker timed out', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
