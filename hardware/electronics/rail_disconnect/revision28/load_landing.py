"""Explicit engineering analog force landing; no connector/assembly approval.

Only J3.6 copper is widened along the header pitch direction in this variant.
The actual lead hole, port pose, neighboring lands and signal routes are kept.
Native checks and face-contact copper extraction remain mandatory.
"""

import copy
import hashlib
import json

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .integrate_positive import LIB
from .repair import ROOT

NAME = "Header6_PTH_AnalogForce_Oval24_Engineering"
LIBRARY = "RMX_E28:" + NAME
ORIGINAL = "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"


def widened(pad):
    assert str(pad[1]) == "6" and str(pad[2]) == "thru_hole"
    assert float(first(pad, "drill")[1]) == 1.0
    # J3 is rotated 90deg on this board, giving board-local X2.4/Y1.7.
    first(pad, "size")[1:] = [a("1.7"), a("2.4")]
    pad[3] = a("oval")


def main():
    pcb = ROOT / "rail_disconnect.kicad_pcb"
    sch = ROOT / "rail_disconnect.kicad_sch"
    parts_path = ROOT / "components.json"
    inputs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (pcb, sch, parts_path)}
    tree = read_sexpr(pcb.read_text())
    fp = next(
        f
        for f in children(tree, "footprint")
        if next(p[2] for p in children(f, "property") if p[1] == "Reference") == "J3"
    )
    assert str(fp[1]) == ORIGINAL
    assert list(map(float, first(fp, "at")[1:])) == [150, 137.5, 90]
    pad = next(p for p in children(fp, "pad") if p[1] == "6")
    original = copy.deepcopy(pad)
    widened(pad)
    fp[1] = LIBRARY
    source = LIB / "Connector_PinHeader_2.54mm.pretty/PinHeader_1x06_P2.54mm_Vertical.kicad_mod"
    pattern = read_sexpr(source.read_text())
    pattern[1] = NAME
    widened(next(p for p in children(pattern, "pad") if p[1] == "6"))
    target = ROOT / "RMX_E28.pretty" / (NAME + ".kicad_mod")
    schematic = read_sexpr(sch.read_text())
    for symbol in children(schematic, "symbol"):
        properties = {p[1]: p for p in children(symbol, "property")}
        if properties.get("Reference", [None, None, None])[2] == "J3":
            assert properties["Footprint"][2] == ORIGINAL
            properties["Footprint"][2] = LIBRARY
            break
    else:
        raise AssertionError("Actual J3 symbol missing")
    parts = json.loads(parts_path.read_text())
    part = next(p for p in parts if p["ref"] == "J3")
    part["footprint"] = LIBRARY
    target.write_text(sexpr(pattern) + "\n")
    pcb.write_text(sexpr(tree) + "\n")
    sch.write_text(sexpr(schematic) + "\n")
    parts_path.write_text(json.dumps(parts, indent=2) + "\n")
    receipt = dict(
        source_hashes=inputs,
        output_hashes={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (pcb, sch, parts_path, target)
        },
        original_library_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        original_pad=sexpr(original),
        new_pad=sexpr(pad),
        board_local_copper_dimensions_mm=[2.4, 1.7],
        drill_mm=1.0,
        unchanged_port_center_mm=[62.7, 37.5],
        engineering_land_derivative=True,
        connector_mpn_selected=False,
        manufacturer_land_acceptance=False,
        current_and_temperature_qualified=False,
        native_all_severity_and_parity_check_required=True,
        terminal_contact_and_copper_extraction_required=True,
        physical_qualified=False,
    )
    (ROOT / "generated/analog-load-landing.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Actual J3.6 engineering oval landing", LIBRARY, "with unchanged1.0mm lead hole")


if __name__ == "__main__":
    main()
