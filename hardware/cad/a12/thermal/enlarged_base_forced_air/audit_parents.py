"""Source-only FI01 audit, safe while new OpenSCAD execution is paused."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh
from hardware.cad.a12.thermal.enlarged_base_pot.stage import sha, write

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
CP = ROOT.parent / "enlarged_base_pot"
FA = ROOT.parent / "forced_air_prototype"


def audit():
    if (ROOT / "handoff.json").exists():
        raise RuntimeError("Sealed parent audit is read-only; do not recapture it")
    parents = {}
    for p in [CP, FA]:
        h = json.loads((p / "handoff.json").read_text())
        assert all(sha(p / n) == x for n, x in h["files_sha256"].items())
        parents[p.name] = dict(handoff_sha256=sha(p / "handoff.json"), files=len(h["files_sha256"]))
    proof = json.loads((FA / "generated/verification.json").read_text())
    checked = {}
    for n, row in proof["cases"].items():
        log = (FA / "generated" / (n + ".log")).read_text()
        target = FA / "generated" / (n + ".stl")
        assert "WARNING" not in log and "ERROR" not in log
        if n.endswith("_collision"):
            assert (
                row["returncode"] == 1 and "Current top level object is empty." in log and not target.exists()
            )
            checked[n] = dict(empty=True)
        else:
            assert row["returncode"] == 0 and "NoError" in log
            actual = mesh(target)
            assert all(actual[k] == x for k, x in row["statistics"].items())
            checked[n] = dict(empty=False, mesh=actual)
    for group in ["source_sha256", "artifact_sha256"]:
        assert all(sha(REPO / n) == x for n, x in proof[group].items())
    data = json.loads((FA / "generated/analysis.json").read_text())
    line = next(
        l for l in (CP / "generated/parts.scad").read_text().splitlines() if l.startswith("eb_part_pins=")
    )
    pins = json.loads(line.split("=", 1)[1].rstrip(";"))
    removed = set(map(tuple, data["removed_pin_centres_mm"]))
    kept = [p for p in pins if tuple(p) not in removed]
    assert len(pins) == 1037 and len(removed) == 77 and len(kept) == 960
    write(
        ROOT / "foot-screw-source.json",
        dict(
            mpn="Accu SPK-M3-20-A2",
            url="https://www.accu.co.uk/pozi-countersunk-screws/9528-SPK-M3-20-A2",
            source="Independent primary Accu product read2026-10-28",
            length_nominal_mm=20,
            thread_nominal_mm=3,
            pitch_mm=0.5,
            head_OD_mm=5.6,
            head_OD_tolerance_mm=[-0.3, 0],
            head_length_listed_mm=1.65,
            head_length_tolerance_provided=False,
            angle_degrees=90,
            material="A2stainless DIN965Z",
            actual_lot_or_length_runout_or_preload_accepted=False,
        ),
    )
    result = dict(
        scope=__doc__,
        parents=parents,
        FA23raw_records_reintegrated=checked,
        actual_source_CP_pins=1037,
        whole_removed_centres=data["removed_pin_centres_mm"],
        actual_kept_count=960,
        partial_pin_remnants_allowed=False,
        unchanged_manufacturing_foot=True,
        foot_stack=dict(
            screw_nominal_length=20,
            plate=6.2,
            tray_flange=2,
            spacer=6,
            engagement=20 - 6.2 - 2 - 6,
            foot_top=-14.2,
            screw_tip=-20,
            receiving_thread_interval=[-20.00002, -14.19998],
            numerical_endguards_each=0.00002,
            manufacturing_tap_drill_unchanged=True,
            original_foot_translation=-8,
            nominal_bumper_bottom=-36.8,
            nominal_underdeck_table_clearance=10.6,
        ),
        fan_fasteners=dict(
            under_head_z=-27.7,
            nominal_length=20,
            tip_z=-7.7,
            nut_top_z=-9.1,
            nominal_tip_beyond_nut=1.4,
            nominal_tip_to_base_bottom=1.5,
            actual_hardware_not_selected=True,
            source_receiving_gauges_only=True,
        ),
        base_volume_ideal_delta_mm3=-77 * 3 * 3 * 12,
        old_CP_native_base_mm3=json.loads((CP / "generated/verification.json").read_text())["cases"][
            "eb_metal_geometry"
        ]["statistics"]["volume_mm3"],
        initial_audit_before_new_native_execution=True,
        source_R1_PB_Seed_or_current_ledger_not_substituted=True,
        plastic_case_does_not_receive_conditional_metal_wall_lid_credit=True,
        physical_qualified=False,
        thermal_qualified=False,
        fabrication_released=False,
    )
    write(ROOT / "initial-source-audit.json", result)
    print(
        json.dumps(dict(FA_raw_cases=len(checked), kept=len(kept), removed=len(removed), foot_engagement=5.8))
    )


if __name__ == "__main__":
    audit()
