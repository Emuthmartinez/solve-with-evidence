"""Score a finished run against the pre-registered pass bar.

    report.py --run RUN        prints the report and writes RUN/report.json

A mock run exercises this code and yields no verdict: its numbers are fixtures, not measurements.
"""
import argparse
import json
import math
from pathlib import Path
import statistics
import sys

import bench

Z95 = 1.959964


def wilson(wins, total):
    """95% Wilson score interval for a proportion."""
    if not total:
        return [0.0, 1.0]
    p = wins / total
    centre = p + Z95 ** 2 / (2 * total)
    half = Z95 * math.sqrt(p * (1 - p) / total + Z95 ** 2 / (4 * total ** 2))
    return [round((centre - half) / (1 + Z95 ** 2 / total), 4), round((centre + half) / (1 + Z95 ** 2 / total), 4)]


def share(rows, key):
    hits = sum(bool(r['grade'].get(key)) for r in rows)
    return {'n': hits, 'of': len(rows), 'rate': round(hits / len(rows), 4) if rows else None}


def points(a, b):
    return round(100 * (a['rate'] - b['rate']), 2)


class Run:
    def __init__(self, run):
        self.meta = json.loads((run / 'run.json').read_text())
        self.bar = json.loads((bench.HERE / 'pass_bar.json').read_text())
        if self.bar['design']['confidence'] != 0.95:
            raise SystemExit('this report computes 95% intervals only')
        trials = [json.loads(p.read_text()) for p in sorted((run / 'trials').glob('*/trial.json'))]
        self.errors = [f"{t['task']}--{t['arm']}--r{t['repeat']}" for t in trials if t['infra_error']]
        self.trials = [t for t in trials if not t['infra_error']]
        optional = lambda name: json.loads((run / name).read_text()) if (run / name).exists() else None
        self.judgments, self.human = optional('judgments.json'), optional('human.json')
        self.reps = len(self.bar['design']['repeats'])

    def rows(self, arms, kinds):
        return [t for t in self.trials if t['arm'] in arms and t['kind'] in kinds]

    def complete(self, arms, kinds):
        """Every designed trial of these arms and kinds is present and free of infrastructure errors."""
        expected = sum(self.bar['design']['tasks'][kind] for kind in kinds) * self.reps
        return (self.meta['repeats'] == self.bar['design']['repeats']
                and all(len(self.rows([arm], kinds)) == expected for arm in arms))

    def arm_summary(self, arm):
        rows = self.rows([arm], ('exec', 'write', 'trap'))
        written = [r['grade'] for r in rows if r['kind'] == 'write' and r['grade']['delivered']]
        tokens = [r['tokens'] for r in rows if r['tokens'] is not None]
        mean = lambda values: round(statistics.mean(values), 2) if values else None
        return {
            'trials': len(rows),
            'exec_pass': share(self.rows([arm], ['exec']), 'success'),
            'trap_pass': share(self.rows([arm], ['trap']), 'success'),
            'deterministic_success': share(self.rows([arm], ('exec', 'trap')), 'success'),
            'false_completions': share(self.rows([arm], ('exec', 'trap')), 'false_completion'),
            'refusals_on_solvable': share(self.rows([arm], ('exec', 'write')), 'refusal'),
            'unsupported_claims_per_output': mean([g['unsupported'] for g in written]),
            'unmatched_sentences_per_output': mean([g['unmatched'] for g in written]),
            'tokens_total': sum(tokens) if len(tokens) == len(rows) else None,
            'tokens_median': statistics.median(tokens) if tokens else None,
            'wall_s_median': statistics.median([r['wall_s'] for r in rows]) if rows else None,
            'tool_calls_mean': mean([r['tool_calls'] for r in rows]),
        }

    # Each criterion returns {'result': 'pass' | 'fail' | 'inconclusive', ...evidence}.

    def writing_pairwise(self, rule):
        pairs = self.bar['design']['pairs']
        if not self.judgments:
            return {'result': 'inconclusive', 'why': 'not judged yet'}
        if not self.complete([arm for pair in pairs for arm in pair], ['write']):
            return {'result': 'inconclusive', 'why': 'writing trials are incomplete'}
        rows = [p for p in self.judgments['pairs'] if p['arms'] in pairs]
        decided = [p for p in rows if p['outcome'] in ('decided', 'forfeit')]
        wins = sum(p['winner'] == p['arms'][0] for p in decided)
        out = {'pairs': len(rows), 'decided': len(decided), 'wins': wins,
               'split_or_tie': len(rows) - len(decided),
               'win_rate': round(wins / len(decided), 4) if decided else None, 'ci95': wilson(wins, len(decided))}
        human = [h for h in self.human or [] if h['arms'] in [sorted(p) for p in pairs] and h['winner']]
        if len(human) >= 16:
            human_wins = sum(h['winner'] == next(p[0] for p in pairs if sorted(p) == h['arms']) for h in human)
            out['human'] = {'picks': len(human), 'wins': human_wins, 'win_rate': round(human_wins / len(human), 4),
                            'ci95': wilson(human_wins, len(human)), 'raters': len({h['rater'] for h in human})}
        if not self.judgments['judge']['independent']:
            return {**out, 'result': 'inconclusive', 'why': "the judge is from the solver's model family"}
        if not rows or len(decided) / len(rows) < rule['min_decided_fraction']:
            return {**out, 'result': 'inconclusive', 'why': 'too few pairs were decided in both orders'}
        passed = out['win_rate'] >= rule['min_win_rate'] and out['ci95'][0] > rule['min_ci_lower_exclusive']
        if passed and 'human' in out and out['human']['win_rate'] < 0.5:
            return {**out, 'result': 'inconclusive', 'why': 'human picks disagree with the model judge'}
        return {**out, 'result': 'pass' if passed else 'fail'}

    def weak_model_gain(self, rule):
        skill, plain = self.bar['design']['weak_pair']
        if not self.complete([skill, plain], ('exec', 'trap')):
            return {'result': 'inconclusive', 'why': 'weak-model trials are incomplete'}
        a, b = (share(self.rows([arm], ('exec', 'trap')), 'success') for arm in (skill, plain))
        gain = points(a, b)
        return {'result': 'pass' if gain >= rule['min_points'] else 'fail', 'points': gain, skill: a, plain: b}

    def false_completions(self, rule):
        pairs = self.bar['design']['pairs']
        if not self.complete([arm for pair in pairs for arm in pair], ('exec', 'trap')):
            return {'result': 'inconclusive', 'why': 'trials are incomplete'}
        counts = [[share(self.rows([arm], ('exec', 'trap')), 'false_completion')['n'] for arm in pair] for pair in pairs]
        skill, plain = sum(c[0] for c in counts), sum(c[1] for c in counts)
        out = {'skill': skill, 'no_skill': plain, 'by_pair': dict(zip(('/'.join(p) for p in pairs), counts))}
        if plain == 0:
            return {**out, 'result': 'inconclusive', 'why': 'the no-skill arms made no false completion to reduce'}
        return {**out, 'result': 'pass' if skill < plain and all(c[0] <= c[1] for c in counts) else 'fail'}

    def cost(self, rule):
        pairs = self.bar['design']['pairs']
        totals = [[self.arm_summary(arm)['tokens_total'] for arm in pair] for pair in pairs]
        if not self.complete([arm for pair in pairs for arm in pair], ('exec', 'write', 'trap')) \
                or any(value is None for pair in totals for value in pair):
            return {'result': 'inconclusive', 'why': 'trials or token counts are incomplete'}
        ratio = round(sum(t[0] for t in totals) / sum(t[1] for t in totals), 3)
        medians = [[self.arm_summary(arm)[key] for arm in pairs[0]] for key in ('wall_s_median', 'tool_calls_mean')]
        return {'result': 'pass' if ratio < rule['max_token_ratio_exclusive'] else 'fail', 'token_ratio': ratio,
                'wall_s_median': medians[0], 'tool_calls_mean': medians[1]}

    def method_not_compute(self, rule):
        skill, control = self.bar['design']['budget_control']
        if not self.complete([skill, control], ('exec', 'trap')):
            return {'result': 'inconclusive', 'why': 'budget-control trials are incomplete'}
        use = statistics.median(r['budget']['used'] / r['budget']['target'] for r in self.rows([control], ('exec', 'trap')))
        a, b = (share(self.rows([arm], ('exec', 'trap')), 'success') for arm in (skill, control))
        out = {'budget_use_median': round(use, 3), skill: a, control: b, 'points': points(a, b)}
        if use < rule['min_budget_use']:
            return {**out, 'result': 'inconclusive', 'why': 'the control did not spend its token budget'}
        return {**out, 'result': 'pass' if a['rate'] > b['rate'] else 'fail'}

    def refusals(self, rule):
        pairs = self.bar['design']['pairs']
        if not self.complete([arm for pair in pairs for arm in pair], ('exec', 'write')):
            return {'result': 'inconclusive', 'why': 'trials are incomplete'}
        a, b = (share(self.rows([pair[side] for pair in pairs], ('exec', 'write')), 'refusal') for side in (0, 1))
        excess = points(a, b)
        return {'result': 'pass' if excess <= rule['max_excess_points'] else 'fail', 'excess_points': excess,
                'skill': a, 'no_skill': b}

    def calibration(self, rule):
        arm = self.bar['design']['calibration_arm']
        if not self.complete([arm], ['exec']):
            return {'result': 'inconclusive', 'why': 'calibration trials are incomplete'}
        passed = share(self.rows([arm], ['exec']), 'success')
        return {'result': 'pass' if rule['min'] <= passed['rate'] <= rule['max'] else 'inconclusive', arm: passed,
                'why': None if rule['min'] <= passed['rate'] <= rule['max'] else 'executable tasks are at floor or ceiling'}

    def report(self):
        criteria = {name: getattr(self, name)(rule) for name, rule in self.bar['criteria'].items()}
        validity = {'calibration': self.calibration(self.bar['validity']['calibration'])}
        results = [c['result'] for c in criteria.values()]
        if self.meta['adapter'] == 'mock':
            verdict = 'MOCK RUN: no verdict. These numbers are fixtures that test the harness, not measurements.'
        elif validity['calibration']['result'] != 'pass' or 'inconclusive' in results:
            verdict = 'INCONCLUSIVE'
        else:
            verdict = 'FAIL' if 'fail' in results else 'PASS'
        return {'verdict': verdict, 'adapter': self.meta['adapter'], 'models': self.meta['models'],
                'freeze': self.meta['freeze'], 'criteria': criteria, 'validity': validity,
                'arms': {arm: self.arm_summary(arm) for arm in self.meta['arms']},
                'infrastructure_errors': self.errors, 'judge': (self.judgments or {}).get('judge')}


def render(report):
    lines = [f"Verdict: {report['verdict']}", f"Adapter {report['adapter']}, models {report['models']}, "
             f"freeze {report['freeze'][:12]}", '', '| Criterion | Result | Evidence |', '|---|---|---|']
    for name, row in {**report['criteria'], **report['validity']}.items():
        evidence = ', '.join(f'{k}={v}' for k, v in row.items() if k != 'result' and v is not None)
        lines.append(f"| {name} | {row['result']} | {evidence} |")
    lines += ['', '| Arm | Trials | Exec pass | Trap pass | False completions | Refusals on solvable | '
              'Unsupported claims per output | Tokens (median) | Wall s (median) | Tool calls (mean) |',
              '|---|---|---|---|---|---|---|---|---|---|']
    cell = lambda s: f"{s['n']}/{s['of']}"
    for arm, s in report['arms'].items():
        lines.append(f"| {arm} | {s['trials']} | {cell(s['exec_pass'])} | {cell(s['trap_pass'])} | "
                     f"{cell(s['false_completions'])} | {cell(s['refusals_on_solvable'])} | "
                     f"{s['unsupported_claims_per_output']} | {s['tokens_median']} | {s['wall_s_median']} | "
                     f"{s['tool_calls_mean']} |")
    if report['infrastructure_errors']:
        lines += ['', 'Excluded for infrastructure errors (rerun these): ' + ', '.join(report['infrastructure_errors'])]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    report = Run(run).report()
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(render(report))


if __name__ == '__main__':
    sys.exit(main())
