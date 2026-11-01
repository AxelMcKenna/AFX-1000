"""Read existing CP01 meshes: triangle/AABB SAT plus solid containment.

No OpenSCAD execution; this is a source-bound placement precheck rather than
native/hardware qualification. Nominal captured meshes retain their caveats.
"""

import hashlib
import json
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
WORK = ROOT / "generated/u27-band-placement-work"
CP = REPO / "hardware/cad/a12/thermal/enlarged_base_pot/generated"


def triangles(path):
    blob = path.read_bytes()
    n = struct.unpack_from("<I", blob, 80)[0]
    assert len(blob) == 84 + 50 * n and n > 0
    dt = np.dtype([("normal", "<f4", (3,)), ("points", "<f4", (3, 3)), ("attribute", "<u2")])
    return np.frombuffer(blob, dtype=dt, offset=84, count=n)["points"].astype(float)


def hits(ts, box):
    low, high = np.array(box[:3]), np.array(box[3:])
    half = (high - low) / 2
    center = (low + high) / 2
    mask = np.all(ts.max(axis=1) >= low - 1e-9, axis=1) & np.all(ts.min(axis=1) <= high + 1e-9, axis=1)
    selected = ts[mask] - center
    count = 0
    for t in selected:
        edges = [t[1] - t[0], t[2] - t[1], t[0] - t[2]]
        axes = [*np.eye(3), np.cross(edges[0], edges[1])]
        axes += [np.cross(e, a) for e in edges for a in np.eye(3)]
        overlap = True
        for axis in axes:
            if np.dot(axis, axis) < 1e-24:
                continue
            projection = t @ axis
            radius = np.abs(axis) @ half
            if projection.min() > radius + 1e-9 or projection.max() < -radius - 1e-9:
                overlap = False
                break
        count += overlap
    return int(count)


def contains(ts, point):
    direction = np.array([1, 0.123456789, 0.071234567])
    direction /= np.linalg.norm(direction)
    e1, e2 = ts[:, 1] - ts[:, 0], ts[:, 2] - ts[:, 0]
    p = np.cross(direction, e2)
    det = np.sum(e1 * p, axis=1)
    valid = np.abs(det) > 1e-12
    inv = np.divide(1, det, out=np.zeros_like(det), where=valid)
    delta = np.array(point) - ts[:, 0]
    u = np.sum(delta * p, axis=1) * inv
    q = np.cross(delta, e1)
    v = np.sum(direction * q, axis=1) * inv
    t = np.sum(e2 * q, axis=1) * inv
    accepted = t[valid & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-9)]
    return bool(len(np.unique(np.round(accepted, 6))) % 2)


def main():
    proposal_path = WORK / "generated/numeric-MCAD-screen.json"
    proposal = json.loads(proposal_path.read_text())
    paths = [
        CP / (name + ".stl")
        for name in (
            "eb_carrier_geometry",
            "eb_attachment_geometry",
            "eb_metal_geometry",
            "eb_interface_geometry",
            "eb_retained_power_review",
            "ei_controls_geometry",
            "ei_all_ports_geometry",
            "ei_trill_frontbay_geometry",
            "ps_body_geometry",
            "ps_stack",
            "cp_pot_hardware_review",
        )
    ]
    hashes = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [*paths, proposal_path, Path(__file__)]
    }
    results = {}
    body_boxes = {}
    for ref, data in proposal["components"].items():
        b = data["courtyard_body_box_world_mm"]
        body_boxes[ref] = [b[0] - 0.25, b[1] - 0.25, b[2] - 0.45, b[3] + 0.25, b[4] + 0.25, b[5] + 0.45]
    for path in paths:
        ts = triangles(path)
        rows = {}
        for ref, box in body_boxes.items():
            center = (np.array(box[:3]) + np.array(box[3:])) / 2
            rows[ref] = dict(
                surface_intersecting_triangles=hits(ts, box),
                center_containment_ray_parity=contains(ts, center),
            )
        results[path.name] = rows
    carrier = triangles(CP / "eb_carrier_geometry.stl")
    floor_control = contains(carrier, [133, 156, 1])
    post_control = contains(carrier, [130.0871, 168.922, 10])
    edge = [133.5871, 168.822, 9.9, 133.7871, 169.022, 10.1]
    surface_control = hits(carrier, edge)
    failures = [
        dict(obstacle=path, ref=ref, **row)
        for path, rows in results.items()
        for ref, row in rows.items()
        if row["surface_intersecting_triangles"] or row["center_containment_ray_parity"]
    ]
    assert floor_control and post_control and surface_control > 0
    assert all(hashlib.sha256((REPO / n).read_bytes()).hexdigest() == h for n, h in hashes.items())
    result = dict(
        scope=__doc__,
        source_sha256=hashes,
        screen_boxes_world_mm=body_boxes,
        checks=results,
        deliberate_inside_floor_detected=floor_control,
        deliberate_inside_post_detected=post_control,
        deliberate_post_surface_intersections=surface_control,
        observed_intersections=failures,
        captured_mesh_screen_clear=not failures,
        native_reruns_performed=0,
        existing_retained_meshes_are_not_manufacturer_part_bounds=True,
        full_native_MCAD_and_physical_qualification=False,
    )
    (WORK / "generated/numeric-mesh-screen.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                clear=not failures, failures=failures, controls=[floor_control, post_control, surface_control]
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
