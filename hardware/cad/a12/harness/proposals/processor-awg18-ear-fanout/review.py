"""Exact old-source preservation and actual new port/native-copper validation."""

import csv
import hashlib
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear-wide-access"
REPO = ROOT.parents[5]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reference(f):
    return next(p[2] for p in children(f, "property") if p[1] == "Reference")


def compare(old, new, change):
    before = {reference(f): sexpr(f) for f in children(old, "footprint")}
    after = {reference(f): sexpr(f) for f in children(new, "footprint")}
    assert len(before) == 86 and len(after) == 88 and set(after) - set(before) == {"J14", "J15"}
    assert all(after[k] == v for k, v in before.items())
    assert sorted(sexpr(f) for f in children(new, "footprint") if reference(f) in ["J14", "J15"]) == sorted(
        change["new_footprints"]
    )
    mutations = {c["uuid"]: c for c in change["changes"]}
    assert len(mutations) == 5
    restored = []
    for q in new:
        if isinstance(q, list) and q and q[0] == "footprint" and reference(q) in ["J14", "J15"]:
            continue
        if isinstance(q, list) and children(q, "uuid") and str(first(q, "uuid")[1]) in mutations:
            c = mutations[str(first(q, "uuid")[1])]
            assert sexpr(q) == c["after"]
            restored.append(read_sexpr(c["before"]))
        else:
            restored.append(q)
    assert sexpr(restored) == sexpr(old), "Undeclared original routing/stackup/outline/source edit"


def run(write=True):
    change = json.load(open(ROOT / "generated/design-change.json"))
    old = read_sexpr((SOURCE / "processor_carrier.kicad_pcb").read_text())
    new = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    compare(old, new, change)
    sch = read_sexpr((ROOT / "processor_carrier.kicad_sch").read_text())
    oldsch = read_sexpr((SOURCE / "processor_carrier.kicad_sch").read_text())
    added = set(change["new_symbols"] + change["new_schematic_wire_labels"])
    assert len(added) == 10
    restored = [q for q in sch if not isinstance(q, list) or sexpr(q) not in added]
    assert sexpr(restored) == sexpr(oldsch)
    parts = json.load(open(ROOT / "components.json"))
    oldparts = json.load(open(SOURCE / "components.json"))
    assert len(parts) == 79 and parts[:77] == oldparts
    with (ROOT / "bom.csv").open(newline="") as f:
        bom = list(csv.DictReader(f))
    with (SOURCE / "bom.csv").open(newline="") as f:
        oldbom = list(csv.DictReader(f))
    assert len(bom) == 79 and bom[:77] == oldbom
    for name in ["processor_carrier.kicad_pro", "RMX_E19.kicad_sym", "fp-lib-table", "sym-lib-table"]:
        assert (ROOT / name).read_bytes() == (SOURCE / name).read_bytes(), name
    for p in (SOURCE / "RMX_Carrier.pretty").iterdir():
        assert p.read_bytes() == (ROOT / "RMX_Carrier.pretty" / p.name).read_bytes()
    op, on = netlist(SOURCE / "generated/netlist.xml")
    np, nn = netlist(ROOT / "generated/netlist.xml")
    assert len(op) == 77 and len(np) == 79 and all(nn[k] == v for k, v in on.items())
    assert nn["J14"] == nn["J15"] == {"1": "5V_DIG", "2": "AGND"}
    for ref in ["J14", "J15"]:
        part = next(p for p in parts if p["ref"] == ref)
        row = next(p for p in bom if p["Reference"] == ref)
        fp = next(p for p in children(new, "footprint") if reference(p) == ref)
        assert (
            row["Part_or_value"]
            == part["part"]
            == next(p[2] for p in children(fp, "property") if p[1] == "Value")
        )
        assert row["Footprint"] == part["footprint"] == fp[1]
    native = json.load(open(ROOT / "generated/native.json"))
    assert native["candidate_pcb_sha256"] == sha(ROOT / "processor_carrier.kicad_pcb") and all(
        type(v) is int and v == 0 for v in native["counts"].values()
    )
    for group in ["source_sha256", "artifact_sha256"]:
        for rel, h in native[group].items():
            assert sha(REPO / rel) == h, ("Stale native receipt", rel)
    orientation = json.load(open(ROOT / "generated/native-orientation.json"))
    assert orientation["source_pcb_sha256"] == sha(ROOT / "processor_carrier.kicad_pcb") and orientation[
        "source_code_sha256"
    ] == sha(ROOT / "native_orientation.py")
    assert len(orientation["ports"]) == 2 and not orientation["front_courtyard_intersections"]
    copper = json.load(open(ROOT / "generated/native-metal-clearance.json"))
    neck = json.load(open(ROOT / "generated/native-neck.json"))
    assert copper["source_pcb_sha256"] == sha(ROOT / "processor_carrier.kicad_pcb")
    assert (
        copper["actual_filled_pcb_sha256"]
        == neck["source_filled_pcb_sha256"]
        == sha(ROOT / "generated/filled.kicad_pcb")
    )
    assert copper["source_code_sha256"] == sha(ROOT / "native_copper.py") and neck[
        "source_code_sha256"
    ] == sha(ROOT / "native_neck.py")
    assert copper["actual_all_four_layer_copper_clear"] and len(copper["rows"]) == 4
    assert all(
        r[k] == 0
        for r in copper["rows"]
        for k in ["pad_intersection_mm2", "track_via_intersection_mm2", "filled_copper_intersection_mm2"]
    )
    active = [r for r in neck["rows"] if r["centre_line_actual_copper"]["total_width_mm"] > 0]
    assert {(r["layer"], r["net"]) for r in active} == {
        ("F.Cu", "5V_DIG"),
        ("In1.Cu", "AGND"),
        ("In2.Cu", "5V_DIG"),
        ("B.Cu", "5V_DIG"),
    }
    for r in active:
        assert (
            r["probes_connected_before_cut"]
            and r["probes_connected_after_cut"]
            and r["probes_connected_after_top_cut_only"]
            and not r["probes_connected_after_both_cuts"]
        )
        assert all(r["source_to_output_probes_connected"].values())
    allocations = {"Seed": 1.0, "LED": 0.764, "bypass": 0.14, "monitor": 0.08, "reserve_unassigned": 0.416}
    assert abs(sum(allocations.values()) - 2.4) < 1e-12
    report = dict(
        candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        filled_pcb_sha256=sha(ROOT / "generated/filled.kicad_pcb"),
        native_counts=native["counts"],
        original86FP_and77parts_pinmaps_routing_stackup_exact=True,
        total_FP=88,
        total_schematic_parts=79,
        only_declared_edges_zone_and_two_ports_added=True,
        actual_native_horizontal_pad_transform_verified=True,
        native_front_courtyard_intersections=[],
        nominal_right_pad_land_to_edge_mm=0.8,
        unchanged_min_copper_edge_rule_mm=0.5,
        all4_layer_full_H9_disk_copper_clear=True,
        actual_source_output_flood_connectivity_all4_active_layers=True,
        input_current_allocation_a=allocations,
        current_allocations_are_not_guaranteed_native_loads=True,
        old_J1_unfitted_service=True,
        unassigned_reserve_has_no_connector=True,
        source_to_load_PDN_solved=False,
        parent_MCAD_or_PDN_pass_inherited=False,
        whole_solder_service_wire_fit_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    if write:
        (ROOT / "generated/package-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Validated79parts/88FP/native0/source-outputflood", report["candidate_pcb_sha256"])
    return report


if __name__ == "__main__":
    run()
