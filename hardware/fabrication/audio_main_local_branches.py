"""Finish local endpoints with conventional escapes; keep HF capacitors direct."""

import argparse
import copy
import json
import math
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_candidate import sha

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "hardware/fabrication"
SOURCE = ROOT / "staging/audio-main-local-routing-01"
OUT = ROOT / "staging/audio-main-local-routing-02"


def corrected_requests(captured, construction):
    pads = {(p["ref"], p["pin"]): p for p in captured["objects"] if p["pin"]}
    types = {(n.attrib["ref"], n.attrib["pin"]): n.attrib["pintype"]
             for n in ET.parse(SOURCE / "native-netlist.xml").findall("nets/net/node")}
    requests = []
    for row in construction["requests"]:
        if row["kind"] != "local_ground_return":
            requests.append(copy.deepcopy(row))
            continue
        p = pads[(row["ref"], "2")]
        candidates = [q for key, q in pads.items() if key[0] == row["owner"] and q["net"] == "AGND"
                      and types.get(key) == "power_in"]
        if candidates:
            q = min(candidates, key=lambda q: math.dist(p["position_mm"], q["position_mm"]))
            requests.append(dict(row, owner_pin=q["pin"]))
    assert len(requests) == 151
    return requests


def build():
    from shapely.geometry import LineString, Point
    from shapely.ops import substring

    from hardware.fabrication.route_nf_surface import Screen, candidate_paths, shape

    assert not OUT.exists()
    old = json.loads((SOURCE / "construction.json").read_text())
    verify_hashes(old["source_sha256"])
    assert sha(SOURCE / "audio_core.kicad_pcb") == old["candidate_PCB_sha256"]
    native = json.loads((SOURCE / "local-connectivity-review.json").read_text())
    verify_hashes(native["source_sha256"])
    captured = json.loads((SOURCE / "native-inputs.json").read_text())
    verify_hashes(captured["source_sha256"])
    pads = {(p["ref"], p["pin"]): p for p in captured["objects"] if p["pin"]}
    requests = corrected_requests(captured, old)
    identities = {(r["ref"], r["pin"], r["owner"], r["owner_pin"]): r for r in requests}
    def key(row):
        return row["ref"], row["pin"], row["owner"], row["owner_pin"]

    retained = [r for r in old["routes"] if key(r) in identities]
    removed = [r for r in old["routes"] if key(r) not in identities]
    assert [(r["ref"], r["pin"], r["owner_pin"]) for r in removed] == [("C612", "2", "13")]
    removed_ids = {v for r in removed for v in r["segment_uuids"]}
    assert removed_ids.isdisjoint({v for r in retained for v in r["segment_uuids"]})
    board = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    board = [n for n in board if not isinstance(n, list) or not n or n[0] != "segment"
             or first(n, "uuid")[1] not in removed_ids]
    before = sexpr(board)
    baseline_count = len(board)
    nets = {str(n[2]): int(n[1]) for n in children(board, "net")}
    screen = Screen(captured)
    for row in retained:
        screen.added.append((row["net"], row["layer"], LineString(row["path_mm"])))
    routes = copy.deepcopy(retained)
    deferred, added, vias = [], [], []
    copper = [(p["net"], layer, shape(ps), p) for p in captured["objects"]
              for layer, ps in p["layers"].items() if ps]

    def via_sites(pad, layer, net):
        x, y = pad["position_mm"]
        left, top, right, bottom = shape(pad["layers"][layer]).bounds
        sites = []
        for offset in (0, .25, -.25, .5, -.5, .75, -.75):
            for xy in ((left - .32, y + offset), (right + .32, y + offset),
                       (x + offset, top - .32), (x + offset, bottom + .32)):
                point = Point(xy)
                if not shape(captured["outline"]).buffer(-.81).covers(point):
                    continue
                if any(point.distance(g) < (.511 if other != net else 0)
                       or (not any(p["drill_mm"]) and point.distance(g) < .301)
                       for other, _, g, p in copper):
                    continue
                if any(any(p["drill_mm"]) and math.dist(xy, p["position_mm"]) < .15 + max(p["drill_mm"]) / 2 + .261
                       for p in captured["objects"]):
                    continue
                if any(point.distance(g) < .611 for other, _, g in screen.added if other != net):
                    continue
                if any(math.dist(xy, v["xy_mm"]) < (.561 if v["net"] == net else .811) for v in vias):
                    continue
                if any(point.distance(shape(z["polygons"])) < .31 for z in captured["zones"] if z["keepout"]):
                    continue
                if screen.legal(net, layer, [pad["position_mm"], xy]):
                    sites.append((math.dist(xy, pad["position_mm"]), xy))
        return [xy for _, xy in sorted(set(sites))[:12]]

    done = {key(r) for r in routes}
    for row in requests:
        if key(row) in done:
            continue
        start = tuple(pads[(row["ref"], row["pin"])]["position_mm"])
        end = tuple(pads[(row["owner"], row["owner_pin"])]["position_mm"])
        trunks = [r for r in routes if r["owner"] == row["owner"] and r["owner_pin"] == row["owner_pin"]
                  and r["net"] == row["net"] and r["layer"] == row["layer"]]
        choices = []
        targets = [(end, [end], [])]
        for trunk in trunks:
            line = LineString(trunk["path_mm"])
            distances = {0.0, line.length, line.project(Point(start))}
            distances.update(line.project(Point(p)) for p in trunk["path_mm"])
            for distance in distances:
                point = line.interpolate(distance)
                xy = (point.x, point.y)
                tail = substring(line, distance, line.length)
                path = list(tail.coords) if tail.geom_type == "LineString" else [xy]
                targets.append((xy, path, trunk["segment_uuids"]))
        for xy, tail, inherited_ids in targets:
            for path in candidate_paths(start, xy):
                path = [p for i, p in enumerate(path) if not i or p != path[i - 1]]
                if len(path) < 2:
                    continue
                witness = path + tail[1:]
                length = sum(math.dist(p, q) for p, q in zip(witness, witness[1:]))
                if length <= row["route_length_limit_mm"] and screen.legal(row["net"], row["layer"], path):
                    choices.append((length, path, witness, inherited_ids))
        via_choice = None
        if not choices and row["kind"] != "local_ground_return":
            layer = row["layer"]
            other = "B.Cu" if layer == "F.Cu" else "F.Cu"
            p, q = pads[(row["ref"], row["pin"])], pads[(row["owner"], row["owner_pin"])]
            for u in via_sites(p, layer, row["net"]):
                for v in via_sites(q, layer, row["net"]):
                    if math.dist(u, v) < .561:
                        continue
                    for middle in candidate_paths(u, v):
                        middle = [p for i, p in enumerate(middle) if not i or p != middle[i - 1]]
                        length = math.dist(start, u) + math.dist(v, end) + sum(
                            math.dist(p, q) for p, q in zip(middle, middle[1:]))
                        if length <= row["route_length_limit_mm"] and screen.legal(row["net"], other, middle):
                            if via_choice is None or length < via_choice[0]:
                                via_choice = length, [(layer, [start, u]), (other, middle), (layer, [v, end])], [u, v]
        if not choices and via_choice is None:
            deferred.append(dict(row, reason="No short same-face branch; plane or local placement work remains"))
            continue
        if choices:
            length, path, witness, inherited_ids = min(choices, key=lambda r: r[0])
            paths, new_vias = [(row["layer"], path)], []
        else:
            length, paths, new_vias = via_choice
            witness, inherited_ids = [], []
        ids = []
        for layer, path in paths:
            for p, q in zip(path, path[1:]):
                ident = str(uuid.uuid5(uuid.NAMESPACE_URL,
                    f"AFX:AC04:branch:{sha(SOURCE / 'audio_core.kicad_pcb')}:{row['net']}:{layer}:{p}:{q}"))
                ids.append(ident)
                board.append([a("segment"), [a("start"), *p], [a("end"), *q], [a("width"), .2],
                              [a("layer"), layer], [a("net"), nets[row["net"]]], [a("uuid"), ident]])
            screen.added.append((row["net"], layer, LineString(path)))
        via_ids = []
        for xy in new_vias:
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:AC04:escape:{row['net']}:{xy}"))
            via_ids.append(ident)
            board.append([a("via"), [a("at"), *xy], [a("size"), .6], [a("drill"), .3],
                          [a("layers"), "F.Cu", "B.Cu"], [a("net"), nets[row["net"]]], [a("uuid"), ident]])
            vias.append(dict(uuid=ident, net=row["net"], xy_mm=xy, diameter_mm=.6, drill_mm=.3))
            for layer in ("F.Cu", "B.Cu"):
                screen.added.append((row["net"], layer, Point(xy).buffer(.2)))
        result = dict(row, actual_length_mm=length, paths=paths, path_mm=witness,
                      segment_uuids=ids, via_uuids=via_ids, inherited_trunk_segment_uuids=inherited_ids,
                      nominal_via_barrel_traversal_mm=len(new_vias) * 1.6)
        routes.append(result)
        added.append(result)
        print("Branched", row["ref"], row["pin"], "to", row["owner"], row["owner_pin"], round(length, 3), "mm")
    assert sexpr(board[:baseline_count]) == before and len(added) >= 1
    OUT.mkdir()
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in (
                "plan.json", "fp-lib-table", "sym-lib-table"):
            shutil.copyfile(p, OUT / p.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    dest = OUT / "audio_core.kicad_pcb"
    dest.write_text(sexpr(board) + "\n")
    inputs = [Path(__file__), ROOT / "audio_main_local_routes.py", ROOT / "route_nf_surface.py",
              SOURCE / "audio_core.kicad_pcb", SOURCE / "construction.json", SOURCE / "native-inputs.json",
              SOURCE / "local-connectivity-review.json", OUT / "audio_core.kicad_dru"]
    report = dict(source_sha256=relative_hashes(inputs), candidate_PCB_sha256=sha(dest),
                  requests=requests, routes=routes, deferred=deferred, added_branches=added,
                  removed_routes=removed, removed_segment_uuids=sorted(removed_ids),
                  removal_reason="C612 bypass return must not terminate at logic input U608.13; actual power ground is U608.7",
                  bypass_ground_targets_are_native_schematic_power_inputs=True,
                  width_mm=.2, general_clearance_mm=.2, inner_layer_tracks=False, added_vias=vias,
                  high_frequency_compensation_capacitor_routes_unchanged=True,
                  trace_length_budgets_exclude_separately_recorded_via_barrel_traversal=True,
                  all_nonremoved_authored_geometry_exact=True, native_checks_pending=True,
                  complete_return_distribution_and_audio_qualification=False, fabrication_released=False)
    (OUT / "construction.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Local pairs", len(routes), "; unresolved", len(deferred), "; added", len(added))


def review():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    from hardware.fabrication import audio_main_placement

    construction = json.loads((OUT / "construction.json").read_text())
    verify_hashes(construction["source_sha256"])
    assert sha(OUT / "audio_core.kicad_pcb") == construction["candidate_PCB_sha256"]
    before = relative_hashes([Path(__file__), OUT / "audio_core.kicad_dru", OUT / "construction.json"])
    audio_main_placement.OUT = OUT
    audio_main_placement.review()
    board = pcbnew.LoadBoard(str(OUT / "audio_core.kicad_pcb"))
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    pads = {(f.GetReference(), p.GetNumber()): p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
    witnesses = []
    for row in construction["routes"]:
        p, q = pads[(row["ref"], row["pin"])], pads[(row["owner"], row["owner_pin"])]
        assert p.GetNetname() == q.GetNetname() == row["net"]
        assert q.m_Uuid.AsString() in {v.m_Uuid.AsString() for v in conn.GetConnectedItems(p)}
        witnesses.append(dict(ref=row["ref"], pin=row["pin"], owner=row["owner"],
                              owner_pin=row["owner_pin"], native_connected=True))
    verify_hashes(before)
    before.update(relative_hashes([OUT / p for p in (
        "audio_core.kicad_pcb", "placement-native-review.json", "native-netlist.xml")]))
    result = dict(source_sha256=before, native_version=pcbnew.GetBuildVersion(), connections=witnesses,
                  uncapped_open_connections=conn.GetUnconnectedCount(False), original_open_connections=724,
                  native_via_count=sum(p.GetClass() == "PCB_VIA" for p in board.GetTracks()),
                  complete_routing_and_qualification=False, fabrication_released=False)
    (OUT / "local-connectivity-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Native connected", len(witnesses), "pairs; remaining opens", result["uncapped_open_connections"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "review"))
    args = parser.parse_args()
    {"build": build, "review": review}[args.action]()
