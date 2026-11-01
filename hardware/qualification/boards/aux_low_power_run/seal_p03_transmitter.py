"""Bind the paired source/receiver contract and exact strict-source conservation."""

import copy
import hashlib
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

from .p03_contract import interface

REPO = Path(__file__).resolve().parents[4]
WORK = REPO/"hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def objects(tree, kinds):
    return {str(first(n, "uuid")[1]): n for kind in kinds for n in children(tree, kind)}


def run():
    native = WORK/"generated/native-closed-transmitter"
    strict = WORK.parent/"strict-native-centering"
    rx = REPO/"hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-signal-stub-cleanup-06"
    assert not (native/"handoff.json").exists() and not (WORK/"CURRENT_LAYOUT.json").exists()
    result = json.loads((native/"review.json").read_text())
    assert result["status"]["native_closed"] and result["uncapped_missing_connections"] == 0
    assert result["electrical_parts"] == 264 and result["native_footprints"] == 274
    assert all(sha(Path(p)) == digest for p, digest in result["source_sha256"].items())
    assert sha(native/"power_p03.kicad_pcb") == result["checked_PCB_sha256"]
    assert sha(native/"power_p03.kicad_pro") == result["checked_project_sha256"]
    parent, final = [read_sexpr(p.read_text()) for p in (strict/"power_p03.kicad_pcb", native/"power_p03.kicad_pcb")]
    old, new = [objects(t, ("segment", "via")) for t in (parent, final)]
    assert len(children(parent,"via")) == 1254 and len(children(parent,"footprint")) == 266
    removed = set(old)-set(new)
    assert all(first(old[key], "net")[1] == "/POWER_RUN" for key in removed)
    assert all(sexpr(old[key]) == sexpr(new[key]) for key in set(old) & set(new)), "Original copper edited"
    assert all(key in new for key, item in old.items() if item[0] == "via")
    old_fp, new_fp = [objects(t, ("footprint",)) for t in (parent, final)]
    assert set(old_fp) <= set(new_fp) and len(new_fp)-len(old_fp) == 8
    for key, previous in old_fp.items():
        expected = copy.deepcopy(previous)
        name = next(p[2] for p in children(expected, "property") if p[1] == "Reference")
        if name == "J106":
            first(next(p for p in children(expected, "pad") if p[1] == "3"), "net")[1] = "/POWER_RUN_E28_LEAF"
        assert sexpr(expected) == sexpr(new_fp[key]), name
    for tag in ("general", "layers", "setup"):
        assert sexpr(first(parent, tag)) == sexpr(first(final, tag)), tag
    for tag in ("gr_line", "gr_arc", "gr_poly", "group"):
        assert [sexpr(n) for n in children(parent, tag)] == [sexpr(n) for n in children(final, tag)]
    zones = []
    for tree in (parent, final):
        zones.append({str(first(z, "uuid")[1]): sexpr([n for n in z if not
            (isinstance(n, list) and n and n[0] in ("filled_polygon", "fill_segments"))]) for z in children(tree, "zone")})
    assert zones[0] == zones[1], "Zone rules or keepouts changed"
    p03_parts, p03_pins = netlist(native/"netlist.xml")
    e28_parts, e28_pins = netlist(rx/"netlist.xml")
    mapping = interface(p03_parts, p03_pins, e28_parts, e28_pins)
    bypass_path = native/"local-bypass-inventory.json"
    bypass = json.loads(bypass_path.read_text())
    assert len(bypass["local_paths"]) == 4 and all(p["actual_authored_and_barrel_path_found"] for p in bypass["local_paths"])
    assert all(sha(Path(p)) == digest for p,digest in bypass["source_sha256"].items())
    assert len(bypass["new_drills_overlapping_SMD_copper"]) == 5
    rx_review = json.loads((rx/"review.json").read_text())
    assert rx_review["uncapped_missing_connections"] == 0 and rx_review["status"]["all_native_rule_checks_enabled"]
    assert not [v for v in json.loads((rx/"drc.json").read_text())["violations"] if v["severity"] == "error"]
    assert json.loads((REPO/"hardware/validation/board-qualification/NATIVE-CAD-STOP.json").read_text())["native_cad_launches_disabled"]
    assert (REPO/".rmx-audio-output-paused").exists()
    paths = [native/name for name in ("power_p03.kicad_pcb", "power_p03.kicad_pro", "power_p03.kicad_sch", "power_p03.kicad_dru",
        "review.json", "drc.json", "erc.json", "netlist.xml", "closed-top.svg", "svg-review.json")]
    paths += [strict/"power_p03.kicad_pcb", strict/"README.md", strict/"generated/source-delta.json", strict/"generated/six-front-paths-new.json",
              rx/"netlist.xml", rx/"review.json", rx/"drc.json", Path(__file__), Path(__file__).with_name("p03_contract.py"), bypass_path]
    paths += [WORK/"generated"/p for p in ("integration.json", "placement/placement.json", "local-fanout/fanout.json",
             "strict-composition/composition.json", "local-bypass/bypass.json", "closed-transmitter/cleanup.json")]
    record = dict(source_sha256={str(p): sha(p) for p in paths}, preferred_project=str(native/"power_p03.kicad_pro"),
        electrical_parts=264, mechanical_footprints=10, uncapped_open_connections=0, DRC_errors=0, DRC_warnings=0,
        ERC_findings=0, schematic_parity_findings=0, all_native_rule_checks_enabled=True,
        strict_source_track_and_via_objects_exact_except_unused_RUN_removals=True,
        removed_strict_source_unused_RUN_track_UUIDs=sorted(removed),
        all_original_1254_vias_exact=True, all_original_266_footprints_exact_except_J106_3_net=True,
        original_R113_PG_switch_and_internal_RUN_pin_contract_preserved=True,
        board_outline_mounts_stackup_rules_keepouts_unchanged=True,
        nominal_board_mm=[160, 45, 1.6], added_electrical_parts=8, source_cell_on_front=True,
        local_bypass_paths=bypass["local_paths"],
        new_drills_overlapping_SMD_copper=bypass["new_drills_overlapping_SMD_copper"],
        new_via_process_drawing_metadata_reconciled=False,
        logical_four_wire_map=mapping, physical_harness_qualified=False,
        physical_connector_selection_open="P03 keyed2.50mm XH4; E28 J5/J9 generic2.54mm headers; wire order, keying, mating and strain relief unqualified",
        paired_E28_remaining_warnings=52,
        inherited_strict_geometry_limits=dict(two_P19_SRC_local_necks_mm=[.333542, .8, .6],
            old_current_and_thermal_qualification_inherited=False, diagnostic_point2A_not_a_qualified_current_limit=True),
        receiving_actual_band_AUP_current_and_threshold_limits_qualified=False,
        whole_unit_mechanical_qualified=False, physical_qualified=False, fabrication_released=False,
        native_Mac_CAD_launches=0,
        release_gates=["E28 remaining52 force/return warnings", "Refreshed actual PDN, ground, thermal and fault-energy extraction",
            "Independent hot startup, partial-power, line-short/open and loaded cutoff measurements",
            "Actual-band AUX/input-current and Schmitt threshold receiving qualification",
            "Supplier acceptance and drawing/metadata reconciliation of C50 and all via processes",
            "Complete keyed harness, new component receiving fit, airflow and prototype bring-up"])
    (native/"handoff.json").write_text(json.dumps(record, indent=2)+"\n")
    (WORK/"CURRENT_LAYOUT.json").write_text(json.dumps(dict(project="generated/native-closed-transmitter/power_p03.kicad_pro",
        handoff="generated/native-closed-transmitter/handoff.json", root_PCB_is_an_incomplete_staging_parent=True,
        uncapped_open_connections=0, all_native_rule_findings=0, physical_qualified=False, fabrication_released=False), indent=2)+"\n")
    print("Sealed264-part P03 source: zero native findings; exact strict-source power copper and cross-board pin contract verified")


if __name__ == "__main__":
    run()
