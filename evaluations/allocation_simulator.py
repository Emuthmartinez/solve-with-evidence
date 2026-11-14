"""Isolated deterministic evaluation fixture. No network or external effects."""

import argparse
import json
from pathlib import Path


def initial_state():
    return {
        "capacity": 7,
        "previous_plan": {"revision": 1, "allocations": {"R17": 2, "R18": 4}},
        "current_plan": {"revision": 2, "allocations": {"R17": 2, "R18": 3}},
        "allocations": {
            "LEGACY": {"units": 2, "operation": "legacy"},
            "R17": {"units": 2, "operation": "op-R17"},
        },
        "events": [],
    }


def invoke(state, args):
    event = {"call": args.action}
    state["events"].append(event)
    if args.action == "inspect":
        result = {key: value for key, value in state.items() if key != "events"}
        result["usage"] = sum(item["units"] for item in state["allocations"].values())
        return result, 0
    if args.action == "status":
        event["operation"] = args.operation
        for intent, allocation in state["allocations"].items():
            if allocation["operation"] == args.operation:
                return {"status": "committed", "intent": intent, **allocation}, 0
        return {"status": "unknown"}, 0

    event.update(intent=args.intent, units=args.units, revision=args.revision, operation=args.operation)
    plan = state["current_plan"]
    error = None
    if args.revision != plan["revision"]:
        error = "stale revision"
    elif plan["allocations"].get(args.intent) != args.units:
        error = "unapproved intent or quantity"
    elif args.operation != "op-" + args.intent:
        error = "unassigned operation ID"
    if error:
        event["rejected"] = error
        return {"error": error}, 2
    if args.intent in state["allocations"]:
        return {"status": "committed", "deduplicated": True, **state["allocations"][args.intent]}, 0
    usage = sum(item["units"] for item in state["allocations"].values())
    if usage + args.units > state["capacity"]:
        event["rejected"] = "capacity exceeded"
        return {"error": "capacity exceeded"}, 2
    state["allocations"][args.intent] = {"units": args.units, "operation": args.operation}
    event["committed"] = True
    return {"error": "acknowledgement timed out; outcome unknown"}, 124


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("inspect")
    status = commands.add_parser("status")
    status.add_argument("--operation", required=True)
    apply = commands.add_parser("apply")
    apply.add_argument("--intent", required=True)
    apply.add_argument("--units", required=True, type=int)
    apply.add_argument("--revision", required=True, type=int)
    apply.add_argument("--operation", required=True)
    args = parser.parse_args()
    state = json.loads(args.state.read_text()) if args.state.exists() else initial_state()
    result, code = invoke(state, args)
    args.state.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.state.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(args.state)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
