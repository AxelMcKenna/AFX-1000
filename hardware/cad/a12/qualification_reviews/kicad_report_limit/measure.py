"""Measure uncapped native connectivity independently of DRC marker limits."""

import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cases = [
        ("NF03P231", "hardware/qualification/boards/startup_negative_circuit/placement/negative_startup_placement.kicad_pcb", None),
        ("NF04R233", "hardware/qualification/boards/startup_negative_circuit/ready_integration/pcb/negative_startup_ready.kicad_pcb", None),
        ("NF06P265_unrouted", "hardware/qualification/boards/startup_negative_circuit/physical_layout/negative_startup_physical.kicad_pcb", "hardware/qualification/boards/startup_negative_circuit/physical_layout/generated/functional-drc.json"),
        ("NF06P265_first_signal_trial", "hardware/qualification/boards/startup_negative_circuit/physical_layout/routing/first-six-layer-02/output.kicad_pcb", "hardware/qualification/boards/startup_negative_circuit/physical_layout/routing/first-six-layer-02/output-drc.json"),
        ("NF06P265_literal_power", "hardware/qualification/boards/startup_negative_circuit/physical_layout/routing/power-stitches/input.kicad_pcb", "hardware/qualification/boards/startup_negative_circuit/physical_layout/routing/power-stitches/input-drc.json"),
        ("FPC_M1", "hardware/qualification/boards/fan_health/composite_mount/fan_power_health.kicad_pcb", "hardware/qualification/boards/fan_health/composite_mount/generated/drc.json"),
        ("FPC_M2", "hardware/qualification/boards/fan_health/composite_nf_branch/fan_power_health.kicad_pcb", "hardware/qualification/boards/fan_health/composite_nf_branch/generated/final-drc.json"),
    ]
    rows = []
    for label, name, drc_name in cases:
        path = REPO / name
        before = sha(path)
        board = pcbnew.LoadBoard(str(path))
        board.BuildConnectivity()
        conn = board.GetConnectivity()
        conn.RecalculateRatsnest()
        count = conn.GetUnconnectedCount(False)
        assert sha(path) == before
        drc = REPO / drc_name if drc_name else None
        marker_count = len(json.loads(drc.read_text())["unconnected_items"]) if drc and drc.is_file() else None
        if marker_count is not None:
            assert marker_count == min(count, 499), (label, count, marker_count)
        rows.append(dict(label=label, PCB=name, PCB_sha256=before,
                         actual_uncapped_native_missing_connections=count,
                         DRC_report=drc_name if drc and drc.is_file() else None,
                         DRC_report_sha256=sha(drc) if drc and drc.is_file() else None,
                         reported_DRC_missing_connection_markers=marker_count,
                         report_truncated=marker_count is not None and marker_count < count,
                         source_PCB_unchanged=True))
    result = dict(native_version=pcbnew.GetBuildVersion(), source_script_sha256=sha(Path(__file__)),
                  official_primary_source="https://gitlab.com/kicad/code/kicad/-/raw/10.0.7/pcbnew/drc/drc_engine.cpp",
                  primary_source_lines={"constants": [58, 59], "RunTests_limits": [832, 839]},
                  stock_per_type_limits=dict(clearance=499, unconnected_items=499, other_types=199),
                  all_track_errors_does_not_remove_per_type_limits=True,
                  uncapped_method="BOARD.BuildConnectivity; CONNECTIVITY_DATA.RecalculateRatsnest; GetUnconnectedCount(False)",
                  zero_finding_DRC_is_not_invalidated_by_a_positive_marker_limit=True,
                  rows=rows, physical_qualified=False, fabrication_released=False)
    out = ROOT / "measurements.json"
    assert not out.exists()
    out.write_text(json.dumps(result, indent=2) + "\n")
    print([(r["label"], r["actual_uncapped_native_missing_connections"]) for r in rows])


if __name__ == "__main__":
    main()
