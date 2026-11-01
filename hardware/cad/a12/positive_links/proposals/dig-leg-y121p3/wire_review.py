"""Independent source-congruence and raw-result review of the positive wire lift."""

import hashlib
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
    out = ROOT / "wire-raise-1mm"
    a, plan = read(out / "verification.json"), read(out / "plan.json")
    assert a["all_required_native_screens_passed"] and not a["changed_inputs"]
    for n, expected in {**a["source_sha256"], **a["artifact_sha256"]}.items():
        assert sha(REPO / n) == expected, n
    source = REPO / "hardware/cad/a12/harness/ear_connector_search/generated/selected-paths.json"
    parent = read(REPO / "hardware/cad/a12/harness/generated/receiver-full-route/analysis.json")
    assert sha(source) == parent["source_sha256"][str(source.relative_to(REPO))]
    selected = read(source)["routes"][0]
    i = selected["native_boundary_indices"]
    original = selected["native_points_mm"][
        i["source_initial_straight_end"] : i["destination_stub_start"] + 1
    ]
    old, new = plan["old_values"], plan["only_overrides"]
    assert set(new) == {"pf_middle", "pf_bend", "pf_stub_start"}
    assert len(original) == len(old["pf_middle"][0]) == len(new["pf_middle"][0])
    for actual, expected in zip(old["pf_middle"][0], original):
        assert math.dist(actual, expected) < 1e-10
    for oldpoint, newpoint in zip(old["pf_middle"][0], new["pf_middle"][0]):
        assert oldpoint[:2] == newpoint[:2]
        assert math.isclose(newpoint[2] - oldpoint[2], 1, abs_tol=1e-12)
    for name in new:
        assert old[name][1] == new[name][1]
    for name in ["pf_bend", "pf_stub_start"]:
        assert old[name][0][:2] == new[name][0][:2]
        assert math.isclose(new[name][0][2] - old[name][0][2], 1, abs_tol=1e-12)
    assert math.dist(new["pf_middle"][0][0], new["pf_bend"][0]) < 1e-10
    assert math.dist(new["pf_middle"][0][-1], new["pf_stub_start"][0]) < 1e-10
    certificate = selected["continuous_radius_certificate"]
    assert certificate["certified"] and certificate["all_unit_tangent_joins_C1"]
    assert certificate["radius_lower_mm"] > certificate["minimum_required_true_centerline_radius_mm"]
    assert len(a["records"]) == 9
    empties = 0
    for name, row in a["records"].items():
        log = (out / (name + ".log")).read_text()
        target = out / (name + ".stl")
        assert row["passed"] and "WARNING" not in log and "ERROR" not in log
        if row["expected_empty"]:
            assert row["returncode"] == 1 and not target.exists()
            assert "Current top level object is empty." in log and row["statistics"] is None
            empties += 1
        else:
            assert row["returncode"] == 0 and "NoError" in log
            assert binary_stl(target) == row["statistics"]
            assert row["statistics"]["volume_mm3"] > 0
            if name == "wire_control":
                assert math.isclose(row["statistics"]["volume_mm3"], 0.008, abs_tol=2e-6)
        command = row["command"]
        definitions = [command[k + 1] for k, v in enumerate(command[:-1]) if v == "-D"]
        for key, value in new.items():
            raw = next(x.split("=", 1)[1] for x in definitions if x.startswith(key + "="))
            assert json.loads(raw) == value
    assert empties == 7
    result = dict(
        scope=__doc__,
        source_hashes_checked=len(a["source_sha256"]),
        artifact_hashes_checked=len(a["artifact_sha256"]),
        all9_actual_native_records_reintegrated=True,
        seven_empty_intersections=True,
        positive_control_mm3=a["records"]["wire_control"]["statistics"]["volume_mm3"],
        original_selected_path_sha256=sha(source),
        original_parent_receipt_sha256=sha(
            REPO / "hardware/cad/a12/harness/generated/receiver-full-route/analysis.json"
        ),
        all_curved_points_only_rigidly_translated=True,
        curve_radius_lower_mm_preserved=certificate["radius_lower_mm"],
        true_radius_requirement_mm_preserved=certificate["minimum_required_true_centerline_radius_mm"],
        both_vertical_extensions_mm=1,
        old_positive_wire_length_upper_mm=selected["wire_length_upper_mm_including_prefix_stub_boardtails"],
        new_positive_wire_length_upper_mm=selected["wire_length_upper_mm_including_prefix_stub_boardtails"]
        + 2,
        unchanged_negative_wire_and_bare_joint_ports=True,
        passed_conditional_local_geometry=True,
        complete_U14_J8_return_wiring_adopted=False,
        new_copper_resistance_bound_or_strain_relief_verified=False,
        physical_qualified=False,
        fabrication_released=False,
        audit_script_sha256=sha(Path(__file__)),
    )
    (ROOT / "wire-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Wire lift:9rawcases/960input hashes and congruent analytic path checked")


if __name__ == "__main__":
    main()
