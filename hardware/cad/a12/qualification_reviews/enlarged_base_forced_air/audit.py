"""Independent raw-result and strict-mesh review of the sealed FI01 packet."""

import hashlib
import importlib.util
import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
PACKET = REPO / "hardware/cad/a12/thermal/enlarged_base_forced_air"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    handoff = read(PACKET / "handoff.json")
    assert sha(PACKET / "handoff.json") == "c718dac8223e345fca449634c4b97efb2b71ef757cf3b5e6076b0bd24e7b74d2"
    assert len(handoff["files_sha256"]) == 620
    for name, expected in handoff["files_sha256"].items():
        assert sha(PACKET / name) == expected, name
    main_run = read(PACKET / "generated/verification.json")
    retry = read(PACKET / "generated/retry-ps-hardware/verification.json")
    split = read(PACKET / "generated/hardware-split-v2/verification.json")
    cases = read(PACKET / "generated/cases.json")
    assert len(cases) == len(main_run["cases"]) == 162
    assert set(cases) == set(main_run["cases"]) == set(main_run["required_cases"])
    failed = "ps_hardware_other_components_collision"
    assert {n for n, r in main_run["cases"].items() if not r["clear"]} == {failed}
    assert main_run["input_sha256"] == retry["input_sha256"]
    assert all(split["input_sha256"].get(n) == h for n, h in main_run["input_sha256"].items())
    helper = REPO / "hardware/cad/a12/positive_links/proposals/dig-leg-y121p3/mesh_review.py"
    spec = importlib.util.spec_from_file_location("root_strict_mesh", helper)
    meshes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(meshes)
    counts = dict(
        direct_empty=0,
        direct_positive=0,
        strict_mesh=0,
        preserved_execution_failure=0,
        split_empty=0,
        split_control=0,
    )
    for directory, report in [
        (PACKET / "generated", main_run),
        (PACKET / "generated/retry-ps-hardware", retry),
        (PACKET / "generated/hardware-split-v2", split),
    ]:
        assert not report["changed_inputs"]
        for n, expected in {**report["input_sha256"], **report["artifact_sha256"]}.items():
            assert sha(Path(n)) == expected, n
        for name, row in report["cases"].items():
            log = (directory / (name + ".log")).read_text()
            target = directory / (name + ".stl")
            assert "ERROR" not in log and "WARNING" not in log
            if name == failed:
                assert row["returncode"] == 137 and not row["clear"]
                assert not log.strip() and not target.exists() and row["statistics"] is None
                counts["preserved_execution_failure"] += 1
                continue
            empty = row.get("expected_empty", row.get("role") == "empty")
            assert row["clear"]
            if empty:
                assert row["returncode"] == 1 and "Current top level object is empty." in log
                assert row["statistics"] is None and not target.exists()
                counts["split_empty" if report is split else "direct_empty"] += 1
                continue
            assert row["returncode"] == 0 and "NoError" in log
            actual = binary_stl(target)
            stored = row["statistics"]
            for field in ["triangles", "min_mm", "max_mm"]:
                assert actual[field] == stored[field], (name, field)
            assert math.isclose(actual["volume_mm3"], stored["volume_mm3"], rel_tol=1e-11, abs_tol=1e-8)
            assert actual["volume_mm3"] > 0.001
            if row.get("role") != "review":
                assert meshes.inspect(target)["strict_closed_oriented_nonzero"], name
                counts["strict_mesh"] += 1
            counts["split_control" if report is split else "direct_positive"] += 1
    assert counts == dict(
        direct_empty=98,
        direct_positive=63,
        strict_mesh=56,
        preserved_execution_failure=2,
        split_empty=60,
        split_control=10,
    ), counts
    plan = read(PACKET / "generated/hardware-split-plan-v2.json")
    assert plan["obstacle_family_expressions_exact"] == [
        "ui_electronics(false,false)",
        "cp_other_pot_bodies(p)",
        "ui_power_only()",
        "ps_other_controls()",
        "pf_wires(.25)",
        "ui_all_joints(.25)",
    ]
    assert set(map(tuple, plan["pairs"])) == {(i, j) for i in range(10) for j in range(6)}
    assert len(plan["pairs"]) == 60 and len(plan["centres"]) == 10
    assert {(r["pot_index"], r["family_index"]) for r in split["cases"].values()} == {
        (i, j) for i in range(10) for j in range(7)
    }
    model = (PACKET / "generated/context-derived.scad").read_text()
    assert plan["original_branch_exact"] in model
    assert (
        hashlib.sha256(plan["original_branch_exact"].encode()).hexdigest() == plan["original_branch_sha256"]
    )
    result = dict(
        scope=__doc__,
        packet_handoff_sha256=sha(PACKET / "handoff.json"),
        files_checked=620,
        raw_result_counts=counts,
        original_union_native_completed=False,
        all162_conditions_covered_via_direct_and_distributive_evidence=True,
        assembly_STEP_or_3MF_geometry_replayed_in_this_audit=False,
        new_native_commands_run=False,
        sealed_files_modified=False,
        physical_or_cooling_qualified=False,
        audit_sha256=sha(Path(__file__)),
        mesh_helper_sha256=sha(helper),
    )
    (ROOT / "review.json").write_text(json.dumps(result, indent=2) + "\n")
    print("FI01 independent review:", counts)


if __name__ == "__main__":
    main()
