#!/usr/bin/env python3
"""Public text prompts and deterministic JSON graders for six two-turn cases."""
import argparse
import copy
from fractions import Fraction
import json
import math
from pathlib import Path

if __package__:
    from . import probe, roster
else:
    import probe
    import roster

FAMILIES = {"probe": probe, "roster": roster}
IDS = tuple(f"{family}-{variant}" for family in FAMILIES for variant in ("d1", "d2", "h1"))


def lookup(case_id):
    if case_id not in IDS:
        raise ValueError(f"Unknown case {case_id!r}")
    family, variant = case_id.split("-")
    return FAMILIES[family], variant


def prompt(case_id, stage):
    if stage not in (1, 2):
        raise ValueError("stage must be 1 or 2")
    module, variant = lookup(case_id)
    return module.prompt(variant, stage)


class Checks:
    def __init__(self, tolerance):
        self.tolerance = tolerance
        self.checks = {}
        self.critical_failures = []

    @staticmethod
    def action(value):
        return value.strip().upper() if isinstance(value, str) else None

    def fail(self, name):
        if name not in self.critical_failures:
            self.critical_failures.append(name)

    def number(self, value, expected):
        if expected is None:
            return value is None
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            return False
        # Python JSON parses integers exactly and preserves floats close to a stated boundary.
        try:
            return math.isfinite(value) and abs(value - expected) <= self.tolerance + 1e-12
        except OverflowError:
            return False

    def add(self, name, correct, weight):
        self.checks[name] = {"passed": bool(correct), "weight": weight}

    def values(self, name, given, target, weight):
        ok = isinstance(given, dict) and given.keys() == target.keys()
        self.add(name, ok and all(self.number(given[k], v) for k, v in target.items()), weight)


def grade(case_id, replies):
    module, variant = lookup(case_id)
    if not isinstance(replies, (tuple, list)) or len(replies) != 2:
        raise ValueError("Exactly two chronological replies are required.")
    check = Checks(0.01 if module is probe else 0)
    normalized = []
    for i, reply in enumerate(replies, 1):
        if not isinstance(reply, dict):
            check.fail(f"{i}.invalid_json_object")
        normalized.append(reply if isinstance(reply, dict) else {})
    module.checks(variant, *normalized, check)
    points = sum(item["weight"] for item in check.checks.values() if item["passed"])
    maximum = sum(item["weight"] for item in check.checks.values())
    return {"case": case_id, "points": points, "max_points": maximum,
            "pass": points == maximum and not check.critical_failures,
            "critical_failures": check.critical_failures, "checks": check.checks}


def probe_check(variant):
    costs, losses, rows, initial, first, bit, _, revised = probe.data(variant)
    independent = probe.enumerate_policies(rows, probe.TESTS, costs, losses)
    assert independent == initial
    assert first not in probe.best_choices(probe.action_values(rows, probe.TESTS, costs, losses, 1))
    ranks = sorted(initial.values())
    assert (ranks[1] - ranks[0]) / probe.mass(rows) >= Fraction(12, 100)
    remaining = [test for test in probe.TESTS if test != first]

    def brute_one(group, prices):
        # Enumerate both contingent terminal repairs for each remaining purchase.
        sums = {a: sum(w * losses[i][m] for m, _, w, _ in group) for i, a in enumerate(probe.MODES)}
        for t in remaining:
            sums[t] = min(sum(w * (prices[t] + losses[(b if readings[probe.TESTS.index(t)] else a)][m])
                              for m, _, w, readings in group) for a in range(4) for b in range(4))
        return sums

    for b in (0, 1):
        group = [row for row in rows if row[-1][probe.TESTS.index(first)] == b]
        assert brute_one(group, costs) == probe.action_values(group, remaining, costs, losses, 1)
    group = [row for row in rows if row[-1][probe.TESTS.index(first)] == bit]
    new = brute_one(group, revised)
    assert new == probe.action_values(group, remaining, revised, losses, 1)
    assert probe.best_choices(new) != probe.best_choices(brute_one(group, costs))
    ranks = sorted(new.values())
    assert (ranks[1] - ranks[0]) / probe.mass(group) >= Fraction(15, 100)
    posterior = probe.answer(variant)[1]["posterior"]
    total = sum(row[2] for row in group)
    twice = []
    for index, mode in enumerate(probe.MODES):
        prior_weight = sum(row[2] for row in rows if row[0] == index)
        like = sum(row[2] for row in group if row[0] == index) / prior_weight
        twice.append(posterior[mode] * like)
        expected = sum(row[2] / total for row in group if row[0] == index)
        assert abs(expected - posterior[mode]) < 1e-12
    assert any(abs(posterior[mode] - twice[i] / sum(twice)) > 0.01 for i, mode in enumerate(probe.MODES))


def selftest():
    cases = []
    for case_id in IDS:
        module, variant = lookup(case_id)
        if module is probe:
            probe_check(variant)
        else:
            roster.exhaustive_check(variant)
            _, nominal, _, scores, _ = roster.evaluate(roster.SEEDS[variant])
            nominal_best = roster.minima({seq: n for seq, n in nominal.items() if n is not None})
            robust_best = roster.minima(scores)
            assert set(nominal_best).isdisjoint(robust_best)
            assert len(robust_best) == 1 and len(scores) < sum(n is not None for n in nominal.values())
            root, _, _, _, values, _ = roster.case(variant)
            assert len(roster.minima(values)) == 1 and roster.DIST[root][roster.minima(values)[0]] == (1 if variant == "d2" else 2)
        original = module.answer(variant)
        gold = grade(case_id, original)
        assert gold["pass"] and gold["points"] == gold["max_points"] == 10
        assert grade(case_id, [{}, {}])["points"] == 0
        assert not grade(case_id, [None, "invalid"])["pass"]
        bad = copy.deepcopy(original)
        partial = copy.deepcopy(original)
        if module is probe:
            bad[1]["action"] = probe.data(variant)[4]
            partial[0]["first_losses"]["STOP"] += 2
        else:
            bad[1]["roster"] = "EEEEE"
            partial[0]["next_score"] += 1
        invalid = grade(case_id, bad)
        scored = grade(case_id, partial)
        assert invalid["critical_failures"] and not invalid["pass"]
        assert 0 < scored["points"] < 10 and not scored["pass"] and not scored["critical_failures"]
        assert grade(case_id, [original[0], {}])["points"] == 5
        for stage in (1, 2):
            assert prompt(case_id, stage).strip()
        cases.append(case_id)
    return {"pass": True, "cases": cases, "coverage":
            ["all oracle answers", "independent enumeration", "branch/update margins", "missing and malformed replies",
             "partial credit", "critical illegal action", "stage independence"]}


def read_answer(path):
    content = Path(path).read_text().strip()
    if content.startswith(("```json\n", "```JSON\n", "```\n")) and content.endswith("\n```"):
        content = content.split("\n", 1)[1].rsplit("\n```", 1)[0]
    try:
        def reject_constant(value):
            raise ValueError(f"Non-finite JSON constant: {value}")
        return json.loads(content, parse_constant=reject_constant)
    except (ValueError, RecursionError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    show = sub.add_parser("prompt")
    show.add_argument("case", choices=IDS)
    show.add_argument("stage", choices=(1, 2), type=int)
    assess = sub.add_parser("grade")
    assess.add_argument("case", choices=IDS)
    assess.add_argument("answers", nargs=2)
    sub.add_parser("selftest")
    args = parser.parse_args()
    if args.command == "prompt":
        print(prompt(args.case, args.stage))
    elif args.command == "grade":
        print(json.dumps(grade(args.case, [read_answer(path) for path in args.answers]), indent=2))
    else:
        print(json.dumps(selftest(), indent=2))


if __name__ == "__main__":
    main()
