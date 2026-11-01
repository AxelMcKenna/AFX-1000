"""Independent read-only raw-log, mesh and input audit of sealed CP01."""

import hashlib
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
PACKET = REPO / "hardware/cad/a12/thermal/enlarged_base_pot"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def main():
    h = read(PACKET / "handoff.json")
    assert len(h["files_sha256"]) == 598
    for n, expected in h["files_sha256"].items():
        assert sha(PACKET / n) == expected, n
    a = read(PACKET / "generated/verification.json")
    specs = read(PACKET / "generated/cases.json")
    assert a["complete_required_set"] and not a["changed_inputs"]
    assert set(a["cases"]) == set(specs) == set(a["required_cases"])
    assert len(specs) == 122
    for n, expected in {**a["input_sha256"], **a["artifact_sha256"]}.items():
        assert sha(Path(n)) == expected, n
    helper = REPO / "hardware/cad/a12/positive_links/proposals/dig-leg-y121p3/mesh_review.py"
    spec = importlib.util.spec_from_file_location("independent_triangle_review", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    counts = Counter()
    native_rows = {}
    for name, row in a["cases"].items():
        role = specs[name]["role"]
        counts[role] += 1
        target = PACKET / "generated" / (name + ".stl")
        log = (PACKET / "generated" / (name + ".log")).read_text()
        assert row["clear"] and not row["errors"]
        assert "ERROR" not in log and "WARNING" not in log
        if role == "empty":
            assert row["returncode"] == 1 and "Current top level object is empty." in log
            assert not target.exists() and row["statistics"] is None
            native_rows[name] = dict(role=role, strict_empty=True)
            continue
        assert row["returncode"] == 0 and "NoError" in log and target.exists()
        actual = binary_stl(target)
        stored = row["statistics"]
        assert actual["triangles"] == stored["triangles"]
        assert actual["min_mm"] == stored["min_mm"] and actual["max_mm"] == stored["max_mm"]
        assert math.isclose(actual["volume_mm3"], stored["volume_mm3"], rel_tol=1e-11, abs_tol=1e-8)
        assert actual["volume_mm3"] > 0.001
        if specs[name]["expected_volume"] is not None:
            assert math.isclose(actual["volume_mm3"], specs[name]["expected_volume"], abs_tol=2e-6)
        record = dict(role=role, actual_mesh_statistics=actual)
        if role != "review":
            integrity = module.inspect(target)
            assert integrity["strict_closed_oriented_nonzero"], (name, integrity)
            record["independent_strict_mesh"] = integrity
        else:
            record["manufacturing_mesh_approval_granted"] = False
        native_rows[name] = record
    assert counts["empty"] == 73 and counts["part"] == 12 and counts["review"] == 14
    assert sum(counts.values()) == 122
    for flag in [
        "physical_qualified",
        "thermal_qualified",
        "fabrication_released",
        "whole_unit_electrical_qualified",
        "full_wiring_qualified",
        "structural_qualified",
    ]:
        assert not h[flag]
    assert h["complete_component_review_objects"] == 11
    assert h["complete_component_review_source_triangles"] == 719812
    assert not h["whole_fused_model_promoted_as_manufacturable"]
    result = dict(
        scope=__doc__,
        packet_handoff_sha256=sha(PACKET / "handoff.json"),
        sealed_files_checked=598,
        live_and_captured_input_hashes_checked=len(a["input_sha256"]),
        current_native_artifact_hashes_checked=len(a["artifact_sha256"]),
        all122_raw_native_cases_reintegrated=True,
        counts=dict(counts),
        native_rows=native_rows,
        all_nonreview_positive_outputs_independently_strict_meshes=True,
        component_3MF_triangle_correspondence_independently_replayed_here=False,
        no_new_native_commands_run=True,
        no_sealed_files_modified=True,
        physical_thermal_electrical_fabrication_qualified=False,
        audit_script_sha256=sha(Path(__file__)),
        independent_mesh_helper_sha256=sha(helper),
    )
    (ROOT / "review.json").write_text(json.dumps(result, indent=2) + "\n")
    print("CP01:598hashes/122rawrecords checked; roles", dict(counts))


if __name__ == "__main__":
    main()
