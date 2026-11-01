"""Select mutually clear actual through-via escapes for one IC together."""

import math

from ..revision26.layout import Layout
from ..routing.check import point_segment, segment_distance
from .local_escapes import escape


def solve(rt, pads, max_nodes=10000):
    coordinates = [{round(p["xy"][i], 5) for p in pads} for i in (0, 1)]
    axis = next(i for i, x in enumerate(coordinates) if len(x) == 2)
    tangent = 1 - axis
    centre = sum(coordinates[axis]) / 2
    judge = Layout.__new__(Layout)
    judge.router = rt
    choices = {}
    ordered = []
    for side in sorted(coordinates[axis]):
        row = sorted([p for p in pads if abs(p["xy"][axis] - side) < 1e-4], key=lambda p: p["xy"][tangent])
        sign = 1 if side > centre else -1
        for index, pad in enumerate(row):
            if pad["net"].startswith("unconnected-"):
                continue
            key = pad["pin"]
            ordered.append(key)
            available = []
            seen = set()
            for direction in (-1, 1):
                for distance in (1.3 + 0.5 * (index % 2), 1.3, 1.8, 2.3, 2.8, 3.3):
                    for shift in (0, 0.2, -0.2, 0.4, -0.4, 0.6, -0.6, 0.8, -0.8):
                        xy = list(pad["xy"])
                        xy[axis] += sign * direction * distance
                        xy[tangent] += shift
                        xy = tuple(round(x, 6) for x in xy)
                        if xy in seen:
                            continue
                        seen.add(xy)
                        saved = rt.geometry
                        rt.geometry = [
                            g
                            for g in saved
                            if not (g["kind"] == "rect" and g["net"] == pad["net"] and not g.get("through"))
                        ]
                        clear = judge.free_via(pad["net"], xy)
                        rt.geometry = saved
                        if not clear:
                            continue
                        points = [pad["xy"]]
                        if shift:
                            bend = list(pad["xy"])
                            bend[axis] += sign * direction * 1.1
                            points.append(tuple(bend))
                        points.append(xy)
                        if not all(
                            judge.free_line(pad["net"], pad["layers"][0], a, b, 0.2)
                            for a, b in zip(points, points[1:])
                        ):
                            continue
                        available.append(
                            dict(
                                ref=pad["ref"],
                                pin=key,
                                net=pad["net"],
                                source=pad["xy"],
                                via=xy,
                                layer=pad["layers"][0],
                                points=points,
                                cost=distance + abs(shift) * 0.2 + (2 if direction == 1 else 0),
                            )
                        )
            choices[key] = sorted(available, key=lambda c: c["cost"])
    hard = {}
    for key in ordered:
        if choices[key]:
            continue
        pad = next(p for p in pads if p["pin"] == key)
        route, reason = escape(rt, pad, maxdistance=6)
        if route is not None:
            hard[key] = dict(
                ref=pad["ref"],
                pin=key,
                net=pad["net"],
                source=pad["xy"],
                via=route["via"],
                layer=pad["layers"][0],
                points=route["path"],
                cost=0,
                fine_grid_escape=True,
            )
    memo = {}
    visits = 0
    best = {}

    def compatible(a, b):
        ids = tuple(sorted((id(a), id(b))))
        if ids in memo:
            return memo[ids]
        same = a["net"] == b["net"]
        distance = math.dist(a["via"], b["via"])
        okay = distance >= (0.56 if same else 0.81) or same and distance < 1e-6
        if okay and not same:
            # Fine-grid paths can repeat their initial anchor. The native
            # emitter omits zero-length segments; collision checks must agree.
            sa = [(s, t) for s, t in zip(a["points"], a["points"][1:]) if math.dist(s, t) > 1e-8]
            sb = [(s, t) for s, t in zip(b["points"], b["points"][1:]) if math.dist(s, t) > 1e-8]
            okay = all(point_segment(a["via"], s, t) >= 0.61 for s, t in sb) and all(
                point_segment(b["via"], s, t) >= 0.61 for s, t in sa
            )
            if okay:
                okay = all(segment_distance(s, t, u, v) >= 0.41 for s, t in sa for u, v in sb)
        memo[ids] = okay
        return okay

    def search(remaining, selected):
        nonlocal visits, best
        visits += 1
        if len(selected) > len(best):
            best = dict(selected)
        if not remaining:
            return dict(selected)
        if visits > max_nodes:
            return None
        viable = {
            k: [c for c in choices[k] if all(compatible(c, x) for x in selected.values())] for k in remaining
        }
        key = min(remaining, key=lambda k: len(viable[k]))
        if not viable[key]:
            greedy = dict(selected)
            for other in sorted(remaining, key=lambda k: len(viable[k])):
                available = [c for c in viable[other] if all(compatible(c, x) for x in greedy.values())]
                if available:
                    greedy[other] = available[0]
            if len(greedy) > len(best):
                best = greedy
            return None
        for candidate in viable[key]:
            selected[key] = candidate
            found = search([k for k in remaining if k != key], selected)
            if found is not None:
                return found
            del selected[key]
        return None

    possible = [k for k in ordered if choices[k] and k not in hard]
    best = dict(hard)
    result = search(possible, dict(hard))
    selected = best if result is None else result
    successful = []
    failed = []
    for key in ordered:
        if key in selected:
            plan = selected[key]
            if key not in hard:
                rt.path(plan["net"], plan["layer"], plan["points"], 0.2)
                rt.via(plan["net"], plan["via"])
            successful.append(plan)
        else:
            pad = next(p for p in pads if p["pin"] == key)
            failed.append(
                dict(
                    ref=pad["ref"],
                    pin=key,
                    net=pad["net"],
                    source=pad["xy"],
                    candidate_count=len(choices[key]),
                    reason="no_fixed_geometry_candidate"
                    if not choices[key]
                    else "joint_selection_budget_or_conflict",
                )
            )
    return (
        successful,
        failed,
        dict(
            search_nodes=visits,
            max_search_nodes=max_nodes,
            candidate_counts={k: len(v) for k, v in choices.items()},
            complete=len(selected) == len(ordered),
        ),
    )
