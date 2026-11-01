"""Explicit value/library/SCH/PCB/BOM-coherent10k R135 receiving candidate."""

import copy
import csv
import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .reset_pullup import FOOTPRINT, MODEL_URL, MPN, PART, screen, validate_footprint

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u12-band-reconnect1-work"
WORK = ROOT / "generated/u12-reset-pullup10k2-work"
PRIMARY = ROOT / "generated/r135-primary-review"


def prop(node, name, value):
    matches = [p for p in children(node, "property") if p[1] == name]
    if not matches and name in ("Footprint", "Datasheet"):
        field = read_sexpr(
            '(property "FIELD" "VALUE" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'
        )
        field[1:3] = [str(name), str(value)]
        node.append(field)
        return
    assert len(matches) == 1, (name, len(matches))
    matches[0][2] = str(value)


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    tree = read_sexpr(original.decode())
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1] == "Reference" and p[2] == "R135" for p in children(f, "property"))
    )
    old_fp = sexpr(fp)
    assert first(fp, "layer")[1] == "B.Cu"
    assert next(p[2] for p in children(fp, "property") if p[1] == "Value") == "100k"
    fp[1] = FOOTPRINT
    first(fp, "descr")[1] = (
        "Panasonic ERA6A recommended land example: a1.2/b3.4/c1.25mm; process approval pending. Display fields adapted from KiCad R_0805_2012Metric."
    )
    fp[:] = [
        n for n in fp if not (isinstance(n, list) and n and n[0] == "property" and n[1] == "KiLib_Generator")
    ]
    prop(fp, "Value", PART)
    prop(fp, "MPN", MPN)
    prop(fp, "Datasheet", MODEL_URL)
    for p in children(fp, "pad"):
        p[3] = a("rect")
        first(p, "at")[1:3] = [a("-1.15" if p[1] == "1" else "1.15"), a("0")]
        first(p, "size")[1:] = [a("1.1"), a("1.25")]
        p[:] = [n for n in p if not (isinstance(n, list) and n and n[0] == "roundrect_rratio")]
    court = next(q for q in children(fp, "fp_rect") if first(q, "layer")[1] == "B.CrtYd")
    first(court, "start")[1:] = [a("-1.95"), a(".925")]
    first(court, "end")[1:] = [a("1.95"), a("-.925")]
    validate_footprint(fp)
    module = copy.deepcopy(fp)
    module[1] = FOOTPRINT.split(":")[-1]
    module[:] = [
        n
        for n in module
        if not (isinstance(n, list) and n and n[0] in ("at", "uuid", "path", "sheetname", "sheetfile"))
    ]

    def front(node):
        if not isinstance(node, list) or not node:
            return
        if node[0] in ("layer", "layers"):
            for i, v in enumerate(node[1:], 1):
                if str(v).startswith("B."):
                    node[i] = "F." + str(v)[2:]
        if node[0] in ("at", "start", "end") and len(node) >= 3:
            node[2] = a(str(-float(node[2])))
            if node[0] == "at" and len(node) >= 4:
                node[3] = a(str(-float(node[3])))
        for n in list(node):
            if isinstance(n, list) and n and n[0] == "justify" and n[1:] == ["mirror"]:
                node.remove(n)
            else:
                front(n)

    front(module)
    for p in children(module, "pad"):
        p[:] = [n for n in p if not (isinstance(n, list) and n and n[0] in ("net", "uuid"))]
    prop(module, "Reference", "REF**")
    validate_footprint(module)
    sch_source = SOURCE / "rail_disconnect.kicad_sch"
    sch = read_sexpr(sch_source.read_text())
    symbol = next(
        s
        for s in children(sch, "symbol")
        if any(p[1] == "Reference" and p[2] == "R135" for p in children(s, "property"))
    )
    libid = str(first(symbol, "lib_id")[1])
    embedded = next(s for s in children(first(sch, "lib_symbols"), "symbol") if s[1] == libid)
    before_symbols = [sexpr(symbol), sexpr(embedded)]
    for s in (symbol, embedded):
        prop(s, "Value", PART)
        prop(s, "Footprint", FOOTPRINT)
        prop(s, "Datasheet", MODEL_URL)
    parts = json.loads((SOURCE / "components.json").read_text())
    part = next(p for p in parts if p["ref"] == "R135")
    assert part["part"] == "100k"
    old_part = copy.deepcopy(part)
    assert {p["net"] for p in part["pins"]} == {"E28_AUX_RESET_N", "V2V5_AUX"}
    receiver = next(p for p in parts if p["ref"] == "U31")
    assert receiver["part"] == "SN74AUP2G08DCUR"
    assert next(p for p in receiver["pins"] if str(p["number"]) == "5")["net"] == "E28_AUX_RESET_N"
    part.update(
        part=PART,
        footprint=FOOTPRINT,
        source=MODEL_URL,
        note="Actual U31 is AUP2G08, not2G17.10k improves strict200ns/V receiving C ceiling to17.097pF; actual nodeC/edges and manufacturer conflicting Schmitt text unresolved.2%total resistance/2uA board leakage are receiving requirements.",
    )
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, WORK / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, WORK / p.name)
    (WORK / source.name).write_text(sexpr(tree) + "\n")
    (WORK / sch_source.name).write_text(sexpr(sch) + "\n")
    (WORK / "components.json").write_text(json.dumps(parts, indent=2) + "\n")
    external_changes = []
    for path in WORK.glob("*.kicad_sym"):
        lib = read_sexpr(path.read_text())
        for s in children(lib, "symbol"):
            if s[1] == libid.split(":")[-1]:
                before = sexpr(s)
                prop(s, "Value", PART)
                prop(s, "Footprint", FOOTPRINT)
                prop(s, "Datasheet", MODEL_URL)
                external_changes.append(dict(path=path.name, before=before, after=sexpr(s)))
        path.write_text(sexpr(lib) + "\n")
    assert len(external_changes) == 1
    (WORK / "RMX_E28.pretty" / (FOOTPRINT.split(":")[-1] + ".kicad_mod")).write_text(sexpr(module) + "\n")
    with (WORK / "generated/bom.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Reference", "Value / selected part", "Footprint", "Primary source"])
        writer.writerows([p["ref"], p["part"], p["footprint"], p.get("source", "")] for p in parts)
    old, new = screen(100000), screen(10000)
    assert old["static_high_margin_v"] > 0
    assert new["RESET_LOW_sink_allocation_a"] < new["TPS3890_LOW_row_current_a"]
    report = dict(
        source_pcb_sha256=hashlib.sha256(original).hexdigest(),
        source_sch_sha256=hashlib.sha256(sch_source.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        correct_model_sha256=hashlib.sha256((ROOT / "reset_pullup.py").read_bytes()).hexdigest(),
        primary_review_sha256=hashlib.sha256((PRIMARY / "review.json").read_bytes()).hexdigest(),
        before_part=old_part,
        after_part=part,
        before_footprint=old_fp,
        after_footprint=sexpr(fp),
        before_schematic_symbols=before_symbols,
        after_schematic_symbols=[sexpr(symbol), sexpr(embedded)],
        external_library_changes=external_changes,
        old100k_screen=old,
        new10k_screen=new,
        old100k_DC_failure_claim_withdrawn_wrong_receiver=True,
        selected_land_example_mm=dict(a=1.2, b=3.4, c=1.25, pad=[1.1, 1.25], centres=[-1.15, 1.15]),
        source_tracks_vias_ports_other_parts_and_netlist_topology_unchanged=True,
        source_hashes={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in PRIMARY.iterdir() if p.is_file()
        },
        native_netlist_BOM_masks_process_AUX_PDN_and_physical_checks_pending=True,
        qualified=False,
    )
    (WORK / "generated/reset-pullup-change.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == original
    print("R13510k coherent candidate written; native/receiving checks pending", flush=True)


if __name__ == "__main__":
    main()
