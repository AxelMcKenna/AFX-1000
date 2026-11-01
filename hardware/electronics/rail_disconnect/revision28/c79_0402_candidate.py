"""Actual manufacturer 0402 bypass that leaves the 0.2mm U36 signal corridor open."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.placement import placed_footprint
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .. import generate as sg
from .positive_footprints import base, pad

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-receiver-bypass-repair-work"
WORK = ROOT / "generated/schmitt-c79-0402-work"
NAME = "RMX_E28:KEMET_C0402_LevelB"
MPN = "100nF 16V X7R 10% KEMET C0402C104K4RACTU"
URL = "https://search.kemet.com/download/specsheet/C0402C104K4RACTU"


def pattern():
    f = base(NAME.split(":")[1], "C0402C104K4RACTU", URL, (0.525, 0.275))
    court = next(r for r in children(f, "fp_rect") if first(r, "layer")[1] == "F.CrtYd")
    first(court, "start")[1:] = [a("-.95"), a("-.5")]
    first(court, "end")[1:] = [a(".95"), a(".5")]
    for n, x in [(1, -0.45), (2, 0.45)]:
        p = pad(n, x, 0, 0.62, 0.62, 0.05)
        p[3] = a("rect")
        p[:] = [v for v in p if not (isinstance(v, list) and v and v[0] == "roundrect_rratio")]
        f.append(p)
    return f


def validate(f):
    ps = {str(p[1]): p for p in children(f, "pad")}
    assert set(ps) == {"1", "2"}
    for n, x in [("1", -0.45), ("2", 0.45)]:
        p = ps[n]
        assert str(p[3]) == "rect" and tuple(map(float, first(p, "at")[1:3])) == (x, 0)
        assert tuple(map(float, first(p, "size")[1:])) == (0.62, 0.62)
        assert set(first(p, "layers")[1:]) == {"F.Cu", "F.Mask", "F.Paste"}
        assert float(first(p, "solder_mask_margin")[1]) == 0.05
    court = next(r for r in children(f, "fp_rect") if first(r, "layer")[1] == "F.CrtYd")
    assert tuple(map(float, first(court, "start")[1:])) == (-0.95, -0.5)
    assert tuple(map(float, first(court, "end")[1:])) == (0.95, 0.5)
    return True


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    s = read_sexpr((SOURCE / "rail_disconnect.kicad_sch").read_text())
    parts = json.loads((SOURCE / "components.json").read_text())
    c = next(c for c in parts if c["ref"] == "C79")
    oldpart = dict(c)
    c.update(
        part=MPN,
        footprint=NAME,
        source=URL,
        note="Primary C1002 Table3 DensityB 0402: two rectangular .62mm lands at±.45mm,1.90x1.00 courtyard. Exact MPN maxbody1.05x.55x.55mm;0.10mm seating allowance. Reflow only; effectiveC>=50nF,bias/aging,stencil/process/assembled PDN remain unverified.",
    )
    libsymbols = first(s, "lib_symbols")
    symbol = next(v for v in children(libsymbols, "symbol") if v[1] == "RMX_E17:E17_C79")
    libsymbols[libsymbols.index(symbol)] = read_sexpr(sg.symbol(c))
    instance = next(
        v
        for v in children(s, "symbol")
        if any(p[1] == "Reference" and p[2] == "C79" for p in children(v, "property"))
    )
    for p in children(instance, "property"):
        if p[1] in ("Value", "Footprint", "Datasheet"):
            p[2] = {"Value": MPN, "Footprint": NAME, "Datasheet": URL}[p[1]]
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
    f = pattern()
    validate(f)
    lib = WORK / "RMX_E28.pretty" / (NAME.split(":")[1] + ".kicad_mod")
    lib.write_text(sexpr(f) + "\n")
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(t, "net")}
    oldfp = next(
        f
        for f in children(t, "footprint")
        if any(p[1] == "Reference" and p[2] == "C79" for p in children(f, "property"))
    )
    newfp = placed_footprint(
        dict(c, value=MPN, mpn=MPN, nets={p["number"]: p["net"] for p in c["pins"]}),
        (13.9, 13.75, 0, "B"),
        lib,
        nets,
        namespace="rmx:E28:allOC:",
    )
    t[t.index(oldfp)] = newfp
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(t) + "\n")
    (WORK / "rail_disconnect.kicad_sch").write_text(sexpr(s) + "\n")
    (WORK / "components.json").write_text(json.dumps(parts, indent=2) + "\n")
    for p in WORK.glob("*.kicad_sym"):
        sym = read_sexpr(p.read_text())
        old = next(v for v in children(sym, "symbol") if v[1] == "E17_C79")
        sym[sym.index(old)] = read_sexpr(sg.symbol(c, False))
        p.write_text(sexpr(sym) + "\n")
    primary = [
        ROOT / "generated/reset-buffer-proposal/sources/kemet-X7R-C1002.pdf",
        ROOT / "generated/schmitt-cone-proposal/sources/kemet-C0402C104K4RACTU.pdf",
    ]
    report = dict(
        source_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                SOURCE / "rail_disconnect.kicad_pcb",
                SOURCE / "rail_disconnect.kicad_sch",
                SOURCE / "components.json",
                Path(__file__),
                *primary,
            ]
        },
        primary_pages_visually_reviewed=[
            "C1002_X7R2026-09-01page12 Table3 DensityB0402",
            "Exact C0402C104K4RACTU specsheet page1 generated2026-10-29",
        ],
        old_component=oldpart,
        new_component=c,
        old_footprint=sexpr(oldfp),
        new_footprint=sexpr(newfp),
        no_copper_or_other_part_changed=True,
        max_body_mm=[1.05, 0.55, 0.55],
        seating_allowance_mm=0.1,
        complete_node_effective_C_requirement_F=50e-9,
        manufacturer_referee_C_test="1kHz1Vrms; bias/aging/temperature receiving requirement not accepted",
        reflow_only=True,
        stencil_process_native_PDN_MCAD_required=True,
        physical_qualified=False,
    )
    (WORK / "generated/c79-0402-change.json").write_text(json.dumps(report, indent=2) + "\n")
    print("C79 exact0402 manufacturer lands/MPN atB13.9,13.75; all nets/nominal C unchanged; checks pending")


if __name__ == "__main__":
    main()
