"""Control tests using a copied, completed development capture as a fixture."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch
import audit


def write(path, obj):
    path.write_text(json.dumps(obj))


def refresh(path):
    write(path / "manifest.json", {name: audit.digest((path / name).read_bytes()) for name in ("trace.jsonl", "summary.json")})


def events(path):
    return [json.loads(line) for line in (path / "trace.jsonl").read_text().splitlines()]


def write_events(path, rows):
    for i, row in enumerate(rows, 1):
        row["seq"] = i
    (path / "trace.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))


def strict_delivery_controls(root, scratch):
    sys.path.insert(0, str(root))
    import compare

    trial_name = "contract-h4-baseline-r1"
    original = root / "trials" / trial_name
    texts = [t["text"] for t in audit.read_json(original / "summary.json")["turns"]]
    good = audit.read_json(original / "grade.json")["score"]
    assert good["pass"]
    # Both variants still contain the correct object for a permissive decoder.
    key = next(iter(json.loads(texts[0])))
    duplicate = "{" + json.dumps(key) + ":null," + texts[0].lstrip()[1:]
    for label, changed in (("duplicate", duplicate), ("fenced", "```json\n" + texts[0] + "\n```")):
        assert audit.answer(changed) == json.loads(texts[0])
        dest = scratch / label
        path = dest / "trials" / trial_name
        shutil.copytree(original, path)
        summary = audit.read_json(path / "summary.json")
        summary["turns"][0]["text"] = changed
        write(path / "summary.json", summary)
        rows = events(path)
        for row in rows:
            item = row["data"].get("item", {})
            if row["stage"] == 1 and item.get("type") == "agentMessage" and item.get("text") == texts[0]:
                item["text"] = changed
        write_events(path, rows)
        refresh(path)
        # Replay through the normal dispatcher using the captured runner output.
        with patch.object(compare.subprocess, "run", return_value=compare.subprocess.CompletedProcess([], 0)) as runner:
            scored = compare.run_job(("baseline", "contract-h4", 1), dest)["score"]
            runner.assert_called_once()
        assert not scored["pass"] and "stage1_deliverable_shape" in scored["critical_failures"]
        assert all(key.startswith("stage1_") for key in scored["critical_failures"])
        replayed = audit.Audit(root, {}).trial(path, "parser", "contract-h4", "baseline", 1)
        assert replayed["grade"] == scored


def test(root, scratch):
    case, arm, repeat = "probe-d1", "baseline", 1
    fixture = root / "trials/probe-d1-baseline-r1"
    path = scratch / fixture.name
    def reset():
        if path.exists():
            shutil.rmtree(path)
        shutil.copytree(fixture, path)
    def run():
        return audit.Audit(root, {}).trial(path, "dev", case, arm, repeat)
    def rejects(fragment):
        try:
            run()
        except audit.Invalid as e:
            assert fragment in str(e), (fragment, e)
        else:
            raise AssertionError(f"accepted corruption {fragment}")
    reset()
    assert run()["grade"]["max_points"] == 10
    with (path / "trace.jsonl").open("a") as stream:
        stream.write("\n")
    rejects("digest")
    reset()
    g = audit.read_json(path / "grade.json")
    g["score"]["points"] = -1
    write(path / "grade.json", g)
    rejects("regrade")

    reset()
    rows = events(path)
    item = next(row for row in rows if row["kind"] == "tool_result")
    item["data"]["callId"] = "no-call"
    write_events(path, rows)
    refresh(path)
    rejects("matching call")

    reset()
    rows = events(path)
    start = next(i for i, r in enumerate(rows) if r["stage"] == 1 and r["kind"] == "tool_call")
    native = {"id": "unauthorized-native-call", "type": "commandExecution", "command": "true"}
    injected = [dict(rows[start], kind=kind, data={"item": native}) for kind in ("item/started", "item/completed")]
    rows[start:start] = injected
    write_events(path, rows)
    refresh(path)
    rejects("item type outside the fixed trial protocol: commandExecution")

    reset()
    s = audit.read_json(path / "summary.json")
    s["turns"][1]["text"] = "{}"
    write(path / "summary.json", s)
    refresh(path)
    rejects("final answer")

    reset()
    rows = events(path)
    rows[0]["data"]["developerInstructions"] += "changed"
    write_events(path, rows)
    refresh(path)
    rejects("skill differs")

    reset()
    runner = audit.Audit(root, {})
    runner.trial(path, "dev", case, arm, repeat)
    s = audit.read_json(path / "summary.json")
    s["turn_timeout_s"] += 1
    s["thread_id"] = "independent-control"
    write(path / "summary.json", s)
    refresh(path)
    try:
        runner.trial(path, "dev", case, arm, repeat)
        raise AssertionError("accepted budget mismatch")
    except audit.Invalid as e:
        assert "limits" in str(e)

    # The optional request can be absent, while the provider must resolve the same model.
    reset()
    runner = audit.Audit(root, {})
    s, rows = audit.read_json(path / "summary.json"), events(path)
    s["requested_model"] = None
    del next(row["data"] for row in rows if row["kind"] == "thread/request")["model"]
    write(path / "summary.json", s)
    write_events(path, rows)
    refresh(path)
    runner.trial(path, "default-model", case, arm, repeat)
    s["thread_id"] = "different-thread"
    s["model"] = s["settings"]["model"] = "different-resolved-model"
    next(row["data"] for row in rows if row["kind"] == "thread/settings")["model"] = s["model"]
    write(path / "summary.json", s)
    write_events(path, rows)
    refresh(path)
    try:
        runner.trial(path, "default-model", case, arm, repeat)
        raise AssertionError("accepted different resolved models under a default request")
    except audit.Invalid as e:
        assert "mismatched model" in str(e)
    reset()
    s, rows = audit.read_json(path / "summary.json"), events(path)
    s["requested_model"] = "explicit-different-model"
    next(row["data"] for row in rows if row["kind"] == "thread/request")["model"] = s["requested_model"]
    write(path / "summary.json", s)
    write_events(path, rows)
    refresh(path)
    rejects("resolved settings mismatch")

    # Synthesize a turn that reached the common deadline after the recorded first answer.
    reset()
    s, g = audit.read_json(path / "summary.json"), audit.read_json(path / "grade.json")
    rows = events(path)
    start = next(i for i, row in enumerate(rows) if row["stage"] == 2 and row["kind"] == "turn/started")
    trimmed = copy.deepcopy(rows[:start+1])
    for kind, data in [("runner_error", {"message": "TimeoutError"}), ("runner_end", {"status": "failed"})]:
        trimmed.append(dict(trimmed[-1], kind=kind, data=data))
    write_events(path, trimmed)
    s.update(status="failed", error="TimeoutError", tool_calls=s["turns"][0]["tool_calls"])
    s["turns"][-1].update(status="failed", text="", usage=None, tool_calls=0, elapsed_s=s["turn_timeout_s"])
    g.update(status="failed", error="TimeoutError", runner_exit=1)
    del g["score"]
    write(path / "summary.json", s)
    write(path / "grade.json", g)
    refresh(path)
    outcome = run()
    assert outcome["disposition"] == "budget_timeout" and outcome["grade"]["points"] == 5

    # A recorded transport failure with the same first turn remains unscored.
    s["error"] = g["error"] = trimmed[-2]["data"]["message"] = "app-server transport closed"
    write_events(path, trimmed)
    write(path / "summary.json", s)
    write(path / "grade.json", g)
    refresh(path)
    outcome = run()
    assert outcome["disposition"] == "infrastructure" and outcome["grade"] is None and outcome["stages_completed"] == 1

    reset()
    grid = audit.Audit(root, {}).grid(dict(name="dev", trials=str(scratch), arms=[arm,"absent"], cases=[case], reps=[1]), root)
    assert len(grid["errors"]) == 1 and not grid["pairs"][0]["matched"]

    # Three arms with crossed outcomes cannot be collapsed to the first A/B pair.
    def scored(r, arm, points):
        return {"case": case, "repeat": r, "arm": arm, "disposition": "complete",
                "grade": {"points": points, "pass": points == 10}}
    rowset = [scored(1, arm, 8), scored(2, arm, 10), scored(1, "candidate", 10), scored(2, "candidate", 10),
              scored(1, "release", 5), scored(2, "release", 7)]
    pairs, totals = audit.comparisons(["candidate", arm, "release"], arm, [case], [1, 2], rowset)
    assert all(p["matched"] and set(p["vs_baseline"]) == {"candidate", "release"} for p in pairs)
    d = {r["arm"]: r for r in totals}
    assert d["candidate"]["points_delta"] == 2 and d["candidate"]["pass_gains"] == 1
    assert d["release"]["points_delta"] == -6 and d["release"]["pass_losses"] == 1
    pairs, totals = audit.comparisons(["candidate", arm, "release"], arm, [case], [1, 2], rowset[:-1])
    assert not pairs[-1]["matched"] and pairs[-1]["vs_baseline"]["release"] is None
    assert totals[0]["matched_pairs"] == 2 and totals[1]["matched_pairs"] == 1 and len(totals[1]["unpaired"]) == 1

    four = rowset + [scored(1, "final", 9), scored(2, "final", 8)]
    pairs, totals = audit.comparisons([arm, "candidate", "release", "final"], arm, [case], [1, 2], four)
    assert all(p["matched"] and len(p["outcomes"]) == 4 and len(p["vs_baseline"]) == 3 for p in pairs)
    assert {t["arm"]: t["points_delta"] for t in totals} == {"candidate": 2, "release": -6, "final": -1}
    five = four + [scored(1, "published", 10), scored(2, "published", 9)]
    for arms in ([arm, "candidate", "release", "final", "published"], [arm, "final", "published"], [arm, "published"]):
        pairs, totals = audit.comparisons(arms, arm, [case], [1, 2], five)
        assert [t["arm"] for t in totals] == arms[1:] and all(t["matched_pairs"] == 2 for t in totals)
        assert all(p["matched"] and set(p["outcomes"]) == set(arms) for p in pairs)

    # Verify sealed-case routing with dummy modules in memory; never evaluate the case.
    import types
    dummy = types.SimpleNamespace(prompt=lambda case, stage: str(stage), grade=lambda *args: None)
    with patch.object(audit.importlib, "import_module", return_value=dummy) as imported:
        suite = audit.Suites(root)
        result, _ = suite.get("closure-h2")
        assert result == ["1", "2"]
        imported.assert_called_with("closure_transfer")
        suite.get("closure-d1")
        imported.assert_called_with("closure")
        suite.get("ledger-h2")
        imported.assert_called_with("ledger_transfer")
        suite.get("ledger-d1")
        imported.assert_called_with("ledger")
        suite.get("artifact-h3")
        imported.assert_called_with("artifact_transfer")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="audit-controls-", dir=Path(__file__).resolve().parent) as tmp:
        test(a.root.resolve(), Path(tmp))
        strict_delivery_controls(a.root.resolve(), Path(tmp))
    print("PASS: good capture; tampered evidence, grade, tool, final, skill and budget; timeout, infrastructure, missing arm, three/four-arm comparisons, sealed-case routing, and strict JSON in dispatch and regrade.")
