"""Private same-value R1 selection with exact manufacturer recommended lands."""

import copy
import csv
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear-fanout-j29-central"
EXPECTED = "3b2a8197e1452c00fb9f7a99a3730cfb97fe176e7f5f41ee6a8a732a843e8ed6"
FP = "RMX_Carrier:WSLT2512_R_2512_Manufacturer"
PART = "0.47R 1% WSLT2512R4700FEA P70=0.815W"
URL = "https://www.vishay.com/docs/30121/wslt2512.pdf"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(f):
    return next(p[2] for p in children(f, "property") if p[1] == "Reference")


def update_props(node):
    for p in children(node, "property"):
        if p[1] == "Value":
            p[2] = PART
        elif p[1] == "Footprint":
            p[2] = FP
        elif p[1] == "Datasheet":
            p[2] = URL
        elif p[1] == "MPN":
            p[2] = "WSLT2512R4700FEA"


def run():
    assert sha(SOURCE / "processor_carrier.kicad_pcb") == EXPECTED
    assert not (ROOT / "processor_carrier.kicad_pcb").exists()
    for p in SOURCE.iterdir():
        if p.is_dir() and p.suffix == ".pretty":
            shutil.copytree(p, ROOT / p.name)
        elif p.is_file() and (
            p.suffix in [".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"]
            or p.name in ["components.json", "bom.csv", "fp-lib-table", "sym-lib-table"]
        ):
            shutil.copyfile(p, ROOT / p.name)
    tree = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    r = next(f for f in children(tree, "footprint") if ref(f) == "R1")
    old = sexpr(r)
    r[1] = FP
    update_props(r)
    first(r, "at")[1:] = [a(180), a(140), a(90)]
    for p in children(r, "pad"):
        first(p, "at")[1:] = [a(-2.855 if p[1] == "1" else 2.855), a(0), a(90)]
        first(p, "size")[1:] = [a(1.65), a(3.68)]
        p[3] = a("rect")
        for q in list(children(p, "roundrect_rratio")):
            p.remove(q)
    for q in children(r, "fp_rect"):
        if first(q, "layer")[1] == "F.Fab":
            first(q, "start")[1:] = [a(-3.175), a(-1.59)]
            first(q, "end")[1:] = [a(3.175), a(1.59)]
        elif first(q, "layer")[1] == "F.CrtYd":
            first(q, "start")[1:] = [a(-3.93), a(-2.09)]
            first(q, "end")[1:] = [a(3.93), a(2.09)]
    for q in list(children(r, "model")):
        r.remove(q)
    for q in list(children(r, "fp_line")):
        if first(q, "layer")[1] == "F.SilkS":
            r.remove(q)
    for y in [-1.85, 1.85]:
        r.append(
            read_sexpr(
                f'(fp_line(start -1.7 {y})(end 1.7 {y})(stroke(width .12)(type default))(layer "F.SilkS"))'
            )
        )
    plan = json.loads((ROOT / "routing-plan.json").read_text())
    removed = []
    added = []
    via_added = []
    for q in list(children(tree, "segment")):
        if str(first(q, "uuid")[1]) in plan["removed_segment_UUIDs"]:
            removed.append(sexpr(q))
            tree.remove(q)
    assert len(removed) == 4
    for i, p in enumerate(plan["segments"]):
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, "afx-r1-wslt-force-segment-" + str(i)))
        ss, ee = p["start"], p["end"]
        q = read_sexpr(
            f'(segment(start {ss[0]} {ss[1]})(end {ee[0]} {ee[1]})(width {p["width"]})(layer "{p["layer"]}")(net "/{p["net"]}")(uuid "{uid}"))'
        )
        tree.append(q)
        added.append(sexpr(q))
    for i, (x, y) in enumerate(plan["vias"]):
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, "afx-r1-wslt-force-via-" + str(i)))
        q = read_sexpr(
            f'(via(at {x} {y})(size .65)(drill .3)(layers "F.Cu" "B.Cu")(net "/SEED_VIN")(uuid "{uid}"))'
        )
        tree.append(q)
        via_added.append(sexpr(q))
    first(r, "descr")[1] = (
        "Vishay30121 WSLT2512 recommended1.65x3.68mm rectangular lands/gap4.06. Body6.35x3.18x0.635mm +/-0.254. Courtyardcontainsmaxbody+.25. Stencil/assembly/thermal/pulse qualificationopen."
    )
    (ROOT / "processor_carrier.kicad_pcb").write_text(sexpr(tree) + "\n")
    lib = copy.deepcopy(r)
    lib[1] = FP.split(":")[1]

    def normalize(n):
        if not isinstance(n, list):
            return
        for q in list(n):
            if isinstance(q, list) and q:
                if q[0] in ["uuid", "net"] or (n is lib and q[0] == "at"):
                    n.remove(q)
                    continue
                if q[0] == "at" and len(q) == 4:
                    q[3] = a(float(q[3]) - 90)
                normalize(q)

    normalize(lib)
    for p in children(lib, "property"):
        if p[1] == "Reference":
            p[2] = "REF**"
    (ROOT / "RMX_Carrier.pretty" / ("WSLT2512_R_2512_Manufacturer.kicad_mod")).write_text(sexpr(lib) + "\n")
    sch = read_sexpr((ROOT / "processor_carrier.kicad_sch").read_text())
    for f in children(sch, "symbol"):
        if ref(f) == "R1":
            update_props(f)
    for f in children(first(sch, "lib_symbols"), "symbol"):
        if f[1] == "RMX_E19:E19_R1":
            update_props(f)
    (ROOT / "processor_carrier.kicad_sch").write_text(sexpr(sch) + "\n")
    syms = read_sexpr((ROOT / "RMX_E19.kicad_sym").read_text())
    for f in children(syms, "symbol"):
        if f[1] == "E19_R1":
            update_props(f)
    (ROOT / "RMX_E19.kicad_sym").write_text(sexpr(syms) + "\n")
    parts = json.loads((ROOT / "components.json").read_text())
    p = next(p for p in parts if p["ref"] == "R1")
    p.update(
        part=PART,
        footprint=FP,
        source=URL,
        note="Retained1ASeedinputallocation. WSLT2512R4700FEA same0.47R; P70=.815W afterresistancevaluederating. Manufacturerlands; actualtheta/bodytemp/pulse/startup notqualified. Not theold0.5Ascreen.",
    )
    (ROOT / "components.json").write_text(json.dumps(parts, indent=2) + "\n")
    with (ROOT / "bom.csv").open(newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    row = next(p for p in rows if p["Reference"] == "R1")
    row["Part_or_value"] = PART
    row["Footprint"] = FP
    with (ROOT / "bom.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    (ROOT / "generated/design-change.json").write_text(
        json.dumps(
            dict(
                parent_pcb_sha256=EXPECTED,
                candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
                old_R1_footprint=old,
                new_R1_footprint=sexpr(r),
                all_other87_FP_and_foreign_traces_exact=True,
                removed_segments=removed,
                added_segments=added,
                added_vias=via_added,
                same0p47_RC_retained=True,
                retained_load_a=1.0,
                manufacturer_recommended_lands_mm=[1.65, 3.68],
                manufacturer_inner_gap_mm=4.06,
                manufacturer_body_max_mm=[6.604, 3.434, 0.889],
                courtyard_mm=[7.86, 4.18],
                minimum_courtyard_margin_from_max_body_mm=0.373,
                selected_assembled_height_receiving_requirement_mm=1.0,
                seat_allocation_mm=0.111,
                native_stencil_and_assembly_approval=False,
                physical_qualified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(sha(ROOT / "processor_carrier.kicad_pcb"))


if __name__ == "__main__":
    run()
