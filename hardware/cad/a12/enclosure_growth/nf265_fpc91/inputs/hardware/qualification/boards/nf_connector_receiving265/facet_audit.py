"""Stronger read-only proof: each triangle belongs to ONE convex seat mask."""

import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EPS = 20e-6


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def masks(name):
    if name == "own_PCB_seats":
        answer = []
        for p in json.loads((ROOT / "ports-v2.json").read_text())["ports"]:
            u, v = p["anchor_mm"]
            a, b, c, d = p["receiving_body_uv_bounds_mm"]
            answer.append(
                dict(
                    id=p["ref"] + "-face", axis=2, plane=0, xy=[0, 1], rectangle=[u + a, v + b, u + c, v + d]
                )
            )
        answer.extend(dict(id="post" + str(u), axis=2, plane=0, xy=[0, 1], disk=[u, 21, 3]) for u in [61, 90])
        return answer
    if name == "base_cap_nonseat_overlap":
        return [dict(id="base-cap-seat", axis=1, plane=21, xy=[0, 2], rectangle=[58, 5.3, 93, 13])]
    if name == "hardware_matched_nominal_PCB":
        return [
            dict(id="backwasher" + str(u), axis=2, plane=-1.6, xy=[0, 1], disk=[u, 21, 2.5]) for u in [61, 90]
        ]
    if name == "hardware_receiving_threads":
        return [
            dict(id="capwasher" + str(u), axis=1, plane=24.5, xy=[0, 2], disk=[u, 9, 2.5]) for u in [61, 90]
        ] + [dict(id="threadtip" + str(u), axis=1, plane=18.85, xy=[0, 2], disk=[u, 9, 1]) for u in [61, 90]]
    raise ValueError(name)


def vertex_inside(p, m):
    if abs(p[m["axis"]] - m["plane"]) > EPS:
        return False
    u, v = (p[i] for i in m["xy"])
    if "rectangle" in m:
        a, b, c, d = m["rectangle"]
        return a - EPS <= u <= c + EPS and b - EPS <= v <= d + EPS
    a, b, r = m["disk"]
    return math.hypot(u - a, v - b) <= r + EPS


def run():
    output = ROOT / "mechanical-v2/facet-boundary-audit.json"
    if output.exists():
        raise RuntimeError("Fresh audit required")
    result = {}
    sources = {}
    for name in [
        "own_PCB_seats",
        "hardware_receiving_threads",
        "hardware_matched_nominal_PCB",
        "base_cap_nonseat_overlap",
    ]:
        p = ROOT / "mechanical-v2/native-run1" / (name + ".stl")
        data = p.read_bytes()
        N = struct.unpack_from("<I", data, 80)[0]
        if len(data) != 84 + 50 * N:
            raise ValueError("Bad binary STL")
        coverage = {}
        unresolved = []
        for i in range(N):
            row = struct.unpack_from("<12fH", data, 84 + i * 50)
            tri = [row[3:6], row[6:9], row[9:12]]
            matching = [m["id"] for m in masks(name) if all(vertex_inside(v, m) for v in tri)]
            if not matching:
                unresolved.append(i)
            else:
                coverage[matching[0]] = coverage.get(matching[0], 0) + 1
        result[name] = dict(
            triangles=N,
            each_entire_triangle_inside_one_convex_mask=not unresolved,
            unresolved_triangle_indices=unresolved,
            triangles_per_convex_mask=coverage,
            masks=masks(name),
        )
        sources[str(p)] = sha(p)
    for p in [Path(__file__), ROOT / "ports-v2.json"]:
        sources[str(p)] = sha(p)
    output.write_text(
        json.dumps(
            dict(
                revision="NC265-one-convex-mask-per-facet",
                cases=result,
                source_sha256=sources,
                normal_and_inplane_guard_mm=EPS,
                raw_failures_retained=True,
                production_geometry_changed=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            dict(
                triangles=sum(x["triangles"] for x in result.values()),
                unresolved=sum(len(x["unresolved_triangle_indices"]) for x in result.values()),
            )
        )
    )


if __name__ == "__main__":
    run()
