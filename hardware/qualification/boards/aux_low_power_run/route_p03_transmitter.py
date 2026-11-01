"""Bounded additions driven by actual P03 native missing connections."""

import argparse
import hashlib
import json
import math
import re
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.power_distribution.p03.route import PowerRouter, coded, named

WORK = Path(__file__).resolve().parents[4] / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter"
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--components", action="store_true")
    args = parser.parse_args()
    assert all(s and all(c.isalnum() or c in "-_" for c in s) for s in (args.source, args.output))
    source = WORK / "generated" / args.source
    destination = WORK / "generated" / args.output
    assert not destination.exists()
    pcb = source / "power_p03.kicad_pcb"
    before = sha(pcb)
    tree = read_sexpr(pcb.read_text())
    # The NC pin stays physically unrouted, but parity requires its native
    # schematic-generated unconnected net identity rather than an empty net.
    nc = next(p for f in children(tree, "footprint") if any(v[1:3] == ["Reference", "U202"] for v in children(f, "property"))
              for p in children(f, "pad") if p[1] == "1")
    if not children(nc, "net"):
        nc.append([a("net"), "unconnected-(U202-NC-Pad1)"])
    tree = coded(tree)
    count, frozen = len(tree), sexpr(tree)
    rt = PowerRouter(tree)
    rt.max_search_nodes = 150000
    rt.search_bias = 2
    raw = json.loads((source / "drc.json").read_text())
    pads = json.loads((source / "pads.json").read_text())
    assert pads["source_pcb_sha256"] == before
    by_pad = {p["uuid"]: p for p in pads["pad_polygons"]}
    objects = {str(first(n, "uuid")[1]): n for kind in ("segment", "via") for n in children(tree, kind)}

    def endpoint(item, net):
        xy = (item["pos"]["x"]-100, item["pos"]["y"]-100)
        if item["uuid"] in by_pad:
            pad = by_pad[item["uuid"]]
            assert pad["net"] == net
            return dict(xy=tuple(v-100 for v in pad["position_mm"]), net=net,
                        layers=tuple(LAYERS.index(layer) for layer in pad["layers"]))
        node = objects[item["uuid"]]
        if node[0] == "via":
            layers = tuple(range(6))
        else:
            layers = (LAYERS.index(first(node, "layer")[1]),)
        return dict(xy=xy, net=net, layers=layers)

    results = []
    if args.components:
        from hardware.electronics.rail_disconnect.revision28 import component_routes
        from hardware.electronics.rail_disconnect.revision28.component_routes import connect_components

        component_routes.aid.STEP = .125
        rt.existing_via = lambda net, point: next((g for g in rt.geometry
            if g["kind"] == "via" and g["net"] == net and math.dist(g["xy"], point) < 1e-6), None)
        graph = json.loads((source/"components.json").read_text())
        assert all(sha(Path(p)) == digest for p, digest in graph["source_sha256"].items())

        def anchors(group):
            return [dict(xy=point, layers=p["layers"], uuid=p["uuid"], kind=p["kind"])
                    for p in group for point in [p["xy"]]+([p["end"]] if "end" in p else [])]

        for net, groups in sorted(graph["inventory"].items()):
            groups = sorted(groups, key=lambda g: sum(p["kind"] == "PAD" for p in g), reverse=True)
            root = anchors(groups[0])
            for group in groups[1:]:
                addition = anchors(group)
                result = connect_components(rt, dict(net=net, components=[addition, root]),
                                            width=.16 if net == "AX03_SOURCE_CT" else .2, budget=350000)
                results.append(dict(net=net, **result))
                print(net, result, flush=True)
                if result.get("connected"):
                    root += addition
    else:
        for finding in raw["unconnected_items"]:
            left, right = finding["items"]
            net = re.search(r"\[/([^]]+)\]", left["description"]).group(1)
            assert net in {"AGND", "V2V5_AUX", "POWER_RUN", "POWER_RUN_E28_LEAF", "AX03_SOURCE_RESET", "AX03_SOURCE_CT", "AX03_RUN_DRIVE"}
            first_point, last_point = endpoint(left, net), endpoint(right, net)
            connected = rt.connect(first_point, last_point, .25 if net in ("AGND", "V2V5_AUX") else .2)
            results.append(dict(net=net, source=first_point, target=last_point, connected=connected))
            print(net, connected, flush=True)
    assert sexpr(tree[:count]) == frozen
    for index, node in enumerate(tree[count:]):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:P03:AX03:{before}:{index}:{sexpr(node)}")))])
    destination.mkdir()
    result = destination / "power_p03.kicad_pcb"
    result.write_text(sexpr(named(tree))+"\n")
    assert sha(pcb) == before
    (destination / "routing.json").write_text(json.dumps(dict(source_pcb_sha256=before,
        output_pcb_sha256=sha(result), recipe_sha256=sha(Path(__file__)), attempts=results,
        only_copper_additions_and_NC_parity_metadata=True, native_validation_pending=True,
        physical_qualified=False, fabrication_released=False), indent=2)+"\n")


if __name__ == "__main__":
    run()
