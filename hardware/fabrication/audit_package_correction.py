"""Independently bound watchdog land revisions; reject incidental circuit edits."""

import argparse
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha
from hardware.fabrication.correct_watchdog_lands import ref
from hardware.fabrication.package_lands import DRB, LIBRARY

ROOT = Path(__file__).resolve().parent


def pad_nets(fp):
    return {str(p[1]):str(first(p,"net")[-1]) for p in children(fp,"pad") if str(p[1]) and children(p,"net")}


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate",required=True)
    parser.add_argument("--review",required=True)
    args = parser.parse_args()
    assert all(s and all(c.isalnum() or c in "-_" for c in s) for s in (args.candidate,args.review))
    candidate, output = [ROOT/"staging"/label for label in (args.candidate,args.review)]
    construction = candidate/"construction.json"
    receipt = json.loads(construction.read_text())
    old_pcb = next(Path(p) for p in receipt["source_sha256"] if p.endswith(".kicad_pcb"))
    old_xml = next(Path(p) for p in receipt["source_sha256"] if p.endswith("netlist.xml"))
    project = next(output.glob("*.kicad_pro"))
    report = json.loads((output/"review.json").read_text())
    assert not native_evidence_errors(project,report)
    old, new = [read_sexpr(p.read_text()) for p in (old_pcb,project.with_suffix(".kicad_pcb"))]
    delta = geometry_delta(old,new)
    assert delta["other_root_geometry_exact"]
    assert all(not any(delta[tag].values()) for tag in ("segment","via","zone"))
    assert not delta["footprint"]["added"] and not delta["footprint"]["removed"]
    before = {ref(p):p for p in children(old,"footprint")}
    after = {ref(p):p for p in children(new,"footprint")}
    targets = {r["ref"] for r in receipt["changes"]}
    assert set(before) == set(after)
    assert set(delta["footprint"]["changed"]) == {str(first(before[r],"uuid")[1]) for r in targets}
    for r in targets:
        a,b = before[r],after[r]
        assert b[1] == LIBRARY+":"+DRB and pad_nets(a) == pad_nets(b)
        for tag in ("at","layer","uuid"):
            assert sexpr(first(a,tag)) == sexpr(first(b,tag))
        assert [sexpr(p) for p in children(a,"property")] == [sexpr(p) for p in children(b,"property")]
    old_parts,old_pins = netlist(old_xml)
    new_parts,new_pins = netlist(output/"netlist.xml")
    assert old_pins == new_pins and set(old_parts) == set(new_parts)
    assert all(old_parts[r].findtext("value") == new_parts[r].findtext("value") for r in old_parts)
    assert {r for r in old_parts if old_parts[r].findtext("footprint") != new_parts[r].findtext("footprint")} == targets
    path = output/"package-correction-review.json"
    assert not path.exists()
    inputs = (old_pcb,old_xml,project.with_suffix(".kicad_pcb"),output/"netlist.xml",output/"review.json",construction,Path(__file__))
    path.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        changed_footprints=sorted(targets),all_original_circuit_values_and_pin_nets_exact=True,
        all_original_component_poses_and_properties_exact=True,all_existing_tracks_vias_and_authored_zones_exact=True,
        native_status=report["status"],uncapped_open_connections=report["uncapped_open_connections"],
        stencil_thermal_via_and_assembly_acceptance_pending=True,physical_qualified=False,
        fabrication_released=False),indent=2)+"\n")
    print("Audited package-only correction",sorted(targets),"circuit and existing copper unchanged")


if __name__ == "__main__":
    run()
