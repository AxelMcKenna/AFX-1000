"""Exact proposed fanout-coordinate feasibility trial; no clearance relaxation."""

import copy
import csv
import hashlib
import io
import json
import shutil
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear-wide-access"
EXPECTED = "2145521ef9319f5bc153f6b394c30d245cec29716f745c1dca836ed0629364b8"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reference(f):
    return next(p[2] for p in children(f, "property") if p[1] == "Reference")


def ids(node, ref):
    if not isinstance(node, list):
        return
    if node and node[0] == "uuid":
        node[1] = str(uuid.uuid5(uuid.NAMESPACE_URL, "afx-ear-fanout-" + ref + "-" + str(node[1])))
    else:
        for q in node:
            ids(q, ref)


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
            shutil.copy2(p, ROOT / p.name)
    out = ROOT / "generated"
    out.mkdir()
    b = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    changes = []
    for q in children(b, "gr_line"):
        if first(q, "layer")[1] != "Edge.Cuts":
            continue
        old = sexpr(q)
        for tag in ["start", "end"]:
            p = first(q, tag)
            if float(p[2]) == 148:
                p[2] = a(143)
        if sexpr(q) != old:
            changes.append(dict(uuid=str(first(q, "uuid")[1]), before=old, after=sexpr(q)))
    assert len(changes) == 3
    for q in children(b, "zone"):
        if (
            children(q, "net")
            and first(q, "net")[1] == "/AGND"
            and children(q, "priority")
            and str(first(q, "priority")[1]) == "1"
            and children(q, "layer")
            and first(q, "layer")[1] == "In1.Cu"
        ):
            old = sexpr(q)
            pts = first(first(q, "polygon"), "pts")
            assert float(pts[1][2]) == float(pts[2][2]) == 148
            pts[1][2] = a(143)
            pts[2][2] = a(143)
            changes.append(dict(uuid=str(first(q, "uuid")[1]), before=old, after=sexpr(q)))
    assert len(changes) == 4
    sch = read_sexpr((ROOT / "processor_carrier.kicad_sch").read_text())
    fp_parent = next(f for f in children(b, "footprint") if reference(f) == "J13")
    symbol_parent = next(f for f in children(sch, "symbol") if reference(f) == "J13")
    symbols = []
    fps = []
    newsch = []
    rows = []
    for ref, y, sy, current, endpoint in [
        ("J14", 145.5, 565.15, 0.140, ["sequenced_bypass", "J1", "1/2"]),
        ("J15", 150.5, 590.55, 0.080, ["rail_monitor", "J1", "1/3"]),
    ]:
        fp = copy.deepcopy(fp_parent)
        ids(fp, ref)
        first(fp, "at")[1:] = [a(258), a(y), a(90)]
        for p in children(fp, "property"):
            if p[1] == "Reference":
                p[2] = ref
        for p in children(fp, "pad"):
            at = first(p, "at")
            at[1:] = [at[1], at[2], a(90)]
        b.append(fp)
        fps.append(sexpr(fp))
        symbol = copy.deepcopy(symbol_parent)
        ids(symbol, ref)
        dy = sy - float(first(symbol_parent, "at")[2])
        first(symbol, "at")[2] = a(sy)
        for p in children(symbol, "property"):
            first(p, "at")[2] = a(float(first(p, "at")[2]) + dy)
            if p[1] == "Reference":
                p[2] = ref
        for path in children(first(first(symbol, "instances"), "project"), "path"):
            first(path, "reference")[1] = ref
        assert first(fp, "uuid")[1] == first(symbol, "uuid")[1]
        sch.append(symbol)
        symbols.append(sexpr(symbol))
        # Clone the two passive-input wires/labels by moving actual J13 pins;
        # preserve every original schematic object and wire/net assignment.
        for wy, net in [(sy - 2.54, "5V_DIG"), (sy + 2.54, "AGND")]:
            for item in [
                f'(wire(pts(xy 219.71 {wy:.6f})(xy 214.63 {wy:.6f}))(stroke(width 0)(type default))(uuid "{uuid.uuid5(uuid.NAMESPACE_URL, ref + net + "wire")}"))',
                f'(label "{net}"(at 214.63 {wy:.6f} 0)(effects(font(size 1 1))(justify right bottom))(uuid "{uuid.uuid5(uuid.NAMESPACE_URL, ref + net + "label")}"))',
            ]:
                q = read_sexpr(item)
                sch.append(q)
                newsch.append(sexpr(q))
        rows.append(
            dict(
                ref=ref,
                positive_native_mm=[258, y],
                AGND_native_mm=[262, y],
                positive_world_mm=[188, y - 58],
                AGND_world_mm=[192, y - 58],
                positive_current_allocation_a=current,
                destination=endpoint,
                unqualified=True,
            )
        )
    (ROOT / "processor_carrier.kicad_pcb").write_text(sexpr(b) + "\n")
    (ROOT / "processor_carrier.kicad_sch").write_text(sexpr(sch) + "\n")
    parts = json.load(open(ROOT / "components.json"))
    base = next(x for x in parts if x["ref"] == "J13")
    with (ROOT / "bom.csv").open(newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        bom = list(reader)
    basebom = next(x for x in bom if x["Reference"] == "J13")
    for ref, sy, current in [("J14", 565.15, 0.140), ("J15", 590.55, 0.080)]:
        p = copy.deepcopy(base)
        p.update(
            ref=ref,
            y=sy,
            note=f"Private single-AWG18 output pair; positive allocation{current}A, actual pad/loop/assembly/current qualification pending",
        )
        parts.append(p)
        q = copy.deepcopy(basebom)
        q.update(Reference=ref, Note=p["note"])
        bom.append(q)
    (ROOT / "components.json").write_text(json.dumps(parts, indent=2) + "\n")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    w.writerows(bom)
    (ROOT / "bom.csv").write_text(buf.getvalue())
    assert len(parts) == 79
    (out / "design-change.json").write_text(
        json.dumps(
            dict(
                parent_pcb_sha256=EXPECTED,
                candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
                changes=changes,
                new_footprints=fps,
                new_symbols=symbols,
                new_schematic_wire_labels=newsch,
                ports=rows,
                world_outline_mm=[[30, 42], [180, 42], [180, 85], [194, 85], [194, 107], [30, 107]],
                added_area_mm2=70,
                original86_footprints_required_exact=True,
                original77_parts_pinmaps_required_exact=True,
                clearance_rules_unchanged=True,
                input_target_a=2.4,
                unassigned_reserve_a=0.416,
                physical_qualified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Exact proposed coordinate trial", sha(ROOT / "processor_carrier.kicad_pcb"))


if __name__ == "__main__":
    run()
