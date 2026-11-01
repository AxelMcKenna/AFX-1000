"""Publish a precise software-layout handoff without releasing fabrication."""

import json
from collections import Counter
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision26.layout import POWER_NETS

from .route_e28 import REPO, WORK, sha


def run():
    native=WORK/"generated/native-closed-control-layout"
    source=WORK/"generated/final-leaf-joins/rail_disconnect.kicad_pcb"
    parent=WORK/"generated/control-wing-return-smoothed/rail_disconnect.kicad_pcb"
    review=json.loads((native/"review.json").read_text())
    drc=json.loads((native/"drc.json").read_text())
    cases=REPO/"hardware/cad/a12/controlled_restart/results"
    positive=cases/"control-wing-positive/result.json"
    receiving=cases/"control-wing-receiving/result.json"
    assert review["uncapped_missing_connections"]==0
    assert not [v for v in drc["violations"] if v["severity"]=="error"]
    assert not drc["schematic_parity"] and review["status"]["counts"]["erc"]==0
    assert review["status"]["all_native_rule_checks_enabled"]
    assert all(json.loads(p.read_text())["clear"] for p in (positive,receiving))
    assert review["manufacturing_process_audit"]["only_one_via_below_030"]
    before,after=[read_sexpr(p.read_text()) for p in (parent,source)]

    def force_items(tree):
        names={str(n[1]):str(n[2]).lstrip("/") for n in children(tree,"net")}
        return Counter(sexpr(n) for kind in ("segment","via") for n in children(tree,kind)
                       if names[str(first(n,"net")[1])] in POWER_NETS)

    assert force_items(before)==force_items(after)
    assert [sexpr(f) for f in children(before,"footprint")]==[sexpr(f) for f in children(after,"footprint")]
    warnings=dict(Counter(v["type"] for v in drc["violations"]))
    paths=[source,native/"rail_disconnect.kicad_pcb",native/"rail_disconnect.kicad_pro",native/"rail_disconnect.kicad_sch",
           native/"review.json",native/"drc.json",native/"erc.json",positive,receiving,native/"closed-top.svg",Path(__file__)]
    report=dict(preferred_project=str(native/"rail_disconnect.kicad_pro"),
        source_sha256={str(p):sha(p) for p in paths},electrical_parts=271,mechanical_footprints=4,
        uncapped_open_connections=0,hard_DRC_errors=0,ERC_findings=0,schematic_parity_findings=0,
        all_native_rule_checks_enabled=True,warnings=warnings,warning_count=sum(warnings.values()),
        force_track_and_via_objects_preserved=True,all_post_wing_footprint_poses_preserved=True,
        conservative_captured_assembly_clearance_passed=True,whole_unit_receiving_qualified=False,
        smaller_via=dict(count=1,net="E28_OUT_READY",land_mm=.5,drill_mm=.2,
            nominal_annular_mm=.15,required_fill_and_cap=True,
            receiving=dict(max_finished_board_mm=1.782,finished_bore_range_mm=[.18,.22],
                min_land_mm=.48,max_radial_registration_mm=.025,factor=1.2,
                worst_aspect_ratio=1.782/.18,required_aspect_capacity_at_least=1.782/.18*1.2,
                worst_annular_mm=(.48-.22)/2-.025,
                manufacturer_min_annular_must_be_at_most=((.48-.22)/2-.025)/1.2),
            manufacturer_accepted=False),
        fabrication_release_gates=["Resolve or justify the153 remaining native warnings",
            "Supplier acceptance of the full eight-layer heavy-copper stackup and filled/capped via process",
            "Fresh filled-power/return resistance, fault-energy, thermal and transient checks after the new drills",
            "Actual-band AUX/input-current and threshold measurements for AX03",
            "Implement the matching AX03 transmitter on the actual P03 board",
            "Complete updated whole-unit mechanical, harness, airflow and prototype receiving checks"],
        physical_qualified=False,fabrication_released=False,native_Mac_CAD_launches=0)
    out=native/"handoff.json"
    assert not out.exists()
    out.write_text(json.dumps(report,indent=2)+"\n")
    pointer=WORK/"CURRENT_LAYOUT.json"
    assert not pointer.exists()
    pointer.write_text(json.dumps(dict(project="generated/native-closed-control-layout/rail_disconnect.kicad_pro",
        handoff="generated/native-closed-control-layout/handoff.json",uncapped_open_connections=0,
        hard_DRC_errors=0,warning_count=report["warning_count"],manufacturing_profile="single-ready-020",
        older_root_PCB_is_a_preserved_parent=True,physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Sealed closed-layout handoff;153 warnings and all physical/fabrication gates remain explicit")


if __name__=="__main__":
    run()
