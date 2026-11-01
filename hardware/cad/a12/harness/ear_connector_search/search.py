"""Exact-circle C1 connector families on captured extended native obstacles."""

import importlib.util
import json
import math

import numpy as np
from scipy.spatial import cKDTree

from .arcs import connect, evaluate, lift_connect, prefix
from .capture import INPUTS, OUT, ROOT, WINDOW

spec = importlib.util.spec_from_file_location(
    "captured_curve_obstacles", INPUTS / "captured_source_search.py"
)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
OD = 1.7526
POSITION = 0.65
CLEARANCE = 0.25
RESERVE = 0.005
CIRC = 1 / math.cos(math.pi / 64) ** 2
MIN_R = 9.6393


def obstacles():
    cap = json.loads((ROOT / "capture.json").read_text())
    if not cap["native_obstacles_accepted"]:
        raise ValueError("Rejected extended obstacle capture")
    for p, h in cap["captured_inputs_sha256"].items():
        if helpers.sha(INPUTS / p) != h:
            raise ValueError("Changed captured source:" + p)
    data = json.loads((INPUTS / "electronics.json").read_text())
    n, o = data["native"], data["other"]
    boxes = []
    cylinders = []

    def box(row, expand=True):
        lo = np.array(row[1:4], float)
        size = np.array(row[4:7], float)
        if expand:
            lo[2] -= 0.2
            size[2] += 0.4
        if np.all(lo + size >= WINDOW[0]) and np.all(lo <= WINDOW[1]):
            boxes.append((row[0], lo, size))

    for b in n["boxes"] + o["envelopes"] + o["port_envelopes"]:
        if b[0] != "e19_J13":
            box(b)
    for b in o["boards"]:
        box(["pcb:" + b[0], *b[1:7]], False)
    for b in n["boards"]:
        pts = np.array(b["outline_relative_mm"])
        lo = pts.min(axis=0) + b["datum"][:2]
        hi = pts.max(axis=0) + b["datum"][:2]
        box(
            [
                "pcb:" + b["id"],
                *lo,
                b["datum"][2] - 0.2,
                *(hi - lo),
                b["thickness_range_allocation_mm"][1] + 0.4,
            ],
            False,
        )
    ear = o["ear_board"]
    pts = np.array(ear["outline_relative_mm"])
    lo = pts.min(axis=0) + ear["datum"][:2]
    hi = pts.max(axis=0) + ear["datum"][:2]
    box(["pcb:E19_ear", *lo, 6.3, *(hi - lo), 2.16], False)
    for c in n["cylinders"]:
        x, y, z, d, h = map(float, c[1:6])
        r = d / 2 / math.cos(math.pi / 128)
        if np.all(np.array([x + r, y + r, z + h + 0.2]) >= WINDOW[0]) and np.all(
            np.array([x - r, y - r, z - 0.2]) <= WINDOW[1]
        ):
            cylinders.append((c[0], x, y, z - 0.2, r, h + 0.4))
    surfaces = {name: helpers.Surface(INPUTS / (name + ".stl")) for name in ["case", "return", "positive"]}
    witness = float(surfaces["case"].values(np.array([[164, 110, 23.1]]))[0])
    if witness >= 0:
        raise ValueError("Missed actual native switch-lead witness")
    return (
        boxes,
        cylinders,
        surfaces,
        dict(
            boxes=len(boxes),
            cylinders=len(cylinders),
            witness_signed_distance_mm=witness,
            surface_topology={k: v.topology for k, v in surfaces.items()},
            own_J13_contact_body_only_excluded=True,
            H9_actual_geometry_captured=not data["H9_provisional_not_actual_source"],
        ),
    )


def exact_bounds(row):
    if row.get("kind") == "cubic_bezier":
        cp = np.array(row["control_points_mm"])
        return np.array([cp.min(axis=0), cp.max(axis=0)])
    start = np.array(row["start"])
    arc = np.array(row.get("horizontal_arc_start", row["start"]))
    r = row["horizontal_radius_mm"]
    sign = row["turn_sign"]
    phi = math.radians(row["initial_heading_deg"])
    end = math.radians(row["final_horizontal_heading_deg"])
    pts = [start, arc, np.array(row["first_join"]), np.array(row["second_join"]), np.array(row["finish"])]
    if "lift_segment" in row:
        pts.extend([np.array(row["lift_segment"]["start"]), np.array(row["lift_segment"]["finish"])])
    for i in range(-8, 9):
        a = i * math.pi / 2
        if min(phi, end) <= a <= max(phi, end):
            pts.append(
                arc + [sign * r * (math.sin(a) - math.sin(phi)), sign * r * (math.cos(phi) - math.cos(a)), 0]
            )
    return np.array([np.min(pts, axis=0), np.max(pts, axis=0)])


def individual(rows, obs, step=0.25):
    boxes, cylinders, surfaces, _ = obs
    parts = []
    valid = []
    external = (OD / 2 + POSITION + CLEARANCE + RESERVE) * CIRC
    for row in rows:
        if row.get("kind") != "cubic_bezier" and row["minimum_continuous_radius_lower_mm"] <= MIN_R:
            continue
        bounds = exact_bounds(row)
        margin = float(
            min(
                (bounds[0] - external - np.array(WINDOW[0])).min(),
                (np.array(WINDOW[1]) - bounds[1] - external).min(),
            )
        )
        if margin <= 0:
            continue
        points, contract = evaluate(row, step)
        row.update(
            window_margin_mm=margin, analytic_centerline_bounds_mm=bounds.tolist(), sample_contract=contract
        )
        parts.append(points)
        valid.append(row)
    if not valid:
        return []
    pts = np.concatenate(parts)
    distances = {k: s.values(pts) for k, s in surfaces.items()}
    distances["components"], indices = helpers.box_values(pts, boxes)
    distances["cylinders"] = helpers.cylinder_values(pts, cylinders)
    at = 0
    for row, points in zip(valid, parts):
        count = len(points)
        sl = slice(at, at + count)
        allow = (
            external
            + row["sample_contract"]["continuous_nearest_sample_cover_mm"]
            + row["sample_contract"]["chord_error_bound_mm"]
        )
        margins = {k: float(v[sl].min() - allow) for k, v in distances.items()}
        details = {}
        for k, v in distances.items():
            j = int(v[sl].argmin())
            details[k] = dict(
                point_mm=points[j].tolist(),
                native_surface_or_envelope_distance_mm=float(v[at + j]),
                component=boxes[int(indices[at + j])][0] if k == "components" else None,
            )
        row.update(
            clearance_lower_estimates_mm=margins,
            nearest=details,
            sample_cover_clear=min(margins.values()) > 0,
            clearance_is_native_boolean_proof=False,
        )
        at += count
    return valid


def pair(a, b, source_profiles, step=0.1):
    paths = []
    covers = []
    radii = []
    for row, pin in [(a, "1"), (b, "2")]:
        begin, bc = prefix(source_profiles[pin], step)
        mid, mc = evaluate(row, step)
        stub = np.array([row["finish"]]) - np.linspace(
            0, row["finish"][2] - 8.1, max(1, math.ceil((row["finish"][2] - 8.1) / step)) + 1
        )[:, None] * [0, 0, 1]
        paths.append(np.vstack([begin, mid[1:], stub[1:]]))
        covers.append(
            max(bc["continuous_nearest_sample_cover_mm"], mc["continuous_nearest_sample_cover_mm"], step / 2)
        )
        radii.append(
            (OD / 2 + POSITION + RESERVE + CLEARANCE / 2) * CIRC
            + max(bc["chord_error_bound_mm"], mc["chord_error_bound_mm"])
        )
    ds, ids = cKDTree(paths[0]).query(paths[1], workers=1)
    j = int(ds.argmin())
    i = int(ids[j])
    margin = float(ds[j] - sum(covers) - sum(radii))
    return margin, dict(
        sampled_distance_mm=float(ds[j]),
        a_point_mm=paths[0][i].tolist(),
        b_point_mm=paths[1][j].tolist(),
        combined_continuous_cover_mm=sum(covers),
        inflated_pair_radii_mm=radii,
        max_insulation_OD_conservatively_used_for_bare_segments=True,
    )


def run(stub=7):
    src = json.loads((INPUTS / "selected-source.json").read_text())["tight_sample_cover_candidate"]
    source = {"1": src["positive"], "2": src["return_profile"]}
    obs = obstacles()
    built = {}
    for pin, key, sign in [("1", "positive", -1), ("2", "return_profile", 1)]:
        p = src[key]
        finish = [188, 100 if pin == "1" else 104, 8.1 + stub]
        rows = []
        if pin == "1":
            for rise in [0.65, 0.8, 1.0, 1.2, 1.5]:
                for theta in np.arange(-85, -145.1, -2):
                    for r in np.arange(9.7, 14.01, 0.3):
                        try:
                            rows.append(
                                lift_connect(
                                    p["endpoint_mm"],
                                    p["angle_deg"],
                                    finish,
                                    float(theta),
                                    sign,
                                    float(r),
                                    rise,
                                    9.7,
                                )
                            )
                        except ValueError:
                            pass
        else:
            for theta in np.arange(-37.44, -37.20, 0.01):
                try:
                    rows.append(connect(p["endpoint_mm"], p["angle_deg"], finish, float(theta), sign))
                except ValueError:
                    pass
        print(pin, "analytic candidates", len(rows), flush=True)
        screened = individual(rows, obs)
        clear = [r for r in screened if r["sample_cover_clear"]]
        clear.sort(
            key=lambda r: (-min(r["clearance_lower_estimates_mm"].values()), r["analytic_length_upper_mm"])
        )
        built[pin] = clear
        (OUT / ("lift-individual-" + pin + ".json")).write_text(
            json.dumps(dict(screened=screened, clear=len(clear)), indent=2) + "\n"
        )
        print(
            pin,
            "window candidates",
            len(screened),
            "clear",
            len(clear),
            "best",
            clear[0]["clearance_lower_estimates_mm"] if clear else None,
            flush=True,
        )
    pairs = []
    for a in built["1"][:120]:
        for b in built["2"][:40]:
            margin, near = pair(a, b, source, 0.2)
            if margin > 0:
                pairs.append(
                    dict(
                        positive=a,
                        return_profile=b,
                        pair_margin_mm=margin,
                        pair_nearest=near,
                        minimum_margin_mm=min(
                            margin,
                            *a["clearance_lower_estimates_mm"].values(),
                            *b["clearance_lower_estimates_mm"].values(),
                        ),
                    )
                )
    pairs.sort(key=lambda r: -r["minimum_margin_mm"])
    report = dict(
        scope=__doc__,
        stub_length_mm=stub,
        source_profiles=source,
        obstacle_metadata=obs[-1],
        candidate_counts={k: len(v) for k, v in built.items()},
        recommended_pairs=pairs[:12],
        full_native_validation_completed=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (OUT / ("lift-search-" + str(stub) + "mm.json")).write_text(json.dumps(report, indent=2) + "\n")
    print("clear pairs", len(pairs), "best", pairs[0]["minimum_margin_mm"] if pairs else None, flush=True)


if __name__ == "__main__":
    run()
