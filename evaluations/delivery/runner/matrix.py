"""Run a paired matrix, one candidate smoke then interleaved pairs. Preserve all attempts."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['cases','repo','out']:
        p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args()
    cases,repo,out=a.cases.resolve(),a.repo.resolve(),a.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):
        p.error('output must be empty')
    case_names = sorted(p.stem for p in (cases/'inputs').glob('*.json'))
    if not case_names:
        p.error('case directory needs frozen inputs')
    order=[(case,arm,repeat) for repeat in (1,2) for case in case_names for arm in
           (('candidate','baseline') if repeat==1 else ('baseline','candidate'))]
    env=dict(os.environ, SOLVE_EVAL_CALCULATOR=str(repo/'evaluations/hard/runner/calculate.py'))
    candidate = repo/'evaluations/delivery/snapshots/candidate'
    def run(task):
        case,arm,repeat=task
        trial=out/f'{case}-{arm}-r{repeat}'
        skill = candidate if arm == 'candidate' else repo/'evaluations/hard/snapshots/shipped'
        command=[sys.executable,'-B',str(HERE/'run.py'),'--core',str(repo/'evaluations/hard/runner'),
                 '--case',str(cases/'inputs'/f'{case}.json'),'--consumer',str(cases/'consumer.py'),
                 '--gate',str(candidate/'scripts/json_handoff.py'),'--skill',str(skill),
                 '--arm',arm,'--repeat',str(repeat),'--out',str(trial)]
        result=subprocess.run(command,env=env,capture_output=True,text=True)
        print(trial.name,'exit',result.returncode,result.stdout.strip()[:160],flush=True)
        if result.returncode:
            print('manifest', (trial/'manifest.json').is_file(), 'runner stderr',result.stderr[-400:],flush=True)
        return result.returncode
    if run(order[0]):
        return 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(run,order[1:]))
    return int(any(results))


if __name__=='__main__':
    raise SystemExit(main())
