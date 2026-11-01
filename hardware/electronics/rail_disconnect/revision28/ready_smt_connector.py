"""Explicit SMT PH receiving candidate, preserving actual READY/GND pin centres."""

import copy
import csv
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.placement import strip_and_flip
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .reset_pullup_candidate2 import prop

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/reset-triple-remaining-batch1-work"
WORK = ROOT / "generated/ready-smt-connector-work"
STOCK = Path(
    "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints/Connector_JST.pretty/JST_PH_B2B-PH-SM4-TB_1x02-1MP_P2.00mm_Vertical.kicad_mod"
)
FP = "RMX_E28:JST_B2B_PH_SM4_TB_MechanicalLands"
PART = "JST B2B-PH-SM4-TB(LF)(SN)"
URL = "https://www.jst-mfg.com/product/pdf/eng/ePH.pdf"


def validate(fp):
    pads = children(fp, "pad")
    assert len(pads) == 4
    expected = {"1": ((-1, 0.5), (1, 5.5)), "2": ((1, 0.5), (1, 5.5))}
    for p in pads:
        assert p[2:4] == ["smd", "roundrect"]
        assert (
            abs(float(first(p, "roundrect_rratio")[1]) * min(map(float, first(p, "size")[1:])) - 0.25) < 1e-9
        )
        assert not children(p, "drill")
        assert set(first(p, "layers")[1:]) == {"F.Cu", "F.Mask", "F.Paste"}
        xy = tuple(map(float, first(p, "at")[1:3]))
        size = tuple(map(float, first(p, "size")[1:]))
        if p[1]:
            assert (xy, size) == expected[p[1]]
        else:
            assert xy in ((-3.4, -1.75), (3.4, -1.75)) and size == (1.6, 3)
            assert not children(p, "net"), "Mechanical hold-down must not be credited as a ground terminal"
    assert len([p for p in pads if not p[1]]) == 2
    return True


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    tree = read_sexpr(original.decode())
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1] == "Reference" and p[2] == "J12" for p in children(f, "property"))
    )
    before = sexpr(fp)
    oldpads = {str(p[1]): copy.deepcopy(first(p, "net")) for p in children(fp, "pad")}
    assert tuple(map(float, first(fp, "at")[1:])) == (245, 149.5, 0)
    module = strip_and_flip(read_sexpr(STOCK.read_text()), False)
    module[1] = FP.split(":")[1]
    for p in children(module, "pad"):
        if p[1] == "MP":
            p[1] = ""
    validate(module)
    new = copy.deepcopy(module)
    new[1] = FP
    new.append([a("at"), a("246"), a("149"), a("0")])
    new.append(copy.deepcopy(first(fp, "uuid")))
    for key in ("Reference", "Value", "Datasheet"):
        prop(new, key, {"Reference": "J12", "Value": PART, "Datasheet": URL}[key])
    for key in ("path", "sheetname", "sheetfile"):
        if children(fp, key):
            new.append(copy.deepcopy(first(fp, key)))
    for p in children(new, "pad"):
        if p[1]:
            p.append(oldpads[p[1]])
    fp[:] = new
    added = []
    # Real filled/capped0.3mm through barrels replace the removed0.75mm pin bores.
    # Centroids stay at the same physical operating1/2 endpoints; no ideal join.
    for num, x in (("1", 245), ("2", 247)):
        code = oldpads[num][1]
        ident = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL, "rmx:E28:readySMT:" + hashlib.sha256(original).hexdigest() + ":" + num
            )
        )
        v = read_sexpr(
            f'(via (at {x} 149.5) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {code}) (uuid {ident}))'
        )
        tree.append(v)
        added.append(sexpr(v))
    parts = json.loads((SOURCE / "components.json").read_text())
    part = next(p for p in parts if p["ref"] == "J12")
    oldpart = copy.deepcopy(part)
    part.update(
        part=PART,
        footprint=FP,
        source=URL,
        note="SMT topentryPH; exactstandardland+mechanicalholddowns retained with unnumberednon-electricaltabs. PHR-2/SPH-002T mate. Mated<=9.0mm body envelope is unverified receiving gauge; wirebend/retention/stencil/process approval false. Real.3mmfilled/cappedvia-in-pad replaces each oldpinbore, samepincentres.",
    )
    sch = read_sexpr((SOURCE / "rail_disconnect.kicad_sch").read_text())
    inst = next(
        s
        for s in children(sch, "symbol")
        if any(p[1] == "Reference" and p[2] == "J12" for p in children(s, "property"))
    )
    libid = first(inst, "lib_id")[1]
    emb = next(s for s in children(first(sch, "lib_symbols"), "symbol") if s[1] == libid)
    for node in (inst, emb):
        prop(node, "Value", PART)
        prop(node, "Footprint", FP)
        prop(node, "Datasheet", URL)
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
    for path2 in WORK.glob("*.kicad_sym"):
        lib = read_sexpr(path2.read_text())
        node = next(s for s in children(lib, "symbol") if s[1] == str(libid).split(":")[1])
        prop(node, "Value", PART)
        prop(node, "Footprint", FP)
        prop(node, "Datasheet", URL)
        path2.write_text(sexpr(lib) + "\n")
    (WORK / "RMX_E28.pretty" / (FP.split(":")[1] + ".kicad_mod")).write_text(sexpr(module) + "\n")
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    (WORK / "rail_disconnect.kicad_sch").write_text(sexpr(sch) + "\n")
    (WORK / "components.json").write_text(json.dumps(parts, indent=2) + "\n")
    with (WORK / "generated/bom.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Reference", "Value / selected part", "Footprint", "Primary source"])
        w.writerows([p["ref"], p["part"], p["footprint"], p["source"]] for p in parts)
    report = dict(
        source_pcb_sha256=hashlib.sha256(original).hexdigest(),
        stock_footprint_sha256=hashlib.sha256(STOCK.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        before_footprint=before,
        after_footprint=sexpr(fp),
        before_part=oldpart,
        after_part=part,
        actual_new_barrels=added,
        pin_centres_world_mm={"1": [153, 158], "2": [155, 158]},
        mechanical_tabs_have_no_assigned_electrical_net=True,
        PCB_thickness_or_tail_trim_dependency_removed=True,
        stock_and_manufacturer_land_stencil_and_fillets_accepted=False,
        mated_body_height_receiving_requirement_mm=9.0,
        manufacturer_bound_for_that_requirement=False,
        native_MCAD_current_leak_loading_PDN_and_fabrication_pending=True,
        qualified=False,
    )
    (WORK / "generated/connector-change.json").write_text(json.dumps(report, indent=2) + "\n")
    assert path.read_bytes() == original


if __name__ == "__main__":
    main()
