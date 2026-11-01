"""Independent raw-result review of the fresh pinned-Linux R1/CP01 fit packet."""

import hashlib
import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
PACKET = REPO / "hardware/cad/a12/enclosure_growth/r1_local"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def main():
    h = read(PACKET / "handoff.json")
    assert len(h["files_sha256"]) == 132
    for n, expected in h["files_sha256"].items():
        assert sha(PACKET / n) == expected, n
    a = read(PACKET / "generated/verification.json")
    assert a["complete_required_case_set"] and a["all_native_local_checks_clear"]
    assert len(a["cases"]) == 15 and not a["changed_inputs"] and not a["executable_changed"]
    for n, expected in {**a["source_sha256"], **a["original_inputs_sha256"], **a["artifact_sha256"]}.items():
        p = Path(n)
        if not p.is_absolute():
            p = REPO / p
        assert sha(p) == expected, p
    empties, controls = 0, 0
    rows = {}
    for name, row in a["cases"].items():
        target = PACKET / "generated" / (name + ".stl")
        log = (PACKET / "generated" / (name + ".log")).read_text()
        assert row["clear"] and not row["errors"]
        assert "ERROR" not in log and "WARNING" not in log
        if row["statistics"] is None:
            assert (
                row["returncode"] == 1 and "Current top level object is empty." in log and not target.exists()
            )
            empties += 1
            rows[name] = dict(strict_empty=True)
        else:
            actual = binary_stl(target)
            assert row["returncode"] == 0 and "NoError" in log
            stored = row["statistics"]
            assert actual["triangles"] == stored["triangles"]
            assert actual["min_mm"] == stored["min_mm"] and actual["max_mm"] == stored["max_mm"]
            assert math.isclose(actual["volume_mm3"], stored["volume_mm3"], rel_tol=1e-11, abs_tol=1e-9)
            assert stored["closed_oriented_boundary"] and not stored["degenerate_triangles_excluded"]
            if name != "receiving_geometry":
                assert math.isclose(actual["volume_mm3"], 0.008, abs_tol=2e-6)
                controls += 1
            else:
                assert math.isclose(actual["volume_mm3"], 4.18 * 7.86, abs_tol=0.0001)
            rows[name] = dict(actual_statistics=actual)
    assert (empties, controls) == (10, 4)
    assert a["external_clearance_mm"] == 0.25 and a["PCB_Z_sweep_mm"] == 0.2
    assert a["only_old_R1_row_excluded"] and a["only_own_E19_PCB_excluded_from_external_margin"]
    for flag in ["physical_qualified", "thermal_qualified", "whole_unit_qualified", "fabrication_released"]:
        assert not h[flag]
    result = dict(
        scope=__doc__,
        packet_handoff_sha256=sha(PACKET / "handoff.json"),
        packet_hashes_checked=132,
        all15_raw_records_reintegrated=True,
        ten_empty_intersections=True,
        four_positive_control_volumes_checked=True,
        actual_source_inputs_unchanged=True,
        native_rows=rows,
        native_tool_image=a["tool_image"],
        native_tool_binary_sha256=a["tool_binary_sha256"],
        new_native_commands_run=False,
        physical_thermal_full_unit_qualified=False,
        script_sha256=sha(Path(__file__)),
    )
    (ROOT / "local-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print("R1local:132hashes/15actualrecords reviewed;10empty+4controls")


if __name__ == "__main__":
    main()
