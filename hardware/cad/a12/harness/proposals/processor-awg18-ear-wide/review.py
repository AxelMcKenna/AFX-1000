"""Exact source preservation and current full-native/copper/topology evidence."""

import hashlib
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear-supported"
REPO = ROOT.parents[5]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reference(f):
    return next(p[2] for p in children(f, "property") if p[1] == "Reference")


def compare(old, new, change):
    before = {reference(f): sexpr(f) for f in children(old, "footprint")}
    after = {reference(f): sexpr(f) for f in children(new, "footprint")}
    assert len(before) == len(after) == 86 and before == after
    assert [sexpr(t) for t in children(old, "segment")] == [sexpr(t) for t in children(new, "segment")]
    assert [sexpr(t) for t in children(old, "via")] == [sexpr(t) for t in children(new, "via")]
    mutations = {x["uuid"]: x for x in change["edge_changes"] + change["zone_changes"]}
    assert len(mutations) == 4
    restored = []
    for q in new:
        if isinstance(q, list) and children(q, "uuid") and str(first(q, "uuid")[1]) in mutations:
            c = mutations[str(first(q, "uuid")[1])]
            assert sexpr(q) == c["after"]
            restored.append(read_sexpr(c["before"]))
        else:
            restored.append(q)
    assert sexpr(restored) == sexpr(old), "Undeclared source node/stackup/object edit"


def run(write=True):
    old = read_sexpr((SOURCE / "processor_carrier.kicad_pcb").read_text())
    new = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    change = json.loads((ROOT / "generated/design-change.json").read_text())
    compare(old, new, change)
    for p in SOURCE.iterdir():
        if p.is_dir() and p.suffix == ".pretty":
            for q in p.rglob("*"):
                if q.is_file():
                    assert q.read_bytes() == (ROOT / p.name / q.relative_to(p)).read_bytes(), q
        elif (
            p.is_file()
            and p.name != "processor_carrier.kicad_pcb"
            and (
                p.suffix in [".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"]
                or p.name in ["components.json", "bom.csv", "fp-lib-table", "sym-lib-table"]
            )
        ):
            assert p.read_bytes() == (ROOT / p.name).read_bytes(), p
    oa, on = netlist(SOURCE / "generated/netlist.xml")
    na, nn = netlist(ROOT / "generated/netlist.xml")
    assert len(oa) == len(na) == 77 and on == nn
    native = json.loads((ROOT / "generated/native.json").read_text())
    assert native["candidate_pcb_sha256"] == sha(ROOT / "processor_carrier.kicad_pcb")
    assert all(type(x) is int and x == 0 for x in native["counts"].values())
    for group in ["source_sha256", "artifact_sha256"]:
        for rel, h in native[group].items():
            assert sha(REPO / rel) == h, ("Stale native receipt", rel)
    copper = json.loads((ROOT / "generated/native-metal-clearance.json").read_text())
    neck = json.loads((ROOT / "generated/native-neck.json").read_text())
    assert copper["source_pcb_sha256"] == sha(ROOT / "processor_carrier.kicad_pcb")
    assert (
        copper["actual_filled_pcb_sha256"]
        == neck["source_filled_pcb_sha256"]
        == sha(ROOT / "generated/filled.kicad_pcb")
    )
    assert copper["source_code_sha256"] == sha(ROOT / "native_copper.py")
    assert neck["source_code_sha256"] == sha(ROOT / "native_neck.py")
    assert copper["actual_all_four_layer_copper_clear"]
    assert len(copper["rows"]) == 4 and all(
        r[k] == 0
        for r in copper["rows"]
        for k in ["pad_intersection_mm2", "track_via_intersection_mm2", "filled_copper_intersection_mm2"]
    )
    active = [r for r in neck["rows"] if r["new_top_corridor_actual_copper"]["total_width_mm"] > 0]
    assert {(r["layer"], r["net"]) for r in active} == {
        ("F.Cu", "5V_DIG"),
        ("In1.Cu", "AGND"),
        ("In2.Cu", "5V_DIG"),
        ("B.Cu", "5V_DIG"),
    }
    for r in active:
        assert r["probes_connected_before_cut"] and r["probes_connected_after_cut"]
        assert r["probes_connected_after_top_cut_only"] and not r["probes_connected_after_both_cuts"]
        assert abs(r["new_top_corridor_actual_copper"]["total_width_mm"] - 2.893916) < 1e-8
    report = dict(
        parent_source_sha256=sha(SOURCE / "processor_carrier.kicad_pcb"),
        candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        filled_pcb_sha256=sha(ROOT / "generated/filled.kicad_pcb"),
        all86_complete_footprints_exact=True,
        all77_pinmaps_exact=True,
        all_tracks_vias_stackup_H9_keepout_exact=True,
        only_declared3_edge_and1_zone_contracts_changed=True,
        native_counts=native["counts"],
        full_H9_disk_actual_copper_clear_all4layers=True,
        actual_parallel_top_bypass_width_mm=2.893916,
        old_gate_width_mm=0.779689133,
        independent_cut_controls_prove_parallel_paths=True,
        added_board_area_mm2=70,
        original_J1_unfitted_service=True,
        new_fanout_ports=False,
        parent_PDN_inherited=False,
        full_PDN_solved=False,
        new_MCAD_passed=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    if write:
        (ROOT / "generated/package-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Verified86originalFP/77pinmaps/fullnative/topology", report["candidate_pcb_sha256"])
    return report


if __name__ == "__main__":
    run()
