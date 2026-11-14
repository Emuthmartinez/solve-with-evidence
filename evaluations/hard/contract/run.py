"""Execute one frozen matched case with the same harness and record its public grade."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from contract_transfer import CASE, decode, grade, prompt
from controls import controls
BASE = Path(__file__).resolve().parent
HARD = BASE.parent
SKILLS = {"baseline":HARD.parent/"solve-with-evidence-source/solve-with-evidence", "shipped": HARD/"shipped"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_manifest():
    items = [BASE/f for f in ("contract_transfer.py","controls.py","run.py","inputs/contract-h4.json","controls.json")]
    return {str(p.relative_to(BASE)):digest(p) for p in items}


def freeze():
    dest = BASE/"freeze.json"
    assert not dest.exists()
    payload = {"id":CASE, "messages":[prompt(CASE,s) for s in (1,2)]}
    (BASE/"inputs/contract-h4.json").write_text(json.dumps(payload,indent=2)+"\n")
    (BASE/"controls.json").write_text(json.dumps(controls(),indent=2)+"\n")
    frozen = {"files":expected_manifest(),"model":"gpt-6.1-sol","effort":"medium","timeout":200,
              "cohort":[[a,r] for r in (1,2) for a in SKILLS],
              "rule":"Two repeats per arm, report every observed turn, score strict JSON, semantic truth table evaluated on the full finite domain."}
    dest.write_text(json.dumps(frozen,indent=2)+"\n")
    return digest(dest)


def run(arm,repeat):
    spec = json.loads((BASE/"freeze.json").read_text())
    assert spec["files"] == expected_manifest() and [arm,repeat] in spec["cohort"]
    out = BASE/"trials"/f"{CASE}-{arm}-r{repeat}"
    command = [sys.executable,str(HARD/"runner/run_trial.py"),"--case",str(BASE/"inputs/contract-h4.json"),
               "--skill",str(SKILLS[arm]),"--out",str(out),"--model",spec["model"],"--effort",spec["effort"],"--timeout",str(spec["timeout"])]
    rc = subprocess.run(command).returncode
    summary = json.loads((out/"summary.json").read_text())
    subprocess.run([sys.executable,str(HARD/"runner/verify_trial.py"),str(out)],check=True)
    record = {"arm":arm,"case":CASE,"repeat":repeat,"status":summary["status"],"runner_exit":rc}
    if summary["status"] == "completed":
        record["score"] = grade(CASE,[decode(t["text"]) for t in summary["turns"]])
    else:
        record["error"] = summary.get("error","see trace")
    (out/"grade.json").write_text(json.dumps(record,indent=2)+"\n")
    print(out.name,record["status"],record.get("score",{}).get("critical_failures"))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("arm",choices=["freeze",*SKILLS]); p.add_argument("repeat",type=int,nargs="?")
    args = p.parse_args()
    if args.arm == "freeze":
        print(freeze())
    else:
        run(args.arm,args.repeat)
