"""Run the verifier in isolated disposable copies of this specific historical fixture."""

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
HISTORICAL = ["--manifest", "historical-candidate"]


def run_case(name, prepare, args, expected):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        evaluations = root / "evaluations"
        evaluations.mkdir()
        for file in ("allocation_simulator.py", "records.json"):
            shutil.copyfile(SOURCE / "evaluations" / file, evaluations / file)
        shutil.copyfile(SOURCE / "evaluations/verify_evidence.py", evaluations / "verify_evidence.py")
        shutil.copytree(HERE / "snapshots/baseline", root / "solve-with-evidence")
        prepare(root)
        for flags in ([], ["-O"]):
            result = subprocess.run(
                [sys.executable, "-B", *flags, "evaluations/verify_evidence.py", *args],
                cwd=root, capture_output=True, text=True,
            )
            output = (result.stdout + result.stderr).strip()
            should_pass = expected is None
            if (result.returncode == 0) != should_pass or (expected and expected not in output):
                raise RuntimeError(f"{name} ({flags!r}): {result.returncode}: {output}")
            rows.append({"case": name, "optimized": bool(flags), "exit": result.returncode, "output": output})


def corrupt_replay(root):
    file = root / "evaluations/records.json"
    records = json.loads(file.read_text())
    records["trials"]["candidate-d1"]["state"]["capacity"] = 999
    file.write_text(json.dumps(records))


def corrupt_probe(root):
    file = root / "evaluations/allocation_simulator.py"
    source = file.read_text()
    file.write_text(source.replace('return {"error": "acknowledgement timed out; outcome unknown"}, 124',
                                   'return {"error": "acknowledgement timed out; outcome unknown"}, 0'))


def replace_file_with_symlink(root):
    target = root / "solve-with-evidence/SKILL.md"
    source = root / "original-bytes"
    target.rename(source)
    target.symlink_to(source)


def prepare_new(root):
    changed = root / "solve-with-evidence/SKILL.md"
    changed.write_text(changed.read_text() + "\nNew candidate.\n")
    new = root / "solve-with-evidence/references/new.md"
    new.write_text("New reference.\n")
    folder = root / "solve-with-evidence"
    manifest = {p.relative_to(folder).as_posix(): sha256(p.read_bytes()).hexdigest()
                for p in folder.rglob("*") if p.is_file()}
    (root / "frozen-new.json").write_text(json.dumps(manifest))


rows = []
run_case("original package control", lambda _: None, HISTORICAL, None)
run_case("changed skill", lambda r: (r / "solve-with-evidence/SKILL.md").write_text("changed"), HISTORICAL, "Digest differs")
run_case("extra nested file", lambda r: (r / "solve-with-evidence/references/new").touch(), HISTORICAL, "Unexpected file")
run_case("missing file", lambda r: (r / "solve-with-evidence/SKILL.md").unlink(), HISTORICAL, "Missing files")
run_case("same bytes via symlink", replace_file_with_symlink, HISTORICAL, "Unexpected symlink")
run_case("symlink to directory", lambda r: (r / "solve-with-evidence/linked").symlink_to(r / "evaluations"), HISTORICAL, "Unexpected symlink")
run_case("dangling symlink", lambda r: (r / "solve-with-evidence/linked").symlink_to(r / "absent"), HISTORICAL, "Unexpected symlink")
run_case("extra empty directory", lambda r: (r / "solve-with-evidence/empty").mkdir(), HISTORICAL, "Unexpected directory")
run_case("package root symlink", lambda r: (r / "alias").symlink_to(r / "solve-with-evidence"), [*HISTORICAL, "--package", "alias"], "Package must be a directory")
run_case("unchanged bytes against other historical manifest", lambda _: None, ["--manifest", "historical-baseline"], "Digest differs")
run_case("new package and explicit new manifest", prepare_new, ["--manifest", "frozen-new.json"], None)
run_case("historical replay after package advances", prepare_new, [], None)
run_case("historical replay distinguishes corrupt state", corrupt_replay, [], "Trace differs")
run_case("probe distinguishes wrong acknowledgement code", corrupt_probe, [], "Expected acknowledgement timeout")
run_case("explicit package requires identity manifest", lambda _: None, ["--package", "solve-with-evidence"], "requires --manifest")

print(f"{len(rows)} CLI checks passed ({len(rows) // 2} scenarios across normal and optimized Python).")
