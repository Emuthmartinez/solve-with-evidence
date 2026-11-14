"""Sharp identification bounds for people linked across two account rosters."""

from collections import Counter
from functools import lru_cache
from itertools import permutations, product
import json
from pathlib import Path

CASES = json.loads(Path(__file__).with_name("cases.json").read_text())
IDS = tuple(CASES)


def prompt(case_id, stage):
    case = CASES[case_id]
    if stage not in (1, 2):
        raise ValueError("Stage must be 1 or 2.")
    fields = """
Return one JSON object with these five keys:
- feasible_linkages: exact integer count of complete assignments consistent with all evidence. Treat people and accounts as labeled.
- bounds: [smallest, largest] achievable number of people who attended on at least three distinct days.
- low_witness and high_witness: complete assignments attaining the respective endpoints. Each is an object with keys A and B; each value is a string of exactly five person-ID letters in account order 1 through 5. If endpoints coincide the same witness is allowed twice.
- decision: "confirmed" if the threshold is reached in every feasible assignment, "excluded" if it is reached in none, or "undetermined" otherwise.
You may use Python, exhaustive enumeration, or another exact method."""
    if stage == 2:
        recovered = case["recovered"]
        return f"""Two signed intake slips have now been recovered. They establish that A{recovered['fixed_row']+1} belongs to {recovered['person']}, and that A{recovered['left']+1} and B{recovered['right']+1} belong to the same person. Both facts are binding. All previous information and the board's threshold remain in force. Recompute the result for these tighter conditions, even if your earlier answer differs.{fields}"""
    rows = []
    for label, accounts in zip("AB", case["rows"]):
        for i, row in enumerate(accounts, 1):
            rows.append(f"{label}{i}    {','.join(row['possible'])}    {','.join(map(str, row['days']))}")
    return f"""A community center changed its check-in system mid-program. The A and B exports below cover overlapping dates and use separate account namespaces. An authoritative roster contains seven people with IDs {', '.join(case['people'])}. Each listed account maps to exactly one of the indicated people. Within an export, each person has at most one account. A person can appear in both exports or neither. An independent audit established that exactly {case['overlap']} people have accounts in both exports, of whom exactly {case['west_overlap']} are from the West roster ({', '.join(case['west'])}). These are exact joint constraints.

Every account row lists all calendar-day numbers on which that account checked in. The same number in either export is the same calendar date. A person gets at most one attendance credit per date, including when both of that person's accounts checked in. People absent from both exports have zero attendance. There are no other check-ins, matches, priors, or tie-breaking rules. The board wants to know whether at least {case['threshold']} people each attended on three or more distinct days.

account    possible person IDs    attendance days
{chr(10).join(rows)}
{fields}"""


def inspect_witness(case, stage, witness):
    """Check one proposed mapping directly against the problem, independent of its generator."""
    if not isinstance(witness, dict) or set(witness) != {"A", "B"}:
        return None
    attendance = {}
    for label, rows in zip("AB", case["rows"]):
        ids = witness[label]
        if not isinstance(ids, str) or len(ids) != len(rows) or len(set(ids)) != len(ids):
            return None
        for person, row in zip(ids, rows):
            if person not in row["possible"]:
                return None
            attendance.setdefault(person, set()).update(row["days"])
    a, b = witness["A"], witness["B"]
    overlap = set(a) & set(b)
    if len(overlap) != case["overlap"] or len(overlap & set(case["west"])) != case["west_overlap"]:
        return None
    if stage == 2:
        fixed = case["recovered"]
        if a[fixed["fixed_row"]] != fixed["person"] or a[fixed["left"]] != b[fixed["right"]]:
            return None
    return sum(len(days) >= 3 for days in attendance.values())


@lru_cache(maxsize=None)
def oracle(case_id, stage):
    """Enumerate all within-roster injections and retain each feasible complete linkage."""
    case = CASES[case_id]
    sides = []
    for accounts in case["rows"]:
        allowed = [set(row["possible"]) for row in accounts]
        possibilities = ["".join(assignment) for assignment in permutations(case["people"], len(accounts))
                         if all(person in choices for person, choices in zip(assignment, allowed))]
        sides.append(possibilities)
    counts = Counter()
    examples = {}
    for a, b in product(*sides):
        witness = {"A": a, "B": b}
        score = inspect_witness(case, stage, witness)
        if score is not None:
            counts[score] += 1
            examples.setdefault(score, witness)
    return counts, examples


def decision(bounds, threshold):
    lower, upper = bounds
    if lower >= threshold:
        return "confirmed"
    if upper < threshold:
        return "excluded"
    return "undetermined"


def exact_integer(value):
    # JSON numbers of the form 4.0 represent exactly the same integer as 4.
    return type(value) is int or type(value) is float and value.is_integer()


def grade(case_id, replies):
    if not isinstance(replies, (list, tuple)) or len(replies) != 2:
        raise ValueError("Exactly two chronological replies are required.")
    checks = {}
    failures = []

    def add(name, result):
        checks[name] = {"passed": bool(result), "weight": 1}

    case = CASES[case_id]
    for stage, reply in enumerate(replies, 1):
        key = f"{stage}."
        if not isinstance(reply, dict):
            failures.append(key + "invalid_json_object")
            reply = {}
        counts, _ = oracle(case_id, stage)
        bounds = [min(counts), max(counts)]
        n = reply.get("feasible_linkages")
        add(key + "feasible_linkages", exact_integer(n) and n == sum(counts.values()))
        claimed = reply.get("bounds")
        valid_range = isinstance(claimed, list) and len(claimed) == 2 and all(exact_integer(i) for i in claimed)
        add(key + "bounds", valid_range and claimed == bounds)
        for name, expected in zip(("low_witness", "high_witness"), bounds):
            actual = inspect_witness(case, stage, reply.get(name))
            add(key + name, actual == expected)
            if name in reply and actual is None:
                failures.append(key + "infeasible_" + name)
        required = decision(bounds, case["threshold"])
        actual_decision = reply.get("decision")
        add(key + "decision", actual_decision == required)
        if actual_decision in ("confirmed", "excluded") and actual_decision != required:
            failures.append(key + "unsupported_threshold_claim")
    points = sum(item["passed"] for item in checks.values())
    return {"case": case_id, "points": points, "max_points": 10, "pass": points == 10 and not failures,
            "checks": checks, "critical_failures": failures}


def independent_counts(case, stage):
    """Check the oracle with a row-oriented DFS, roster bitmasks and numeric attendance bitsets."""
    ids = {person: i for i, person in enumerate(case["people"])}
    west = sum(1 << ids[p] for p in case["west"])
    rows = [(tuple(ids[p] for p in row["possible"]), sum(1 << d for d in row["days"]))
            for side in case["rows"] for row in side]
    selected = []
    totals = Counter()
    half = len(rows) // 2
    fixed = case["recovered"]

    def visit(i, masks, days):
        if i == len(rows):
            both = masks[0] & masks[1]
            if both.bit_count() != case["overlap"] or (both & west).bit_count() != case["west_overlap"]:
                return
            attended = sum(n.bit_count() >= 3 for n in days)
            totals[attended] += 1
            return
        side = int(i >= half)
        options, hits = rows[i]
        for p in options:
            if masks[side] & (1 << p):
                continue
            if stage == 2:
                if i == fixed["fixed_row"] and p != ids[fixed["person"]]:
                    continue
                if i == half + fixed["right"] and p != selected[fixed["left"]]:
                    continue
            selected.append(p)
            old = days[p]
            days[p] |= hits
            masks[side] |= 1 << p
            visit(i + 1, masks, days)
            days[p] = old
            masks[side] ^= 1 << p
            selected.pop()

    visit(0, [0, 0], [0] * len(ids))
    return totals


def selftest():
    from copy import deepcopy

    def require(test, reason):
        if not test:
            raise ValueError(reason)

    for case_id, case in CASES.items():
        answers = []
        for stage in (1, 2):
            counts, examples = oracle(case_id, stage)
            require(counts == independent_counts(case, stage), "Disagreement between independent enumerations.")
            bounds = [min(counts), max(counts)]
            answers.append({"feasible_linkages": sum(counts.values()), "bounds": bounds,
                            "low_witness": examples[bounds[0]], "high_witness": examples[bounds[1]],
                            "decision": decision(bounds, case["threshold"])})
        first, second = answers
        require(first["decision"] == "undetermined" and second["decision"] in ("confirmed", "excluded"),
                "Stage transition must resolve the threshold.")
        require(first["bounds"][1] - first["bounds"][0] >= 3, "Insufficient initial ambiguity.")
        require(first["feasible_linkages"] > second["feasible_linkages"] >= 5, "Missing genuine joint constraint.")
        require(grade(case_id, answers)["pass"], "Gold rejected.")
        require(grade(case_id, [None, {}])["points"] == 0, "Malformed reply accepted.")
        require(grade(case_id, [first, {}])["points"] == 5, "Incorrect stage separation.")
        require(not grade(case_id, [first, first])["pass"], "Stale stage accepted.")
        def mutate(stage, field, value):
            attempt = deepcopy(answers)
            attempt[stage-1][field] = value
            return grade(case_id, attempt)
        require(mutate(1, "decision", "confirmed")["critical_failures"], "Unsupported decision accepted.")
        require(mutate(1, "low_witness", {"A":"KKKKK", "B":"KKKKK"})["critical_failures"], "Invalid witness accepted.")
        require(mutate(1, "low_witness", first["high_witness"])["points"] == 9, "Wrong endpoint accepted.")
        require(mutate(2, "feasible_linkages", True)["points"] == 9, "Boolean count accepted.")
        require(mutate(2, "bounds", [True, 4])["points"] == 9, "Boolean endpoint accepted.")
        require(mutate(2, "bounds", [second["bounds"][1] + 1, second["bounds"][1] + 1])["points"] == 9,
                "Fabricated bound accepted.")
        require(mutate(1, "feasible_linkages", first["feasible_linkages"]-1)["points"] == 9,
                "Incorrect number of feasible linkages accepted.")
        missing_new_evidence = next((w for w in (first["low_witness"], first["high_witness"])
                                     if inspect_witness(case, 2, w) is None), None)
        require(missing_new_evidence and mutate(2, "low_witness", missing_new_evidence)["critical_failures"],
                "Witness violating recovered evidence accepted.")
        require(prompt(case_id, 1) != prompt(case_id, 2), "Prompt stages collapsed.")
    return {"pass": True, "cases": list(IDS), "stages": 6, "independent_histograms": 6,
            "controls": ["gold/malformed/single-stage", "reused initial decision and witnesses", "false certainty",
                         "duplicate identity", "wrong endpoint witness", "boolean fields",
                         "inflated bound", "incorrect feasible-set size", "violated recovered evidence"]}


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
