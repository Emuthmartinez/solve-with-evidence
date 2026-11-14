#!/usr/bin/env python3
"""Verify a specified matrix of two-turn trials and summarize regraded results."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib
import itertools
import json
from pathlib import Path
import re
import sys


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf8"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stable(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def answer(text):
    # The earlier suites allow a Markdown fence around a JSON object.
    text = text.strip()
    if text.startswith("```") and text.endswith("```") and "\n" in text:
        text = text.split("\n", 1)[1][:-3].strip()
    try:
        obj = json.loads(text)
    except ValueError:
        return {}
    return obj if isinstance(obj, dict) else {}


class Suites:
    def __init__(self, root):
        sys.path[:0] = [str(root / folder) for folder in ("benchdesign", "linkage", "reconciliation", "closure", "contract")]
        self.prompts = {}

    def get(self, case):
        family = case.split("-", 1)[0]
        transfers = {"closure-h2": "closure_transfer", "ledger-h2": "ledger_transfer",
                     "artifact-h3": "artifact_transfer", "contract-h4": "contract_transfer"}
        module_name = transfers.get(case)
        if module_name is None:
            module_name = {"probe": "bench", "roster": "bench", "linkage": "linkage",
                           "ledger": "ledger", "closure": "closure"}[family]
        module = importlib.import_module(module_name)
        if case not in self.prompts:
            self.prompts[case] = [module.prompt(case, stage) for stage in [1, 2]]
        decode = module.decode if case == "contract-h4" else answer

        def score(final_texts):
            return module.grade(case, [decode(text) for text in final_texts])

        return self.prompts[case], score


def evidence(folder):
    manifest = read_json(folder / "manifest.json")
    require(set(manifest) == {"summary.json", "trace.jsonl"}, "unexpected evidence manifest")
    for file, expected in manifest.items():
        require(digest((folder / file).read_bytes()) == expected, f"{file} digest mismatch")
    events = [json.loads(line) for line in (folder / "trace.jsonl").read_text().splitlines()]
    summary = read_json(folder / "summary.json")
    grade = read_json(folder / "grade.json")
    require(events and [e["seq"] for e in events] == list(range(1, len(events) + 1)),
            "trace event sequence is incomplete")
    require(all(a["elapsed_s"] <= b["elapsed_s"] for a, b in zip(events, events[1:])), "event clock reversed")
    require(events[-1]["kind"] == "runner_end" and events[-1]["data"]["status"] == summary["status"],
            "runner end missing or disagrees with summary")
    return summary, grade, events


def phase(events, row, prompt, cap, reference_hashes, seen_calls):
    stage = row["stage"]
    require(events and events[0]["kind"] == "user_input" and events[0]["data"]["text"] == prompt,
            f"stage {stage} input does not match the case")
    require(sum(e["kind"] == "user_input" for e in events) == 1, "duplicate user input")
    active = completed = usage = final = None
    provider_user_seen = False
    user_seen_before_output = True
    calls, results, items = {}, {}, {}
    messages = []
    for e in events[1:]:
        kind, data = e["kind"], e["data"]
        if kind in {"runner_error", "runner_end", "error", "model/verification", "model/rerouted"}:
            continue
        require(completed is None, "conversation event occurs after turn completion")
        if kind == "turn/started":
            require(active is None, "duplicate turn start")
            active = data["id"]
            continue
        require(active is not None, "stage event before turn start")
        if kind == "turn/completed":
            require(data["id"] == active, "turn identifier changed")
            completed = data["status"]
        elif kind == "usage":
            usage = data
        elif kind == "tool_call":
            user_seen_before_output &= provider_user_seen
            cid = data["callId"]
            require(cid and cid not in seen_calls and data["tool"] in ("python", "read_reference"),
                    "unrecognized or repeated tool call")
            seen_calls.add(cid)
            calls[cid] = data
        elif kind == "tool_result":
            cid = data["callId"]
            require(cid in calls and cid not in results and data["tool"] == calls[cid]["tool"],
                    "tool result without a matching call")
            result = data["result"]
            require(isinstance(result["success"], bool) and len(result["contentItems"]) == 1,
                    "invalid tool result")
            content = result["contentItems"][0]
            require(content["type"] == "inputText" and isinstance(content["text"], str), "invalid tool payload")
            if list(calls).index(cid) >= cap:
                require(not result["success"] and content["text"] == "Trial tool call cap reached.",
                        "tool cap not enforced")
            if data["tool"] == "read_reference" and result["success"]:
                path = calls[cid]["arguments"]["path"]
                require(digest(content["text"].encode()) == reference_hashes.get(path),
                        "served reference differs from manifest")
            results[cid] = result
        elif kind in ("item/started", "item/completed"):
            item = data["item"]
            iid, typ = item["id"], item["type"]
            require(typ in ("userMessage", "dynamicToolCall", "agentMessage"),
                    f"item type outside the fixed trial protocol: {typ}")
            if kind == "item/started":
                require(iid not in items, "duplicate item start")
                items[iid] = [typ, False]
                continue
            require(items.get(iid) == [typ, False], "completed item lacks matching start")
            items[iid][1] = True
            if typ == "dynamicToolCall":
                require(iid in results and calls[iid]["arguments"] == item["arguments"] and
                        calls[iid]["tool"] == item["tool"] and results[iid]["success"] == item["success"] and
                        results[iid]["contentItems"] == item["contentItems"], "tool item contradicts captured exchange")
            elif typ == "userMessage":
                provider_user_seen = True
                messages.append([part.get("text") for part in item["content"] if part["type"] == "text"])
            elif typ == "agentMessage" and item.get("phase") in (None, "final_answer"):
                user_seen_before_output &= provider_user_seen
                final = item["text"]
        else:
            raise Invalid(f"unknown stage event {kind}")
    require(len(calls) == row["tool_calls"] and (final or "") == row["text"] and usage == row["usage"],
            "stage tool count, final answer or last usage differs from summary")
    if completed == "completed":
        require(messages == [[prompt]] and user_seen_before_output and row["status"] == completed and all(v[1] for v in items.values()),
                "completed stage lacks captured user, final or completed item")
        require(calls.keys() == results.keys() and set(calls) == {i for i, v in items.items() if v[0] == "dynamicToolCall"},
                "incomplete tool exchanges in completed stage")
    else:
        require(row["status"] != "completed", "summary declares stage complete without event")
    return {"final_text": final if completed == "completed" and final else "", "usage": usage,
            "calls": len(calls), "tools_failed": sum(not r["success"] for r in results.values()),
            "started": active is not None, "complete": completed == "completed" and bool(final)}


class Audit:
    def __init__(self, root, skills):
        self.suites = Suites(root)
        self.runner = {name: digest((root / "runner" / name).read_bytes()) for name in ("run_trial.py", "calculate.py")}
        self.skills = skills
        self.cohort_settings = {}
        self.cohort_skills = {}
        self.seen_threads = set()

    def trial(self, folder, name, case, arm, rep):
        s, g, events = evidence(folder)
        require((g["arm"], g["case"], g["repeat"], g["status"]) == (arm, case, rep, s["status"])
                and s["case_id"] == case, "grade identity/status mismatch")
        require(s["runner_sha256"] == self.runner, "recorded runner differs from published runner")
        prompts, grader = self.suites.get(case)
        expected_input = digest(json.dumps(prompts, ensure_ascii=False).encode())
        require(s["case_messages_sha256"] == expected_input, "case inputs differ from generated instance")
        hashes = s["skill_files_sha256"]
        require("SKILL.md" in hashes and all(re.fullmatch(r"[a-f0-9]{64}", h) for h in hashes.values()),
                "invalid skill hash manifest")
        if arm in self.skills:
            require(hashes == self.skills[arm], "skill differs from supplied snapshot")
        require(self.cohort_skills.setdefault((name, arm), hashes) == hashes, "skill differs within arm")
        status = s["status"]
        require(status in ("completed", "failed") and (g["runner_exit"] == 0) == (status == "completed"),
                "outcome differs from runner exit status")
        req = [e["data"] for e in events if e["kind"] == "thread/request"]
        settings = [e["data"] for e in events if e["kind"] == "thread/settings"]
        require(len(req) <= 1 and len(settings) <= 1 and (not settings or req), "duplicate or missing thread setup")
        if req:
            require(events[0]["kind"] == "thread/request", "thread setup out of order")
            req = dict(req[0])
            require(req["ephemeral"] and req["environments"] == req["selectedCapabilityRoots"] == [] and
                    req["cwd"] == "/" and req["allowProviderModelFallback"] is False and
                    req["sandbox"] == "read-only" and req["approvalPolicy"] == "never", "unexpected trial isolation")
            instructions = req.pop("developerInstructions")
            entry, marker, paths = instructions.rpartition("\n\nAvailable skill reference paths:\n")
            require(marker and digest(entry.encode()) == hashes["SKILL.md"] and paths.splitlines() ==
                    sorted(k for k in hashes if k != "SKILL.md"), "submitted skill differs from manifest")
        if settings:
            require(settings[0] == s["settings"] and isinstance(s["model"], str) and s["model"] and
                    s["model"] == settings[0]["model"] and
                    (s["requested_model"] is None or s["requested_model"] == s["model"]) and
                    s["provider"] == settings[0]["modelProvider"] and s["auth"] == "chatgpt", "resolved settings mismatch")
            require(settings[0]["instructionSources"] == [] and settings[0]["cwd"] == "/" and
                    req.get("model") == s["requested_model"], "unexpected host instructions or requested model")
            require(s["thread_id"] and s["thread_id"] not in self.seen_threads, "solver thread reused")
            self.seen_threads.add(s["thread_id"])
            compared = {k: s[k] for k in ("requested_model","model","provider","auth","effort","settings","runtime",
                                            "turn_timeout_s","tool_cap_per_turn","calculator_timeout_s",
                                            "calculator_output_cap_bytes_per_stream","runner_sha256")}
            compared["request_without_skill"] = req
            require(self.cohort_settings.setdefault(name, compared) == compared,
                    "mismatched model, tools, limits, runtime or request within cohort")
        rows = s["turns"]
        require([r["stage"] for r in rows] == list(range(1, len(rows)+1)) and len(rows) <= 2,
                "unexpected stage sequence")
        stages = [e["stage"] for e in events]
        require(stages == sorted(stages) and set(stages) <= set(range(len(rows)+1)), "interleaved trace stages")
        require((not rows or settings) and all(e["stage"] == 0 for e in events if e["kind"].startswith("thread/")),
                "turn started before thread setup")
        seen_calls = set()
        observed = [phase([e for e in events if e["stage"] == i], row, prompts[i-1], s["tool_cap_per_turn"], hashes, seen_calls)
                    for i, row in enumerate(rows, 1)]
        require(all(turn["complete"] for turn in observed[:-1]), "later user input before prior turn completion")
        require(s["tool_calls"] == len(seen_calls), "summary tool count differs from trace")
        err = [e["data"]["message"] for e in events if e["kind"] == "runner_error"]
        score = None
        if status == "completed":
            require(len(observed) == 2 and all(t["complete"] for t in observed) and not err, "incomplete scored trial")
            score = grader([t["final_text"] for t in observed])
            require(stable(score) == stable(g["score"]), "saved grade differs from deterministic regrade")
            disposition = "complete"
        else:
            require(err == [s["error"]] and "score" not in g and g.get("error") == s["error"], "failure evidence mismatch")
            # An active turn reaching its configured deadline counts as a resource-budget loss.
            # A provider error that consumed that window is reported as an infrastructure failure.
            timed_out = (s["error"] == "TimeoutError" and observed and observed[-1]["started"]
                         and not observed[-1]["complete"] and rows[-1]["elapsed_s"] >= s["turn_timeout_s"] - 1
                         and not any(e["kind"] in ("error", "model/rerouted") for e in events))
            missing_final = s["error"] == "No public final answer for completed turn" and observed and not observed[-1]["complete"]
            disposition = "budget_timeout" if timed_out else "no_final_answer" if missing_final else "infrastructure"
            if timed_out or missing_final:
                present = [t["final_text"] for t in observed]
                score = grader((present + ["", ""])[:2])
        usage = next((t["usage"]["total"] for t in reversed(observed) if t["usage"]), None)
        return {"case": case, "arm": arm, "repeat": rep, "disposition": disposition, "grade": score,
                "stages_completed": sum(t["complete"] for t in observed), "elapsed_s": s["elapsed_s"],
                "tool_calls": len(seen_calls), "failed_tool_calls": sum(t["tools_failed"] for t in observed),
                "last_reported_cumulative_usage": usage, "reason": s.get("error")}

    def grid(self, cohort, root):
        name = cohort["name"]
        folder = root / cohort.get("trials", "trials")
        arms, cases, reps = [cohort[k] for k in ("arms", "cases", "reps")]
        require(all(x and len(set(x)) == len(x) for x in [arms, cases, reps]) and
                all(isinstance(n, int) and n >= 1 for n in reps), "cohort has empty or duplicate dimensions")
        results, errors = [], []
        for case, rep, arm in itertools.product(cases, reps, arms):
            trial = f"{case}-{arm}-r{rep}"
            try:
                results.append(self.trial(folder / trial, name, case, arm, rep))
            except (OSError, ValueError, KeyError, IndexError, TypeError, ImportError) as e:
                errors.append({"trial": trial, "error": str(e)})
        groups = defaultdict(list)
        for row in results:
            groups[(row["case"].split("-")[0], row["arm"])].append(row)
        totals = [{"family": key[0], "arm": key[1], **aggregate(rows)} for key, rows in sorted(groups.items())]
        base = cohort.get("baseline", "baseline" if "baseline" in arms else arms[0])
        require(base in arms, "baseline must name a declared arm")
        pairs, contrasts = comparisons(arms, base, cases, reps, results)
        exclusions = []
        for item in cohort.get("exclusions", []):
            try:
                require(isinstance(item["reason"], str) and item["reason"].strip(), "exclusion requires a reason")
                path = root / item["path"]
                excluded_paths = {(folder / f"{c}-{a}-r{r}").resolve() for c,r,a in itertools.product(cases,reps,arms)}
                require(path.resolve() not in excluded_paths, "cannot exclude an expected comparison trial")
                s, g, _ = evidence(path)
                exclusions.append({"path": item["path"], "reason": item["reason"], "recorded_status": s["status"],
                                   "arm": g["arm"], "case": s["case_id"], "repeat": g["repeat"]})
            except (OSError, ValueError, KeyError, TypeError) as e:
                errors.append({"excluded": item.get("path"), "error": str(e)})
        return {"cohort": name, "expected": len(cases)*len(arms)*len(reps), "errors": errors, "by_family_arm": totals,
                "pairs": pairs, "baseline_arm": base, "baseline_comparisons": contrasts, "trials": results, "archived_exclusions": exclusions,
                "matched_execution_settings": self.cohort_settings.get(name),
                "skill_hashes": {a: self.cohort_skills.get((name, a)) for a in arms}}


def comparisons(arms, baseline, cases, reps, rows):
    by_id = {(r["case"], r["repeat"], r["arm"]): r for r in rows}
    others = [arm for arm in arms if arm != baseline]
    totals = {arm: dict(arm=arm, baseline=baseline, expected_pairs=len(cases)*len(reps), matched_pairs=0,
                        points_delta=0, pass_delta=0, baseline_passes=0, arm_passes=0,
                        pass_gains=0, pass_losses=0, unpaired=[]) for arm in others}
    pairs = []
    for case, repeat in itertools.product(cases, reps):
        outcomes = {}
        for arm in arms:
            row = by_id.get((case, repeat, arm))
            grade = row["grade"] if row and row["grade"] is not None else {}
            outcomes[arm] = {"disposition": row["disposition"] if row else "audit_error_or_missing",
                             "points": grade.get("points"), "pass": grade.get("pass")}
        reference = outcomes[baseline]
        deltas = {}
        for arm in others:
            other = outcomes[arm]
            total = totals[arm]
            if reference["points"] is None or other["points"] is None:
                deltas[arm] = None
                total["unpaired"].append({"case": case, "repeat": repeat,
                                          "baseline_outcome": reference["disposition"],
                                          "arm_outcome": other["disposition"]})
                continue
            points = other["points"] - reference["points"]
            passes = int(other["pass"]) - int(reference["pass"])
            deltas[arm] = {"points_delta": points, "pass_delta": passes}
            total["matched_pairs"] += 1
            total["points_delta"] += points
            total["pass_delta"] += passes
            total["baseline_passes"] += int(reference["pass"])
            total["arm_passes"] += int(other["pass"])
            total["pass_gains"] += int(passes > 0)
            total["pass_losses"] += int(passes < 0)
        pairs.append({"case": case, "repeat": repeat, "matched": all(r["points"] is not None for r in outcomes.values()),
                      "outcomes": outcomes, "vs_baseline": deltas})
    return pairs, list(totals.values())


def aggregate(rows):
    scored = [r["grade"] for r in rows if r["grade"] is not None]
    checks = defaultdict(Counter)
    critical = Counter()
    for score in scored:
        critical.update(score["critical_failures"])
        for key, check in score["checks"].items():
            checks[key]["passed"] += int(check["passed"])
            checks[key]["evaluated"] += 1
    usage = Counter()
    for row in rows:
        usage.update(row["last_reported_cumulative_usage"] or {})
    return {"attempts": len(rows), "scored": len(scored), "full_pass": sum(s["pass"] for s in scored),
            "partial": sum(0 < s["points"] < s["max_points"] for s in scored),
            "points": sum(s["points"] for s in scored), "possible": sum(s["max_points"] for s in scored),
            "outcomes": dict(Counter(r["disposition"] for r in rows)), "critical_failures": critical,
            "checks": dict(checks), "tool_calls": sum(r["tool_calls"] for r in rows),
            "failed_tool_calls": sum(r["failed_tool_calls"] for r in rows),
            "elapsed_s": round(sum(r["elapsed_s"] for r in rows),3), "reported_tokens": usage,
            "trials_reporting_usage": sum(r["last_reported_cumulative_usage"] is not None for r in rows)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--trials", default="trials")
    for key in ("arms","cases","reps"):
        p.add_argument("--"+key, nargs="+", type=int if key == "reps" else str)
    p.add_argument("--cohorts", type=Path)
    p.add_argument("--skill", action="append", default=[], metavar="ARM=DIR")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    root = args.root.resolve()
    if args.cohorts:
        cohorts = read_json(args.cohorts)
    elif args.arms and args.cases and args.reps:
        cohorts = [dict(name="comparison", trials=args.trials, arms=args.arms, cases=args.cases, reps=args.reps)]
    else:
        p.error("provide --arms, --cases, --reps or --cohorts")
    require(cohorts and len({c["name"] for c in cohorts}) == len(cohorts), "cohort names must be unique")
    skills = {}
    for spec in args.skill:
        arm, directory = spec.split("=", 1)
        path = root / directory
        files = [path / "SKILL.md", *sorted((path / "references").rglob("*.md"))]
        skills[arm] = {f.relative_to(path).as_posix(): digest(f.read_text().encode()) for f in files}
    audit = Audit(root, skills)
    reports = [audit.grid(cohort, root) for cohort in cohorts]
    ok = not any(r["errors"] for r in reports)
    payload = json.dumps({"ok": ok, "cohorts": reports}, indent=2) + "\n"
    if args.out:
        args.out.write_text(payload)
    else:
        print(payload, end="")
    return int(not ok)


if __name__ == "__main__":
    raise SystemExit(main())
