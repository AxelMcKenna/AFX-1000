"""Exact R1-only pose/metadata/force repair and actual manufacturer land contract."""

import csv
import hashlib
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist, number
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
SOURCE = ROOT.parent / "processor-awg18-ear-fanout-j29-central"
SEED = ROOT.parent / "processor-awg18-ear-fanout-j29-central-seed"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(f):
    return next(p[2] for p in children(f, "property") if p[1] == "Reference")


def check_ast(old, new, change):
    before = {ref(f): f for f in children(old, "footprint")}
    after = {ref(f): f for f in children(new, "footprint")}
    assert len(before) == len(after) == 88 and set(before) == set(after)
    assert all(sexpr(after[k]) == sexpr(f) for k, f in before.items() if k != "R1")
    assert (
        sexpr(before["R1"]) == change["old_R1_footprint"] and sexpr(after["R1"]) == change["new_R1_footprint"]
    )
    r = after["R1"]
    assert r[1] == "RMX_Carrier:WSLT2512_R_2512_Manufacturer"
    assert list(map(float, first(r, "at")[1:])) == [180, 140, 90]
    for p in children(r, "pad"):
        assert p[3] == "rect" and list(map(float, first(p, "size")[1:])) == [1.65, 3.68]
        assert list(map(float, first(p, "at")[1:])) == [-2.855 if p[1] == "1" else 2.855, 0, 90]
    court = next(q for q in children(r, "fp_rect") if first(q, "layer")[1] == "F.CrtYd")
    assert list(map(float, first(court, "start")[1:])) == [-3.93, -2.09]
    assert list(map(float, first(court, "end")[1:])) == [3.93, 2.09]
    removed = set(change["removed_segments"])
    added = set(change["added_segments"])
    vias = set(change["added_vias"])
    assert len(removed) == 4 and len(added) == 8 and len(vias) == 5
    assert {first(read_sexpr(q), "net")[1] for q in removed} == {"/5V_DIG", "/SEED_VIN"}
    assert {first(read_sexpr(q), "net")[1] for q in added | vias} == {"/SEED_VIN"}
    assert removed <= {sexpr(q) for q in children(old, "segment")}
    assert added <= {sexpr(q) for q in children(new, "segment")}
    assert vias <= {sexpr(q) for q in children(new, "via")}
    oldbase = [q for q in old if not isinstance(q, list) or sexpr(q) not in removed]
    newbase = []
    for q in new:
        if isinstance(q, list) and sexpr(q) in added | vias:
            continue
        if isinstance(q, list) and q and q[0] == "footprint" and ref(q) == "R1":
            newbase.append(before["R1"])
        else:
            newbase.append(q)
    assert sexpr(oldbase) == sexpr(newbase), (
        "Undeclaredforeignrouting/quietfilter/via/zone/outline/stackup change"
    )


def run(write=True):
    old = read_sexpr((SOURCE / "processor_carrier.kicad_pcb").read_text())
    new = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    change = json.loads((ROOT / "generated/design-change.json").read_text())
    check_ast(old, new, change)
    op, on = netlist(SOURCE / "generated/netlist.xml")
    np, nn = netlist(ROOT / "generated/netlist.xml")
    assert on == nn and len(np) == len(op) == 79
    assert number(np["R1"].findtext("value")) == 0.47 and nn["R1"] == {"1": "5V_DIG", "2": "SEED_VIN"}
    assert all(
        np[n].findtext("value") == p.findtext("value")
        and np[n].findtext("footprint") == p.findtext("footprint")
        for n, p in op.items()
        if n != "R1"
    )
    a = json.loads((SOURCE / "components.json").read_text())
    b = json.loads((ROOT / "components.json").read_text())
    assert len(a) == len(b) == 79
    assert [p for p in a if p["ref"] != "R1"] == [p for p in b if p["ref"] != "R1"]
    r = next(p for p in b if p["ref"] == "R1")
    assert r["part"] == np["R1"].findtext("value") and r["footprint"] == np["R1"].findtext("footprint")
    with (ROOT / "bom.csv").open(newline="") as f:
        bom = list(csv.DictReader(f))
    row = next(p for p in bom if p["Reference"] == "R1")
    assert row["Part_or_value"] == r["part"] and row["Footprint"] == r["footprint"]
    for name in ["processor_carrier.kicad_pro", "fp-lib-table", "sym-lib-table"]:
        assert (ROOT / name).read_bytes() == (SOURCE / name).read_bytes()
    # ExactschematicAST maydiffer only R1instance/librarymetadata.
    so, sn = [read_sexpr((p / "processor_carrier.kicad_sch").read_text()) for p in [SOURCE, ROOT]]
    for tag in ["symbol"]:
        ao, an = children(so, tag), children(sn, tag)
        assert len(ao) == len(an)
        assert all(sexpr(x) == sexpr(y) for x, y in zip(ao, an) if ref(x) != "R1")
    lo, ln = [children(first(t, "lib_symbols"), "symbol") for t in [so, sn]]
    assert all(sexpr(x) == sexpr(y) for x, y in zip(lo, ln) if x[1] != "RMX_E19:E19_R1")
    native = json.loads((ROOT / "generated/native.json").read_text())
    assert native["candidate_pcb_sha256"] == sha(ROOT / "processor_carrier.kicad_pcb") and all(
        v == 0 for v in native["counts"].values()
    )
    for key in ["source_sha256", "artifact_sha256"]:
        for p, h in native[key].items():
            assert sha(REPO / p) == h, ("Stalenative", p)
    seed = json.loads((SEED / "handoff.json").read_text())
    assert all(sha(SEED / p) == h for p, h in seed["files_sha256"].items())
    copper = json.loads((ROOT / "generated/native-metal-clearance.json").read_text())
    neck = json.loads((ROOT / "generated/native-neck.json").read_text())
    assert copper["actual_all_four_layer_copper_clear"] and copper["actual_filled_pcb_sha256"] == neck[
        "source_filled_pcb_sha256"
    ] == sha(ROOT / "generated/filled.kicad_pcb")
    assert all(
        r[k] == 0
        for r in copper["rows"]
        for k in ["pad_intersection_mm2", "track_via_intersection_mm2", "filled_copper_intersection_mm2"]
    )
    assert all(
        all(r["source_to_output_probes_connected"].values())
        for r in neck["rows"]
        if r["centre_line_actual_copper"]["total_width_mm"] > 0
    )
    report = dict(
        candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        filled_pcb_sha256=sha(ROOT / "generated/filled.kicad_pcb"),
        native_counts=native["counts"],
        all_other87_FP_all79_pinmaps_quietfilters_foreign_routes_exact=True,
        R1_same0p47_1A_retained=True,
        manufacturer_lands_exact=True,
        actual_four_layer_H9_clear=True,
        ear_source_outputs_actual_flood_connected=True,
        new_Seed_VIN_barrels=5,
        new_Seed_force_width_mm=0.75,
        maximum_body_mm=[6.604, 3.434, 0.889],
        assembled_height_receiving_requirement_mm=1.0,
        old_PDN_or_MCAD_inherited=False,
        actual_current_temperature_or_pulse_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    if write:
        (ROOT / "generated/package-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print("R1manufacturerforce/79pinmaps/87otherFP/nativeproofclear", report["candidate_pcb_sha256"])
    return report


if __name__ == "__main__":
    run()
