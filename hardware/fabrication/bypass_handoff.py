"""Independent physical/circuit audit and source-bound development handoff."""

import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT.parents[1]/"hardware/electronics/sequenced_bypass"
PLACEMENT = ROOT/"staging/bypass-placement-native-04"
CHECKED = ROOT/"staging/bypass-closed-native-03"


def ref(fp):
    return next(str(p[2]) for p in children(fp,"property") if p[1] == "Reference")


def run():
    output = CHECKED/"handoff.json"
    assert not output.exists()
    project = CHECKED/"sequenced_bypass.kicad_pro"
    report = json.loads((CHECKED/"review.json").read_text())
    assert not native_evidence_errors(project,report) and report["status"]["native_closed"]
    old_pcb = PLACEMENT/"sequenced_bypass.kicad_pcb"
    pcb = project.with_suffix(".kicad_pcb")
    old,new = [read_sexpr(p.read_text()) for p in (old_pcb,pcb)]
    delta = geometry_delta(old,new)
    before,after = [{ref(fp):fp for fp in children(tree,"footprint")} for tree in (old,new)]
    assert len(before) == len(after) == 59 and set(before) == set(after)
    assert not delta["footprint"]["added"] and not delta["footprint"]["removed"]
    assert set(delta["footprint"]["changed"]) == {str(first(before["C1"],"uuid")[1])}
    assert delta["other_root_geometry_exact"] and not any(delta["zone"].values())
    assert not delta["segment"]["removed"] and not delta["via"]["removed"]
    assert list(map(float,first(before["C1"],"at")[1:3])) == list(map(float,first(after["C1"],"at")[1:3])) == [54,16]
    assert float(first(after["C1"],"at")[3]) == 180
    for r in before:
        assert before[r][1] == after[r][1]
        for tag in ("property","layer"):
            assert [sexpr(p) for p in children(before[r],tag)] == [sexpr(p) for p in children(after[r],tag)]
    original_parts,original_pins = netlist(BASELINE/"generated/netlist.xml")
    actual,actual_pins = netlist(CHECKED/"netlist.xml")
    assert len(original_parts) == len(actual) == 55 and original_pins == actual_pins
    assert all(original_parts[r].findtext("value") == actual[r].findtext("value") for r in actual)
    assert {r for r in actual if original_parts[r].findtext("footprint") != actual[r].findtext("footprint")} == {"U1","U3"}
    assert len(children(new,"segment")) == 406 and len(children(new,"via")) == 64
    assert all(float(first(t,"width")[1]) >= .2 for t in children(new,"segment"))
    assert all(float(first(v,"drill")[1]) >= .3 for v in children(new,"via"))
    assert {str(first(t,"layer")[1]) for t in children(new,"segment")} <= {"F.Cu","B.Cu"}
    native_files = [p for p in CHECKED.rglob("*") if p.is_file() and p.suffix != ".kicad_prl"]
    inputs = [old_pcb,BASELINE/"generated/netlist.xml",ROOT/"package-contract.json",Path(__file__),*native_files]
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        actual_electrical_parts=55,actual_footprints_including_mounts=59,segments=406,through_vias=64,
        all_original_E11_circuit_pin_nets_and_values_exact=True,
        only_original_footprint_ID_changes=["U1","U3"],only_placement_pose_change="C1 rotation0to180; same position",
        both_authored_power_planes_and_board_geometry_exact=True,minimum_track_mm=.2,minimum_drill_mm=.3,
        no_signal_tracks_on_In1_or_In2=True,native_status=report["status"],
        visual_top_and_bottom_copper_review=True,
        inspection_notes=["Mount references at the upper edge need placement within the future assembly drawing margin",
            "Audio, coil-driver and timing/logic placement are separate; installed harness/grounding/noise qualification remains open"],
        board_size_mm=[110,55,1.6],native_Mac_CAD_launches=0,
        exact_passive_MPNs_and_production_connectors_selected=False,installed_fit_qualified=False,
        stack_stencil_and_assembly_accepted=False,physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("E11 handoff:55 exact circuit parts,59 footprints,406 segments,64 vias;all native counts zero")


if __name__ == "__main__":
    run()
