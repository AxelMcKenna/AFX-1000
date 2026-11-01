"""Reserve two fine-pitch escapes before routing other AX03 signals."""

import hashlib
import json
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.power_distribution.p03.route import coded, named

WORK = Path(__file__).resolve().parents[4] / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter"


def run():
    source = WORK / "generated/placement/power_p03.kicad_pcb"
    output = WORK / "generated/local-fanout"
    assert not output.exists()
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    tree = read_sexpr(source.read_text())
    fp = next(f for f in children(tree, "footprint") if any(p[1:3] == ["Reference", "U201"] for p in children(f, "property")))
    assert list(map(float, first(fp, "at")[1:3])) == [104.5, 120.5]
    first(fp, "at")[1] = a(104)
    nc = next(p for f in children(tree, "footprint") if any(v[1:3] == ["Reference", "U202"] for v in children(f, "property"))
              for p in children(f, "pad") if p[1] == "1")
    nc.append([a("net"), "unconnected-(U202-NC-Pad1)"])
    tree = coded(tree)
    codes = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    for net, start, end, width in (
        ("POWER_RUN", (103.45, 120), (103.45, 119.25), .2),
        ("AX03_SOURCE_CT", (104.6, 120.5), (105.3, 120.5), .16),
        ("AX03_SOURCE_CT", (102.225, 118), (101.25, 118), .2),
    ):
        for kind, geometry in (
            ("segment", f'(start {start[0]} {start[1]}) (end {end[0]} {end[1]}) (width {width}) (layer "F.Cu")'),
            ("via", f'(at {end[0]} {end[1]}) (size .6) (drill .25) (layers "F.Cu" "B.Cu")'),
        ):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:P03:AX03:escape:{before}:{net}:{kind}:{geometry}"))
            tree.append(read_sexpr(f'({kind} {geometry} (net {codes[net]}) (uuid "{uid}"))'))
    output.mkdir()
    pcb = output / source.name
    pcb.write_text(sexpr(named(tree))+"\n")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    (output/"fanout.json").write_text(json.dumps(dict(source_pcb_sha256=before,
        output_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
        U201_shift_mm=[-.5, 0], only_new_controller_moved=True, original_parts_and_copper_preserved=True,
        new_through_vias=3, new_via_land_mm=.6, new_via_drill_mm=.25,
        added_vias_outside_new_SMD_paste_lands=True, native_clearance_and_routing_pending=True,
        physical_qualified=False, fabrication_released=False), indent=2)+"\n")
    print("Reserved three ordinary .6/.25mm escape vias; moved only new U201 by0.5mm")


if __name__ == "__main__":
    run()
