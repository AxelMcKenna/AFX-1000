"""Orient the new nonpolar bypass toward U202 and reserve both local paths."""

import hashlib
import json
import uuid
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

WORK = Path(__file__).resolve().parents[4] / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter"


def run():
    source = WORK/"generated/native-closed-transmitter"
    output = WORK/"generated/buffer-bypass"
    assert not output.exists()
    pcb = source/"power_p03.kicad_pcb"
    digest = hashlib.sha256(pcb.read_bytes()).hexdigest()
    tree = read_sexpr(pcb.read_text())
    parent = read_sexpr((WORK.parent/"strict-native-centering/power_p03.kicad_pcb").read_text())
    original = {str(first(n,"uuid")[1]) for kind in ("segment","via") for n in children(parent,kind)}
    pads = json.loads((source/"pads.json").read_text())
    region = unary_union([Polygon(poly["outer"]) for p in pads["pad_polygons"] if p["ref"] == "C401"
                          for poly in p["layers"].get("F.Cu",[])])
    displaced = []
    for node in list(children(tree,"segment")):
        if first(node,"layer")[1] != "F.Cu" or first(node,"net")[1] not in ("/AGND","/V2V5_AUX"):
            continue
        line = LineString([tuple(map(float,first(node,k)[1:3])) for k in ("start","end")])
        if line.distance(region) < float(first(node,"width")[1])/2+.170001:
            assert str(first(node,"uuid")[1]) not in original, "Never displace original strict source copper"
            tree.remove(node)
            displaced.append(sexpr(node))
    assert displaced
    fp = next(f for f in children(tree,"footprint") if any(p[1:3] == ["Reference","C401"] for p in children(f,"property")))
    assert float(first(fp,"at")[3]) == 90
    first(fp,"at")[3] = a(270)
    routes = [
        ("V2V5_AUX",[(111.75,134.725),(113.85,134.4)]),
        ("AGND",[(111.75,136.275),(113.35,137.4),(115.15,137.4),(115.15,136.6)]),
        ("AGND",[(115.15,136.6),(115.9,137.7)]),
    ]
    for route_index,(net,points) in enumerate(routes):
        for index,(left,right) in enumerate(zip(points,points[1:])):
            key = str(uuid.uuid5(uuid.NAMESPACE_URL,f"rmx:P03:AX03:bufferbypass:{digest}:{route_index}:{index}"))
            tree.append(read_sexpr(f'(segment (start {left[0]} {left[1]}) (end {right[0]} {right[1]}) (width .25) (layer "F.Cu") (net "/{net}") (uuid "{key}"))'))
    key = str(uuid.uuid5(uuid.NAMESPACE_URL,f"rmx:P03:AX03:bufferbypass:{digest}:returnvia"))
    tree.append(read_sexpr(f'(via (at 115.9 137.7) (size .6) (drill .25) (layers "F.Cu" "B.Cu") (net "/AGND") (uuid "{key}"))'))
    output.mkdir()
    destination = output/pcb.name
    destination.write_text(sexpr(tree)+"\n")
    assert hashlib.sha256(pcb.read_bytes()).hexdigest() == digest
    (output/"buffer-bypass.json").write_text(json.dumps(dict(source_PCB_sha256=digest,
        output_PCB_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        removed_only_new_cap_branches=displaced, C401_rotation_before_after_deg=[90,270],
        C401_body_centre_unchanged=True, planned_direct_front_paths=routes,
        ordinary_ground_via_mm=[115.9,137.7,.6,.25], original_strict_source_objects_unchanged=True,
        native_full_validation_pending=True, physical_qualified=False, fabrication_released=False),indent=2)+"\n")
    print("Rotated only new C401; reserved local F bypass paths and an ordinary off-pad return via")


if __name__ == "__main__":
    run()
