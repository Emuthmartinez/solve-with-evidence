"""Finite robust roster with discrete repair actions and a revised incident."""

from collections import deque
from functools import lru_cache
from itertools import combinations, permutations
import random

JOBS = "ABCDE"
ROSTERS = tuple("".join(seq) for seq in permutations(JOBS))
SCENARIOS = ("rain", "road", "lift")
SEEDS = {"d1": 27, "d2": 124, "h1": 206}


def distance(original, final):
    # A permutation cycle of length k takes k-1 unrestricted pair exchanges.
    where = {job: position for position, job in enumerate(original)}
    seen = set()
    cycles = 0
    for position in range(len(original)):
        if position not in seen:
            cycles += 1
            while position not in seen:
                seen.add(position)
                position = where[final[position]]
    return len(original) - cycles


DIST = {a: {b: distance(a, b) for b in ROSTERS} for a in ROSTERS}


def generate(seed):
    rng = random.Random(seed)
    data = {"slots": {job: [rng.randint(0, 11) for _ in JOBS] for job in JOBS},
            "transfer": {(a, b): rng.randint(0, 5) for a in JOBS for b in JOBS if a != b},
            "fee": rng.randint(1, 4), "extra": rng.randint(4, 11)}
    scenarios = {}
    for name in SCENARIOS:
        jobs = rng.sample(list(JOBS), 3)
        scenarios[name] = {"blocked": [(jobs[0], rng.randrange(5)), (jobs[1], rng.randrange(5))],
                           "late": (jobs[2], rng.randint(1, 3), rng.randint(5, 10))}
    data["scenarios"] = scenarios
    return data


def cost(data, seq, scenario=None):
    if seq.index("A") > seq.index("D"):
        return None
    total = sum(data["slots"][job][slot] for slot, job in enumerate(seq))
    total += sum(data["transfer"][a, b] for a, b in zip(seq, seq[1:]))
    if scenario:
        if any(seq[slot] == job for job, slot in scenario["blocked"]):
            return None
        job, threshold, rate = scenario["late"]
        total += rate * max(0, seq.index(job) + 1 - threshold)
    return total


def candidates(seq, table, data, limit):
    return {candidate: value + data["fee"] * DIST[seq][candidate] +
            (data["extra"] if DIST[seq][candidate] == 2 else 0)
            for candidate, value in table.items() if value is not None and DIST[seq][candidate] <= limit}


@lru_cache(maxsize=16)
def evaluate(seed):
    data = generate(seed)
    nominal = {seq: cost(data, seq) for seq in ROSTERS}
    tables = {name: {seq: cost(data, seq, sc) for seq in ROSTERS}
              for name, sc in data["scenarios"].items()}
    scores, options = {}, {}
    for seq, base in nominal.items():
        if base is None:
            continue
        plans = {name: candidates(seq, table, data, 1) for name, table in tables.items()}
        if all(plans.values()):
            scores[seq] = base + max(min(group.values()) for group in plans.values())
            options[seq] = plans
    return data, nominal, tables, scores, options


def minima(mapping):
    minimum = min(mapping.values())
    return sorted(key for key, value in mapping.items() if value == minimum)


def incident(seed):
    data, _, _, scores, _ = evaluate(seed)
    base = minima(scores)[0]
    # Select an actual closure leaving a consequential trade-off at two swaps.
    groups = {}
    for name, old in data["scenarios"].items():
        for slot, job in enumerate(base):
            if (job, slot) in old["blocked"]:
                continue
            actual = {**old, "blocked": old["blocked"] + [(job, slot)]}
            table = {seq: cost(data, seq, actual) for seq in ROSTERS}
            values = candidates(base, table, data, 2)
            by = [{seq: value for seq, value in values.items() if DIST[base][seq] == n} for n in (0, 1, 2)]
            if not by[1] or not by[2]:
                continue
            gap = min(by[2].values()) - min(by[1].values())
            if gap == 0 or len(minima(values)) != 1:
                continue
            # Pick a case where global reoptimization would lead to a different dispatch,
            # or where the surcharge changes which class wins.
            unconstrained = min(x for x in table.values() if x is not None)
            if unconstrained == table[minima(values)[0]]:
                continue
            groups.setdefault(gap < 0, (base, name, (job, slot), actual, values, by))
    return groups


def case(variant):
    seed = SEEDS[variant]
    prefer_two = variant != "d2"
    return incident(seed)[prefer_two]


def answer(variant):
    seed = SEEDS[variant]
    _, _, _, scores, options = evaluate(seed)
    base, _, _, _, values, by = case(variant)
    ordered = sorted(set(scores.values()))
    s1 = {"roster": base, "score": ordered[0], "feasible_count": len(scores), "next_score": ordered[1],
          "repairs": {n: minima(g)[0] for n, g in options[base].items()},
          "repair_costs": {n: min(g.values()) for n, g in options[base].items()}}
    s2 = {"roster": minima(values)[0], "score": min(values.values()),
          "best_by_swaps": {str(i): min(g.values()) if g else None for i, g in enumerate(by)},
          "feasible_by_swaps": {str(i): len(g) for i, g in enumerate(by)}}
    return [s1, s2]


def prompt(variant, stage):
    seed = SEEDS[variant]
    data, *_ = evaluate(seed)
    base, name, (job, slot), _, _, _ = case(variant)
    if stage == 2:
        return f"""Dispatch confirms that the published roster is {base}, regardless of your earlier recommendation. Incident {name} is active with BOTH of its exclusions and its stated late penalty. An additional closure now forbids {job} in slot {slot+1}. No other named incident applies. Operations now permits up to two pair exchanges from that published roster. Pay {data["fee"]} per exchange plus a one-time exceptional staffing surcharge of {data["extra"]} if two exchanges are used. Charge the minimum number of exchanges needed for each distinct final roster. Minimize actual incident cost (nominal cost of the FINAL roster + active late penalty + exchange fees + any two-exchange surcharge). The earlier stage-one minimax score has no role in this accounting.

Return one JSON object with roster (optimal final five-letter sequence), score (minimal actual cost), best_by_swaps (minimum actual cost among feasible final rosters at EXACTLY each minimum exchange distance, keys "0","1","2", null for an empty class), and feasible_by_swaps (matching counts of distinct feasible final rosters). Any optimum is acceptable. Python enumeration is allowed."""
    slots = "\n".join(f"{j}  " + " ".join(str(n) for n in data["slots"][j]) for j in JOBS)
    moves = "\n".join(f"{j}  " + " ".join(str(data["transfer"].get((j, k), 0)) for k in JOBS) for j in JOBS)
    rules = []
    for label, rule in data["scenarios"].items():
        exclusions = " and ".join(f"{j} in slot {s+1}" for j, s in rule["blocked"])
        j, threshold, rate = rule["late"]
        rules.append(f"{label}: forbid {exclusions}. Add {rate} for every slot {j} runs after slot {threshold}.")
    return f"""Dispatch must publish a five-job roster, one job per slot (1–5), containing each of A,B,C,D,E exactly once. A must precede D in every published and final roster. The nominal cost of a roster is its five job/slot costs plus the four directed transfer costs between consecutive jobs. There is no transfer cost before the first or after the last job.

job/slot cost (columns 1 2 3 4 5):
{slots}
directed transfer cost (row = FROM, columns A B C D E = TO):
{moves}

Exactly one of these incidents may be announced after publication:
{chr(10).join(rules)}

For each incident you may retain the published roster or exchange any two positions once. Incident cost is the nominal cost of the FINAL roster plus that incident's late penalty plus {data["fee"]} if exchanged. Exclusions apply to the final roster for that incident. A candidate publication is robust-feasible if each incident has at least one legal final roster within this exchange limit. Score it by its nominal PUBLISHED cost PLUS the largest of its three minimized incident costs. Choose a publication that minimizes this score. Python enumeration is allowed.

Return one JSON object with roster (five-letter sequence), score (optimal score), repairs (map rain/road/lift to a minimum-cost final roster in each incident for your chosen publication), repair_costs (their respective incident costs), feasible_count (count of distinct robust-feasible publications), and next_score (smallest distinct feasible publication score strictly greater than the optimum). Any tied optimum is valid."""


def checks(variant, stage1, stage2, check):
    data, _, _, scores, options = evaluate(SEEDS[variant])
    official1, official2 = answer(variant)
    published = check.action(stage1.get("roster"))
    check.add("1.roster", published in minima(scores), 1)
    check.add("1.optimum", check.number(stage1.get("score"), official1["score"]), 1)
    check.add("1.proof", all(check.number(stage1.get(k), official1[k]) for k in ("feasible_count", "next_score")), 1)
    repairs, costs = stage1.get("repairs"), stage1.get("repair_costs")
    plans = options.get(published, {})
    if published in ROSTERS and published not in scores:
        check.fail("1.infeasible_publication")
    selections = {name: check.action(repairs.get(name)) for name in SCENARIOS} if isinstance(repairs, dict) else {}
    valid = bool(plans and selections)
    cost_valid = bool(plans and isinstance(costs, dict))
    for name in SCENARIOS:
        if plans:
            if name in selections and selections[name] is not None and selections[name] not in plans[name]:
                check.fail("1.illegal_incident_repair")
            valid &= selections.get(name) in minima(plans[name])
            cost_valid &= isinstance(costs, dict) and check.number(costs.get(name), min(plans[name].values()))
    check.add("1.repairs", valid, 1)
    check.add("1.repair_costs", cost_valid, 1)
    _, _, _, _, values, _ = case(variant)
    final = check.action(stage2.get("roster"))
    if final is not None and final not in values:
        check.fail("2.illegal_dispatch")
    check.add("2.roster", final in minima(values), 2)
    check.add("2.optimum", check.number(stage2.get("score"), official2["score"]), 1)
    check.values("2.best_by_swaps", stage2.get("best_by_swaps"), official2["best_by_swaps"], 1)
    check.values("2.feasible_by_swaps", stage2.get("feasible_by_swaps"), official2["feasible_by_swaps"], 1)


def exhaustive_check(variant):
    """Cross-check cycle distance and all costs with direct exchanges and row scans."""
    seed = SEEDS[variant]
    data, _, _, scores, _ = evaluate(seed)
    root, name, closure, _, _, _ = case(variant)

    def reachable(seq, limit):
        seen = {seq: 0}
        q = deque([seq])
        while q:
            seq = q.popleft()
            depth = seen[seq]
            if depth >= limit:
                continue
            for i, j in combinations(range(5), 2):
                candidate = list(seq)
                candidate[i], candidate[j] = candidate[j], candidate[i]
                candidate = "".join(candidate)
                if candidate not in seen:
                    seen[candidate] = depth + 1
                    q.append(candidate)
        return seen

    def value(seq, sc=None, extra_block=None):
        if seq.index("D") < seq.index("A"):
            return None
        total = sum(data["slots"][j][seq.index(j)] for j in JOBS)
        total += sum(v for (a, b), v in data["transfer"].items() if a+b in seq)
        if sc:
            rules = data["scenarios"][sc]
            exclusions = list(rules["blocked"])
            if extra_block:
                exclusions.append(extra_block)
            if any(seq.index(j) == slot for j, slot in exclusions):
                return None
            j, threshold, rate = rules["late"]
            total += sum(rate for pos in range(threshold, 5) if pos <= seq.index(j))
        return total

    alternative = {}
    for seq in ROSTERS:
        nominal = value(seq)
        if nominal is None:
            continue
        neighbor = reachable(seq, 1)
        incidents = []
        for sc in SCENARIOS:
            costs = [val + depth * data["fee"] for candidate, depth in neighbor.items()
                     if (val := value(candidate, sc)) is not None]
            if costs:
                incidents.append(min(costs))
        if len(incidents) == 3:
            alternative[seq] = nominal + max(incidents)
    assert scores == alternative
    paths = reachable(root, 2)
    vals = [{}, {}, {}]
    for seq, depth in paths.items():
        val = value(seq, name, closure)
        if val is not None:
            vals[depth][seq] = val + data["fee"] * depth + data["extra"] * (depth == 2)
    assert vals == case(variant)[5]
