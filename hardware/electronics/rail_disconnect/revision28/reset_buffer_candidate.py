"""Explicit255-part supervisor Schmitt and NF-ready-only integration draft."""

import copy
import csv
import hashlib
import json
import shutil
from pathlib import Path

from ...common.placement import placed_footprint
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .. import generate as sg
from .reset_buffer_patterns import BYPASS, TRIPLE, bypass, triple, validate

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/timeout-pullup-placement-work"
WORK = ROOT / "generated/reset-triple-ready-placement-work"
LIB = Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints")
CHANGES = {
    ("U19", "6"): "E28_AUX_RESET_RAW",
    ("R135", "1"): "E28_AUX_RESET_RAW",
    ("U20", "6"): "E28_TIMEOUT_RAW",
    ("R136", "1"): "E28_TIMEOUT_RAW",
    ("U27", "3"): "POS_OUTPUT_READY",
    ("U25", "4"): "POS_OUTPUT_READY",
    ("U25", "5"): "NF_VALID_LOGIC",
    ("U25", "6"): "E28_OUTPUT_READY",
}
POSES = {
    "U35": (104, 49.5, 0, "B"),
    "C78": (103.3, 52.7, 0, "B"),
    "R143": (103.3, 52.2, 270, "F"),
    "J12": (145, 49.5, 0, "F"),
}


def pin(n, name, net, kind="input", side="L"):
    return dict(number=str(n), name=name, net=net, kind=kind, side=side)


def added_parts():
    return [
        dict(
            ref="U35",
            part="SN74LVC3G17DCUR",
            footprint=TRIPLE,
            source="https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf",
            pins=[
                pin(1, "1A", "E28_TIMEOUT_RAW"),
                pin(7, "1Y", "E28_TIMEOUT", "output", "R"),
                pin(3, "2A", "E28_AUX_RESET_RAW"),
                pin(5, "2Y", "E28_AUX_RESET_N", "output", "R"),
                pin(6, "3A", "NF_OUTPUT_VALID_RAW"),
                pin(2, "3Y", "NF_VALID_LOGIC", "output", "R"),
                pin(4, "GND", "AGND", "power_in"),
                pin(8, "VCC", "V2V5_AUX", "power_in", "R"),
            ],
            x=190.5,
            y=2540,
            note="Three real non-inverting Schmitt stages. Supervisors are slow raw inputs; NF valid gates READY only. Dynamic/partial-power/threshold-transfer holds remain.",
        ),
        dict(
            ref="C78",
            part="100nF 16V X7R 10% KEMET C0603C104K4RACTU",
            footprint=BYPASS,
            source="https://search.kemet.com/download/specsheet/C0603C104K4RACTU",
            pins=[pin(1, "1", "V2V5_AUX", "passive"), pin(2, "2", "AGND", "passive", "R")],
            x=330.2,
            y=2540,
            note="Manufacturer DensityB land. Receiving effective-C>=50nF is unverified; generic bodyheight envelope1.5mm retained.",
        ),
        dict(
            ref="R143",
            part="15k 0.1% 25ppm Panasonic ERA6AEB153V",
            footprint="RMX_E28:Resistor_SMD_Panasonic_ERA6A_2012",
            source="https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA6AEB153V",
            pins=[pin(1, "1", "NF_OUTPUT_VALID_RAW", "passive"), pin(2, "2", "AGND", "passive", "R")],
            x=469.9,
            y=2540,
            note="FailLOW15k totalassembled/lifetime3% receiving requirement; NF U49 source load/ground/partial-power remains unqualified.",
        ),
        dict(
            ref="J12",
            part="JST B2B-PH-K-S(LF)(SN)",
            footprint="Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
            source="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf",
            pins=[
                pin(1, "NF_OUTPUT_VALID_RAW", "NF_OUTPUT_VALID_RAW", "passive"),
                pin(2, "AGND", "AGND", "passive"),
            ],
            x=609.6,
            y=2540,
            note="READY-only pair to NFJ1.30/2; PHR-2/SPH-002T-P0.5S24..30AWG. Stock3.4mm tails require explicit trimmed<=1.5mm protrusion process before floor fit. NF30pinmate/wirebend/assembly not selected or approved.",
        ),
    ]


def main():
    assert not WORK.exists()
    original = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    tree = read_sexpr(original.decode())
    sch = read_sexpr((SOURCE / "rail_disconnect.kicad_sch").read_text())
    parts = json.loads((SOURCE / "components.json").read_text())
    assert len(parts) == 251
    old_parts = copy.deepcopy(parts)
    by = {p["ref"]: p for p in parts}
    for (ref, num), net in CHANGES.items():
        p = next(p for p in by[ref]["pins"] if p["number"] == num)
        old = p["net"]
        p["net"] = net
        if (ref, num) == ("U25", "6"):
            p["kind"] = "output"
        labels = [
            n for n in children(sch, "label") if str(first(n, "uuid")[1]) == sg.uid("label" + ref + "." + num)
        ]
        if old is not None:
            assert len(labels) == 1 and labels[0][1] == old, (ref, num, old, labels)
            labels[0][1] = net
        else:
            assert (ref, num) == ("U25", "6")
            nc = next(
                n
                for n in children(sch, "no_connect")
                if str(first(n, "uuid")[1]) == sg.uid("nc" + ref + "." + num)
            )
            sch.remove(nc)
            q = next(q for q in sg.geometry(by[ref])[0] if q["number"] == num)
            px, py = sg.grid(by[ref]["x"] + q["x"]), sg.grid(by[ref]["y"] - q["y"])
            end = sg.grid(px + 5.08)
            sch.extend(
                [
                    read_sexpr(
                        f"(wire (pts (xy {px} {py}) (xy {end} {py})) (stroke (width 0) (type default)) (uuid {sg.uid('wire' + ref + '.' + num)}))"
                    ),
                    read_sexpr(
                        f'(label "{net}" (at {end} {py} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {sg.uid("label" + ref + "." + num)}))'
                    ),
                ]
            )
    new = added_parts()
    parts.extend(new)
    # Refresh U25 pin electrical type in both embedded/external symbol, no position changes.
    symbol = next(s for s in children(first(sch, "lib_symbols"), "symbol") if s[1] == "RMX_E17:E17_U25")
    for unit in children(symbol, "symbol"):
        for p in children(unit, "pin"):
            if first(p, "number")[1] == "6":
                p[1] = a("output")
    for c in new:
        first(sch, "lib_symbols").append(read_sexpr(sg.symbol(c)))
        x, y = c["x"], c["y"]
        _, hh = sg.geometry(c)
        ref = c["ref"]
        s = read_sexpr(
            f'(symbol (lib_id "RMX_E17:E17_{ref}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {sg.uid(ref)}))'
        )
        for key, v, py, hide in [
            ("Reference", ref, y - hh - 3.81, False),
            ("Value", c["part"], y + hh + 3.81, False),
            ("Footprint", c["footprint"], y, True),
            ("Datasheet", c["source"], y, True),
        ]:
            s.append(
                read_sexpr(
                    f"(property {sg.q(key)} {sg.q(v)} (at {x} {sg.grid(py)} 0) (effects (font (size 1.27 1.27)) {'(hide yes)' if hide else ''}))"
                )
            )
        for p in sg.geometry(c)[0]:
            s.append(read_sexpr(f'(pin "{p["number"]}" (uuid {sg.uid(ref + "." + p["number"])}))'))
        s.append(
            read_sexpr(
                f'(instances (project "rail_disconnect" (path "/{first(sch, "uuid")[1]}" (reference "{ref}") (unit 1))))'
            )
        )
        sch.append(s)
        for p in sg.geometry(c)[0]:
            px, py = sg.grid(x + p["x"]), sg.grid(y - p["y"])
            end = sg.grid(px + (-5.08 if p["side"] == "L" else 5.08))
            ident = ref + "." + p["number"]
            just = "right" if p["side"] == "L" else "left"
            sch.extend(
                [
                    read_sexpr(
                        f"(wire (pts (xy {px} {py}) (xy {end} {py})) (stroke (width 0) (type default)) (uuid {sg.uid('wire' + ident)}))"
                    ),
                    read_sexpr(
                        f'(label "{p["net"]}" (at {end} {py} 0) (effects (font (size 1 1)) (justify {just} bottom)) (uuid {sg.uid("label" + ident)}))'
                    ),
                ]
            )
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    for c in parts:
        for p in c["pins"]:
            net = p["net"]
            if net is not None and net not in nets:
                code = max(nets.values()) + 1
                nets[net] = code
                tree.append([a("net"), a(str(code)), "/" + net])
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    for (ref, num), net in CHANGES.items():
        p = next(p for p in children(fps[ref], "pad") if p[1] == num)
        first(p, "net")[:] = [a("net"), a(str(nets[net])), "/" + net]
    # Rebuild only the three ordinary signals in full, eliminating old long RESET stubs.
    rebuild = {"E28_AUX_RESET_N", "E28_TIMEOUT", "E28_OUTPUT_READY"}
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed = [
        n for k in ("segment", "via") for n in children(tree, k) if names[str(first(n, "net")[1])] in rebuild
    ]
    ground_ids = {"e26ed493-0285-5c8a-a73c-1a7f6704b44d", "9ff5f3c6-9aba-56bc-8c0f-2843c12c9844"}
    g = [n for n in children(tree, "segment") if str(first(n, "uuid")[1]) in ground_ids]
    assert len(g) == 2
    removed.extend(g)
    tree[:] = [n for n in tree if n not in removed]
    # Obsolete unconnected U25.6 code is removed, never a physical termination.
    oldcode = next(n for n in children(tree, "net") if "unconnected-(U25-Y-Pad6)" in str(n[2]))
    tree.remove(oldcode)
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
    modules = {TRIPLE: triple(), BYPASS: bypass()}
    for name, fp in modules.items():
        validate(fp)
        (WORK / "RMX_E28.pretty" / (name.split(":")[1] + ".kicad_mod")).write_text(sexpr(fp) + "\n")
    for c in new:
        fpname = c["footprint"]
        lib = (
            (WORK / "RMX_E28.pretty" / (fpname.split(":")[1] + ".kicad_mod"))
            if fpname.startswith("RMX_E28:")
            else LIB / (fpname.split(":")[0] + ".pretty") / (fpname.split(":")[1] + ".kicad_mod")
        )
        comp = dict(c, value=c["part"], mpn=c["part"], nets={p["number"]: p["net"] for p in c["pins"]})
        tree.append(placed_footprint(comp, POSES[c["ref"]], lib, nets, namespace="rmx:E28:resetready:"))
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    (WORK / "rail_disconnect.kicad_sch").write_text(sexpr(sch) + "\n")
    (WORK / "components.json").write_text(json.dumps(parts, indent=2) + "\n")
    for path in WORK.glob("*.kicad_sym"):
        lib = read_sexpr(path.read_text())
        u = next(s for s in children(lib, "symbol") if s[1] == "E17_U25")
        for unit in children(u, "symbol"):
            for p in children(unit, "pin"):
                if first(p, "number")[1] == "6":
                    p[1] = a("output")
        lib.extend(read_sexpr(sg.symbol(c, False)) for c in new)
        path.write_text(sexpr(lib) + "\n")
    table = read_sexpr((WORK / "fp-lib-table").read_text())
    table.append(
        read_sexpr(
            '(lib (name "Connector_JST") (type "KiCad") (uri "${KICAD10_FOOTPRINT_DIR}/Connector_JST.pretty") (options "") (descr "Manufacturer PH drawing reviewed; assembly pending"))'
        )
    )
    (WORK / "fp-lib-table").write_text(sexpr(table) + "\n")
    with (WORK / "generated/bom.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Reference", "Value / selected part", "Footprint", "Primary source"])
        w.writerows([p["ref"], p["part"], p["footprint"], p["source"]] for p in parts)
    report = dict(
        source_pcb_sha256=hashlib.sha256(original).hexdigest(),
        source_parts_sha256=hashlib.sha256((SOURCE / "components.json").read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        before_parts=old_parts,
        net_endpoint_changes=[dict(ref=r, pin=p, new_net=n) for (r, p), n in CHANGES.items()],
        new_parts=new,
        poses=POSES,
        removed_ordinary_copper=[sexpr(n) for n in removed],
        all_force_and_quiet_geometry_preserved=True,
        ready_only_NF_gate=True,
        all_native_loading_MCAD_PDN_partialpower_process_checks_pending=True,
        qualified=False,
    )
    (WORK / "generated/change.json").write_text(json.dumps(report, indent=2) + "\n")
    assert (SOURCE / "rail_disconnect.kicad_pcb").read_bytes() == original
    print("255part actual Schmitt/NF-ready draft written; checks pending", flush=True)


if __name__ == "__main__":
    main()
