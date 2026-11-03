"""Replay a complete INPUT_ENABLE comparison without hiding its longer route.

Forty millimetres is a bounded construction trial, not electrical acceptance.
The original distance-based search target and actual full length are retained.
"""

import copy
import math

from shapely.geometry import LineString

from hardware.fabrication.audio_main_global_controls import SignalScreen

NET = "/BYPASS/INPUT_ENABLE"
COMPARISON_LENGTH_MM = 40.


def rebase_seeds(previous, captured, rows):
    old_objects = {o["uuid"]: o for o in previous["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in captured["objects"] if o["kind"] == "PAD" and o["pin"]}
    members = {i: key for key, ids in captured["groups"].items() for i in ids}
    result = copy.deepcopy(rows)
    for row in result:
        sides = []
        for side in row["source_groups"]:
            current = set()
            for key in side:
                contacts = [old_objects[i] for i in previous["groups"][key]
                            if old_objects[i]["kind"] == "PAD" and old_objects[i]["pin"]]
                assert contacts
                groups = set()
                for pad in contacts:
                    actual = pads[pad["ref"], pad["pin"]]
                    assert actual["net"] == pad["net"] == row["net"]
                    assert math.dist(actual["position_mm"], pad["position_mm"]) < 1e-7
                    groups.add(members[actual["uuid"]])
                assert len(groups) == 1, "Earlier complete native island has split"
                current.update(groups)
            sides.append(sorted(current))
        assert not set(sides[0]) & set(sides[1])
        row["source_groups"] = sides
        row["groups"] = [min(side) for side in sides]
        row["seed_rebased_by_complete_ref_pin_witnesses"] = True
    return result


def comparison(captured, proposal, seeds, port):
    objects = {o["uuid"]: o for o in captured["objects"]}
    membership = {i: key for key, ids in captured["groups"].items() for i in ids}
    screen = SignalScreen(captured)
    for row in seeds:
        for layer, points in row["runs"]:
            screen.added.append((row["net"], layer, LineString(points)))
        screen.new_vias.extend((row["net"], p) for p in row["new_vias_mm"])
    for decision in proposal["decisions"]:
        if decision["net"] != NET or not decision["path_found"]:
            continue
        row = copy.deepcopy(decision["result"])
        if not all(screen.legal(NET, layer, points) for layer, points in row["runs"]):
            continue
        fresh = [p for p in row["vias"] if not any(n == NET and math.dist(p, q) < 1e-7
                                                   for n, q in screen.vias+screen.new_vias)]
        if not all(screen.via_legal(NET, p) for p in fresh):
            continue
        if any(math.dist(p, q) <= .86 for i, p in enumerate(fresh) for q in fresh[i+1:]):
            continue
        terminals = [row["runs"][0][1][0], row["runs"][-1][1][-1]]
        assert math.dist(terminals[1], port["point"]) < 1e-7
        groups = []
        for (face, _), point in zip((row["runs"][0], row["runs"][-1]), terminals):
            contact = next(o for o in objects.values() if o["net"] == NET and o["layers"].get(face) and
                           math.dist(point, o["position_mm"]) < 1e-7)
            groups.append(membership[contact["uuid"]])
        assert len(set(groups)) == 2
        length = sum(LineString(points).length for _, points in row["runs"])
        neck = sum(LineString(points).length for _, points in port["runs"])
        physical = [terminals[0], port["runs"][0][1][0]]
        assert length+neck <= COMPARISON_LENGTH_MM and len(fresh)+1 <= 4
        row.update(net=NET, groups=groups, source_groups=[[k] for k in groups],
                   new_vias_mm=fresh, planar_length_mm=length,
                   maximum_planar_length_mm=COMPARISON_LENGTH_MM-neck,
                   terminal_points_mm=terminals, physical_terminal_points_mm=physical,
                   escape_inclusive_length_mm=length+neck,
                   maximum_escape_inclusive_length_mm=COMPARISON_LENGTH_MM,
                   original_distance_based_search_target_mm=min(180, 2.5*math.dist(*physical)+10),
                   fresh_vias_including_reserved=len(fresh)+1,
                   explicit_longer_route_comparison=True,
                   timing_loading_return_noise_and_EMC_qualified=False)
        return row
    return None
