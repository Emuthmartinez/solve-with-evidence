"""Dispatch matched trials with isolated solver contexts, and score recorded final answers."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import random
import subprocess
import sys

HERE = Path(__file__).resolve().parent
from tracecheck.audit import Suites


def run_job(job, destination):
    arm, case, repeat = job
    messages, grade = Suites(HERE).get(case)
    trials = destination / 'trials'
    trial = trials / f'{case}-{arm}-r{repeat}'
    inputs = destination / 'inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    case_file = inputs / f'{case}-{arm}-r{repeat}.json'
    case_file.write_text(json.dumps({'id': case, 'messages': messages}, indent=2) + '\n')
    package = HERE.parents[1] / 'solve-with-evidence' if arm == 'shipped' else HERE / 'snapshots' / arm
    cmd = [sys.executable, '-B', str(HERE / 'runner/run_trial.py'),
           '--case', str(case_file), '--skill', str(package), '--out', str(trial),
           '--model', 'gpt-6.1-sol', '--effort', 'medium', '--timeout', '200']
    print('start',trial.name,flush=True)
    result=subprocess.run(cmd,capture_output=True,text=True)
    summary_file=trial/'summary.json'
    if not summary_file.exists():
        print('runner missing summary',trial.name,result.returncode, result.stderr[-650:], flush=True)
        raise RuntimeError('No runner summary: '+trial.name)
    summary=json.loads(summary_file.read_text())
    record={'arm':arm,'case':case,'repeat':repeat,'status':summary['status'],'runner_exit':result.returncode}
    if summary['status']=='completed':
        record['score'] = grade([turn['text'] for turn in summary['turns']])
    else:
        record['error']=summary.get('error','See trial trace')
    (trial/'grade.json').write_text(json.dumps(record,indent=2)+'\n')
    print('finish',trial.name,record['status'],(record.get('score') or {}).get('points'),(record.get('score') or {}).get('pass'),flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='Fresh directory for captured traces and inputs')
    parser.add_argument('--arms', nargs='+', choices=['baseline', 'candidate', 'release', 'final', 'published', 'shipped'], required=True)
    parser.add_argument('--cases', nargs='+', required=True)
    parser.add_argument('--repeats', nargs='+', type=int, required=True)
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    destination = args.out.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        parser.error('choose an empty output directory to preserve existing trial records')
    if args.jobs < 1 or min(args.repeats) < 1:
        parser.error('jobs and repetition identifiers must be positive')
    jobs = [(arm, case, rep) for rep in args.repeats for case in args.cases for arm in args.arms]
    if len(set(jobs)) != len(jobs):
        parser.error('duplicate trials in requested matrix')
    random.Random(1428).shuffle(jobs)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_job, job, destination) for job in jobs]
        for future in as_completed(futures):
            future.result()


if __name__ == '__main__':
    main()
