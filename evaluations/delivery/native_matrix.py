"""Run the published matched native CLI comparison. Each conversation starts from scratch."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--outage',action='store_true')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    if any(args.out.iterdir()):
        parser.error('use an empty output directory')
    cases=('packet-map',) if args.outage else ('packet-map','night-window','octet-frame')
    grid=[(case,arm,rep) for rep in (1,2) for case in cases for arm in
          (('candidate','baseline') if rep==1 else ('baseline','candidate'))]
    def run(row):
        case,arm,repeat=row
        cmd=[sys.executable,'-B',str(Path(__file__).with_name('native.py')),arm,case,str(repeat),
             str(args.out/f'{case}-{arm}-r{repeat}')]
        if args.outage:
            cmd.append('--unavailable')
        return subprocess.run(cmd).returncode
    if run(grid[0]):
        return 1
    with ThreadPoolExecutor(max_workers=3) as pool:
        return int(any(list(pool.map(run,grid[1:]))))


if __name__=='__main__':
    raise SystemExit(main())
