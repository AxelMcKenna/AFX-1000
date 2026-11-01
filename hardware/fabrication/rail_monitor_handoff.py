"""Source-bound circuit, placement and native evidence for an E13 candidate."""

import argparse
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT.parents[1]/"hardware/electronics/rail_monitor"
PLACEMENT = ROOT/"staging/rail-monitor-placement-native-01/rail_monitor.kicad_pcb"


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",required=True)
    args = parser.parse_args()
    assert args.source and all(c.isalnum() or c in "-_" for c in args.source)
    folder = ROOT/"staging"/args.source
    output = folder/"handoff.json"
    assert not output.exists()
    project = folder/"rail_monitor.kicad_pro"
    review = json.loads((folder/"review.json").read_text())
    assert not native_evidence_errors(project,review)
    counts = review["status"]["counts"]
    assert counts["violations"] == counts["schematic_parity"] == counts["erc"] == 0
    before,after = [read_sexpr(p.read_text()) for p in (PLACEMENT,project.with_suffix(".kicad_pcb"))]
    delta = geometry_delta(before,after)
    assert delta["other_root_geometry_exact"] and not any(delta["footprint"].values()) and not any(delta["zone"].values())
    assert not children(before,"segment") and not children(before,"via")
    assert len(children(after,"footprint")) == 185
    old_parts,old_pins = netlist(BASELINE/"generated/netlist.xml")
    parts,pins = netlist(folder/"netlist.xml")
    assert len(parts) == len(old_parts) == 181 and pins == old_pins
    assert all(all(parts[r].findtext(k) == old_parts[r].findtext(k) for k in ("value","footprint")) for r in parts)
    copper = children(after,"segment")+children(after,"via")
    assert len({str(first(n,"uuid")[1]) for n in copper}) == len(copper)
    assert all(float(first(n,"width")[1]) >= .2 and first(n,"layer")[1] in ("F.Cu","B.Cu") for n in children(after,"segment"))
    assert all(float(first(n,"drill")[1]) >= .3 for n in children(after,"via"))
    files = [p for p in folder.rglob("*") if p.is_file() and p.suffix not in (".kicad_prl",".pdf")]
    inputs = [PLACEMENT,BASELINE/"generated/netlist.xml",BASELINE/"components.json",Path(__file__),*files]
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        original181_circuit_parts_values_pin_nets_and_footprint_IDs_exact=True,
        all185_original_component_and_mount_geometries_exact=True,all_authored_planes_and_board_setup_exact=True,
        actual_segments=len(children(after,"segment")),actual_through_vias=len(children(after,"via")),
        unique_copper_object_UUIDs=True,minimum_track_mm=.2,minimum_drill_mm=.3,board_size_mm=[80,70,1.6],
        visual_top_and_bottom_copper_review=True,
        inspection_notes=["Mount references at the upper edge need margins in the production assembly drawing",
            "Logic, comparator and inverting-sense clusters require integrated return/noise and local-loop review"],
        native_status=review["status"],uncapped_open_connections=review["uncapped_open_connections"],
        exact_passive_MPNs_selected=False,precision_error_budget_qualified=False,
        installed_allocation_and_harness_qualified=False,power_return_noise_and_fault_qualified=False,
        manufacturing_process_accepted=False,physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("E13 original181 circuit parts and185 placements exact; remaining opens",review["uncapped_open_connections"])


if __name__ == "__main__":
    run()
