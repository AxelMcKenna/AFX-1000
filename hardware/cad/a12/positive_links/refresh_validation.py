"""Revalidate unchanged native output after the collision-artifact gate fix only."""

import ast
import copy
import json

from .generate import OUT, REPO, ROOT, sha
from .verify import saved_report_errors, stale_paths


def gate_only_change(old_source, new_source):
    def normalized(source):
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "saved_report_errors":
                node.body = [ast.Pass()]
        return ast.dump(tree, include_attributes=False)

    return normalized(old_source) == normalized(new_source)


def main():
    archive = OUT / "history/validation-only-before-collision-artifact-gate"
    old = json.loads((archive / "verification.json").read_text())
    key = str((ROOT / "verify.py").relative_to(REPO))
    assert sha(archive / "verify.py") == old["source_sha256"][key]
    assert gate_only_change((archive / "verify.py").read_text(), (ROOT / "verify.py").read_text()), (
        "Native driver/model code changed; full rerun required"
    )
    changed = stale_paths(old["source_sha256"], REPO)
    assert set(changed).issubset({key}), changed
    for group in ("geometry_sha256", "native_input_sha256", "native_evidence_sha256"):
        assert not stale_paths(old[group], REPO), group
    current = json.loads((OUT / "verification.json").read_text())
    assert current["native_checks"] == old["native_checks"], "Executed numerical evidence changed"
    report = copy.deepcopy(old)
    report["native_execution_source_sha256"] = old["source_sha256"]
    report["source_sha256"][key] = sha(ROOT / "verify.py")
    report["validation_only_refresh"] = dict(
        geometry_rerun=False,
        only_changed_function="saved_report_errors",
        original_executed_report_sha256=sha(archive / "verification.json"),
        original_gate_sha256=sha(archive / "verify.py"),
        current_gate_sha256=sha(ROOT / "verify.py"),
        native_driver_ast_unchanged=True,
        native_input_and_evidence_bytes_unchanged=True,
    )
    report["validation_errors"] = saved_report_errors(
        report, json.loads((OUT / "geometry.json").read_text()), OUT
    )
    report["accepted_native_evidence"] = not report["validation_errors"]
    assert report["accepted_native_evidence"], report["validation_errors"]
    packet = json.loads((OUT / "obstacles.json").read_text())
    packet["source_sha256"][key] = report["source_sha256"][key]
    (OUT / "obstacles.json").write_text(json.dumps(packet, indent=2) + "\n")
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "Strict gate revalidation passed; original execution provenance retained; native inputs/evidence and driver AST unchanged."
    )


if __name__ == "__main__":
    main()
