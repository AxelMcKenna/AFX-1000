"""Source-bound low-corridor full wire-pair investigation; not native qualification.

Uses the actual separate pitch9 source and real receiving PCB. No switch-lead,
wire-radius or clearance requirement is relaxed. Source native findings and
length failures remain explicit even if a numerical body screen is clear.
"""

import argparse
import json
import math
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.repaired import packet
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from ..generate import REPO, sha
from .route_geometry import Route, cross

ROOT = Path(__file__).resolve().parent
POWER = REPO / "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined"


def offset(r, height, radius=10):
    assert abs(r.tangent[2]) < 1e-12 and 0 < abs(height) < 2 * radius
    axis = cross(r.tangent, [0, 0, 1 if height > 0 else -1])
    angle = math.acos(1 - abs(height) / (2 * radius))
    r.arc(radius, axis, angle)
    r.arc(radius, axis, -angle)


def low_route(start, target, net, required):
    r = Route(start, [0, 0, 1], required)
    plane = 18 if net == "5V_DIG" else 20.5
    r.line(plane - 10 - start[2])
    r.arc(10, [1, 0, 0], math.pi / 2)
    if net == "AGND":
        r.line(r.point[1] - 116)
    r.arc(10, [0, 0, 1], -math.pi / 2)
    if net == "AGND":
        offset(r, -2.5)
    r.line(r.point[0] - (121 if net == "5V_DIG" else 126))
    r.arc(10, [0, 0, 1], math.pi / 2)
    r.line(r.point[1] - 88)
    offset(r, (23 if net == "5V_DIG" else 26.5) - 18)
    r.line(r.point[1] - (74 if net == "5V_DIG" else 69))
    r.arc(10, [0, 0, 1], -math.pi / 2)
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
        net=net,
        source_face_mm=start,
        receiving_face_mm=target,
        pieces=r.pieces,
        points=points,
        bounds=bounds,
        source_bare_length_above_face_mm=3.1,
        destination_bare_length_above_face_mm=3.1,
        total_conductor_with_board_penetration_and_tails_mm=bounds["exact_centerline_length_mm"]
        + start[2]
        - 3.5
        + target[2]
        - 5,
        strain_slack_included=False,
    )


def main(candidate):
    import numpy as np
    from scipy.spatial import cKDTree

    native, other, hashes = snapshot()
    actual = packet({"P03": POWER, "E28": candidate})
    native.update(actual)
    hashes.update(actual["source_sha256"])
    board = next(b for b in native["boards"] if b["id"] == "E28")
    pcb = candidate / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "J4"] for p in children(f, "property"))
    )
    assert first(fp, "layer")[1] == "F.Cu"
    face = board["datum"][2] + float(first(first(tree, "general"), "thickness")[1])
    starts = {}
    for p in children(fp, "pad"):
        xy = transform(fp, first(p, "at")[1:3])
        net = str(first(p, "net")[-1]).lstrip("/")
        assert float(first(p, "drill")[1]) == 2.2
        assert list(map(float, first(p, "size")[1:3])) == [4.2, 4.2]
        starts[net] = [board["datum"][0] + xy[0] - 100, board["datum"][1] + xy[1] - 100, face]
    assert starts == {"5V_DIG": [161, 120.5, face], "AGND": [161, 129.5, face]}, starts
    receive = ROOT / "generated/receiver-awg18"
    d = json.loads((receive / "analysis.json").read_text())
    dv = json.loads((receive / "verification.json").read_text())
    assert dv["all_checked_receiver_intersections_clear"]
    for key in ["source_sha256", "evidence_inputs_sha256", "evidence_sha256"]:
        hashes.update(dv[key])
    chosen = ROOT / "proposals/processor-awg18/generated/independent-review.json"
    pads = json.loads(chosen.read_text())["actual_pads"]
    wirefile = ROOT / "output-wire-6715.json"
    wire = json.loads(wirefile.read_text())["wire"]
    required = wire["minimum_bend_radius_mm"] + wire["insulation_od_mm"][1] / 2
    routes = [
        low_route(starts[net], next(p["world_mm"] for p in pads if p["net"] == net), net, required)
        for net in ["5V_DIG", "AGND"]
    ]
    boxes = [b for b in native["boxes"] if not b[0].startswith("E28_J4")] + native["switch_diagnostic_boxes"]
    boxes += [b for b in other["envelopes"] if not b[0].startswith(("e19_", "disconnect_"))] + other[
        "port_envelopes"
    ]
    boxes += [
        b
        for b in d["current_E19_component_packet"]["bodies"]
        if b[0] != "e19_J1" and not b[0].startswith("e19_J1_lead_")
    ]
    radius = wire["insulation_od_mm"][1] / 2 + 0.65 + 0.005
    screens = []
    for route in routes:
        points = np.asarray(route["points"])
        cover = route["bounds"]["maximum_centerline_sample_cover_mm"]
        nearest = []
        for b in boxes:
            lo, hi = np.asarray(b[1:4], dtype=float), np.asarray(b[1:4], dtype=float) + np.asarray(b[4:7])
            lo[2] -= 0.2
            hi[2] += 0.2
            ds = np.linalg.norm(np.maximum(np.maximum(lo - points, points - hi), 0), axis=1)
            i = int(np.argmin(ds))
            nearest.append(
                dict(obstacle=b[0], gap_mm=float(ds[i] - radius - 0.25 - cover), point=route["points"][i])
            )
        for c in native["cylinders"]:
            xy = np.maximum(np.linalg.norm(points[:, :2] - np.asarray(c[1:3]), axis=1) - c[4] / 2, 0)
            z = np.maximum(np.maximum(c[3] - 0.2 - points[:, 2], points[:, 2] - c[3] - c[5] - 0.2), 0)
            ds = np.hypot(xy, z)
            i = int(np.argmin(ds))
            nearest.append(
                dict(obstacle=c[0], gap_mm=float(ds[i] - radius - 0.25 - cover), point=route["points"][i])
            )
        nearest.sort(key=lambda x: x["gap_mm"])
        screens.append(dict(net=route["net"], nearest=nearest[:15], clear=nearest[0]["gap_mm"] > 0))
    ds, _ = cKDTree(routes[0]["points"]).query(routes[1]["points"])
    pair = float(min(ds) - 2 * radius - 0.25 - 0.04)
    for p in [
        Path(__file__),
        ROOT / "route_geometry.py",
        chosen,
        wirefile,
        receive / "analysis.json",
        receive / "verification.json",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Inputchanged"
    out = ROOT / "generated/output-under-switch" / candidate.name
    out.mkdir(parents=True, exist_ok=True)
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        source_pcb_sha256=sha(pcb),
        source_candidate=str(candidate.relative_to(REPO)),
        paths=routes,
        component_screens=screens,
        conservative_pair_gap_mm=pair,
        component_pair_screen_clear=pair > 0 and all(s["clear"] for s in screens),
        proposed_installed_length_max_mm=200,
        length_screen_clear=all(
            r["total_conductor_with_board_penetration_and_tails_mm"] <= 200 for r in routes
        ),
        native_case_power_hardware_checks_performed=False,
        source_terminal_native_qualification=False,
        source_bare_and_insulated_solids_separately_verified=False,
        complete_output_harness=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (out / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                lengths_mm=[r["total_conductor_with_board_penetration_and_tails_mm"] for r in routes],
                pair_gap_mm=pair,
                nearest=[s["nearest"][:4] for s in screens],
            ),
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_candidate", type=Path)
    result = main(parser.parse_args().source_candidate.resolve())
    raise SystemExit(0 if result["component_pair_screen_clear"] and result["length_screen_clear"] else 1)
