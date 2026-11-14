"""Compare two explicit interpretations of the completion contract on synthetic notices."""

from dataclasses import dataclass, replace
import json

from closure import CASES, outcome, snapshots


@dataclass(frozen=True)
class Goal:
    goal: str
    required: bool
    outcome: str


@dataclass(frozen=True)
class State:
    # The signed order ledger and goal import are independent input streams.
    original: frozenset
    register: tuple
    # IDs of goals with accepted, sufficient, current evidence and a usable artifact.
    qualified: frozenset
    amendments: tuple = ()  # each authorized replacement has (retired IDs, added IDs)
    run: str = "order"
    authority: bool = True
    stopped_runs: frozenset = frozenset()
    obligations_resolved: bool = True
    common_checks_pass: bool = True  # remaining predicate conditions, including quiescence


def legacy(state):
    required = {goal.goal for goal in state.register if goal.required}
    return bool(state.register) and required <= state.qualified and state.common_checks_pass


def candidate_one(state, final_guard=False):
    """Transliterate candidate 1's numbered guards, including its empty-amendment exception."""
    if not state.authority or state.run in state.stopped_runs or not state.common_checks_pass:
        return False
    required = set(state.original)
    removed_remaining = False
    for retired, added in state.amendments:
        before = bool(required)
        required.difference_update(retired)
        required.update(added)
        if before and not required:
            removed_remaining = True
    if final_guard and (not required or not state.obligations_resolved):
        return False
    if not required and removed_remaining:
        return False
    registered = [goal for goal in state.register if goal.required]
    if any(goal.goal not in state.qualified for goal in registered):
        return False
    covered = {goal.outcome for goal in registered}
    return required <= covered


def final_candidate(state):
    """Require an established, nonempty set of authorized delivery outcomes."""
    return candidate_one(state, final_guard=True)


def project(case, index):
    snap = snapshots(case)[index]
    original = frozenset(key for key, description in case["request"])
    goals = tuple(Goal(goal, required, source) for source, goal, required in snap["bindings"])
    signed = ()
    if index == 2:
        signed = ((frozenset([case["request"][2][0]]), frozenset([case["replacement"][0]])),)
    stop = frozenset([snap["id"]]) if snap["cancel"] else frozenset()
    if index == 2:
        stop = frozenset(["another-order"])
    return State(original, goals, frozenset(g.goal for g in goals), amendments=signed,
                 run=snap["id"], stopped_runs=stop)


def at_notification(predicate, accepted, live):
    # Synthetic test of final-boundary readback. An already withheld transaction cannot send.
    return predicate(accepted) and predicate(live)


def counted(rows):
    result = {}
    for name in ("legacy", "candidate_one", "final_candidate"):
        result[name] = {
            "false_release": sum(r[name] and not r["expected_release"] for r in rows),
            "false_withholding": sum(not r[name] and r["expected_release"] for r in rows),
        }
    return result


def compare(label, expected, before, live=None):
    state = live if live is not None else before
    return {"id": label, "expected_release": expected,
            "legacy": at_notification(legacy, before, state),
            "candidate_one": at_notification(candidate_one, before, state),
            "final_candidate": at_notification(final_candidate, before, state)}


def main():
    report = {"scope": "Three source-derived reference adapters for synthetic states. No provider or scheduler runs.",
              "cases": {}}
    for name, case in CASES.items():
        rows = []
        for i, snap in enumerate(snapshots(case)):
            expected = outcome(snap)["disposition"] == "release"
            row = compare(snap["id"], expected, project(case, i))
            if row["legacy"] != outcome(snap)["legacy_gate"]:
                raise ValueError("Legacy import diverged from the frozen adapter in " + name)
            rows.append(row)
        report["cases"][name] = {"snapshots": rows, "counts": counted(rows)}

    original = frozenset(["delivery"])
    base = State(original, (Goal("g", True, "delivery"),), frozenset(["g"]))
    none = frozenset()
    optional = replace(base, register=(Goal("g", False, "delivery"),))
    controls = [
        compare("clean_success", True, base),
        compare("withhold_stale_evidence", False, replace(base, qualified=none)),
        compare("withhold_unresolved_common_check", False, replace(base, common_checks_pass=False)),
        compare("withhold_demoted_required_goal", False, optional),
        compare("withhold_unrepresented_second_deliverable", False, replace(base, original=original | {"second"})),
        compare("release_different_job_stopped_at_notice", True, base, replace(base, stopped_runs={"another-order"})),
        compare("withhold_this_job_stopped_after_acceptance_before_notice", False, base, replace(base, stopped_runs={"order"})),
        compare("withhold_expired_notice_authority", False, base, replace(base, authority=False)),
        compare("withhold_amended_scope_after_acceptance", False, base,
                replace(base, amendments=((none, frozenset(["second"])),))),
        compare("withhold_zero_obligations_after_signed_removal", False,
                replace(optional, amendments=((original, none),))),
        compare("withhold_initially_empty_order_and_register", False, State(none, (), none)),
        compare("withhold_initially_empty_order_with_optional_registry", False, replace(optional, original=none)),
        compare("withhold_unresolved_obligation_with_guessed_receipt", False, replace(base, obligations_resolved=False)),
    ]
    report["independent_controls"] = {"snapshots": controls, "counts": counted(controls)}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
