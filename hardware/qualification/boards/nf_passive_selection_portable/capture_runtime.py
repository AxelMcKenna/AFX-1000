"""Capture NP01 replay under one Python runtime without editing NP01."""

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

from hardware.qualification.boards.nf_passive_selection import audit, lifetime, selection, verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "nf_passive_selection"
EXPECTED = "bce8bfb8154395f2480742a1f37f3ecccc29d9fef96cdbb40567a20e4067845a"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_parent():
    handoff = PARENT / "handoff.json"
    if sha(handoff) != EXPECTED:
        raise ValueError("Wrong NP01 parent seal")
    data = json.loads(handoff.read_text())
    bad = [name for name, expected in data["files_sha256"].items() if sha(PARENT / name) != expected]
    if bad:
        raise ValueError(bad)
    return data


def build(out):
    if out.exists():
        raise RuntimeError("Fresh output required")
    parent = check_parent()
    out.mkdir()
    selection.build(out / "selection")
    parts = json.loads((PARENT / "sources/NF261/components.json").read_text())
    parameters = json.loads((PARENT / "sources/reference-baseline/parameters.json").read_text())
    d = dict(
        python_version=sys.version,
        executable=sys.executable,
        platform=platform.platform(),
        parent_seal_sha256=EXPECTED,
        parent_files_verified_before=len(parent["files_sha256"]),
        selection=json.loads((out / "selection/selections.json").read_text()),
        lifetime=lifetime.analysis(),
        monitor=audit.monitor_scenarios(parts, parameters),
        power=audit.dc_power_screens(),
        legacy_saved_errors=verify.saved_errors(),
        source_sha256={str(Path(__file__)): sha(Path(__file__))},
    )
    check_parent()
    d["parent_files_verified_after"] = len(parent["files_sha256"])
    (out / "runtime.json").write_text(json.dumps(d, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                python=platform.python_version(),
                parent_files=len(parent["files_sha256"]),
                legacy_saved_errors=d["legacy_saved_errors"],
            )
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
