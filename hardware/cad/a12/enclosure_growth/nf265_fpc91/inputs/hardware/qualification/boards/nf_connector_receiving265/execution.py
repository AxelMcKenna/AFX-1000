"""Capture final portable test/audit statuses under both installed Pythons."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(out):
    if out.exists():
        raise RuntimeError("Fresh final execution output required")
    files = list(ROOT.glob("*.py")) + [
        ROOT / "ports-v2.json",
        ROOT / "mechanical-v2/geometry.scad",
        ROOT / "mechanical-v2/datums.json",
    ]
    bindings = {str(p): sha(p) for p in files}
    out.mkdir()
    records = []
    for version, python in [("python39", "/usr/bin/python3"), ("python312", str(REPO / ".venv/bin/python"))]:
        for name, cmd in [
            (
                "tests",
                [
                    python,
                    "-m",
                    "unittest",
                    "hardware.qualification.boards.nf_connector_receiving265.test_nc265",
                ],
            ),
            (
                "audit",
                [
                    python,
                    "-m",
                    "hardware.qualification.boards.nf_connector_receiving265.audit",
                    "--output",
                    str(out / (version + "-audit.json")),
                ],
            ),
        ]:
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=False)
            p = out / (version + "-" + name + ".log")
            p.write_text(r.stdout + r.stderr)
            records.append(
                dict(name=version + "-" + name, command=cmd, returncode=r.returncode, log_sha256=sha(p))
            )
    changed = [str(p) for p in files if sha(p) != bindings[str(p)]]
    report = dict(
        source_sha256=bindings,
        jobs=records,
        changed_inputs=changed,
        all4_actual_commands_returned0=all(r["returncode"] == 0 for r in records),
        no_native_geometry_repeated=True,
        physical_qualified=False,
    )
    (out / "execution.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(dict(jobs=len(records), returncodes=[r["returncode"] for r in records], changed=changed))
    )
    raise SystemExit(bool(changed) or not report["all4_actual_commands_returned0"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
