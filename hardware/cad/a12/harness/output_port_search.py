"""Read-only J4 landing screen against both populated faces and routed copper.

This is a conservative placement screen, not a native DRC replacement. Zones
are deliberately not obstacles: any new landing must later quantify real pour
antipads/resistance and rebuild its connections. No board or component is moved.
"""

import argparse
import json
import math
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.electronics.common.sexpr import children, first, read_sexpr

from ..generate import REPO, sha

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated/port-search"
PADS = ROOT / "generated/port-search-native-pads.json"
PCB = REPO / "hardware/electronics/rail_disconnect/revision28/rail_disconnect.kicad_pcb"


def run(pcb=PCB, pads_path=PADS, out=OUT, body_contract=None):
    import numpy as np
    import shapely
    from shapely.geometry import LineString, Point, Polygon, box
    from shapely.ops import unary_union

    native, _, hashes = snapshot()
    pads = json.loads(pads_path.read_text())
    assert pads["source_pcb_sha256"] == sha(pcb)
    exporter = PCB.parent / "native_pad_geometry.py"
    assert pads["exporter_sha256"] == sha(exporter)
    if pcb.resolve() != PCB.resolve():
        assert body_contract is not None, (
            "A different source requires complete native body/pad/edge equivalence"
        )
        contract = json.loads(body_contract.read_text())
        verifier = PCB.parent / "native_contract_compare.py"
        assert contract["contracts_equal"]
        assert contract["original_pcb_sha256"] == sha(PCB) and contract["candidate_pcb_sha256"] == sha(pcb)
        assert contract["verifier_sha256"] == sha(verifier)
        for p in [body_contract, verifier]:
            hashes[str(p.relative_to(REPO))] = sha(p)
    for p in [Path(__file__), pads_path, exporter, pcb]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    tree = read_sexpr(pcb.read_text())
    assert not children(tree, "arc"), "Native arcs need a supported conservative shape"
    resolution = 32

    def round_buffer(shape, radius):
        # Shapely approximates round boundaries inside their ideal circle.
        # Circumscribe them and retain a 1um extra routing-screen reserve.
        return shape.buffer((radius + 0.001) / math.cos(math.pi / (4 * resolution)), resolution=resolution)

    copper = []
    for row in pads["pad_polygons"]:
        if row["ref"] == "J4":
            continue
        polygons = [Polygon(p["outer"], p["holes"]) for layer in row["layers"].values() for p in layer]
        copper.append((row["net"], row["ref"] + "." + row["pin"], unary_union(polygons).buffer(0.001)))
    drills = []
    for row in pads["pad_polygons"]:
        if row["ref"] != "J4" and max(row["drill_mm"]):
            drills.append(round_buffer(Point(row["position_mm"]), max(row["drill_mm"]) / 2))
    for node in children(tree, "segment"):
        net = str(first(node, "net")[-1]).lstrip("/")
        shape = LineString([list(map(float, first(node, k)[1:3])) for k in ["start", "end"]])
        copper.append((net, "track", round_buffer(shape, float(first(node, "width")[1]) / 2)))
    for node in children(tree, "via"):
        net = str(first(node, "net")[-1]).lstrip("/")
        point = Point(list(map(float, first(node, "at")[1:3])))
        copper.append((net, "via", round_buffer(point, float(first(node, "size")[1]) / 2)))
        drills.append(round_buffer(point, float(first(node, "drill")[1]) / 2))
    foreign = {net: unary_union([shape for n, _, shape in copper if n != net]) for net in ["5V_DIG", "AGND"]}
    holes = unary_union(drills)
    # Native assembly rows already include both PCB faces, THT tails, mounting
    # heads and radial capacitor bodies. Exclude only the old J4 being studied.
    bodies = []
    for b in native["boxes"]:
        if b[0].startswith("E28_") and not b[0].startswith("E28_J4"):
            bodies.append((b[0], box(b[1] + 92, b[2] - 8.5, b[1] + 92 + b[4], b[2] - 8.5 + b[5])))
    for c in native["cylinders"]:
        if c[0].startswith("E28_"):
            bodies.append((c[0], round_buffer(Point(c[1] + 92, c[2] - 8.5), c[4] / 2)))
    body_union = unary_union([p for _, p in bodies])
    points = np.array(
        [[x, y] for x in np.arange(217, 246.001, 0.25) for y in np.arange(102.7, 115.701, 0.25)]
    )
    point_shapes = shapely.points(points)
    copper_distance = {net: shapely.distance(point_shapes, shape) for net, shape in foreign.items()}
    hole_distance = shapely.distance(point_shapes, holes)
    body_distance = shapely.distance(point_shapes, body_union)
    valid = {net: (copper_distance[net] >= 2.1 + 0.16) & (hole_distance >= 1.1 + 0.2) for net in foreign}
    index = {tuple(np.round(p, 6)): i for i, p in enumerate(points)}
    candidates = []
    for i, p in enumerate(points):
        if not valid["5V_DIG"][i]:
            continue
        for dx, dy, angle in [(6, 0, 90), (0, 6, 0)]:
            q = p + [dx, dy]
            j = index.get(tuple(np.round(q, 6)))
            if j is None or not valid["AGND"][j]:
                continue
            reserve = box(
                min(p[0], q[0]) - 2.35, min(p[1], q[1]) - 2.35, max(p[0], q[0]) + 2.35, max(p[1], q[1]) + 2.35
            )
            body_gap = reserve.distance(body_union)
            if body_gap < 0.25:
                continue
            candidates.append(
                dict(
                    native_pad1_mm=p.tolist(),
                    native_pad2_mm=q.tolist(),
                    world_pad1_mm=[p[0] - 92, p[1] + 8.5],
                    world_pad2_mm=[q[0] - 92, q[1] + 8.5],
                    footprint_angle_deg=angle,
                    minimum_body_gap_mm=body_gap,
                    minimum_foreign_copper_gap_mm=min(
                        float(copper_distance["5V_DIG"][i]), float(copper_distance["AGND"][j])
                    ),
                )
            )
    best = {}
    for net in foreign:
        i = int(np.argmax(copper_distance[net]))
        p = points[i]
        nearest = sorted(
            [(name, shape.distance(Point(p))) for n, name, shape in copper if n != net], key=lambda r: r[1]
        )[:8]
        best[net] = dict(
            world_mm=[float(p[0] - 92), float(p[1] + 8.5)],
            maximum_available_foreign_copper_gap_mm=float(copper_distance[net][i]),
            required_gap_mm=2.26,
            nearest_foreign_items=[dict(item=n, gap_mm=g) for n, g in nearest],
        )
    report = dict(
        scope="Conservative no-parts-moved J4 placement screen within upper-right output region only; not an exhaustive layout search or native DRC",
        source_sha256=hashes,
        native_pcb_sha256=sha(pcb),
        separate_copper_candidate=pcb.resolve() != PCB.resolve(),
        grid_mm=0.25,
        screen_world_bounds_mm=[125, 111.2, 154, 124.2],
        sites_evaluated=len(points),
        positive_copper_clear_sites=int(np.count_nonzero(valid["5V_DIG"])),
        return_copper_clear_sites=int(np.count_nonzero(valid["AGND"])),
        single_site_body_clear_count=int(np.count_nonzero(body_distance >= 2.35 + 0.25)),
        best_copper_gaps=best,
        both_face_body_records=len(bodies),
        track_via_pad_shapes=len(copper),
        land_diameter_mm=4.2,
        drill_mm=2.2,
        pin_pitch_mm=6,
        foreign_copper_clearance_mm=0.16,
        hole_hole_clearance_mm=0.2,
        body_clearance_mm=0.25,
        native_pad_curve_error_reserve_mm=0.001,
        buffer_curve_approximation_is_circumscribed=True,
        zone_antipad_loss_evaluated=False,
        original_J4_only_excluded=True,
        eligible_candidates=candidates,
        numpy_version=np.__version__,
        shapely_version=shapely.__version__,
        native_DRC_verified=False,
        wire_route_verified=False,
        complete_output_harness=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Port search source changed"
    out.mkdir(parents=True, exist_ok=True)
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7), sharex=True, sharey=True)
    for ax, net in zip(axes, foreign):
        values = copper_distance[net].reshape(117, 53).T
        im = ax.imshow(
            values,
            origin="lower",
            extent=[124.875, 154.125, 111.075, 124.325],
            aspect="equal",
            vmin=0,
            vmax=2.26,
            cmap="viridis",
        )
        ax.set_title(net + " landing: gap to foreign routed copper")
        p = best[net]["world_mm"]
        ax.add_patch(Circle(p, 2.1, fill=False, color="red", linewidth=1.3))
        ax.plot(*p, "rx", markersize=7)
        ax.set_xlabel("Housing X, mm")
        ax.set_xlim(125, 154)
        ax.set_ylim(111.2, 124.2)
    axes[0].set_ylabel("Housing Y, mm")
    fig.colorbar(
        im,
        ax=axes.ravel().tolist(),
        orientation="horizontal",
        fraction=0.08,
        pad=0.22,
        label="Available copper gap, mm; 2.26 mm required",
    )
    fig.suptitle(
        "Upper-edge port screen: both faces and all routed copper layers\nRed circle = 4.2 mm land at largest gap; zone antipads are not screened",
        fontsize=11,
    )
    fig.savefig(out / "clearance-review.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    report["review_png_sha256"] = sha(out / "clearance-review.png")
    (out / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "sites_evaluated",
                    "positive_copper_clear_sites",
                    "return_copper_clear_sites",
                    "single_site_body_clear_count",
                    "best_copper_gaps",
                    "eligible_candidates",
                ]
            },
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", type=Path, default=PCB)
    parser.add_argument("--pads", type=Path, default=PADS)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--body-contract", type=Path)
    args = parser.parse_args()
    run(
        args.pcb.resolve(),
        args.pads.resolve(),
        args.out.resolve(),
        None if args.body_contract is None else args.body_contract.resolve(),
    )
