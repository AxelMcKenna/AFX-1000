"""Replay captured native commands into new outputs; never capture live PCBs."""

import argparse
import json
import subprocess
from pathlib import Path

from . import audit
from .capture import ROOT, sha


def destination(path):
    p = Path(path).resolve()
    if p.exists() or p.is_relative_to(ROOT) or not p.is_relative_to(ROOT.parents[4]):
        raise RuntimeError("Use a NEW directory inside the repository but outside the sealed FR01 packet")
    return p


def run(kind, target):
    target = destination(target)
    if audit.run()["errors"]:
        raise RuntimeError("Captured saved evidence must validate before replay")
    from .verify_escape import specs as wire
    from .verify_mount5 import specs as mounting
    from .verify_robust import specs as robust

    folder, definitions = {
        "mounting": ("native-mount5", mounting),
        "wire": ("native-wire-escape", wire),
        "robust": ("native-robust-rear", robust),
    }[kind]
    original = json.loads((ROOT / "generated" / folder / "verification.json").read_text())
    specs = definitions()
    assert original["required_cases"] == list(specs)
    inputs = dict(original["input_sha256"])
    inputs[str(Path(__file__))] = sha(Path(__file__))
    target.mkdir(parents=True)
    rows = {}
    expected_failures = (
        ["NF233_mate_other_components_collision", "FPC84_short_bundle_electronics_collision"]
        if kind == "robust"
        else []
    )
    primitive = json.loads((ROOT / "generated/robust-projection-validation.json").read_text())[
        "independent_expected_volume_mm3"
    ]
    for name, spec in specs.items():
        command = list(original["cases"][name]["command"])
        output = target / (name + ".stl")
        command[command.index("-o") + 1] = str(output)
        p = subprocess.run(command, capture_output=True, text=True)
        (target / (name + ".log")).write_text(p.stdout + p.stderr)
        row = dict(
            role=spec["role"],
            returncode=p.returncode,
            command=command,
            statistics=audit.mesh(output) if output.exists() else None,
        )
        row["errors"] = audit.row_errors(name, row, spec, target, primitive)
        row["clear"] = not row["errors"]
        rows[name] = row
        changed = audit.hash_errors(inputs)
        failed = [n for n, r in rows.items() if not r["clear"]]
        complete = len(rows) == len(specs)
        result = dict(
            kind=kind,
            cases=rows,
            required_cases=list(specs),
            complete_set=complete,
            expected_retained_failures=expected_failures,
            all_collision_checks_clear=not failed and complete,
            all_expected_outcomes_reproduced=complete
            and set(failed) == set(expected_failures)
            and not changed,
            changed_inputs=changed,
            input_sha256=inputs,
            artifact_sha256={str(p): sha(p) for p in target.iterdir() if p.suffix in [".log", ".stl"]},
            captured_commands_replayed=True,
            live_PCBS_recaptured=False,
            physical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
        )
        (target / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(dict(case=name, clear=row["clear"], errors=row["errors"])), flush=True)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=["mounting", "wire", "robust"], required=True)
    p.add_argument("--outdir", type=Path, required=True)
    a = p.parse_args()
    raise SystemExit(not run(a.kind, a.outdir)["all_expected_outcomes_reproduced"])
