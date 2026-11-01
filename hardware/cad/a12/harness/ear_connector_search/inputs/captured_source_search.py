"""Bounded quarter-profile ranking on actual clipped native obstacle surfaces.

This is a conservative sampled clearance screen, not a native geometry pass,
whole-route feasibility proof or global impossibility result. Source joints,
bare/cut/source bores and the entire receiving route remain separate checks.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import vtk
from scipy.spatial.distance import cdist
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

ROOT = Path(__file__).resolve().parent
OD_MAX = 1.7526
FACE = 6.62
POSITION = 0.65
CLEARANCE = 0.25
RESERVE = 0.005
BARE_LENGTH = 3.1
CIRC = 1 / math.cos(math.pi / 64) ** 2
WINDOW = np.array([[154, 104, 3], [185, 139, 37]], float)
STARTS = {"1": np.array([161, 120.5, FACE]), "2": np.array([161, 126.5, FACE])}
TARGETS = {"1": np.array([188, 100, 8.1]), "2": np.array([188, 104, 8.1])}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def profile(pin, radius, angle, plane, step):
    assert radius >= 9.6393
    straight = plane - FACE - radius
    if straight < 0:
        return None
    phi = math.radians(angle)
    total = straight + radius * math.pi / 2
    pieces = []
    chord = radius * (math.pi / 240) ** 2 / 8
    for kind, lo, hi, base in [
        ("bare", 0, min(BARE_LENGTH, total), 0.7),
        ("insulated", BARE_LENGTH, total, OD_MAX / 2),
    ]:
        if hi < lo:
            continue
        count = max(1, math.ceil((hi - lo) / step))
        s = np.linspace(lo, hi, count + 1)
        theta = np.maximum(s - straight, 0) / radius
        z = np.where(s <= straight, FACE + s, FACE + straight + radius * np.sin(theta))
        d = np.where(s <= straight, 0, radius * (1 - np.cos(theta)))
        pts = np.column_stack((STARTS[pin][0] + d * math.cos(phi), STARTS[pin][1] + d * math.sin(phi), z))
        cover = (hi - lo) / count / 2
        pieces.append(
            dict(
                kind=kind,
                points=pts,
                cover_mm=cover,
                external_radius_mm=(base + POSITION + RESERVE + CLEARANCE) * CIRC + chord,
                pair_radius_mm=(base + POSITION + RESERVE + CLEARANCE / 2) * CIRC + chord,
            )
        )
    endpoint = pieces[-1]["points"][-1]
    bounds = np.array([np.minimum(STARTS[pin], endpoint), np.maximum(STARTS[pin], endpoint)])
    outer = (OD_MAX / 2 + POSITION + RESERVE + CLEARANCE) * CIRC + chord
    clip = float(min((bounds[0] - outer - WINDOW[0]).min(), (WINDOW[1] - bounds[1] - outer).min()))
    tangent = np.array([math.cos(phi), math.sin(phi), 0])
    delta = TARGETS[pin] - endpoint
    align = float(np.dot(tangent, delta) / np.linalg.norm(delta))
    key = f"{pin}:R{radius:g}:A{angle:g}:Z{plane:g}"
    return dict(
        id=key,
        pin=pin,
        radius_mm=radius,
        angle_deg=angle,
        endplane_mm=plane,
        initial_straight_mm=straight,
        curve_length_mm=total,
        pieces=pieces,
        endpoint_mm=endpoint.tolist(),
        window_margin_mm=clip,
        endpoint_straight_line_distance_to_receiver_mm=float(np.linalg.norm(delta)),
        endpoint_tangent_alignment_to_receiver=align,
        chord_bound_mm=chord,
    )


class Surface:
    def __init__(self, path):
        reader = vtk.vtkSTLReader()
        reader.SetFileName(str(path))
        reader.Update()
        self.mesh = reader.GetOutput()
        assert self.mesh.GetNumberOfCells() > 0
        edges = vtk.vtkFeatureEdges()
        edges.SetInputData(self.mesh)
        edges.BoundaryEdgesOn()
        edges.NonManifoldEdgesOff()
        edges.FeatureEdgesOff()
        edges.ManifoldEdgesOff()
        edges.Update()
        boundary_edges = edges.GetOutput().GetNumberOfCells()
        assert boundary_edges == 0, ("Open STL boundary", path)
        edges.BoundaryEdgesOff()
        edges.NonManifoldEdgesOn()
        edges.Update()
        self.topology = dict(
            boundary_edges=boundary_edges,
            nonmanifold_contact_edges=edges.GetOutput().GetNumberOfCells(),
            native_STL_sha256=sha(path),
        )
        self.function = vtk.vtkImplicitPolyDataDistance()
        self.function.SetInput(self.mesh)
        self.path = path

    def values(self, pts):
        x = numpy_to_vtk(np.ascontiguousarray(pts), deep=False)
        out = vtk.vtkDoubleArray()
        out.SetNumberOfComponents(1)
        out.SetNumberOfTuples(len(pts))
        self.function.FunctionValue(x, out)
        return vtk_to_numpy(out).copy()


def inputs():
    capture = json.loads((ROOT / "capture.json").read_text())
    for name, digest in capture["copied_inputs_sha256"].items():
        assert sha(ROOT / "inputs" / name) == digest, ("Changed frozen input", name)
    data = json.loads((ROOT / "inputs/electronics.json").read_text())
    native, other = data["native"], data["other"]
    boxes = []
    switch = []

    def add_box(target, b, expand_z=True):
        lo = np.array(b[1:4], float)
        size = np.array(b[4:7], float)
        if expand_z:
            lo[2] -= 0.2
            size[2] += 0.4
        if np.all(lo + size >= WINDOW[0]) and np.all(lo <= WINDOW[1]):
            target.append((b[0], lo, size))

    for b in native["boxes"]:
        if not b[0].startswith("E28_J4"):
            add_box(boxes, b)
    for b in other["envelopes"]:
        if not b[0].startswith("disconnect_"):
            add_box(boxes, b)
    for b in other["port_envelopes"]:
        add_box(boxes, b)
    for b in native["switch_diagnostic_boxes"]:
        add_box(switch, b)
    for b in other["boards"]:
        if b[0] != "disconnect_carrier":
            add_box(boxes, ["pcb:" + b[0], *b[1:7]], False)
    for b in native["boards"]:
        if b["id"] == "E28":
            continue
        pts = np.array(b["outline_relative_mm"])
        lo = pts.min(axis=0) + np.array(b["datum"][:2])
        hi = pts.max(axis=0) + np.array(b["datum"][:2])
        add_box(
            boxes,
            [
                "pcb:" + b["id"],
                *lo,
                b["datum"][2] - 0.2,
                *(hi - lo),
                b["thickness_range_allocation_mm"][1] + 0.4,
            ],
            False,
        )
    cylinders = []
    for c in native["cylinders"]:
        cx, cy, z, d, h = map(float, c[1:6])
        r = d / 2 / math.cos(math.pi / 128)
        lo = np.array([cx - r, cy - r, z - 0.2])
        size = np.array([2 * r, 2 * r, h + 0.4])
        if np.all(lo + size >= WINDOW[0]) and np.all(lo <= WINDOW[1]):
            cylinders.append((c[0], cx, cy, z - 0.2, r, h + 0.4))
    surfaces = {name: Surface(ROOT / "inputs" / f"{name}.stl") for name in ["case", "return", "positive"]}
    witness = surfaces["case"].values(np.array([[164, 110, 23.1]]))[0]
    assert witness < 0, ("Native lead witness not inside case solid", witness)
    return (
        boxes,
        switch,
        cylinders,
        surfaces,
        dict(
            local_component_board_boxes=len(boxes),
            switch_diagnostic_boxes=len(switch),
            mount_cylinders=len(cylinders),
            native_case_lead_witness_signed_distance_mm=float(witness),
            VTK_version=vtk.vtkVersion().GetVTKVersion(),
            surface_topology={name: surface.topology for name, surface in surfaces.items()},
        ),
    )


def box_values(points, boxes):
    if not boxes:
        return np.full(len(points), np.inf), np.full(len(points), -1)
    lo = np.array([b[1] for b in boxes])
    half = np.array([b[2] for b in boxes]) / 2
    centre = lo + half
    values = []
    which = []
    for i in range(0, len(points), 4000):
        q = np.abs(points[i : i + 4000, None, :] - centre[None, :, :]) - half[None, :, :]
        d = np.linalg.norm(np.maximum(q, 0), axis=2) + np.minimum(q.max(axis=2), 0)
        values.append(d.min(axis=1))
        which.append(d.argmin(axis=1))
    return np.concatenate(values), np.concatenate(which)


def cylinder_values(points, cylinders):
    if not cylinders:
        return np.full(len(points), np.inf)
    values = []
    for c in cylinders:
        _, x, y, z, r, h = c
        qr = np.linalg.norm(points[:, :2] - [x, y], axis=1) - r
        qz = np.abs(points[:, 2] - (z + h / 2)) - h / 2
        values.append(
            np.sqrt(np.maximum(qr, 0) ** 2 + np.maximum(qz, 0) ** 2) + np.minimum(np.maximum(qr, qz), 0)
        )
    return np.min(values, axis=0)


def individual(profiles, obstacles):
    boxes, switch, cylinders, surfaces, meta = obstacles
    valid = [p for p in profiles if p and p["window_margin_mm"] > 0]
    parts = [q for p in valid for q in p["pieces"]]
    pts = np.concatenate([p["points"] for p in parts])
    distances = {name: surf.values(pts) for name, surf in surfaces.items()}
    distances["components"], ids = box_values(pts, boxes)
    distances["cylinders"] = cylinder_values(pts, cylinders)
    switchdist, _ = box_values(pts, switch)
    at = 0
    for p in valid:
        margins = {k: np.inf for k in distances}
        switchmargin = np.inf
        nearest = {}
        for piece in p["pieces"]:
            n = len(piece["points"])
            allow = piece["external_radius_mm"] + piece["cover_mm"]
            sl = slice(at, at + n)
            for name, values in distances.items():
                v = values[sl] - allow
                j = int(v.argmin())
                if v[j] < margins[name]:
                    margins[name] = float(v[j])
                    nearest[name] = dict(
                        point_mm=piece["points"][j].tolist(),
                        kind=piece["kind"],
                        native_surface_or_envelope_distance_mm=float(values[at + j]),
                        continuous_sample_cover_mm=piece["cover_mm"],
                        inflated_native_radius_mm=piece["external_radius_mm"],
                        component=boxes[int(ids[at + j])][0] if name == "components" else None,
                    )
            switchmargin = min(switchmargin, float((switchdist[sl] - allow).min()))
            at += n
        p.update(
            clearance_lower_estimates_mm=margins,
            switch_AABB_diagnostic_margin_mm=switchmargin,
            nearest=nearest,
            individual_sample_cover_clear=min(margins.values()) > 0,
        )
    return valid


def pair_gap(a, b):
    best = np.inf
    details = None
    for x in a["pieces"]:
        for y in b["pieces"]:
            d = cdist(x["points"], y["points"])
            i, j = np.unravel_index(int(d.argmin()), d.shape)
            gap = float(d[i, j]) - x["pair_radius_mm"] - y["pair_radius_mm"] - x["cover_mm"] - y["cover_mm"]
            if gap < best:
                best = gap
                details = dict(
                    a_point_mm=x["points"][i].tolist(),
                    b_point_mm=y["points"][j].tolist(),
                    a_kind=x["kind"],
                    b_kind=y["kind"],
                    sampled_distance_mm=float(d[i, j]),
                    combined_continuous_cover_mm=x["cover_mm"] + y["cover_mm"],
                )
    return float(best), details


def public(p):
    return {k: v for k, v in p.items() if k != "pieces"}


def run(step=0.25, refine=False):
    obstacles = inputs()
    radii = [10.0, 12.0, 14.0, 16.0]
    if refine:
        coarse = json.loads((ROOT / "coarse.json").read_text())
        selected = coarse["recommended_pairs"][:10]
        parameters = {pin: set() for pin in ["1", "2"]}
        for pair in selected:
            for pin, part in [("1", "positive"), ("2", "return")]:
                p = pair[part]
                for angle in np.arange(max(-90, p["angle_deg"] - 5), min(30, p["angle_deg"] + 5) + 0.1, 2.5):
                    for plane in np.arange(
                        max(18, p["endplane_mm"] - 1), min(32, p["endplane_mm"] + 1) + 0.01, 0.25
                    ):
                        parameters[pin].add((p["radius_mm"], float(angle), float(plane)))
        profiles = [
            profile(pin, *args, step) for pin, args_set in parameters.items() for args in sorted(args_set)
        ]
    else:
        profiles = [
            profile(pin, r, angle, z, step)
            for pin in ["1", "2"]
            for r in radii
            for angle in range(-90, 31, 10)
            for z in range(18, 33)
        ]
    profiles = [p for p in profiles if p]
    valid = individual(profiles, obstacles)
    clear = {
        pin: [p for p in valid if p["pin"] == pin and p["individual_sample_cover_clear"]]
        for pin in ["1", "2"]
    }
    pairs = []
    for a in clear["1"]:
        for b in clear["2"]:
            gap, detail = pair_gap(a, b)
            if gap <= 0:
                continue
            minimum = min(
                gap, *a["clearance_lower_estimates_mm"].values(), *b["clearance_lower_estimates_mm"].values()
            )
            length = (
                a["endpoint_straight_line_distance_to_receiver_mm"]
                + b["endpoint_straight_line_distance_to_receiver_mm"]
            )
            alignment = (
                a["endpoint_tangent_alignment_to_receiver"] + b["endpoint_tangent_alignment_to_receiver"]
            )
            score = minimum - 0.01 * length + 0.1 * alignment
            pairs.append(
                dict(
                    positive=public(a),
                    return_profile=public(b),
                    pair_clearance_lower_estimate_mm=gap,
                    pair_nearest=detail,
                    minimum_individual_or_pair_margin_mm=minimum,
                    receiver_distance_sum_mm=length,
                    receiver_tangent_alignment_sum=alignment,
                    ranking_score=score,
                )
            )
    pairs.sort(key=lambda p: p["ranking_score"], reverse=True)
    # Preserve expected 'return' key for simple downstream profile tuple construction.
    for p in pairs:
        p["return"] = p.pop("return_profile")
    report = dict(
        scope=__doc__,
        input_capture_sha256=sha(ROOT / "capture.json"),
        source_code_sha256=sha(Path(__file__)),
        sampling_arc_length_maximum_mm=step,
        profile_count=len(profiles),
        clipped_window_rejected_count=sum(p["window_margin_mm"] <= 0 for p in profiles),
        individual_feasible_counts={pin: len(p) for pin, p in clear.items()},
        pair_feasible_count=len(pairs),
        recommended_pairs=pairs[:30],
        best_individual_profiles={
            pin: [
                public(p)
                for p in sorted(
                    [q for q in valid if q["pin"] == pin],
                    key=lambda q: min(q["clearance_lower_estimates_mm"].values()),
                    reverse=True,
                )[:15]
            ]
            for pin in ["1", "2"]
        },
        input_geometry=obstacles[-1],
        constraints=dict(
            OD_max_mm=OD_MAX,
            minimum_centreline_radius_mm=9.6393,
            position_allocation_each_wire_mm=POSITION,
            clearance_mm=CLEARANCE,
            geometry_reserve_mm=RESERVE,
            native_circumscription_factor=CIRC,
            radius_choices_mm=radii,
            azimuth_bounded_deg=[-90, 30],
            endplane_bounded_mm=[18, 32],
            bare_first_mm=BARE_LENGTH,
            clipped_window_mm=WINDOW.tolist(),
            clipped_window_faces_not_used_as_free_space=True,
        ),
        continuous_cover_method="Arc-length sampling; signed-distance1-Lipschitz bound subtracts half maximum spacing per curve. Pair subtracts both independent cover lengths/position allocations. Native circumscribed sphere and chord bounds retained.",
        flat_insulation_cut_approximated_by_conservative_capsule_superset=True,
        switch_diagnostic_AABBs_not_used_as_hard_rejection_because_exact_case_STL_contains_actual_rotated_switches=True,
        source_joint_bore_and_whole_path_native_checks_required=True,
        native_geometry_pass=False,
        global_impossibility_claim=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    target = ROOT / ("refined.json" if refine else "coarse.json")
    target.write_text(json.dumps(report, indent=2) + "\n")
    print("RESULT", report["individual_feasible_counts"], "pairs", len(pairs), flush=True)
    for p in pairs[:5]:
        print(
            "PAIR",
            p["positive"]["id"],
            p["return"]["id"],
            "min",
            p["minimum_individual_or_pair_margin_mm"],
            "pair",
            p["pair_clearance_lower_estimate_mm"],
            flush=True,
        )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=float, default=0.25)
    parser.add_argument("--refine", action="store_true")
    args = parser.parse_args()
    run(args.step, args.refine)
