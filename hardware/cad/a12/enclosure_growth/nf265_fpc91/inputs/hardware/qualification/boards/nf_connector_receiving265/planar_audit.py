"""Read-only classification of every raw failed NC265 contact triangle."""

import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUARD_MM = 20e-6


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def in_rect(u, v, bounds):
    a, b, c, d = bounds
    return a - GUARD_MM <= u <= c + GUARD_MM and b - GUARD_MM <= v <= d + GUARD_MM


def near_disk(u, v, centres, radius):
    return any(math.hypot(u - a, v - b) <= radius + GUARD_MM for a, b in centres)


def accepted_vertex(name, p):
    u, v, w = p
    if name == "own_PCB_seats":
        plan = json.loads((ROOT / "ports-v2.json").read_text())
        rects = []
        for port in plan["ports"]:
            a, b, c, d = port["receiving_body_uv_bounds_mm"]
            x, y = port["anchor_mm"]
            rects.append([a + x, b + y, c + x, d + y])
        return abs(w) <= GUARD_MM and (
            any(in_rect(u, v, b) for b in rects) or near_disk(u, v, [(61, 21), (90, 21)], 3)
        )
    if name == "base_cap_nonseat_overlap":
        return abs(v - 21) <= GUARD_MM and in_rect(u, w, [58, 5.3, 93, 13])
    if name == "hardware_matched_nominal_PCB":
        return abs(w + 1.6) <= GUARD_MM and near_disk(u, v, [(61, 21), (90, 21)], 2.5)
    if name == "hardware_receiving_threads":
        return (abs(v - 24.5) <= GUARD_MM and near_disk(u, w, [(61, 9), (90, 9)], 2.5)) or (
            abs(v - 18.85) <= GUARD_MM and near_disk(u, w, [(61, 9), (90, 9)], 1)
        )
    raise ValueError(name)


def run():
    out = ROOT / "mechanical-v2/raw-planar-audit.json"
    if out.exists():
        raise RuntimeError("Fresh audit output required")
    cases = {}
    inputs = {}
    for name in [
        "own_PCB_seats",
        "hardware_receiving_threads",
        "hardware_matched_nominal_PCB",
        "base_cap_nonseat_overlap",
    ]:
        p = ROOT / "mechanical-v2/native-run1" / (name + ".stl")
        data = p.read_bytes()
        inputs[str(p)] = sha(p)
        N = struct.unpack_from("<I", data, 80)[0]
        if len(data) != 84 + 50 * N:
            raise ValueError("Unexpected STL")
        invalid = []
        max_deviation = 0
        planes = {}
        for i in range(N):
            row = struct.unpack_from("<12fH", data, 84 + 50 * i)
            points = [row[3:6], row[6:9], row[9:12]]
            if not all(accepted_vertex(name, q) for q in points):
                invalid.append(i)
            allowed = {
                "own_PCB_seats": [(2, 0)],
                "hardware_receiving_threads": [(1, 18.85), (1, 24.5)],
                "hardware_matched_nominal_PCB": [(2, -1.6)],
                "base_cap_nonseat_overlap": [(1, 21)],
            }[name]
            deviations = [max(abs(q[axis] - value) for q in points) for axis, value in allowed]
            k = min(range(len(allowed)), key=lambda j: deviations[j])
            max_deviation = max(max_deviation, deviations[k])
            key = str(allowed[k])
            planes[key] = planes.get(key, 0) + 1
        cases[name] = dict(
            triangles=N,
            unclassified_triangle_indices=invalid,
            max_normal_deviation_mm=max_deviation,
            matched_declared_planes=planes,
            all_vertices_inside_bounded_declared_masks=not invalid,
            raw_test_still_failed=True,
        )
    inputs[str(Path(__file__))] = sha(Path(__file__))
    inputs[str(ROOT / "ports-v2.json")] = sha(ROOT / "ports-v2.json")
    out.write_text(
        json.dumps(
            dict(
                revision="NC265-raw-contact-plane-audit",
                cases=cases,
                source_sha256=inputs,
                proposed_test_only_guard_mm=GUARD_MM,
                geometry_parts_NOT_modified=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            dict(
                triangles=sum(c["triangles"] for c in cases.values()),
                unclassified=sum(len(c["unclassified_triangle_indices"]) for c in cases.values()),
            )
        )
    )


if __name__ == "__main__":
    run()
