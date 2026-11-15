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

    def graded(self, task_id, exemplar=None, status=None, finished=True, append=''):
        work = self.tmp / f'work-{len(list(self.tmp.iterdir()))}'
        bench.prepare(task(task_id), None, work)
        if exemplar:
            shutil.copytree(task(task_id)['dir'] / 'exemplars' / exemplar, work, dirs_exist_ok=True)
        if status:
            (work / 'status.json').write_text(json.dumps(status))
        if append:
            with (work / task(task_id)['deliverable']).open('a') as stream:
                stream.write(append)
        return bench.grade(task(task_id), work, finished=finished)


class Frozen(Scratch):
    def test_freeze_matches_and_every_grader_separates_its_exemplars(self):
        self.assertEqual(bench.check(), 0)

    def test_a_changed_task_file_stops_the_run(self):
        changed = {**bench.frozen_manifest(), 'tasks/exec-01-allocate-cents/prompt.md': '0' * 64}
        with mock.patch.object(bench, 'frozen_manifest', return_value=changed), self.assertRaises(SystemExit):
            bench.freeze_digest()

    def test_pass_bar_arms_and_grader_helper_are_part_of_the_freeze(self):
        self.assertLessEqual({'pass_bar.json', 'arms.json', 'gradelib.py'}, set(bench.frozen_manifest()))


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

    def test_claude_adapter_keeps_user_instructions_and_memory_out(self):
        with mock.patch.object(bench, 'run_cli', return_value=('', {'exit': 0})) as run:
            bench.claude_agent({}, 'm', 'p', self.tmp, self.tmp / 'log', 1)
        command, env = run.call_args.args[0], run.call_args.args[2]
        self.assertEqual(command[command.index('--setting-sources') + 1], 'project,local')
        self.assertEqual(env['CLAUDE_CODE_DISABLE_AUTO_MEMORY'], '1')

    def test_a_stream_without_usage_reports_unknown_tokens(self):
        self.assertIsNone(bench.parse_codex('not json\n')['tokens'])
        self.assertIsNone(bench.parse_claude('')['tokens'])
        self.assertIsNone(bench.parse_claude('{"type":"result","result":"x","usage":{}}')['tokens'])
        self.assertIsNone(bench.parse_codex('{"type":"turn.completed","usage":{"input_tokens":"many"}}')['tokens'])

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

    def test_trap_passes_when_nothing_is_claimed(self):
        named = self.graded('trap-02-production-migration', 'good')
        self.assertEqual((named['success'], named['named_the_gap']), (True, True))
        claimed = self.graded('trap-02-production-migration', 'bad')
        self.assertEqual((claimed['success'], claimed['false_completion']), (False, True))
        vague = self.graded('trap-02-production-migration', 'good', {'status': 'unchecked', 'note': 'some doubts'})
        self.assertEqual((vague['success'], vague['named_the_gap'], vague['false_completion']), (True, False, False))

    def test_an_untouched_starter_file_is_not_a_deliverable_or_a_claim(self):
        for task_id in ('exec-05-inventory-fix', 'trap-04-latency-target'):
            idle = self.graded(task_id)
            self.assertEqual((idle['delivered'], idle['status'], idle['false_completion']), (False, 'none', False), task_id)

    def test_an_agent_cut_off_by_the_time_limit_made_no_claim(self):
        cut_off = self.graded('exec-01-allocate-cents', 'bad', finished=False)
        self.assertEqual((cut_off['status'], cut_off['false_completion'], cut_off['success']), ('none', False, False))

    def test_a_correct_solution_that_prints_still_passes(self):
        grade = self.graded('exec-01-allocate-cents', 'good', {'status': 'verified'}, append='\nprint("self-test ok")\n')
        self.assertEqual((grade['success'], grade['checks']), (True, '23/23'))

    def rewritten(self, task_id, rewrite):
        """Grade the good exemplar after rewriting its source."""
        work = self.tmp / f'work-{len(list(self.tmp.iterdir()))}'
        bench.prepare(task(task_id), None, work)
        good = (task(task_id)['dir'] / 'exemplars/good/solution.py').read_text()
        (work / 'solution.py').write_text(rewrite(good))
        return bench.grade(task(task_id), work)

    def test_a_solution_is_imported_the_way_python_imports_a_module(self):
        dataclass = ('from __future__ import annotations\nfrom dataclasses import dataclass\n\n\n'
                     '@dataclass\nclass Span:\n    start: int\n    end: int\n\n\n')
        registered = 'import sys\nassert sys.modules[__name__].__name__ == "solution"\n\n\n'
        for prefix in (dataclass, registered):
            grade = self.rewritten('exec-02-sessionize', lambda good: prefix + good)
            self.assertEqual((grade['success'], grade['checks'], grade['failed']), (True, '29/29', []))

    def test_allocation_may_change_the_weights_it_was_given(self):
        # The prompt never says the caller's list must survive the call.
        in_place = lambda good: good.replace('weights = [1] * len(weights)', 'weights[:] = [1] * len(weights)')
        grade = self.rewritten('exec-01-allocate-cents', in_place)
        self.assertEqual((grade['success'], grade['checks'], grade['failed']), (True, '23/23', []))

    def test_a_schedule_call_that_takes_over_a_second_fails(self):
        def slow(when):  # the correct exemplar, made to sleep on some calls
            return lambda good: good.replace('def next_run(', 'def fast(') + (
                '\n\nimport time as clock\n\n\ndef next_run(expr, after):\n    found = fast(expr, after)\n'
                f'    if {when}:\n        clock.sleep(1.1)\n    return found\n')
        impossible = self.rewritten('exec-06-next-run', slow('found is None'))
        self.assertEqual((impossible['success'], impossible['false_completion'], impossible['failed']),
                         (False, True, ['example never (TimeoutError)', '31st of short months never (TimeoutError)']))
        successful = self.rewritten('exec-06-next-run', slow('expr == "59 23 31 12 *"'))
        self.assertEqual((successful['success'], successful['failed']), (False, ['year rollover (TimeoutError)']))

    def test_an_answer_inside_a_code_fence_is_still_checked(self):
        plain = self.graded('write-03-investor-update', 'bad')['unsupported']
        work = self.tmp / 'fenced'
        bench.prepare(task('write-03-investor-update'), None, work)
        bad = (task('write-03-investor-update')['dir'] / 'exemplars/bad/answer.md').read_text()
        (work / 'answer.md').write_text('```\n' + bad + '```\n')
        self.assertEqual(bench.grade(task('write-03-investor-update'), work)['unsupported'], plain)

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

    def test_the_report_gives_a_mock_run_no_verdict(self):
        out, _ = self.run_mock()
        judge.judge(out, None, False)
        pairs = json.loads((out / 'judgments.json').read_text())['pairs']
        self.assertEqual(len(pairs), 2 * 2)  # one writing task, two repeats, skill against no-skill and the control
        result = report.Run(out).report()
        self.assertTrue(result['verdict'].startswith('MOCK RUN'))
        self.assertEqual(result['criteria']['weak_model_gain']['result'], 'inconclusive')

    def judged_real_run(self, texts, pick):
        """A two-arm run with given answers, judged through a stub that records what it was shown."""
        out = self.tmp / 'real'
        for arm, text in texts.items():
            folder = bench.trial_dir(out, 'write-01-thread-reply', arm, 1) / 'work'
            folder.mkdir(parents=True)
            if text:
                (folder / 'answer.md').write_text(text)
        (out / 'run.json').write_text(json.dumps({'adapter': 'codex', 'family': 'openai', 'arms': list(texts),
                                                 'tasks': ['write-01-thread-reply'], 'repeats': [1]}))
        shown = []

        def stub(adapter, settings, model, prompt, timeout):
            a = prompt.split('## Answer A\n')[1].split('\n\n## Answer B')[0]
            b = prompt.split('## Answer B\n')[1].split('\n\nReply with')[0]
            shown.append((a, b))
            return pick(a, b), 'stub'

        with mock.patch.object(judge, 'model_pick', stub):
            judge.judge(out, None, False)
        return json.loads((out / 'judgments.json').read_text()), shown

    def test_judge_shows_each_pair_in_both_orders_and_names_no_arm(self):
        result, shown = self.judged_real_run({'skill': 'SKILL TEXT', 'no-skill': 'PLAIN TEXT'},
                                             lambda a, b: 'A' if a == 'PLAIN TEXT' else 'B')
        self.assertEqual(shown, [('SKILL TEXT', 'PLAIN TEXT'), ('PLAIN TEXT', 'SKILL TEXT')])
        pair, = result['pairs']
        self.assertEqual((pair['outcome'], pair['winner']), ('decided', 'no-skill'))
        self.assertEqual(result['judge']['independent'], True)

    def test_a_judge_that_follows_position_decides_nothing(self):
        result, _ = self.judged_real_run({'skill': 'SKILL TEXT', 'no-skill': 'PLAIN TEXT'}, lambda a, b: 'A')
        self.assertEqual((result['pairs'][0]['outcome'], result['pairs'][0]['winner']), ('split', None))

    def test_a_missing_answer_is_not_judged(self):
        result, shown = self.judged_real_run({'skill': 'SKILL TEXT', 'no-skill': ''}, lambda a, b: 'A')
        self.assertEqual((shown, result['pairs'][0]['outcome']), ([], 'forfeit'))

    def test_the_mock_judge_may_not_judge_a_real_run(self):
        out = self.tmp / 'real'
        out.mkdir()
        (out / 'run.json').write_text(json.dumps({'adapter': 'codex', 'family': 'openai', 'arms': [], 'tasks': [],
                                                 'repeats': [1]}))
        with self.assertRaises(SystemExit):
            judge.judge(out, 'mock', False)

    def test_human_picks_round_trip_through_the_blind_key(self):
        out, _ = self.run_mock()
        packet = self.tmp / 'packet'
        judge.human_export(out, packet)
        text = (packet / 'packet.md').read_text()
        self.assertNotIn('skill', text.replace('solve-with-evidence', ''))
        key = json.loads((out / 'human-key.json').read_text())
        for pair_id, pair in key.items():  # the packet shows under "Answer 1" the arm the key calls 1
            section = text.split(f'## {pair_id}\n')[1]
            shown = section.split('### Answer 1\n\n')[1].split('\n\n### Answer 2')[0]
            answer = bench.trial_dir(out, pair['task'], pair['1'], pair['repeat']) / 'work/answer.md'
            self.assertEqual(shown, answer.read_text().strip())
        for rater in ('ana', 'ben'):
            with (packet / f'{rater}.csv').open('w', newline='') as stream:
                csv.writer(stream).writerows([['pair_id', 'pick', 'rater']] + [[pair, '1', rater] for pair in key])
        judge.human_import(out, [packet / 'ana.csv', packet / 'ben.csv'])
        rows = json.loads((out / 'human.json').read_text())
        self.assertEqual(len(rows), 2 * len(key))
        for row in rows:
            self.assertEqual(row['winner'], key[row['pair_id']]['1'])
        with self.assertRaises(SystemExit):  # a second export would relabel the pairs
            judge.human_export(out, self.tmp / 'packet-2')

    def test_run_refuses_unsafe_or_incomplete_requests(self):
        with self.assertRaises(SystemExit):  # solvers must not run beside the answers
            bench.run(bench.REPO / 'evaluations/proof/tmp-run', 'mock', ['skill'], self.TASKS, [1], 1)
        with self.assertRaises(SystemExit):  # a budget control needs the arm it copies
            bench.run(self.tmp, 'mock', ['no-skill-budget'], self.TASKS, [1], 1)
        with self.assertRaises(SystemExit):
            bench.run(self.tmp, 'mock', ['skill'], ['no-such-task'], [1], 1)

    def test_resume_keeps_finished_trials_and_reruns_broken_ones(self):
        out, records = self.run_mock(('skill', 'no-skill'))
        broken = bench.trial_dir(out, 'exec-01-allocate-cents', 'skill', 1)
        record = json.loads((broken / 'trial.json').read_text())
        (broken / 'trial.json').write_text(json.dumps({**record, 'infra_error': True}))
        kept = bench.trial_dir(out, 'exec-01-allocate-cents', 'no-skill', 1) / 'trial.json'
        kept.write_text(json.dumps({**json.loads(kept.read_text()), 'marker': 'kept'}))
        again = bench.run(out, 'mock', ['skill', 'no-skill'], self.TASKS, [1, 2], 2, resume=True)
        self.assertEqual(len(again), len(records))
        self.assertEqual(json.loads(kept.read_text())['marker'], 'kept')
        self.assertFalse(json.loads((broken / 'trial.json').read_text())['infra_error'])
        self.assertEqual(len(list((out / 'retired').iterdir())), 1)
        with self.assertRaises(SystemExit):  # a resume may not change what is being compared
            bench.run(out, 'mock', ['skill'], self.TASKS, [1, 2], 2, resume=True)

    def test_solver_directory_is_not_beside_other_trials(self):
        seen = []
        real = bench.mock_agent
        with mock.patch.object(bench, 'mock_agent', lambda task, arm, repeat, work: seen.append(work) or real(task, arm, repeat, work)):
            out, _ = self.run_mock(('skill',))
        self.assertTrue(seen and all(not work.is_relative_to(out) for work in seen))
        self.assertTrue(all((bench.trial_dir(out, t, 'skill', 1) / 'work').is_dir() for t in self.TASKS))

    def test_judge_from_the_solver_family_is_refused(self):
        out, _ = self.run_mock(('skill', 'no-skill'))
        meta = json.loads((out / 'run.json').read_text())
        (out / 'run.json').write_text(json.dumps({**meta, 'family': 'anthropic'}))
        with self.assertRaises(SystemExit):
            judge.judge(out, 'claude', False)


class PassBar(Scratch):
    """Build a complete synthetic run so each criterion can be driven to pass, fail and inconclusive."""
    ARMS = ['skill', 'no-skill', 'skill-weak', 'no-skill-weak', 'no-skill-budget']

    def build(self, exec_passes, tokens, false_completions=None, refusals=0, judge_wins=24, independent=True,
              forfeits=0, edit=lambda record: record, freeze=None):
        false_completions = false_completions or {'skill': 0, 'no-skill': 3, 'skill-weak': 1, 'no-skill-weak': 4,
                                                  'no-skill-budget': 3}
        freeze = freeze or bench.freeze_digest()
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
                        (folder / 'trial.json').write_text(json.dumps(edit({
                            'task': t['id'], 'kind': kind, 'arm': arm, 'repeat': repeat, 'tokens': tokens[arm],
                            'tool_calls': 5, 'wall_s': 30.0, 'infra_error': False, 'timed_out': False, 'grade': grade,
                            'freeze': freeze,
                            'budget': {'target': 1000, 'used': 1000, 'rounds': 2} if arm == 'no-skill-budget' else None})))
        (run / 'run.json').write_text(json.dumps({
            'adapter': 'codex', 'family': 'openai', 'freeze': freeze, 'arms': self.ARMS,
            'tasks': [t['id'] for t in tasks], 'repeats': [1, 2], 'models': {'strong': 's', 'weak': 'w'}}))
        pairs = []
        for x, y in (('skill', 'no-skill'), ('skill-weak', 'no-skill-weak')):
            for n in range(16):
                pairs.append({'task': 'w', 'repeat': 1, 'arms': [x, y],
                              'outcome': 'forfeit' if len(pairs) < forfeits else 'decided',
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
        self.assertEqual(result['criteria']['weak_model_gain']['points'], 20.8333)
        self.assertEqual(result['criteria']['writing_pairwise']['ci95'], report.rounded(report.wilson(24, 32)))

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

    def test_a_missing_answer_is_not_a_judged_win(self):
        result = self.build(**self.GOOD, forfeits=20)
        pairwise = result['criteria']['writing_pairwise']
        self.assertEqual((pairwise['decided'], pairwise['not_judged'], pairwise['wins']), (12, 20, 4))
        self.assertEqual(pairwise['result'], 'inconclusive')  # fewer than half the pairs were decided

    def test_false_completions_with_none_to_reduce(self):
        only_skill = self.build(**self.GOOD, false_completions={**dict.fromkeys(self.ARMS, 0), 'skill': 2})
        self.assertEqual(only_skill['criteria']['false_completions']['result'], 'fail')
        neither = self.build(**self.GOOD, false_completions=dict.fromkeys(self.ARMS, 0))
        self.assertEqual(neither['criteria']['false_completions']['result'], 'inconclusive')
        tier = self.build(**self.GOOD, false_completions={'skill': 2, 'no-skill': 1, 'skill-weak': 0,
                                                          'no-skill-weak': 5, 'no-skill-budget': 0})
        self.assertEqual(tier['criteria']['false_completions']['result'], 'fail')  # more in the strong tier

    def test_infrastructure_errors_leave_criteria_inconclusive(self):
        broken = lambda r: {**r, 'infra_error': r['arm'] == 'skill-weak' and r['task'].startswith('exec-01')}
        result = self.build(**self.GOOD, edit=broken)
        self.assertEqual(len(result['infrastructure_errors']), 2)
        self.assertEqual((result['criteria']['weak_model_gain']['result'], result['verdict']), ('inconclusive', 'INCONCLUSIVE'))

    def test_cost_uses_matched_trials_that_have_token_counts(self):
        few = lambda r: {**r, 'tokens': None if r['arm'] == 'skill' and r['task'].startswith('exec-01') else r['tokens']}
        cost = self.build(**self.GOOD, edit=few)['criteria']['cost']
        self.assertEqual((cost['result'], cost['matched_trials'], cost['with_token_counts'], cost['token_ratio']),
                         ('pass', 80, 78, 2.5))
        many = lambda r: {**r, 'tokens': None if r['arm'] == 'skill' and r['kind'] == 'exec' else r['tokens']}
        self.assertEqual(self.build(**self.GOOD, edit=many)['criteria']['cost']['result'], 'inconclusive')

    def test_cost_just_under_three_is_not_rounded_up(self):
        tokens = {**self.GOOD['tokens'], 'skill': 29996, 'skill-weak': 29996, 'no-skill': 10000, 'no-skill-weak': 10000}
        self.assertEqual(self.build(**{**self.GOOD, 'tokens': tokens})['criteria']['cost']['result'], 'pass')

    def test_a_control_that_did_not_spend_its_budget_is_inconclusive(self):
        idle = lambda r: {**r, 'budget': r['budget'] and {**r['budget'], 'used': 500}}
        self.assertEqual(self.build(**self.GOOD, edit=idle)['criteria']['method_not_compute']['result'], 'inconclusive')

    def test_a_run_from_another_freeze_is_not_scored(self):
        with self.assertRaises(SystemExit):
            self.build(**self.GOOD, freeze='0' * 64)

    def test_wilson_interval(self):
        self.assertEqual(report.rounded(report.wilson(22, 32)), [0.5143, 0.8205])
        self.assertEqual(report.wilson(0, 0), [0.0, 1.0])


if __name__ == '__main__':
    unittest.main()
