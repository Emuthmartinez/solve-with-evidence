"""Offline tests for the proof benchmark harness. No model is called.

    python3 -B evaluations/proof/test_bench.py
"""
import csv
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'hard')]
import bench
import compare
import judge
import report

# Shapes captured from one live call to each CLI (codex-cli 0.166.0, Claude Code 2.1.322).
CODEX_STREAM = '''{"type":"thread.started","thread_id":"t"}
{"type":"item.completed","item":{"id":"item_0","type":"command_execution","command":"pwd","exit_code":0,"status":"completed"}}
{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"printf OK > ok.txt","exit_code":0,"status":"completed"}}
{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"DONE"}}
{"type":"turn.completed","usage":{"input_tokens":41053,"cached_input_tokens":38528,"cache_write_input_tokens":0,"output_tokens":63,"reasoning_output_tokens":0}}
Reading additional input from stdin...
'''
CLAUDE_STREAM = '''{"type":"system","subtype":"init","skills":[],"mcp_servers":[],"slash_commands":[],"plugins":[{"name":"cc-plugin-telemetry"}]}
{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Write","input":{}}]}}
{"type":"user","message":{"content":[{"type":"tool_result"}]}}
{"type":"assistant","message":{"content":[{"type":"text","text":"DONE"}]}}
{"type":"result","subtype":"success","is_error":false,"result":"DONE","total_cost_usd":0.0013,"usage":{"input_tokens":4,"cache_creation_input_tokens":4372,"cache_read_input_tokens":41369,"output_tokens":99,"service_tier":"standard"}}
'''


def task(task_id):
    return next(t for t in bench.load_tasks() if t['id'] == task_id)


class Scratch(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()

    def graded(self, task_id, exemplar=None, status=None):
        work = self.tmp / f'work-{len(list(self.tmp.iterdir()))}'
        bench.prepare(task(task_id), None, work)
        if exemplar:
            shutil.copytree(task(task_id)['dir'] / 'exemplars' / exemplar, work, dirs_exist_ok=True)
        if status:
            (work / 'status.json').write_text(json.dumps(status))
        return bench.grade(task(task_id), work)


class Frozen(Scratch):
    def test_freeze_matches_and_every_grader_separates_its_exemplars(self):
        self.assertEqual(bench.check(), 0)

    def test_a_changed_task_file_stops_the_run(self):
        changed = {**bench.frozen_manifest(), 'tasks/exec-01-allocate-cents/prompt.md': '0' * 64}
        with mock.patch.object(bench, 'frozen_manifest', return_value=changed), self.assertRaises(SystemExit):
            bench.freeze_digest()

    def test_pass_bar_and_arms_are_part_of_the_freeze(self):
        self.assertLessEqual({'pass_bar.json', 'arms.json'}, set(bench.frozen_manifest()))


class Arms(Scratch):
    def test_registry_has_no_skill_weak_model_and_budget_control(self):
        arms = compare.ARMS['arms']
        self.assertIsNone(arms['no-skill']['skill'])
        self.assertEqual((arms['skill-weak']['model'], arms['no-skill-weak']['model']), ('weak', 'weak'))
        self.assertEqual((arms['no-skill-budget']['skill'], arms['no-skill-budget']['budget_of']), (None, 'skill'))
        for arm in arms.values():
            self.assertTrue(arm['skill'] is None or (compare.HERE / arm['skill'] / 'SKILL.md').is_file())

    def test_sealed_suite_gives_a_no_skill_arm_the_placebo_and_the_weak_model(self):
        with mock.patch.object(compare.subprocess, 'run', return_value=compare.subprocess.CompletedProcess([], 1, '', '')) as runner:
            with self.assertRaises(RuntimeError):  # the stubbed runner writes no summary
                compare.run_job(('no-skill-weak', 'ledger-d1', 1), self.tmp)
        command = runner.call_args[0][0]
        self.assertEqual(command[command.index('--skill') + 1], str(compare.HERE / 'no-skill'))
        self.assertEqual(command[command.index('--model') + 1], compare.ARMS['adapters']['codex']['models']['weak'])


class Adapters(Scratch):
    def test_codex_stream(self):
        parsed = bench.parse_codex(CODEX_STREAM)
        self.assertEqual((parsed['tokens'], parsed['tool_calls'], parsed['text']), (41053 + 63, 2, 'DONE'))

    def test_claude_stream(self):
        parsed = bench.parse_claude(CLAUDE_STREAM)
        self.assertEqual((parsed['tokens'], parsed['tool_calls'], parsed['text']), (4 + 4372 + 41369 + 99, 1, 'DONE'))
        self.assertEqual(parsed['loaded'], {'skills': 0, 'mcp_servers': 0, 'slash_commands': 0,
                                            'plugins': ['cc-plugin-telemetry']})

    def test_a_stream_without_usage_reports_unknown_tokens(self):
        self.assertIsNone(bench.parse_codex('not json\n')['tokens'])
        self.assertIsNone(bench.parse_claude('')['tokens'])

    def test_skill_arm_gets_the_skill_folder_and_one_extra_line(self):
        skill = bench.REPO / 'solve-with-evidence'
        with_skill = bench.prepare(task('write-01-thread-reply'), skill, self.tmp / 'a')
        without = bench.prepare(task('write-01-thread-reply'), None, self.tmp / 'b')
        self.assertEqual(with_skill, bench.SKILL_LINE + without)
        self.assertTrue((self.tmp / 'a/solve-with-evidence/SKILL.md').is_file())
        self.assertFalse((self.tmp / 'b/solve-with-evidence').exists())
        self.assertEqual(len(list((self.tmp / 'b/notes').iterdir())), 8)
        self.assertFalse(any('exemplar' in p.name or p.name == 'grader.py' for p in (self.tmp / 'a').rglob('*')))


class Grading(Scratch):
    def test_a_failing_deliverable_claimed_as_verified_is_a_false_completion(self):
        grade = self.graded('exec-01-allocate-cents', 'bad', {'status': 'verified'})
        self.assertEqual((grade['success'], grade['false_completion'], grade['refusal']), (False, True, False))

    def test_a_deliverable_with_no_status_is_an_implicit_claim(self):
        grade = self.graded('exec-01-allocate-cents', 'bad')
        self.assertEqual((grade['status'], grade['false_completion']), ('verified', True))

    def test_disclosed_doubt_is_not_a_false_completion(self):
        grade = self.graded('exec-01-allocate-cents', 'bad', {'status': 'unchecked', 'unchecked': ['large totals']})
        self.assertEqual((grade['success'], grade['false_completion']), (False, False))

    def test_refusing_a_solvable_task_is_a_refusal(self):
        grade = self.graded('exec-01-allocate-cents', None, {'status': 'cannot_verify'})
        self.assertEqual((grade['success'], grade['refusal'], grade['false_completion']), (False, True, False))

    def test_trap_passes_only_when_the_gap_is_named_and_nothing_is_claimed(self):
        self.assertTrue(self.graded('trap-02-production-migration', 'good')['success'])
        claimed = self.graded('trap-02-production-migration', 'bad')
        self.assertEqual((claimed['success'], claimed['false_completion']), (False, True))
        vague = self.graded('trap-02-production-migration', 'good', {'status': 'unchecked', 'note': 'some doubts'})
        self.assertEqual((vague['success'], vague['false_completion']), (False, False))

    def test_writing_is_scored_against_the_source_pack(self):
        self.assertEqual(self.graded('write-03-investor-update', 'good')['unsupported'], 0)
        self.assertGreater(self.graded('write-03-investor-update', 'bad')['unsupported'], 3)


class MockRun(Scratch):
    TASKS = ['exec-01-allocate-cents', 'write-01-thread-reply', 'trap-01-legacy-parity']

    def run_mock(self, arms=('skill', 'no-skill', 'no-skill-budget')):
        out = self.tmp / 'run'
        out.mkdir()
        return out, bench.run(out, 'mock', list(arms), self.TASKS, [1, 2], 2)

    def test_matrix_records_cost_and_the_budget_control_spends_its_target(self):
        out, records = self.run_mock()
        self.assertEqual(len(records), 3 * 3 * 2)
        self.assertTrue(all(r['tokens'] and r['tool_calls'] and r['freeze'] for r in records))
        control = [r for r in records if r['arm'] == 'no-skill-budget']
        self.assertTrue(all(r['budget']['used'] >= r['budget']['target'] and r['budget']['rounds'] > 1 for r in control))
        self.assertTrue(all(r['skill_sha256'] for r in records if r['arm'] == 'skill'))
        self.assertTrue(all(r['skill_sha256'] is None for r in records if r['arm'] != 'skill'))

    def test_judge_swaps_positions_and_the_report_gives_a_mock_run_no_verdict(self):
        out, _ = self.run_mock()
        judge.judge(out, None, False)
        pairs = json.loads((out / 'judgments.json').read_text())['pairs']
        self.assertEqual(len(pairs), 2 * 2)  # one writing task, two repeats, skill against no-skill and the control
        for pair in pairs:
            if pair['orders']:
                self.assertEqual([o['first'] for o in pair['orders']], pair['arms'])
        result = report.Run(out).report()
        self.assertTrue(result['verdict'].startswith('MOCK RUN'))
        self.assertEqual(result['criteria']['weak_model_gain']['result'], 'inconclusive')

    def test_human_picks_round_trip_through_the_blind_key(self):
        out, _ = self.run_mock()
        packet = self.tmp / 'packet'
        judge.human_export(out, packet)
        self.assertNotIn('skill', (packet / 'packet.md').read_text().replace('solve-with-evidence', ''))
        key = json.loads((out / 'human-key.json').read_text())
        with (packet / 'picks.csv').open('w', newline='') as stream:
            csv.writer(stream).writerows([['pair_id', 'pick', 'rater']] + [[pair, '1', 'ana'] for pair in key])
        judge.human_import(out, packet / 'picks.csv')
        for row in json.loads((out / 'human.json').read_text()):
            self.assertEqual(row['winner'], key[row['pair_id']]['1'])

    def test_run_refuses_unsafe_or_incomplete_requests(self):
        with self.assertRaises(SystemExit):  # solvers must not run beside the answers
            bench.run(bench.REPO / 'evaluations/proof/tmp-run', 'mock', ['skill'], self.TASKS, [1], 1)
        with self.assertRaises(SystemExit):  # a budget control needs the arm it copies
            bench.run(self.tmp, 'mock', ['no-skill-budget'], self.TASKS, [1], 1)
        with self.assertRaises(SystemExit):
            bench.run(self.tmp, 'mock', ['skill'], ['no-such-task'], [1], 1)

    def test_judge_from_the_solver_family_is_refused(self):
        out, _ = self.run_mock(('skill', 'no-skill'))
        meta = json.loads((out / 'run.json').read_text())
        (out / 'run.json').write_text(json.dumps({**meta, 'family': 'anthropic'}))
        with self.assertRaises(SystemExit):
            judge.judge(out, 'claude', False)


class PassBar(Scratch):
    """Build a complete synthetic run so each criterion can be driven to pass, fail and inconclusive."""
    ARMS = ['skill', 'no-skill', 'skill-weak', 'no-skill-weak', 'no-skill-budget']

    def build(self, exec_passes, tokens, false_completions=None, refusals=0, judge_wins=24, independent=True):
        false_completions = false_completions or {'skill': 0, 'no-skill': 3, 'skill-weak': 1, 'no-skill-weak': 4,
                                                  'no-skill-budget': 3}
        run = self.tmp / f'run-{len(list(self.tmp.iterdir()))}'
        tasks = bench.load_tasks()
        for arm in self.ARMS:
            for kind in ('exec', 'write', 'trap'):
                for index, t in enumerate(x for x in tasks if x['kind'] == kind):
                    for repeat in (1, 2):
                        slot = index * 2 + repeat - 1
                        grade = {'delivered': True, 'status': 'verified', 'refusal': False}
                        if kind == 'exec':
                            grade.update(success=slot < exec_passes[arm], false_completion=slot >= 16 - false_completions[arm],
                                         refusal=arm.startswith('skill') and slot < refusals)
                        elif kind == 'trap':
                            grade.update(success=True, false_completion=False)
                        else:
                            grade.update(unsupported=0, unmatched=0, words=50, over_limit=False)
                        folder = bench.trial_dir(run, t['id'], arm, repeat)
                        folder.mkdir(parents=True)
                        (folder / 'trial.json').write_text(json.dumps({
                            'task': t['id'], 'kind': kind, 'arm': arm, 'repeat': repeat, 'tokens': tokens[arm],
                            'tool_calls': 5, 'wall_s': 30.0, 'infra_error': False, 'grade': grade,
                            'budget': {'target': 1000, 'used': 1000, 'rounds': 2} if arm == 'no-skill-budget' else None}))
        (run / 'run.json').write_text(json.dumps({
            'adapter': 'codex', 'family': 'openai', 'freeze': 'f' * 64, 'arms': self.ARMS,
            'tasks': [t['id'] for t in tasks], 'repeats': [1, 2], 'models': {'strong': 's', 'weak': 'w'}}))
        pairs = []
        for x, y in (('skill', 'no-skill'), ('skill-weak', 'no-skill-weak')):
            for n in range(16):
                pairs.append({'task': 'w', 'repeat': 1, 'arms': [x, y], 'outcome': 'decided',
                              'winner': x if len(pairs) < judge_wins else y})
        (run / 'judgments.json').write_text(json.dumps({'judge': {'independent': independent}, 'pairs': pairs}))
        return report.Run(run).report()

    GOOD = dict(exec_passes={'skill': 13, 'no-skill': 8, 'skill-weak': 10, 'no-skill-weak': 5, 'no-skill-budget': 9},
                tokens={'skill': 2500, 'no-skill': 1000, 'skill-weak': 2500, 'no-skill-weak': 1000, 'no-skill-budget': 2500})

    def test_every_criterion_met_is_a_pass(self):
        result = self.build(**self.GOOD)
        self.assertEqual({name: c['result'] for name, c in result['criteria'].items()},
                         dict.fromkeys(result['criteria'], 'pass'))
        self.assertEqual(result['verdict'], 'PASS')
        self.assertEqual(result['criteria']['weak_model_gain']['points'], 20.83)
        self.assertEqual(result['criteria']['writing_pairwise']['ci95'], report.wilson(24, 32))

    def test_three_times_the_tokens_fails_on_cost(self):
        result = self.build(**{**self.GOOD, 'tokens': {**self.GOOD['tokens'], 'skill': 3000, 'skill-weak': 3000}})
        self.assertEqual((result['criteria']['cost']['result'], result['verdict']), ('fail', 'FAIL'))

    def test_a_win_rate_whose_interval_reaches_half_fails(self):
        result = self.build(**self.GOOD, judge_wins=21)
        self.assertEqual(result['criteria']['writing_pairwise']['win_rate'], 0.6562)
        self.assertEqual(result['criteria']['writing_pairwise']['result'], 'fail')

    def test_a_small_weak_model_gain_fails(self):
        result = self.build(**{**self.GOOD, 'exec_passes': {**self.GOOD['exec_passes'], 'skill-weak': 8}})
        self.assertEqual(result['criteria']['weak_model_gain']['result'], 'fail')

    def test_a_control_that_matches_the_skill_fails_method_not_compute(self):
        result = self.build(**{**self.GOOD, 'exec_passes': {**self.GOOD['exec_passes'], 'no-skill-budget': 13}})
        self.assertEqual(result['criteria']['method_not_compute']['result'], 'fail')

    def test_more_false_completions_or_refusals_fail(self):
        worse = self.build(**self.GOOD, false_completions=dict.fromkeys(self.ARMS, 3))
        self.assertEqual(worse['criteria']['false_completions']['result'], 'fail')
        refusing = self.build(**self.GOOD, refusals=6)
        self.assertEqual(refusing['criteria']['refusals']['result'], 'fail')

    def test_ceiling_and_same_family_judge_are_inconclusive_not_fail(self):
        ceiling = self.build(**{**self.GOOD, 'exec_passes': dict.fromkeys(self.ARMS, 16)})
        self.assertEqual((ceiling['validity']['calibration']['result'], ceiling['verdict']), ('inconclusive', 'INCONCLUSIVE'))
        same = self.build(**self.GOOD, independent=False)
        self.assertEqual((same['criteria']['writing_pairwise']['result'], same['verdict']), ('inconclusive', 'INCONCLUSIVE'))

    def test_wilson_interval(self):
        self.assertEqual(report.wilson(22, 32), [0.5143, 0.8205])
        self.assertEqual(report.wilson(0, 0), [0.0, 1.0])


if __name__ == '__main__':
    unittest.main()
