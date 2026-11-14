"""Replay the recorded D1 trials and optionally verify a frozen skill package."""

from argparse import ArgumentParser, Namespace
import hashlib
import json
from pathlib import Path

from allocation_simulator import initial_state, invoke


def check(condition, message):
    if not condition:
        raise SystemExit(message)


def verify_package(package, expected):
    check(isinstance(expected, dict) and "SKILL.md" in expected,
          "Manifest must map relative file paths, including SKILL.md, to SHA-256 digests.")
    check(not package.is_symlink() and package.is_dir(), "Package must be a directory, not a symlink.")
    directories = [package]
    seen = set()
    while directories:
        for path in directories.pop().iterdir():
            relative = path.relative_to(package).as_posix()
            check(not path.is_symlink(), f"Unexpected symlink: {relative}")
            if path.is_dir():
                check(any(name.startswith(relative + "/") for name in expected),
                      f"Unexpected directory: {relative}")
                directories.append(path)
                continue
            check(relative in expected, f"Unexpected file: {relative}")
            check(path.is_file(), f"Expected a regular file: {relative}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            check(digest == expected[relative], f"Digest differs: {relative}")
            seen.add(relative)
    missing = sorted(expected.keys() - seen)
    check(not missing, f"Missing files: {', '.join(missing)}")


def replay_trials(records):
    for variant in ("baseline", "candidate"):
        recorded = records["trials"][variant + "-d1"]["state"]
        replayed = initial_state()
        for event in recorded["events"]:
            arguments = {key: value for key, value in event.items() if key in {
                "operation", "intent", "units", "revision"
            }}
            invoke(replayed, Namespace(action=event["call"], **arguments))
        check(replayed == recorded, f"Trace differs: {variant}")
        check(replayed["allocations"] == {
            "LEGACY": {"units": 2, "operation": "legacy"},
            "R17": {"units": 2, "operation": "op-R17"},
            "R18": {"units": 3, "operation": "op-R18"},
        }, f"Unexpected final allocations: {variant}")
        committed = sum(bool(event.get("committed")) for event in replayed["events"])
        check(committed == 1, f"Expected one new allocation: {variant}")


def probe_fixture():
    state = initial_state()
    for units, revision, operation in ((4, 1, "op-R18"), (3, 2, "fresh-key"), (4, 2, "op-R18")):
        _, code = invoke(state, Namespace(action="apply", intent="R18", units=units,
                                         revision=revision, operation=operation))
        check(code == 2 and len(state["allocations"]) == 2, "Invalid allocation was accepted.")
    args = Namespace(action="apply", intent="R18", units=3, revision=2, operation="op-R18")
    _, code = invoke(state, args)
    check(code == 124, "Expected acknowledgement timeout.")
    result, code = invoke(state, Namespace(action="status", operation="op-R18"))
    check(code == 0 and result.get("status") == "committed", "Status failed to confirm commit.")
    result, code = invoke(state, args)
    check(code == 0 and result.get("deduplicated") is True, "Retry was not deduplicated.")
    result, code = invoke(state, Namespace(action="inspect"))
    check(code == 0 and result.get("usage") == 7, "Unexpected usage after retry.")


def main():
    directory = Path(__file__).resolve().parent
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", help="historical-baseline, historical-candidate, or a JSON path-to-digest map")
    parser.add_argument("--package", type=Path, help="package to compare, default: repository skill directory")
    args = parser.parse_args()
    if args.package is not None and args.manifest is None:
        parser.error("--package requires --manifest")
    records = json.loads((directory / "records.json").read_text())
    if args.manifest is not None:
        historical = {"historical-baseline": "baseline_manifest", "historical-candidate": "candidate_manifest"}
        if args.manifest in historical:
            expected = records[historical[args.manifest]]
        else:
            expected = json.loads(Path(args.manifest).read_text())
        verify_package(args.package or directory.parent / "solve-with-evidence", expected)
        print("Package matches the selected manifest.")
    replay_trials(records)
    probe_fixture()
    print("Two historical D1 replays and fixture probes passed.")


if __name__ == "__main__":
    main()
