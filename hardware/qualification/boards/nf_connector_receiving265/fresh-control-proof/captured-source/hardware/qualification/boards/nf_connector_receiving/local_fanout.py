"""C1 local PHD30 reference exits, bounded continuously, not a full harness."""

import json
import math
from pathlib import Path

from hardware.cad.a12.enclosure_growth.front_bay_receiving.escape_certificate import trig

from .study import ROOT, phd_pin_xy, sha


def pieces(route):
    result = []
    if route["straight_mm"]:
        result.append(dict(kind="line", t=[0, 1]))
    result.append(dict(kind="arc", t=[0, math.pi / 2]))
    return result


def bounds(route, piece, interval):
    a, b = interval
    x, y, z = route["exit_xyz_mm"]
    L = route["straight_mm"]
    R = route["radius_mm"]
    if piece["kind"] == "line":
        return [x - 1e-9, y - L * b - 1e-9, z - 1e-9], [x + 1e-9, y - L * a + 1e-9, z + 1e-9]
    sa, sb = trig(a, True), trig(b, True)
    ca, cb = trig(a, False), trig(b, False)
    return [x - 1e-9, y - L - R * sb[1] - 1e-9, z + R * (1 - ca[1]) - 1e-9], [
        x + 1e-9,
        y - L - R * sa[0] + 1e-9,
        z + R * (1 - cb[0]) + 1e-9,
    ]


def certify(a, b, required):
    accepted = 0
    maxdepth = 0
    minimum = float("inf")
    for pa in pieces(a):
        for pb in pieces(b):
            stack = [(pa["t"], pb["t"], 0)]
            while stack:
                ia, ib, depth = stack.pop()
                aa, bb = bounds(a, pa, ia), bounds(b, pb, ib)
                lower = math.sqrt(
                    sum(max(aa[0][k] - bb[1][k], bb[0][k] - aa[1][k], 0) ** 2 for k in range(3))
                )
                maxdepth = max(depth, maxdepth)
                if lower >= required:
                    accepted += 1
                    minimum = min(lower, minimum)
                    continue
                if depth >= 32:
                    return dict(certified=False, unresolved_piece=[pa, pb, ia, ib], lower_mm=lower)
                if ia[1] - ia[0] >= ib[1] - ib[0]:
                    mid = sum(ia) / 2
                    stack += [([ia[0], mid], ib, depth + 1), ([mid, ia[1]], ib, depth + 1)]
                else:
                    mid = sum(ib) / 2
                    stack += [(ia, [ib[0], mid], depth + 1), (ia, [mid, ib[1]], depth + 1)]
    return dict(
        certified=True,
        accepted_interval_boxes=accepted,
        max_depth=maxdepth,
        minimum_certified_distance_mm=minimum,
    )


def build():
    target = ROOT / "generated/local-PHD30-fanout.json"
    if target.exists():
        raise RuntimeError("New fanout output required")
    study = json.loads((ROOT / "generated/analysis.json").read_text())
    wire = study["wire_candidates"]["Alpha3049"]
    required_radius = wire["minimum_centerline_bend_radius_mm"]
    route = []
    for n in range(1, 31):
        u, v = phd_pin_xy(n)
        route.append(
            dict(
                circuit=n,
                net=study["source_number_to_candidate_PHD_pad"][str(n)]["net"],
                exit_xyz_mm=[u, 0, v],
                straight_mm=10 if n % 2 else 0,
                radius_mm=14,
            )
        )
    N = 64
    chord = 14 * (1 - math.cos(math.pi / (4 * N)))
    physical_clearance = 0.25
    relative = 0.24
    geometry = 0.005
    required = (wire["OD_mm"][1] + relative + physical_clearance + 2 * geometry + 2 * chord) / (
        math.cos(math.pi / 64) ** 2
    )
    certificates = {}
    for i, a in enumerate(route):
        points = [a["exit_xyz_mm"]]
        x, y, z = a["exit_xyz_mm"]
        L = a["straight_mm"]
        R = a["radius_mm"]
        if L:
            points.append([x, y - L, z])
        points += [
            [x, y - L - R * math.sin(j * math.pi / (2 * N)), z + R * (1 - math.cos(j * math.pi / (2 * N)))]
            for j in range(1, N + 1)
        ]
        a["native_points"] = points
        for b in route[i + 1 :]:
            c = certify(a, b, required)
            assert c["certified"], (a["circuit"], b["circuit"], c)
            certificates[str(a["circuit"]) + "-" + str(b["circuit"])] = c
    assert len(certificates) == 435 and all(a["radius_mm"] >= required_radius for a in route)
    d = dict(
        frame="u along contact columns, y away from mateexit is NEGATIVE, z across rows/up; y=0 is actual wire exit once measured",
        connector_exit_plane_and_crimp_alignment_not_guaranteed=True,
        routes=route,
        continuous_curvature=dict(straight=0, arc=1 / 14, C1_at_line_arc=True, C2_at_join=False),
        source_required_radius_mm=required_radius,
        true_minimum_radius_mm=14,
        wire_OD_max_mm=wire["OD_mm"][1],
        local_relative_pose_stress_mm=relative,
        wire_pair_clearance_mm=physical_clearance,
        geometry_reserve_per_wire_mm=geometry,
        N_arc_segments=N,
        chord_bound_mm=chord,
        required_centerline_separation_mm=required,
        certificates=certificates,
        all435_continuously_certified=True,
        sampled_minimum_used=False,
        complete_wire_lengths_destinations_strain_crimp_and_wholeunit_fit_qualified=False,
        actual_wire_termination_approval=False,
        physical_qualified=False,
        fabrication_released=False,
        source_sha256={
            str(p): sha(p)
            for p in [
                Path(__file__),
                ROOT / "generated/analysis.json",
                Path(__file__).resolve().parents[3]
                / "cad/a12/enclosure_growth/front_bay_receiving/escape_certificate.py",
            ]
        },
    )
    target.write_text(json.dumps(d, indent=2) + "\n")
    print(
        json.dumps(
            dict(wires=30, pairs=435, Rmin=14, required_R=required_radius, separation_threshold=required)
        )
    )


if __name__ == "__main__":
    build()
