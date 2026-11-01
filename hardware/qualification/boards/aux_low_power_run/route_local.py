"""Exact local surface escapes for the three remaining AX03 connections."""

import argparse
import json
import math
import uuid
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision26 import router as aid
from hardware.electronics.rail_disconnect.revision26.layout import POWER_NETS
from hardware.electronics.rail_disconnect.revision28.band_router import BandRouter
from hardware.electronics.rail_disconnect.revision28.component_routes import connect_components
from hardware.electronics.rail_disconnect.revision28.focused import legal_line
from hardware.electronics.rail_disconnect.revision28.receiver_surface_path import connect

from .route_e28 import WORK, sha


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--direct-pose", action="store_true")
    args = parser.parse_args()
    source = WORK / ("generated/receiver-direct-pose/rail_disconnect.kicad_pcb" if args.direct_pose else "rail_disconnect.kicad_pcb")
    out = WORK / ("generated/receiver-direct-routes" if args.direct_pose else "generated/receiver-priority-routes")
    out.mkdir(exist_ok=False)
    original = source.read_bytes()
    tree = read_sexpr(original.decode())
    count = len(tree)
    frozen = sexpr(tree)
    filled_path = WORK / ("generated/native-direct-pose-checked/rail_disconnect.kicad_pcb" if args.direct_pose else "generated/native-placement/rail_disconnect.kicad_pcb")
    filled = read_sexpr(filled_path.read_text())
    pads = json.loads((WORK / "generated/routing-inputs/pads.json").read_text())
    rt = BandRouter(tree, filled, pads, step=0.05)
    power = {}
    for zone in children(filled, "zone"):
        if not children(zone, "net") or str(first(zone, "net")[-1]).lstrip("/") not in POWER_NETS:
            continue
        for poly in children(zone, "filled_polygon"):
            layer = aid.LAYERS.index(str(first(poly, "layer")[1]))
            points = [(float(p[1])-100, float(p[2])-100) for p in first(poly, "pts")[1:]]
            power.setdefault(layer, []).append(Polygon(points).buffer(0))
    power = {layer: unary_union(polys) for layer, polys in power.items()}

    def surface(pad, targets):
        assert all(p["net"] == pad["net"] for p in targets)
        start = len(rt.routes)
        result, reason = connect(rt, pad, targets, radius=12, step=0.025, budget=350000)
        aid.STEP = 0.05
        if result:
            for route in rt.routes[start:]:
                shape = LineString(route["points_relative_mm"]).buffer(0.1+0.2+0.02)
                assert not power.get(pad["layers"][0], Polygon()).intersects(shape), "Power-pour cut rejected"
        return dict(connected=bool(result), result=result, reason=reason)

    results = []
    vcc = next(p for p in rt.by_ref["U43"] if p["pin"] == "5")
    cap = next(p for p in rt.by_ref["C86"] if p["pin"] == "1")
    vcc_face = vcc["layers"][0]
    assert legal_line(rt, "V2V5_AUX", vcc_face, vcc["xy"], cap["xy"], 0.2)
    assert not power.get(vcc_face, Polygon()).intersects(LineString([vcc["xy"],cap["xy"]]).buffer(.32))
    rt.path("V2V5_AUX", vcc_face, [vcc["xy"], cap["xy"]], 0.2)
    targets = [dict(xy=g["xy"], layers=g["layers"], net=g["net"])
               for g in rt.geometry if g["kind"] == "via" and g["net"] == "V2V5_AUX"]
    targets.sort(key=lambda p: math.dist(vcc["xy"], p["xy"]))
    power_targets = targets[:50]
    # Escape the output before adding the raw RUN and ground branches, which
    # otherwise consume the narrow surface corridor beside the new package.

    escaped = []
    for ref, pin in (("U28", "1"), ("U43", "4")):
        pad = next(p for p in rt.by_ref[ref] if p["pin"] == pin)
        rt.cached = {}
        blocked, via = rt.masks("RUN_BUFFERED", .2)
        blocked, via = rt.force_guard.apply("RUN_BUFFERED", blocked, via, .2)
        x, y = pad["xy"]
        d2 = (rt.xx-x)**2 + (rt.yy-y)**2
        ix, iy = np.where((d2 < 8**2) & ~via & ~blocked[pad["layers"][0]])
        choices = sorted(zip(ix,iy), key=lambda q: float(d2[q]))
        targets = []
        for u, v in choices:
            xy = (round(u*.05,6), round(v*.05,6))
            if all(math.dist(xy, p["xy"]) >= .65 for p in targets):
                targets.append(dict(xy=xy, layers=tuple(range(6)), net="RUN_BUFFERED"))
            if len(targets) == 60:
                break
        result = surface(pad, targets)
        if result["connected"]:
            target = result["result"]["target"]
            rt.via("RUN_BUFFERED", target["xy"])
            escaped.append(dict(xy=target["xy"], layers=list(range(6)), kind="PCB_VIA", ref=ref))
        results.append(dict(net="RUN_BUFFERED", ref=ref, **result))
        print(ref, "escape", result["connected"], result["reason"], flush=True)
    if len(escaped) == 2:
        rt.cached = {}
        result = connect_components(rt, dict(net="RUN_BUFFERED", components=[[escaped[0]],[escaped[1]]]),
                                    width=.2, budget=600000)
        results.append(dict(net="RUN_BUFFERED", stage="join_escapes", **result))
        print("RUN_BUFFERED join", result.get("connected"), result.get("reason"), flush=True)
    result = surface(vcc, power_targets)
    results.append(dict(net="V2V5_AUX", **result))
    print("V2V5_AUX local", result["connected"], result["reason"], flush=True)
    inventory = json.loads((WORK / "generated/routing-inputs/components.json").read_text())
    for net, ref, pin in (("POWER_RUN","U43","2"),("AGND","U43","3"),("AGND","C86","2")):
        pad = next(p for p in rt.by_ref[ref] if p["pin"] == pin)
        groups = inventory["inventory"][net]["components"]
        old = [g for g in groups if not any(p.get("ref") in ("U43","C86") for p in g)]
        group = max(old, key=lambda g: sum(p["kind"] == "PAD" for p in g))
        endpoints = []
        for obj in group:
            for xy in [obj["position_mm"]] + ([obj["end_mm"]] if obj["kind"] == "PCB_TRACK" else []):
                endpoints.append(dict(xy=xy, layers=obj["layers"], kind=obj["kind"], ref=obj.get("ref")))
        rt.cached = {}
        result = connect_components(rt, dict(net=net, components=[[dict(xy=pad["xy"],layers=pad["layers"],kind="PAD",ref=ref)],endpoints]),
                                    width=.2, budget=600000)
        results.append(dict(net=net, ref=ref, **result))
        print(net,ref,result.get("connected"),result.get("reason"),flush=True)
    assert sexpr(tree[:count]) == frozen
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL,
                        f"rmx:AX03:local:{sha(source)}:{index}:{sexpr(node)}")))])
    pcb = out / source.name
    pcb.write_text(sexpr(tree)+"\n")
    (out / "routes.json").write_text(json.dumps(dict(source_sha256=sha(source),
        candidate_sha256=sha(pcb), recipe_sha256=sha(Path(__file__)),
        results=results, routes=rt.routes, existing_source_geometry_unchanged=True,
        actual_filled_force_guarded=True, native_checks_pending=True, fabrication_released=False),indent=2)+"\n")
    assert source.read_bytes() == original


if __name__ == "__main__":
    run()
