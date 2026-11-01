"""Capture actual success/failure statuses under both installed runtimes."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from hardware.qualification.boards.nf_passive_selection_portable import capture_runtime

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(out):
    if out.exists():
        raise RuntimeError("Fresh cross-runtime evidence directory required")
    capture_runtime.check_parent()
    out.mkdir()
    jobs = []
    for tag, python in [("python39", Path("/usr/bin/python3")), ("python312", REPO / ".venv/bin/python")]:
        jobs.extend(
            [
                (
                    tag + "-legacy",
                    [
                        str(python),
                        "-m",
                        "unittest",
                        "hardware.qualification.boards.nf_passive_selection.test_np01",
                    ],
                    1 if tag == "python312" else 0,
                ),
                (
                    tag + "-successor",
                    [
                        str(python),
                        "-m",
                        "unittest",
                        "hardware.qualification.boards.nf_passive_selection_portable.test_portable",
                    ],
                    0,
                ),
                (
                    tag + "-verify",
                    [
                        str(python),
                        "-m",
                        "hardware.qualification.boards.nf_passive_selection_portable.verify",
                        "--output",
                        str(out / (tag + "-verify.json")),
                    ],
                    0,
                ),
            ]
        )
    result = []
    for name, cmd, expected in jobs:
        completed = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=False)
        log = out / (name + ".log")
        log.write_text(completed.stdout + completed.stderr)
        result.append(
            dict(
                name=name,
                command=cmd,
                returncode=completed.returncode,
                expected_returncode=expected,
                expected_status_observed=completed.returncode == expected,
                log=str(log),
                log_sha256=sha(log),
            )
        )
    capture_runtime.check_parent()
    report = dict(
        parent_seal_sha256=capture_runtime.EXPECTED,
        original55files_unchanged=True,
        jobs=result,
        old_python312_two_failures_are_NOT_passes=True,
        source_sha256={
            str(p): sha(p)
            for p in [
                Path(__file__),
                ROOT / "verify.py",
                ROOT / "policy.py",
                ROOT / "capture_runtime.py",
                ROOT / "test_portable.py",
            ]
        },
    )
    (out / "execution.json").write_text(json.dumps(report, indent=2) + "\n")
    failed = [r for r in result if not r["expected_status_observed"]]
    print(json.dumps(dict(actual_jobs=len(result), unexpected_statuses=failed)))
    raise SystemExit(bool(failed))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
