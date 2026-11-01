"""Independent PB02 raw-log/source/mesh review; retain the old-wire rejection."""

import hashlib
import importlib.util
import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def main():
    native = read(ROOT / "native/verification.json")
    geometry = read(ROOT / "generated/geometry.json")
    mesh = read(ROOT / "mesh-review.json")
    assert len(native["records"]) == 15 and not native["changed_inputs"]
    for n, h in {**native["source_sha256"], **native["artifact_sha256"]}.items():
        assert sha(REPO / n) == h, n
    assert mesh["all32_parts_strict_meshes"] and len(mesh["records"]) == 32
    assert mesh["source_geometry_receipt_sha256"] == sha(ROOT / "generated/geometry.json")
    assert mesh["script_sha256"] == sha(ROOT / "mesh_review.py")
    spec = importlib.util.spec_from_file_location("pb_mesh_review", ROOT / "mesh_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    records = {}
    import_names = {"candidate_DIG_geometry": "DIG-CU", "candidate_support_geometry": "SUPPORT-ENVELOPE"}
    for name, row in native["records"].items():
        log = (ROOT / "native" / (name + ".log")).read_text()
        assert "ERROR" not in log and "WARNING" not in log
        stl = ROOT / "native" / (name + ".stl")
        if row["empty"]:
            assert row["returncode"] == 1 and "Current top level object is empty." in log and not stl.exists()
            records[name] = dict(result="strict native empty", meets_declared_expectation=True)
            continue
        assert row["returncode"] == 0 and stl.exists()
        actual = binary_stl(stl)
        assert actual == row["statistics"] and actual["volume_mm3"] > 0
        if name in import_names:
            assert (
                "Top level object is a 3D object (PolySet)" in log and "CGAL Polyhedrons in cache: 0" in log
            )
            part = import_names[name]
            source = binary_stl(ROOT / "generated" / (part + ".stl"))
            assert actual == source
            integrity = module.inspect(stl)
            assert integrity["strict_closed_oriented_nonzero"]
            relative = (
                abs(actual["volume_mm3"] - geometry["parts"][part]["volume_mm3"])
                / geometry["parts"][part]["volume_mm3"]
            )
            assert relative < 0.0001
            records[name] = dict(
                result="named literal-import exception; independent exact source statistics and strict mesh proof",
                meets_declared_expectation=True,
                topology=integrity,
                native_vs_BREP_relative_volume_error=relative,
            )
        else:
            assert "NoError" in log
            meets = not row["expected_empty"]
            if name.endswith("_control"):
                assert math.isclose(actual["volume_mm3"], 0.008, abs_tol=2e-6)
            records[name] = dict(
                result="native nonempty", meets_declared_expectation=meets, statistics=actual
            )
    failed = [n for n, r in records.items() if not r["meets_declared_expectation"]]
    assert failed == ["new_positive_old_fed_wire_collision"]
    wire = native["records"][failed[0]]["statistics"]
    assert 3.88 < wire["volume_mm3"] < 3.89
    assert wire["min_mm"][0] > 190 and wire["min_mm"][2] > 24.24
    result = dict(
        scope=__doc__,
        source_inputs_checked=len(native["source_sha256"]),
        native_artifact_hashes_checked=len(native["artifact_sha256"]),
        raw_native_cases_checked=15,
        records=records,
        import_only_geometry_exceptions=list(import_names),
        original_receipt_and_false_import_statuses_preserved=True,
        remaining_failed_constraint=failed,
        failure_region_is_outside_two_changed_midleg_points=True,
        old_fed_wire_route_accepted_with_maximum_positive_envelope=False,
        separate_wire_lift_native_acceptance_required=True,
        all_exported32_part_meshes_closed_oriented_nonzero=True,
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
        reviewed_native_receipt_sha256=sha(ROOT / "native/verification.json"),
        audit_script_sha256=sha(Path(__file__)),
    )
    (ROOT / "review.json").write_text(json.dumps(result, indent=2) + "\n")
    print("15 raw cases reviewed; only rejected constraint:", failed)


if __name__ == "__main__":
    main()
