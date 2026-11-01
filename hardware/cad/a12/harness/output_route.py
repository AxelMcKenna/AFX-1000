"""Full two-ended DIGITAL wire-pair geometry investigation; no fanout/release claim.

Analytic lines/arcs retain true bend-radius and tangent continuity. Actual
receiving PCB source and local source/receiver native evidence are required.
Component and pair screens reject candidates before full native case checks.
"""

import json
import math
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot

from ..generate import REPO, sha
from .route_geometry import Route, cross

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated/output-full-pair"


def route(row, target, plane, required):
    start = row["source_face_mm"]
    r = Route(start, [0, 0, 1], required)
    radius = row["nominal_bend_radius_mm"]
    heading = math.radians(row["angle_deg"])
    h = [math.cos(heading), math.sin(heading), 0]
    r.line(row["initial_straight_mm"])
    r.arc(radius, cross([0, 0, 1], h), math.pi / 2)
    assert math.dist(r.point, row["escape_end_mm"]) < 1e-10
    local_prefix = len(r.pieces)
    r.arc(10, [0, 0, 1], math.pi - heading)
    r.lift(plane - r.point[2], 10)
    r.line(r.point[0] - 96)
    dx, dy = r.point[0] - target[0], r.point[1] - target[1]
    k = math.sqrt(dx * dx + (dy - 10) ** 2 - 100)
    beta = math.atan2(dy - 10, dx) + math.atan2(10, k)
    assert 0 < beta < math.pi / 2 and k > 10
    r.arc(10, [0, 0, 1], beta)
    r.line(k - 10)
    r.arc(10, cross(r.tangent, [0, 0, -1]), math.pi / 2)
    assert math.dist(r.point[:2], target[:2]) < 1e-10
    r.line(r.point[2] - target[2])
    assert math.dist(r.point, target) < 1e-10 and math.dist(r.tangent, [0, 0, -1]) < 1e-12
    points, bounds = r.samples()
    return dict(
        net=row["net"],
        source_face_mm=start,
        receiving_face_mm=target,
        pieces=r.pieces,
        points=points,
        bounds=bounds,
        retained_local_prefix_piece_count=local_prefix,
        source_bare_length_above_face_mm=3.1,
        destination_bare_length_above_face_mm=3.1,
        additional_source_board_and_tail_mm=start[2] - 3.5,
        additional_destination_board_and_tail_mm=target[2] - 5.0,
        total_conductor_with_board_penetration_and_tails_mm=bounds["exact_centerline_length_mm"]
        + start[2]
        - 3.5
        + target[2]
        - 5,
        wire_cut_slack_not_yet_included=True,
    )


def main():
    import numpy as np
    from scipy.spatial import cKDTree

    source = ROOT / "generated/output-formed-6715-balanced-return-r58"
    receiver = ROOT / "generated/receiver-awg18"
    s = json.loads((source / "analysis.json").read_text())
    sv = json.loads((source / "verification.json").read_text())
    d = json.loads((receiver / "analysis.json").read_text())
    dv = json.loads((receiver / "verification.json").read_text())
    assert sv["local_formed_escape_clear"] and dv["all_checked_receiver_intersections_clear"]
    hashes = {}
    for report in [sv, dv]:
        for key in ["source_sha256", "evidence_inputs_sha256", "evidence_sha256"]:
            hashes.update(report[key])
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Stale local evidence"
    pads = json.loads((ROOT / "proposals/processor-awg18/generated/independent-review.json").read_text())[
        "actual_pads"
    ]
    paths = [
        route(
            row,
            next(p["world_mm"] for p in pads if p["net"] == row["net"]),
            31 if row["net"] == "5V_DIG" else 27.5,
            s["required_centerline_radius_mm"],
        )
        for row in s["routes"]
    ]
    native, other, fresh = snapshot()
    hashes.update(fresh)
    # All other E19 bodies are actual renewed receiver-PCB bodies. Source R58
    # is canonical here (more conservative than its repaired position).
    boxes = [b for b in native["boxes"] if not b[0].startswith("E28_J4")]
    boxes += native["switch_diagnostic_boxes"]
    boxes += [b for b in other["envelopes"] if not b[0].startswith(("e19_", "disconnect_"))] + other[
        "port_envelopes"
    ]
    boxes += [
        b
        for b in d["current_E19_component_packet"]["bodies"]
        if b[0] != "e19_J1" and not b[0].startswith("e19_J1_lead_")
    ]
    screens = []
    radius = s["insulated_radius_with_position_and_geometry_reserve_mm"] + 0.25
    for path in paths:
        points = np.asarray(path["points"])
        cover = path["bounds"]["maximum_centerline_sample_cover_mm"]
        nearest = []
        for b in boxes:
            lo, hi = np.asarray(b[1:4]), np.asarray(b[1:4]) + np.asarray(b[4:7])
            lo[2] -= 0.2
            hi[2] += 0.2
            delta = np.maximum(np.maximum(lo - points, points - hi), 0)
            distances = np.sqrt(np.sum(delta * delta, axis=1))
            i = int(np.argmin(distances))
            nearest.append(
                dict(
                    obstacle=b[0],
                    conservative_gap_mm=float(distances[i] - radius - cover),
                    point=path["points"][i],
                )
            )
        for c in native["cylinders"]:
            xy = np.maximum(np.linalg.norm(points[:, :2] - np.asarray(c[1:3]), axis=1) - c[4] / 2, 0)
            z = np.maximum(np.maximum(c[3] - 0.2 - points[:, 2], points[:, 2] - (c[3] + c[5] + 0.2)), 0)
            ds = np.sqrt(xy * xy + z * z)
            i = int(np.argmin(ds))
            nearest.append(
                dict(
                    obstacle=c[0], conservative_gap_mm=float(ds[i] - radius - cover), point=path["points"][i]
                )
            )
        nearest.sort(key=lambda x: x["conservative_gap_mm"])
        screens.append(
            dict(
                net=path["net"],
                nearest=nearest[:15],
                all_components_clear=nearest[0]["conservative_gap_mm"] > 0,
            )
        )
    distance, _ = cKDTree(paths[0]["points"]).query(paths[1]["points"])
    pair_gap = float(
        min(distance) - 2 * s["insulated_radius_with_position_and_geometry_reserve_mm"] - 0.25 - 0.04
    )
    for p in [
        Path(__file__),
        ROOT / "route_geometry.py",
        source / "analysis.json",
        source / "verification.json",
        receiver / "analysis.json",
        receiver / "verification.json",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in hashes.items())
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        paths=paths,
        component_screens=screens,
        conservative_pair_gap_mm=pair_gap,
        component_and_pair_screen_clear=pair_gap > 0 and all(r["all_components_clear"] for r in screens),
        native_case_power_hardware_checks_performed=False,
        receiving_and_source_local_interfaces_clear=True,
        wire_length_limit_mm=200,
        strain_slack_and_fanout_designed=False,
        complete_output_harness=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                lengths_mm=[r["total_conductor_with_board_penetration_and_tails_mm"] for r in paths],
                pair_gap_mm=pair_gap,
                closest=[r["nearest"][:3] for r in screens],
            ),
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    result = main()
    raise SystemExit(0 if result["component_and_pair_screen_clear"] else 1)
