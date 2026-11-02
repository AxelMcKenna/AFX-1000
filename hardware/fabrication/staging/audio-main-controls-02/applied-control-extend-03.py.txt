"""Bounded additive low-speed control routing with a protected analog reference."""

import argparse
import copy
import itertools
import json
import math
import shutil
import sys
import time
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, read_sexpr, sexpr
from hardware.fabrication.audio_main_control_routes import CONTROL_NETS
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-supplies-06"
OUT = ROOT / "staging/audio-main-controls-02"
LAYERS = ("F.Cu", "In2.Cu", "B.Cu")
HELPERS = ("route_nf_surface.py", "nf_minimum_logic.py", "nf_pin_escape_routes.py",
           "nf_multilayer_raster_directed.py", "nf_softstart_joint_screen.py",
           "nf_softstart_cell_routes.py", "nf_ct_leaf_cleanup.py")


def snapshot(label):
    path = OUT / ("applied-"+label+".py.txt")
    assert not path.exists()
    shutil.copyfile(Path(__file__), path)
    return path


def capture():
    from hardware.fabrication.audio_main_native_capture import capture as native_capture

    assert not OUT.exists()
    OUT.mkdir()
    applied = snapshot("input-capture")
    native_capture(SOURCE, OUT, 267, CONTROL_NETS, applied)
    assert sha(applied) == sha(Path(__file__))


class SignalScreen:
    def __init__(self, captured):
        from shapely.geometry import Point
        from shapely.ops import unary_union
        from shapely.strtree import STRtree

        from hardware.fabrication.route_nf_surface import shape

        self.outline = shape(captured["outline"]).buffer(-.61)
        self.via_outline = shape(captured["outline"]).buffer(-.81)
        self.reference = unary_union([shape(z["polygons"]) for z in captured["zones"]
                                     if z["layer"] == "In1.Cu" and not z["keepout"] and z["net"] == "AGND"])
        self.geometry = {layer: [] for layer in LAYERS}
        self.via_geometry, self.vias, self.new_vias, self.added = [], [], [], []
        for o in captured["objects"]:
            copper = shape([p for ps in o["layers"].values() for p in ps])
            if not copper.is_empty:
                self.via_geometry.append((o["net"], copper, o["kind"]))
            for layer, ps in o["layers"].items():
                if layer in self.geometry and ps:
                    self.geometry[layer].append((o["net"], shape(ps), .31))
            if o.get("npth"):
                radius = math.hypot(*o["drill_mm"])/2+.001
                hole = Point(o["position_mm"]).buffer(radius/math.cos(math.pi/128), quad_segs=32)
                self.via_geometry.append((None, hole, "HOLE"))
                for layer in LAYERS:
                    self.geometry[layer].append((None, hole, .36))
            if o["kind"] == "PCB_VIA":
                self.vias.append((o["net"], tuple(o["position_mm"])))
        protected = set()
        for z in captured["zones"]:
            if not z["keepout"] or not z["polygons"]:
                continue
            g = shape(z["polygons"])
            sensitive = not z["prohibit_tracks"] and z["layer"] in ("In1.Cu", "In2.Cu")
            # Keep the additional GPIO copper away from the protected analog
            # nodes on all three routed faces, including under the components.
            key = (g.wkb, sensitive)
            if sensitive and key not in protected:
                for layer in LAYERS:
                    self.geometry[layer].append((None, g, .11))
                self.via_geometry.append((None, g, "KEEPOUT"))
                protected.add(key)
            elif z["prohibit_tracks"] and z["layer"] in LAYERS:
                self.geometry[z["layer"]].append((None, g, .11))
            if z["prohibit_vias"]:
                self.via_geometry.append((None, g, "KEEPOUT"))
        self.trees = {layer: STRtree([g for _, g, _ in rows]) for layer, rows in self.geometry.items()}
        self.via_tree = STRtree([g for _, g, _ in self.via_geometry])
        self._added_count = self._via_count = -1

    def dynamic_indexes(self):
        from shapely.geometry import Point
        from shapely.strtree import STRtree

        if self._added_count != len(self.added):
            self._added_tree = STRtree([g for _, _, g in self.added])
            self._added_count = len(self.added)
        if self._via_count != len(self.vias)+len(self.new_vias):
            self._via_rows = self.vias+self.new_vias
            self._via_points = [Point(xy) for _, xy in self._via_rows]
            self._via_points_tree = STRtree(self._via_points)
            self._via_count = len(self._via_rows)

    def legal(self, net, layer, points):
        from shapely.geometry import LineString

        line = LineString(points)
        if line.length < 1e-7 or not self.outline.covers(line):
            return False
        for i in self.trees[layer].query(line.buffer(.5)):
            other, g, clearance = self.geometry[layer][int(i)]
            if other != net and line.distance(g) <= clearance:
                return False
        self.dynamic_indexes()
        for i in self._added_tree.query(line.buffer(.42)):
            other, face, g = self.added[int(i)]
            if face == layer and other != net and line.distance(g) <= .41:
                return False
        for i in self._via_points_tree.query(line.buffer(.62)):
            other, _ = self._via_rows[int(i)]
            distance = line.distance(self._via_points[int(i)])
            if other != net and distance <= .61:
                return False
            if other == net and 1e-7 < distance < .4:
                return False
        return True

    def via_legal(self, net, xy):
        from shapely.geometry import Point

        centred = [other for other, point in self.vias+self.new_vias if math.dist(point, xy) < 1e-7]
        if centred:
            return all(other == net for other in centred)
        p = Point(xy)
        if not self.via_outline.covers(p) or not self.reference.covers(p.buffer(.51)):
            return False
        if any(math.dist(point, xy) <= .86 for _, point in self.vias+self.new_vias):
            return False
        for i in self.via_tree.query(p.buffer(.7)):
            other, g, kind = self.via_geometry[int(i)]
            clearance = .41 if kind == "HOLE" else .31 if kind == "KEEPOUT" or other == net else .51
            if p.distance(g) <= clearance:
                return False
        return all(p.distance(g) > (.411 if other == net else .611) for other, _, g in self.added)


def via_mask(screen, net, xs, ys):
    import numpy as np
    from shapely import contains_xy
    from shapely.geometry import Point
    from shapely.ops import unary_union

    xx, yy = np.meshgrid(xs, ys)
    obstacles = [g.buffer((.41 if kind == "HOLE" else .31 if kind == "KEEPOUT" or other == net else .51)+.003)
                 for other, g, kind in screen.via_geometry]
    obstacles += [Point(p).buffer(.863) for _, p in screen.vias+screen.new_vias]
    obstacles += [g.buffer(.413 if other == net else .613) for other, _, g in screen.added]
    valid = contains_xy(screen.via_outline, xx, yy) & contains_xy(screen.reference.buffer(-.511), xx, yy)
    if obstacles:
        valid &= ~contains_xy(unary_union(obstacles), xx, yy)
    return valid


def exact_fanouts(screen, pad, group, limit=4):
    from shapely.geometry import LineString

    from hardware.fabrication.route_nf_surface import candidate_paths, shape

    net, start = pad["net"], pad["position_mm"]
    face = next(layer for layer in ("F.Cu", "B.Cu") if pad["layers"].get(layer))
    left, top, right, bottom = shape(pad["layers"][face]).bounds
    x, y = start
    sites = set()
    for offset in (0, .25, -.25, .5, -.5, .75, -.75, 1., -1., 1.5, -1.5):
        for gap in (.32, .57, .82, 1.07, 1.32, 1.57):
            sites.update(((left-gap, y+offset), (right+gap, y+offset), (x+offset, top-gap), (x+offset, bottom+gap)))
    result = []
    for xy in sorted(sites, key=lambda p: (math.dist(start, p), p)):
        if math.dist(start, xy) > 3.5 or not screen.via_legal(net, xy):
            continue
        if any(math.dist(xy, row["point"]) < .39 for row in result):
            continue
        paths = []
        for points in candidate_paths(start, xy):
            points = [p for i, p in enumerate(points) if not i or p != points[i-1]]
            length = LineString(points).length
            if length <= 3.5 and screen.legal(net, face, points):
                paths.append((length, points))
        if paths:
            length, points = min(paths, key=lambda row: row[0])
            result.append(dict(point=xy, layers=list(LAYERS), runs=[(face, points)], vias=[xy],
                               cost=length+2.5, group=group, pad=[pad["ref"], pad["pin"]]))
        if len(result) >= limit:
            break
    return result


def plan(captured, seconds=300, seed_routes=None, per_route=20):
    # The legacy raster implementation changes default NF widths on import.
    # Configure this isolated host-planning process explicitly; the native
    # reviewer and the independent auditor do not import the search module.
    from shapely.geometry import LineString

    import hardware.fabrication.nf_multilayer_raster_directed as search
    import hardware.fabrication.nf_pin_escape_routes as raster
    import hardware.fabrication.route_nf_surface as surface

    surface.WIDTH = raster.WIDTH = search.WIDTH = .2
    surface.MARGIN = .01
    search.LAYERS = LAYERS
    search.via_mask = via_mask
    screen = SignalScreen(captured)
    objects = {o["uuid"]: o for o in captured["objects"]}
    routes, attempts = copy.deepcopy(seed_routes or []), []
    for row in routes:
        assert all(screen.legal(row["net"], layer, points) for layer, points in row["runs"])
        assert all(screen.via_legal(row["net"], p) for p in row["new_vias_mm"])
        for layer, points in row["runs"]:
            screen.added.append((row["net"], layer, LineString(points)))
        screen.new_vias.extend((row["net"], p) for p in row["new_vias_mm"])
    deadline = time.monotonic()+seconds
    nets = sorted({objects[ids[0]]["net"] for ids in captured["groups"].values()})
    assert set(nets) <= CONTROL_NETS
    for net in nets:
        groups = []
        for key, ids in captured["groups"].items():
            if objects[ids[0]]["net"] != net:
                continue
            assert any(objects[i]["kind"] == "PAD" and objects[i]["pin"] for i in ids)
            contacts = set()
            for ident in ids:
                o = objects[ident]
                for layer in LAYERS:
                    if o["layers"].get(layer):
                        for point in [o["position_mm"]]+([o["end_mm"]] if "end_mm" in o else []):
                            contacts.add((layer, tuple(point)))
            groups.append(dict(keys={key}, contacts=contacts))
        for row in routes:
            if row["net"] != net:
                continue
            left_keys, right_keys = [set(side) for side in row["source_groups"]]
            i = next(i for i, g in enumerate(groups) if g["keys"] == left_keys)
            j = next(i for i, g in enumerate(groups) if g["keys"] == right_keys)
            assert i != j
            left, right = groups[i], groups[j]
            left["keys"].update(right["keys"])
            left["contacts"].update(right["contacts"])
            for layer, points in row["runs"]:
                left["contacts"].update((layer, tuple(p)) for p in points)
            for p in row["new_vias_mm"]:
                left["contacts"].update((layer, tuple(p)) for layer in LAYERS)
            groups.pop(j)
        failed = set()
        while len(groups) > 1 and time.monotonic() < deadline:
            choices = []
            for i, j in itertools.combinations(range(len(groups)), 2):
                key = (tuple(sorted(groups[i]["keys"])), tuple(sorted(groups[j]["keys"])))
                if key not in failed:
                    distance = min(math.dist(p, q) for _, p in groups[i]["contacts"] for _, q in groups[j]["contacts"])
                    choices.append((distance, i, j, key))
            if not choices:
                break
            _, i, j, key = min(choices)
            left, right = groups[i], groups[j]

            def portal(layer, point, group):
                return dict(point=point, layers=[layer], runs=[], vias=[], cost=0., group=group)

            starts = [portal(layer, p, min(left["keys"])) for layer, p in sorted(left["contacts"])]
            ends = {layer: [portal(layer, p, min(right["keys"])) for face, p in sorted(right["contacts"]) if face == layer] for layer in LAYERS}
            for key_id in sorted(left["keys"]):
                for ident in captured["groups"][key_id]:
                    pad = objects[ident]
                    if pad["kind"] == "PAD" and pad["pin"]:
                        starts.extend(exact_fanouts(screen, pad, key_id))
            for key_id in sorted(right["keys"]):
                for ident in captured["groups"][key_id]:
                    pad = objects[ident]
                    if pad["kind"] != "PAD" or not pad["pin"]:
                        continue
                    for row in exact_fanouts(screen, pad, key_id):
                        reversed_row = dict(row, runs=[(face, list(reversed(points))) for face, points in reversed(row["runs"])])
                        for layer in LAYERS:
                            ends[layer].append(reversed_row)
            result = search.route_multi(screen, net, starts, ends, min(deadline, time.monotonic()+per_route), max_visits=500000)
            attempt = dict(net=net, source_groups=[list(key[0]), list(key[1])], accepted=False)
            if result:
                fresh = [p for p in result["vias"] if not any(other == net and math.dist(p, q) < 1e-7 for other, q in screen.vias+screen.new_vias)]
                length = sum(LineString(p).length for _, p in result["runs"])
                terminals = [result["runs"][0][1][0], result["runs"][-1][1][-1]]
                limit = min(180, 2.5*math.dist(*terminals)+10)
                if len(fresh) <= 4 and length <= limit and all(screen.via_legal(net, p) for p in fresh):
                    assert all(screen.legal(net, layer, points) for layer, points in result["runs"])
                    for layer, points in result["runs"]:
                        screen.added.append((net, layer, LineString(points)))
                        left["contacts"].update((layer, tuple(p)) for p in points)
                    for p in fresh:
                        screen.new_vias.append((net, p))
                        left["contacts"].update((layer, tuple(p)) for layer in LAYERS)
                    result.update(net=net, source_groups=attempt["source_groups"], new_vias_mm=fresh,
                                  planar_length_mm=length, maximum_planar_length_mm=limit, terminal_points_mm=terminals)
                    routes.append(result)
                    left["keys"].update(right["keys"])
                    left["contacts"].update(right["contacts"])
                    groups.pop(j)
                    attempt["accepted"] = True
                    print("Control", net, round(length, 3), "mm /", len(fresh), "new vias", flush=True)
                else:
                    attempt["reason"] = "Via-count, route-length or final drill screen"
            else:
                attempt["reason"] = "No route within bounded search"
            if not attempt["accepted"]:
                failed.add(key)
            attempts.append(attempt)
    return routes, attempts


def write_candidate(routes, attempts, applied, seconds, extra_inputs=(), per_route=20):
    board = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    parent = copy.deepcopy(board)
    nets = {str(n[2]): n[1] for n in children(board, "net")}
    tracks, vias = [], []
    for row in routes:
        for layer, points in row["runs"]:
            for start, end in zip(points, points[1:]):
                ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:AC04:global-controls02:{row['net']}:{layer}:{start}:{end}"))
                assert not any(r["uuid"] == ident for r in tracks)
                tracks.append(dict(uuid=ident, net=row["net"], layer=layer, start_mm=start, end_mm=end, width_mm=.2))
                board.append([a("segment"), [a("start"), *start], [a("end"), *end], [a("width"), .2],
                              [a("layer"), layer], [a("net"), nets[row["net"]]], [a("uuid"), ident]])
        for p in row["new_vias_mm"]:
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:AC04:global-control-via02:{row['net']}:{p}"))
            vias.append(dict(uuid=ident, net=row["net"], xy_mm=p, diameter_mm=.6, drill_mm=.3))
            board.append([a("via"), [a("at"), *p], [a("size"), .6], [a("drill"), .3],
                          [a("layers"), "F.Cu", "B.Cu"], [a("net"), nets[row["net"]]], [a("uuid"), ident]])
    assert board[:len(parent)] == parent
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            if (OUT / p.name).exists():
                assert (OUT / p.name).read_bytes() == p.read_bytes()
            else:
                shutil.copyfile(p, OUT / p.name)
    if not (OUT / "libraries").exists():
        shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    dest = OUT / "distribution-input.kicad_pcb"
    dest.write_text(sexpr(board)+"\n")
    inputs = [applied, SOURCE / "audio_core.kicad_pcb", SOURCE / "routing-handoff.json", OUT / "native-inputs.json", *extra_inputs]+[ROOT / p for p in HELPERS]
    report = dict(source_sha256=relative_hashes(inputs), authored_PCB_sha256=sha(dest), routes=routes, attempts=attempts,
                  added_segments=tracks, added_vias=vias, allowed_control_nets=sorted(CONTROL_NETS), signal_layers=LAYERS,
                  trace_width_mm=.2, clearance_mm=.2, planning_margin_mm=.01, search_seconds=seconds,
                  per_route_search_seconds=per_route, maximum_search_visits=500000,
                  via_diameter_mm=.6, drill_mm=.3, maximum_new_vias_per_join=4,
                  sensitive_analog_regions_protected_on_all_routed_layers=True,
                  all_parent_objects_exact_before_native_refill=True, native_checks_pending=True,
                  control_timing_signal_integrity_EMI_and_installed_fault_qualified=False, fabrication_released=False)
    (OUT / "distribution-construction.json").write_text(json.dumps(report, indent=2)+"\n")
    assert sha(applied) == sha(Path(__file__))
    print("Built", len(routes), "control joins /", len(tracks), "tracks /", len(vias), "vias")


def build(seconds, per_route):
    from hardware.fabrication.audit_audio_main_supply_completion import check

    assert check() == json.loads((SOURCE / "routing-handoff.json").read_text())
    assert not (OUT / "distribution-input.kicad_pcb").exists()
    applied = snapshot("control-build")
    captured = json.loads((OUT / "native-inputs.json").read_text())
    verify_hashes(captured["source_sha256"])
    routes, attempts = plan(captured, seconds, per_route=per_route)
    assert routes
    write_candidate(routes, attempts, applied, seconds, per_route=per_route)


def extend(seconds, per_route):
    assert not (OUT / "audio_core.kicad_pcb").exists(), "Do not rewrite a native-reviewed candidate"
    round_number = 1
    while (OUT / ("applied-control-extend"+("" if round_number == 1 else f"-{round_number:02}")+".py.txt")).exists():
        round_number += 1
    label = "control-extend"+("" if round_number == 1 else f"-{round_number:02}")
    applied = snapshot(label)
    original_path = OUT / "distribution-construction.json"
    original = json.loads(original_path.read_text())
    verify_hashes(original["source_sha256"])
    pcb = OUT / "distribution-input.kicad_pcb"
    assert sha(pcb) == original["authored_PCB_sha256"]
    captured = json.loads((OUT / "native-inputs.json").read_text())
    verify_hashes(captured["source_sha256"])
    routes, attempts = plan(captured, seconds, original["routes"], per_route)
    assert len(routes) >= len(original["routes"])
    if len(routes) == len(original["routes"]):
        result = dict(source_sha256=relative_hashes([applied, original_path, pcb]), attempts=attempts,
                      no_new_copper=True, fabrication_released=False)
        (OUT / f"extension-{round_number:02}-no-change.json").write_text(json.dumps(result, indent=2)+"\n")
    else:
        prefix = "initial" if round_number == 1 else f"intermediate-{round_number:02}"
        saved_pcb = OUT / (prefix+"-distribution-input.kicad_pcb")
        saved_record = OUT / (prefix+"-distribution-construction.json")
        assert not saved_pcb.exists() and not saved_record.exists()
        pcb.rename(saved_pcb)
        original_path.rename(saved_record)
        write_candidate(routes, original["attempts"]+attempts, applied, original["search_seconds"]+seconds,
                        (saved_pcb, saved_record), per_route)
    assert sha(applied) == sha(Path(__file__))


def native(action):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    applied = snapshot(action+"-entry")
    if action == "fill":
        from hardware.fabrication import audio_main_power_routes as helper

        helper.OUT = OUT
        helper.fill()
        result = OUT / "native-refill.json"
    else:
        from hardware.fabrication.audio_main_native_review import review

        review(OUT, SOURCE / "supply-connectivity-review.json", OUT / "native-inputs.json",
               OUT / "distribution-construction.json", applied)
        result = OUT / "terminal-connectivity-review.json"
    report = dict(source_sha256=relative_hashes([applied, result]), selected_output=str(OUT.relative_to(ROOT)), fabrication_released=False)
    (OUT / (action+"-entry.json")).write_text(json.dumps(report, indent=2)+"\n")
    assert sha(applied) == sha(Path(__file__))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "build", "extend", "fill", "review"))
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--per-route", type=int, default=20)
    args = parser.parse_args()
    assert 30 <= args.seconds <= 600
    assert 1 <= args.per_route <= 30
    {"capture": capture, "build": lambda: build(args.seconds, args.per_route), "extend": lambda: extend(args.seconds, args.per_route),
     "fill": lambda: native("fill"), "review": lambda: native("review")}[args.action]()
