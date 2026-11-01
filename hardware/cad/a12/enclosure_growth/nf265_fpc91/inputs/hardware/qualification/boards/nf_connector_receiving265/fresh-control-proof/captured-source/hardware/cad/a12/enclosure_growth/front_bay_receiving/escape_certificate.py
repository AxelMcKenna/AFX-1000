"""Continuous monotone-arc interval separation, independent of path sampling."""

import json
import math
from decimal import Decimal, localcontext
from pathlib import Path

from .capture import ROOT, sha


def trig(t, sine):
    # Alternating Taylor series on[0,pi/2]; nextterm is a rigorous truncation
    # bound. Decimal60-digit roundoff is additionally enclosed by1e-45.
    with localcontext() as c:
        c.prec = 60
        x = Decimal(str(t))
        power = x if sine else Decimal(1)
        total = Decimal(0)
        for k in range(24):
            total += power
            n = 2 * k + (1 if sine else 0)
            power = -power * x * x / Decimal((n + 1) * (n + 2))
        error = abs(power) + Decimal("1e-45")
        return float(total - error) - 1e-11, float(total + error) + 1e-11


def bounds(route, interval):
    a, b = interval
    r = 10.0
    x, y, z = route["reference_wire_exit"]
    dx, dz = route["turn_direction_XZ"]
    sa, sb = trig(a, True), trig(b, True)
    ca, cb = trig(a, False), trig(b, False)
    return (
        [x + dx * r * (1 - ca[1]) - 1e-9, y - r * sb[1] - 1e-9, z + dz * r * (1 - ca[1]) - 1e-9],
        [x + dx * r * (1 - cb[0]) + 1e-9, y - r * sa[0] + 1e-9, z + dz * r * (1 - cb[0]) + 1e-9],
    )


def separation(a, b, required):
    stack = [((0.0, a["angle_rad"]), (0.0, b["angle_rad"]), 0)]
    accepted = 0
    minimum = float("inf")
    depth = 0
    while stack:
        ia, ib, d = stack.pop()
        aa, bb = bounds(a, ia), bounds(b, ib)
        lower = math.sqrt(sum(max(aa[0][k] - bb[1][k], bb[0][k] - aa[1][k], 0) ** 2 for k in range(3)))
        depth = max(depth, d)
        if lower >= required:
            accepted += 1
            minimum = min(minimum, lower)
            continue
        if d >= 32:
            return dict(certified=False, unresolved_intervals=[ia, ib], lower_mm=lower)
        if ia[1] - ia[0] >= ib[1] - ib[0]:
            mid = sum(ia) / 2
            stack.extend([((ia[0], mid), ib, d + 1), ((mid, ia[1]), ib, d + 1)])
        else:
            mid = sum(ib) / 2
            stack.extend([(ia, (ib[0], mid), d + 1), (ia, (mid, ib[1]), d + 1)])
    return dict(
        certified=True,
        accepted_interval_pairs=accepted,
        minimum_certified_centerline_separation_lower_mm=minimum,
        maximum_depth=depth,
    )


def build():
    folder = ROOT / "fpc_escape_variant2"
    target = folder / "pair-certificate.json"
    if target.exists():
        raise RuntimeError("New certificate required")
    d = json.loads((folder / "contract.json").read_text())
    routes = d["routes"]
    required = 2 * (1.195753 / (math.cos(math.pi / 64) ** 2) + 1e-9)
    pairs = {}
    for i, a in enumerate(routes):
        for b in routes[i + 1 :]:
            proof = separation(a, b, required)
            pairs[a["id"] + "__" + b["id"]] = proof
    result = dict(
        pairs=pairs,
        required_pair_centerline_distance_mm=required,
        all91_pairs_certified=all(p["certified"] for p in pairs.values()),
        local_relative_pose_base_mm=0.2,
        local_relative_pose_stress_mm=0.24,
        wire_OD_receiving_mm=1.9,
        geometry_reserve_mm=0.005,
        chord_cover_mm=0.000753,
        outer_sphere_superset_factor=1 / math.cos(math.pi / 64) ** 2,
        continuous_interval_bounds=True,
        sampled_minimum_used=False,
        full_harness_qualified=False,
        source_sha256={str(p): sha(p) for p in [Path(__file__), folder / "contract.json"]},
    )
    target.write_text(json.dumps(result, indent=2) + "\n")
    assert result["all91_pairs_certified"], [n for n, p in pairs.items() if not p["certified"]]
    print(
        json.dumps(
            dict(
                pairs=len(pairs),
                certified=True,
                required_separation_mm=required,
                maximum_depth=max(p["maximum_depth"] for p in pairs.values()),
            )
        )
    )


if __name__ == "__main__":
    build()
