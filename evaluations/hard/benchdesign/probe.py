"""An adaptive diagnostic using a shared, persistent instrument calibration."""

from fractions import Fraction
from itertools import product
import json
import random

MODES = ("A", "B", "C", "D")
TESTS = ("T", "U", "V", "W")
SEEDS = {"d1": 9, "d2": 20, "h1": 26}


def instrument(seed):
    rng = random.Random(seed)
    costs = {test: Fraction(rng.randint(4, 22), 10) for test in TESTS}
    losses = [[0 if i == j else rng.randint(6, 24) for j in range(4)] for i in range(4)]
    rows = []
    for mode in range(4):
        normal = [rng.randrange(2) for _ in TESTS]
        # A drifted calibration flips multiple instruments together.
        flips = rng.sample(range(4), rng.choice([2, 3]))
        drift = [bit ^ (index in flips) for index, bit in enumerate(normal)]
        rows.extend([(mode, "normal", rng.randint(5, 15), tuple(normal)),
                     (mode, "drift", rng.randint(2, 9), tuple(drift))])
    return costs, losses, rows


def mass(rows):
    return sum(row[2] for row in rows)


def branch(rows, test, bit):
    index = TESTS.index(test)
    return [row for row in rows if row[3][index] == bit]


def repair_totals(rows, losses):
    return {mode: sum(weight * losses[coord][state] for state, _, weight, _ in rows)
            for coord, mode in enumerate(MODES)}


def best_choices(values):
    best = min(values.values())
    return sorted(key for key, value in values.items() if value == best)


def action_values(rows, tests, costs, losses, depth):
    """Bellman recursion. Work in mass-weighted units until display time."""
    values = repair_totals(rows, losses)
    if depth and rows:
        for test in tests:
            remaining = [other for other in tests if other != test]
            continuation = sum(min(action_values(branch(rows, test, bit), remaining, costs,
                                                 losses, depth - 1).values()) for bit in (0, 1))
            values[test] = mass(rows) * costs[test] + continuation
    return values


def enumerate_policies(rows, tests, costs, losses):
    """Independent first-action oracle. Enumerate deterministic policy leaves."""
    def leaf_cost(group, treatment):
        return sum(row[2] * losses[treatment][row[0]] for row in group)

    def terminal_policies(group, options):
        for treatment in range(4):
            yield leaf_cost(group, treatment)
        for probe in options:
            for leaves in product(range(4), repeat=2):
                value = 0
                for mode, _, weight, readings in group:
                    repair = leaves[readings[TESTS.index(probe)]]
                    value += weight * (costs[probe] + losses[repair][mode])
                yield value

    result = {mode: leaf_cost(rows, index) for index, mode in enumerate(MODES)}
    for first in tests:
        options = tuple(other for other in tests if other != first)
        groups = [[row for row in rows if row[3][TESTS.index(first)] == bit] for bit in (0, 1)]
        choices = [list(terminal_policies(group, options)) for group in groups]
        result[first] = mass(rows) * costs[first] + min(a + b for a, b in product(*choices))
    return result


def revision(rows, costs, losses, first):
    """Select a branch with a strictly consequential posted price correction."""
    remaining = [test for test in TESTS if test != first]
    for bit in (0, 1):
        group = branch(rows, first, bit)
        if not group:
            continue
        original = action_values(group, remaining, costs, losses, 1)
        old = best_choices(original)
        if len(old) != 1 or old[0] not in remaining:
            continue
        updated = dict(costs)
        updated[old[0]] += 6
        revised = action_values(group, remaining, updated, losses, 1)
        new = best_choices(revised)
        if len(new) == 1 and new != old:
            return bit, old[0], updated
    return None


def data(variant):
    costs, losses, rows = instrument(SEEDS[variant])
    initial = action_values(rows, TESTS, costs, losses, 2)
    first = best_choices(initial)[0]
    bit, changed, revised = revision(rows, costs, losses, first)
    return costs, losses, rows, initial, first, bit, changed, revised


def numeric(values, scale):
    return {key: float(Fraction(value, scale)) for key, value in values.items()}


def answer(variant):
    costs, losses, rows, initial, first, bit, _, revised = data(variant)
    remaining = [test for test in TESTS if test != first]
    subsets = [branch(rows, first, outcome) for outcome in (0, 1)]
    first_values = {"STOP": min(initial[mode] for mode in MODES),
                    **{test: initial[test] for test in TESTS}}
    s1 = dict(first=first, first_losses=numeric(first_values, mass(rows)),
              next={str(outcome): best_choices(action_values(group, remaining, costs, losses, 1))[0]
                    for outcome, group in enumerate(subsets)})
    group = subsets[bit]
    values = action_values(group, remaining, revised, losses, 1)
    action = best_choices(values)[0]
    after = {}
    if action in remaining:
        for outcome in (0, 1):
            subset = branch(group, action, outcome)
            after[str(outcome)] = best_choices(repair_totals(subset, losses))[0] if subset else "IMPOSSIBLE"
    s2 = dict(posterior=numeric({mode: sum(row[2] for row in group if row[0] == idx)
                                 for idx, mode in enumerate(MODES)}, mass(group)),
              action=action, remaining_losses=numeric(values, mass(group)), repair_after=after)
    return [s1, s2]


def prompt(variant, stage):
    costs, losses, rows, _, first, bit, changed, revised = data(variant)
    if stage == 2:
        return f"""The field supervisor used {first} and observed {bit}. A second display showed {bit} from the SAME stored reading. One additional distinct test can still be bought. The posted cost of {changed} is now {float(revised[changed]):g}. All other prices and data stand. Condition on this update regardless of your prior recommendation. The paid test is a sunk cost.
Return one JSON object with posterior (probabilities keyed A/B/C/D), remaining_losses (all four immediate repairs keyed A/B/C/D and all three still-available first test IDs, each with its expected loss from now under optimal follow-up), action (optimal next repair or test ID), and repair_after (empty object for immediate repair, or a map from "0" and "1" to optimal repair IDs after your chosen test, using IMPOSSIBLE for a zero-probability branch). Report numbers to within 0.01 absolute error."""
    weights = "\n".join(f"{MODES[mode]} {cal:6} {weight:2}  " + " ".join(map(str, bits))
                        for mode, cal, weight, bits in rows)
    matrix = "\n".join(f"{mode}  " + " ".join(map(str, row)) for mode, row in zip(MODES, losses))
    return f"""A field team must repair a failed drive. One latent row below is drawn with probability proportional to weight and persists throughout the job. Columns T through W are deterministic test readings in that row. Tests share that row's calibration. A test reveals only its own reading. You may buy up to two distinct tests, sequentially. You may stop and repair at any time. Each purchased test incurs its listed cost. A repair ends the job. Minimize expected total loss (test costs plus repair loss). Python arithmetic/enumeration is allowed.

mode calibration weight T U V W
{weights}

repair loss by TRUE mode in order A B C D (row = chosen repair):
{matrix}
test costs: {json.dumps({test: float(value) for test, value in costs.items()})}

Return one JSON object with keys first, first_losses, next. first is the optimal test ID or a repair ID A/B/C/D for immediate repair. first_losses is a map with keys STOP,T,U,V,W: STOP is the best immediate repair loss; each test entry is the total expected loss if bought FIRST and followed by the best outcome-dependent policy, including the option of buying one more test. next maps "0" and "1" to the optimal next repair or test after the first choice; use IMPOSSIBLE on a zero-probability branch, or an empty object when repairing immediately. Any tied optimal action is valid. Report numbers within 0.01 absolute error."""


def checks(variant, stage1, stage2, checks):
    costs, losses, rows, initial, _, obs, _, revised = data(variant)
    official1, official2 = answer(variant)
    stage1_first = checks.action(stage1.get("first"))
    checks.add("1.first", stage1_first in best_choices(initial), 2)
    checks.values("1.first_losses", stage1.get("first_losses"), official1["first_losses"], 2)
    next_actions = stage1.get("next")
    correct = stage1_first in MODES and next_actions == {}
    if stage1_first in TESTS and isinstance(next_actions, dict):
        remaining = [test for test in TESTS if test != stage1_first]
        correct = True
        for bit in (0, 1):
            group = branch(rows, stage1_first, bit)
            options = best_choices(action_values(group, remaining, costs, losses, 1)) if group else ["IMPOSSIBLE"]
            correct &= checks.action(next_actions.get(str(bit))) in options
        correct &= set(next_actions) == {"0", "1"}
    checks.add("1.contingency", correct, 1)
    checks.values("2.posterior", stage2.get("posterior"), official2["posterior"], 1)
    checks.values("2.remaining_losses", stage2.get("remaining_losses"), official2["remaining_losses"], 2)
    action = checks.action(stage2.get("action"))
    realized_first = best_choices(initial)[0]
    group = branch(rows, realized_first, obs)
    values = action_values(group, [test for test in TESTS if test != realized_first], revised, losses, 1)
    checks.add("2.action", action in best_choices(values), 1)
    if action == realized_first:
        checks.fail("2.already_used_test")
    if action is not None and action not in set(MODES) | set(TESTS):
        checks.fail("2.unknown_action")
    after = stage2.get("repair_after")
    correct = action in MODES and after == {}
    if action in set(TESTS) - {realized_first} and isinstance(after, dict):
        correct = set(after) == {"0", "1"}
        for bit in (0, 1):
            subset = branch(group, action, bit)
            options = best_choices(repair_totals(subset, losses)) if subset else ["IMPOSSIBLE"]
            correct &= checks.action(after.get(str(bit))) in options
    checks.add("2.repair_after", correct, 1)
