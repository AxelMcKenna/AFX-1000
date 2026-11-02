"""Complete remaining placed supply islands with conventional plated bridges."""

import argparse
import copy
import json
import math
import shutil
import sys
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, read_sexpr, sexpr
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audio_main_power_routes import RAILS, InnerGrid
from hardware.fabrication.audio_main_supply_completion import RoutingSpace
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-supplies-03"
OUT = ROOT / "staging/audio-main-supplies-06"


class FineGrid(InnerGrid):
    step = .1

    def __init__(self, free):
        import numpy as np
        from shapely import contains_xy, prepare

        self.free = free
        self.safe = free.buffer(-self.step/math.sqrt(2)-.001)
        prepare(self.safe)
        xx, yy = np.meshgrid(np.arange(0, 150.05, self.step), np.arange(0, 63.05, self.step))
        self.mask = contains_xy(self.safe, xx, yy)
        self.height, self.width = self.mask.shape

    @staticmethod
    def xy(key):
        return [round(v*.1, 6) for v in key]

    def anchors(self, xy):
        from shapely.geometry import LineString, Point

        cx, cy = (round(v/self.step) for v in xy)
        candidates = [(cx+i, cy+j) for i in range(-8, 9) for j in range(-8, 9)]
        result = []
        for x, y in sorted(candidates, key=lambda k: math.dist(xy, self.xy(k))):
            if 0 <= x < self.width and 0 <= y < self.height and self.mask[y, x]:
                point = self.xy((x, y))
                bridge = Point(xy) if math.dist(xy, point) < 1e-8 else LineString([xy, point])
                if self.free.covers(bridge):
                    result.append((x, y))
        return result[:4]


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
    native_capture(SOURCE, OUT, 278, RAILS, applied)
    assert sha(applied) == sha(Path(__file__))


def expanded_choices(context, objects, net):
    from shapely.geometry import LineString

    from hardware.fabrication.route_nf_surface import candidate_paths

    results = [r for r in context.choices(objects, net) if all(
        context.free_layer(net, layer, .2).covers(LineString(points)) for layer, points in r["paths"])]
    if results:
        return results
    for pad in [o for o in objects if o["kind"] == "PAD" and o["pin"]]:
        layer = next(l for l in ("F.Cu", "B.Cu") if l in pad["layers"])
        free = context.free_layer(net, layer, .2)
        x, y = pad["position_mm"]
        sites = [(round(x+i*.2, 6), round(y+j*.2, 6)) for i in range(-16, 17) for j in range(-16, 17)
                 if .4 < math.hypot(i*.2, j*.2) < 3.3]
        for xy in sorted(sites, key=lambda p: (math.dist((x, y), p), p)):
            if not context.via_ok(net, xy):
                continue
            for points in candidate_paths((x, y), xy):
                points = [p for i, p in enumerate(points) if not i or p != points[i-1]]
                length = sum(math.dist(p, q) for p, q in zip(points, points[1:]))
                if length <= 3.5 and free.covers(LineString(points)):
                    results.append(dict(xy_mm=xy, endpoint_uuid=pad["uuid"], paths=[(layer, points)],
                                        fanout_length_mm=length, added_via=True))
        if results:
            break
    return sorted(results, key=lambda r: r["fanout_length_mm"])[:24]


def plan(captured):
    import numpy as np
    from shapely import contains_xy, prepare
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union

    from hardware.fabrication.route_nf_surface import shape

    objects = {o["uuid"]: o for o in captured["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in captured["objects"] if o["kind"] == "PAD" and o["pin"]}
    membership = {ident: key for key, ids in captured["groups"].items() for ident in ids}
    context = RoutingSpace(captured)
    joined = {net: {membership[pads[root]["uuid"]]} for net, root in RAILS.items()}
    roots_added, routes = [], []

    def root_shapes(net, layer):
        ids = [i for group in joined[net] for i in captured["groups"][group]]
        geoms = [shape(objects[i]["layers"][layer]) for i in ids if objects[i]["layers"].get(layer)]
        geoms += [g for other, face, g in context.added_shapes if other == net and face == layer]
        copper = unary_union(geoms)
        if context.new_vias:
            copper = copper.difference(unary_union([Point(xy).buffer(.9) for xy in context.new_vias]))
        return copper

    def free_for_route(net, layer, width, allowed_via=None):
        margin = width/2+.21
        obstacles = [g.buffer(margin) for o, face, g in context.copper if face == layer and o["net"] != net]
        obstacles += [g.buffer(width/2+.01) for o, face, g in context.copper if face == layer and o["net"] == net
                      and o["kind"] == "PCB_VIA" and o["uuid"] != allowed_via]
        for o in captured["objects"]:
            if o.get("npth"):
                obstacles.append(Point(o["position_mm"]).buffer(math.hypot(*o["drill_mm"])/2+.001+width/2+.26))
        obstacles += [shape(z["polygons"]).buffer(width/2+.01) for z in captured["zones"]
                      if z["keepout"] and z["layer"] == layer and z["prohibit_tracks"]]
        obstacles += [g.buffer(margin) for other, face, g in context.added_shapes if face == layer and other != net]
        outline = shape(captured["outline"]).buffer(-(.5+width/2+.01))
        return outline.difference(unary_union(obstacles)).buffer(0)

    def path_to_root(net, layer, start, width, forced=None, source_neck=False, divider_feed=False):
        from hardware.fabrication.route_nf_surface import candidate_paths

        copper = root_shapes(net, layer)
        endpoint_options = [(forced, None)] if forced is not None else [(None, None)]
        if forced is None:
            ids = [i for group in joined[net] for i in captured["groups"][group]]
            candidates = [objects[i] for i in ids if objects[i]["kind"] == "PCB_VIA" and layer in objects[i]["layers"]]
            candidates.sort(key=lambda o: math.dist(start, o["position_mm"]))
            endpoint_options += [(o["position_mm"], o["uuid"]) for o in candidates[:3]]
            terminals = [objects[i] for i in ids if objects[i]["kind"] == "PAD" and objects[i]["pin"]
                         and layer in objects[i]["layers"]]
            terminals.sort(key=lambda o: math.dist(start, o["position_mm"]))
            endpoint_options += [(o["position_mm"], None) for o in terminals[:3]]
            added = [r for r in roots_added+routes if r["net"] == net and r["added_via"]]
            endpoint_options += [(r["xy_mm"], None) for r in sorted(added, key=lambda r: math.dist(start, r["xy_mm"]))[:2]]
        choices = []
        for endpoint, allowed_via in endpoint_options:
            free = free_for_route(net, layer, width, allowed_via)
            narrow = free_for_route(net, layer, .2, allowed_via)
            blocks = [Point(xy).buffer(width/2+.31) for xy in context.new_vias
                      if endpoint is None or math.dist(xy, endpoint) > 1e-8]
            if blocks:
                free = free.difference(unary_union(blocks))
                narrow = narrow.difference(unary_union(blocks))
            prepare(narrow)
            grid = FineGrid(free) if width == .2 and divider_feed else InnerGrid(free)

            def necks(xy):
                candidates = {}
                cx, cy = (round(v/.2) for v in xy)
                keys = [(cx+i, cy+j) for i in range(-15, 16) for j in range(-15, 16)]
                for key in sorted(keys, key=lambda k: math.dist(xy, grid.xy(k))):
                    x, y = key
                    distance = math.dist(xy, grid.xy(key))
                    if not (.9 <= distance <= 3.2 and 0 <= x < grid.width and 0 <= y < grid.height and grid.mask[y, x]):
                        continue
                    for path in candidate_paths(xy, grid.xy(key)):
                        path = [p for i, p in enumerate(path) if not i or p != path[i-1]]
                        length = sum(math.dist(p, q) for p, q in zip(path, path[1:]))
                        if length <= 3.5 and narrow.covers(LineString(path)):
                            candidates[key] = dict(layer=layer, path_mm=path, width_mm=.2, length_mm=length)
                            break
                    if len(candidates) >= 160:
                        break
                return candidates

            start_necks = necks(start) if source_neck and width == .6 else {}
            starts = list(start_necks) if start_necks else grid.anchors(start)
            end_necks = necks(endpoint) if endpoint is not None and width == .6 else {}
            if end_necks:
                targets = set(end_necks)
            elif endpoint is not None:
                targets = set(grid.anchors(endpoint))
            else:
                if copper.is_empty:
                    continue
                prepare(copper)
                step = getattr(grid, "step", .2)
                xx, yy = np.meshgrid(np.arange(grid.width)*step, np.arange(grid.height)*step)
                rows, columns = np.nonzero(contains_xy(copper, xx, yy) & grid.mask)
                targets = set(zip(columns.tolist(), rows.tolist()))
            keys = grid.route(starts, targets)
            if not keys:
                continue
            points = [grid.xy(k) for k in keys]
            extras = []
            if keys[0] in start_necks:
                extras.append(start_necks[keys[0]])
            else:
                points.insert(0, start)
            if keys[-1] in end_necks:
                extras.append(end_necks[keys[-1]])
            elif endpoint is not None:
                points.append(endpoint)
            points = grid.simplify(points)
            length = sum(math.dist(p, q) for p, q in zip(points, points[1:]))
            total = length+sum(r["length_mm"] for r in extras)
            direct = math.dist(start, endpoint) if endpoint is not None else Point(start).distance(copper)
            narrow_limit = 12 if divider_feed else 3.5
            if total > (narrow_limit if width == .2 else min(200, 2*direct+5)):
                continue
            if len(points) > 1:
                assert free.covers(LineString(points))
            choices.append(dict(layer=layer, width_mm=width, path_mm=points, length_mm=length,
                                total_length_mm=total, necks=extras, reused_root_via_uuid=allowed_via,
                                divider_feed=divider_feed and width == .2))
        return min(choices, key=lambda r: r["total_length_mm"]) if choices else None

    def join(net, ids, forced=None):
        contacts = [objects[i] for i in ids if objects[i]["kind"] == "PAD" and objects[i]["pin"]]
        contacts.sort(key=lambda o: (not o["ref"].startswith("C"), o["ref"], o["pin"]))
        divider_feed = any((p["ref"], p["pin"]) == ("R211", "1") for p in contacts)
        for width in (.6, .2):
            for pad in contacts:
                for layer in ("F.Cu", "B.Cu"):
                    if layer in pad["layers"]:
                        result = path_to_root(net, layer, pad["position_mm"], width, forced,
                                              source_neck=width == .6, divider_feed=divider_feed)
                        if result:
                            return dict(endpoint_uuid=pad["uuid"], added_via=False, paths=[], **result)
        for escape in expanded_choices(context, [objects[i] for i in ids], net):
            if not escape["added_via"] or forced is not None and math.dist(escape["xy_mm"], forced) < .811:
                continue
            face = escape["paths"][0][0]
            other = "B.Cu" if face == "F.Cu" else "F.Cu"
            for width in ((.6, .2) if divider_feed else (.6,)):
                result = path_to_root(net, other, escape["xy_mm"], width, forced,
                                      source_neck=width == .6, divider_feed=divider_feed)
                if result:
                    return dict(escape, **result)
        return None

    for iteration in range(3):
        progress = 0
        for net in ("/CODEC/A3V3", "/CODEC/A4V5", "5V_DIG", "V3V3_IO", "V5_REG"):
            groups = {k: ids for k, ids in captured["groups"].items() if objects[ids[0]]["net"] == net}
            for key in sorted(groups, key=lambda k: min(math.dist(objects[i]["position_mm"], pads[RAILS[net]]["position_mm"]) for i in groups[k])):
                if key in joined[net]:
                    continue
                result = join(net, groups[key])
                root_choice = None
                if result is None and not any(objects[i]["layers"].get("B.Cu") for g in joined[net] for i in groups[g]):
                    root_ids = [i for g in joined[net] for i in groups[g]]
                    for candidate in expanded_choices(context, [objects[i] for i in root_ids], net):
                        if not candidate["added_via"]:
                            continue
                        result = join(net, groups[key], candidate["xy_mm"])
                        if result:
                            root_choice = candidate
                            break
                if result is None:
                    continue
                if root_choice:
                    context.accept(net, root_choice)
                    roots_added.append(dict(net=net, **root_choice))
                if result["added_via"] and not context.via_ok(net, result["xy_mm"]):
                    raise AssertionError("Chosen bridge conflicts with a root drill")
                context.accept(net, result)
                if len(result["path_mm"]) > 1:
                    context.added_shapes.append((net, result["layer"], LineString(result["path_mm"]).buffer(result["width_mm"]/2)))
                for neck in result["necks"]:
                    context.added_shapes.append((net, neck["layer"], LineString(neck["path_mm"]).buffer(.1)))
                routes.append(dict(net=net, group=key, **result))
                joined[net].add(key)
                progress += 1
                print("Joined", net, [(objects[i].get("ref"), objects[i].get("pin")) for i in groups[key] if objects[i]["kind"] == "PAD"],
                      result["layer"], "via", result["added_via"], round(result["length_mm"], 3), "mm", flush=True)
        print("Pass", iteration+1, "joins", progress, flush=True)
        if not progress:
            break
    return roots_added, routes, joined


def build():
    assert not (OUT / "distribution-input.kicad_pcb").exists()
    applied = snapshot("bridge-build")
    captured = json.loads((OUT / "native-inputs.json").read_text())
    verify_hashes(captured["source_sha256"])
    roots_added, routes, joined = plan(captured)
    assert routes
    board = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    parent = copy.deepcopy(board)
    nets = {str(n[2]): n[1] for n in children(board, "net")}
    segments, vias = [], []

    def emit(net, layer, points, width):
        for start, end in zip(points, points[1:]):
            if math.dist(start, end) < 1e-8:
                continue
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:AC04:supply04:{net}:{layer}:{width}:{start}:{end}"))
            assert not any(r["uuid"] == ident for r in segments)
            segments.append(dict(uuid=ident, net=net, layer=layer, start_mm=start, end_mm=end, width_mm=width))
            board.append([a("segment"), [a("start"), *start], [a("end"), *end], [a("width"), width],
                          [a("layer"), layer], [a("net"), nets[net]], [a("uuid"), ident]])

    for row in roots_added+routes:
        net = row["net"]
        if row["added_via"]:
            xy = row["xy_mm"]
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:AC04:supplyvia04:{net}:{xy}"))
            vias.append(dict(uuid=ident, net=net, xy_mm=xy, diameter_mm=.6, drill_mm=.3))
            board.append([a("via"), [a("at"), *xy], [a("size"), .6], [a("drill"), .3],
                          [a("layers"), "F.Cu", "B.Cu"], [a("net"), nets[net]], [a("uuid"), ident]])
        for layer, points in row["paths"]:
            emit(net, layer, points, .2)
    for row in routes:
        emit(row["net"], row["layer"], row["path_mm"], row["width_mm"])
        for neck in row["necks"]:
            emit(row["net"], neck["layer"], neck["path_mm"], .2)
    assert board[:len(parent)] == parent
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            shutil.copyfile(p, OUT / p.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    dest = OUT / "distribution-input.kicad_pcb"
    dest.write_text(sexpr(board)+"\n")
    inputs = [applied, SOURCE / "audio_core.kicad_pcb", SOURCE / "routing-handoff.json", OUT / "native-inputs.json",
              ROOT / "audio_main_supply_completion.py", ROOT / "audio_main_power_routes.py"]
    report = dict(source_sha256=relative_hashes(inputs), authored_PCB_sha256=sha(dest), roots_added=roots_added,
                  routes=routes, joined_groups={net: sorted(ids) for net, ids in joined.items()},
                  added_segments=segments, added_vias=vias, no_parent_geometry_changes=True,
                  native_refill_and_checks_pending=True, fabrication_released=False)
    expected = json.loads((ROOT / "staging/audio-main-integration-04b/expected-circuit.json").read_text())
    assert expected["R211"]["value"] == "27.7k 0.1%" and expected["R212"]["value"] == "10k 0.1%"
    assert expected["U206"]["value"] == "TPS389001DSET"
    current = 4.65/(37700*.999)+1e-6
    resistance = 1.724e-8*(1+.00393*(105-20))*.012/(.0002*.000018)
    report["divider_feed_construction_assessment"] = dict(endpoint=["R211", "1"], net="/CODEC/A4V5",
        surface_width_mm=.2, maximum_trace_mm=12, nominal_divider_current_A=4.5/37700,
        assumed_rail_upper_V=4.65, resistor_tolerance_fraction=.001, sense_current_allowance_A=1e-6,
        assumed_minimum_copper_um=18, assumed_copper_temperature_C=105,
        current_bound_A=current, trace_only_resistance_bound_ohm=resistance,
        trace_only_drop_bound_V=current*resistance,
        source="https://www.ti.com/lit/ds/symlink/tps3890.pdf",
        only_adjustable_supervisor_resistor_feed_uses_this_global_length_budget=True,
        assumptions_require_acceptance_and_via_drop_noise_fault_thermal_qualification_not_inferred=True)
    report["source_sha256"].update(relative_hashes([ROOT / "staging/audio-main-integration-04b/expected-circuit.json"]))
    (OUT / "distribution-construction.json").write_text(json.dumps(report, indent=2)+"\n")
    assert sha(applied) == sha(Path(__file__))
    print("Built", len(routes), "joins /", len(segments), "tracks /", len(vias), "vias")


def native(action):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    from hardware.fabrication import audio_main_power_routes as helper

    applied = snapshot(action+"-entry")
    helper.OUT = OUT
    {"fill": helper.fill, "review": helper.review}[action]()
    result = OUT / ("native-refill.json" if action == "fill" else "supply-connectivity-review.json")
    report = dict(source_sha256=relative_hashes([applied, ROOT / "audio_main_power_routes.py", result]),
                  selected_output=str(OUT.relative_to(ROOT)), helper_source_stays_controls_01_for_full_retained_pair_review=True,
                  fabrication_released=False)
    (OUT / (action+"-entry.json")).write_text(json.dumps(report, indent=2)+"\n")
    assert sha(applied) == sha(Path(__file__))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "build", "fill", "review"))
    args = parser.parse_args()
    {"capture": capture, "build": build, "fill": lambda: native("fill"), "review": lambda: native("review")}[args.action]()
