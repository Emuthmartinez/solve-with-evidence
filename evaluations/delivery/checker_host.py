"""Run the evaluator outside the solver sandbox. Keep acceptance records with the host."""
from contextlib import contextmanager
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import threading
import time
import uuid


def read_request(directory, name):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(name, flags, dir_fd=directory)
    except OSError:
        return None
    with os.fdopen(fd, 'rb', buffering=0) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 131073:
            return None
        return stream.read(131074)


def reply(directory, stem, record):
    temporary = uuid.uuid4().hex + '.sending'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=directory)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(record, stream)
        os.replace(temporary, stem+'.reply', src_dir_fd=directory, dst_dir_fd=directory)
    finally:
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass


@contextmanager
def serve(workspace, archive, consumer, case, unavailable):
    spool = workspace / '.case-check'
    spool.mkdir()
    directory = os.open(spool, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    receipts = archive / 'checker-receipts'
    receipts.mkdir()
    stop = threading.Event()
    failures = []

    def poll():
        try:
            while not stop.wait(.025):
                for name in os.listdir(directory):
                    if not re.fullmatch(r'[0-9a-f]{32}\.request', name):
                        continue
                    stem = name.split('.')[0]
                    raw = read_request(directory, name)
                    try:
                        os.unlink(name, dir_fd=directory)
                    except (FileNotFoundError, IsADirectoryError):
                        continue
                    if raw is None or (receipts/stem).exists():
                        continue
                    if unavailable:
                        code, stdout, stderr = 2, '', 'unavailable: simulated recipient outage\n'
                    else:
                        result = subprocess.run([sys.executable, '-B', str(consumer), case],
                                                input=raw, capture_output=True, timeout=12)
                        code, stdout, stderr = result.returncode, result.stdout.decode(), result.stderr.decode()
                    record = {'time_ns':time.time_ns(), 'exit':code, 'stdout':stdout, 'stderr':stderr,
                              'sha256':hashlib.sha256(raw).hexdigest(), 'origin':'host consumer'}
                    path = receipts/stem
                    path.mkdir()
                    (path/'input.bin').write_bytes(raw)
                    (path/'result.json').write_text(json.dumps(record,indent=2)+'\n')
                    reply(directory, stem, record)
        except Exception as exc:
            failures.append(exc)

    worker = threading.Thread(target=poll, daemon=True)
    worker.start()
    try:
        yield receipts
    finally:
        stop.set()
        worker.join()
        os.close(directory)
        if failures:
            raise RuntimeError('host checker failed') from failures[0]
