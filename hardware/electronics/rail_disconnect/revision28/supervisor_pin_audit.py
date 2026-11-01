"""Independent physical TPS3890 role contract against TI SLVSD65A page3."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/coherent-ground-repair-work"
OUT = ROOT / "generated/tps3890-pin-audit"
ROLES = {"1": "SENSE", "2": "GND", "3": "MR_N", "4": "VDD", "5": "CT", "6": "RESET_N"}
TOP_LANDS = {
    "1": (-0.55, -0.5),
    "2": (-0.6, 0),
    "3": (-0.6, 0.5),
    "4": (0.6, 0.5),
    "5": (0.6, 0),
    "6": (0.6, -0.5),
}


def component_contract(part):
    pins = {str(p["number"]): p for p in part["pins"]}
    assert part["part"] == "TPS389001DSET"
    assert {k: p["name"] for k, p in pins.items()} == ROLES
    assert pins["4"]["kind"] == "power_in" and pins["6"]["kind"] == "open_collector"
    assert pins["4"]["net"] == "V2V5_AUX" and pins["2"]["net"] == "AGND"
    assert pins["6"]["net"] not in {"V2V5_AUX", "AGND", None}
    return pins


def board_contract(part, fp):
    pins = component_contract(part)
    pads = {str(p[1]): p for p in children(fp, "pad")}
    assert set(pads) == set(ROLES)
    bottom = first(fp, "layer")[1] == "B.Cu"
    for n, pad in pads.items():
        assert str(first(pad, "net")[-1]).lstrip("/") == pins[n]["net"], (part["ref"], n)
        x, y = map(float, first(pad, "at")[1:3])
        y = -y if bottom else y
        assert abs(x - TOP_LANDS[n][0]) < 1e-9 and abs(y - TOP_LANDS[n][1]) < 1e-9
    return True


def main():
    parts = json.loads((SOURCE / "components.json").read_text())
    tree = read_sexpr((SOURCE / "rail_disconnect.kicad_pcb").read_text())
    sch = read_sexpr((SOURCE / "rail_disconnect.kicad_sch").read_text())
    xml = ET.parse(OUT / "coherent-native-netlist.xml").getroot()
    by = {p["ref"]: p for p in parts}
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    native = {
        (n.attrib["ref"], n.attrib["pin"]): net.attrib["name"].lstrip("/")
        for net in xml.find("nets")
        for n in net
        if n.tag == "node" and not n.attrib["ref"].startswith("#")
    }
    rows = []
    for ref, part in by.items():
        if not part["part"].startswith("TPS3890"):
            continue
        pins = component_contract(part)
        board_contract(part, fps[ref])
        sym = next(
            s
            for s in children(sch, "symbol")
            if any(p[1] == "Reference" and p[2] == ref for p in children(s, "property"))
        )
        embedded = next(
            s for s in children(first(sch, "lib_symbols"), "symbol") if s[1] == first(sym, "lib_id")[1]
        )
        actual = {}
        for unit in children(embedded, "symbol"):
            for p in children(unit, "pin"):
                actual[str(first(p, "number")[1])] = (first(p, "name")[1], str(p[1]))
        assert actual == {k: (v["name"], v["kind"]) for k, v in pins.items()}
        assert all(native[(ref, n)] == p["net"] for n, p in pins.items())
        rows.append(
            dict(
                ref=ref,
                actual_part=part["part"],
                face=first(fps[ref], "layer")[1],
                pose_native_mm=first(fps[ref], "at")[1:],
                pin_roles={n: dict(name=p["name"], net=p["net"], kind=p["kind"]) for n, p in pins.items()},
                PCB_and_embedded_symbol_and_native_XML_match_primary=True,
            )
        )
    assert {r["ref"] for r in rows} == {"U19", "U20"}
    inputs = [
        SOURCE / p for p in ("rail_disconnect.kicad_pcb", "rail_disconnect.kicad_sch", "components.json")
    ] + [
        OUT / "coherent-native-netlist.xml",
        OUT / "tps3890-03.png",
        ROOT / "generated/r135-primary-review/ti-tps3890-SLVSD65A.pdf",
        Path(__file__),
    ]
    report = dict(
        primary="TI SLVSD65A page3, DSE six-pin WSON TOP view; visually reviewed",
        source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        rows=rows,
        swapped_pin_defect_in_current_E28=False,
        no_source_or_wiring_changed=True,
        physical_qualified=False,
    )
    (OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
