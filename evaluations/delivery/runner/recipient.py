"""Open the answer emitted by a single trial and run the trusted consumer on its bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

LINK = re.compile(rb'\[[^\]\r\n]+\]\((artifacts/([0-9a-f]{64})\.json)\)')


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def inspect(case, message, consumer, attempts):
    raw = message.read_bytes()
    report = {'message_sha256': digest(raw), 'message_bytes': len(raw),
              'channel': 'inline', 'consumer_accepted': False, 'checked_before_delivery': False,
              'verified_link_delivery': False}
    match = LINK.fullmatch(raw.strip(b' \t\r\n'))
    if match:
        report['channel'] = 'file'
        target = message.parent / match[1].decode('ascii')
        report['opened'] = match[1].decode('ascii')
        if target.is_symlink() or target.parent.is_symlink() or not target.is_file():
            report['error'] = 'referenced file unavailable'
            return report, None
        raw = target.read_bytes()
        report['filename_matches_bytes'] = digest(raw) == match[2].decode('ascii')
    report.update(received_sha256=digest(raw), received_bytes=len(raw))
    # A final file verifier cannot establish that this answer was checked earlier.
    # Bind the received bytes to a successful producer-buffer-to-checker receipt as well.
    for attempt in attempts:
        receipt = attempt.get('receipt')
        if (attempt.get('status') == 'accepted' and receipt
                and receipt['sha256'] == report['received_sha256'] == attempt['producer_sha256']
                and receipt['bytes'] == len(raw) == attempt['producer_bytes']
                and (not match or receipt['path'] == report['opened'])):
            report['checked_before_delivery'] = True
            report['producer_call_id'] = attempt['producer_call_id']
            break
    try:
        result = subprocess.run([sys.executable, '-B', str(consumer), case], input=raw,
                                capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        report['consumer_error'] = type(error).__name__
        return report, raw
    report['consumer_exit'] = result.returncode
    report['consumer_stdout'] = result.stdout.decode('utf8', 'replace')
    report['consumer_stderr'] = result.stderr.decode('utf8', 'replace')
    report['consumer_accepted'] = result.returncode == 0
    report['verified_link_delivery'] = bool(match and report['filename_matches_bytes']
                                            and report['checked_before_delivery'] and report['consumer_accepted'])
    return report, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--message', required=True, type=Path)
    parser.add_argument('--receipts', required=True, type=Path)
    parser.add_argument('--consumer', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    report, raw = inspect(args.case, args.message, args.consumer,
                          json.loads(args.receipts.read_bytes()))
    if raw is not None:
        (args.out.parent / 'received.bin').write_bytes(raw)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
