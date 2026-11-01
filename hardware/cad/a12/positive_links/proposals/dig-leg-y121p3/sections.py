"""Renew PB02 normal-section witnesses without changing parent module globals."""

import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    import cadquery as cq
    import numpy as np

    from hardware.cad.a12.positive_links.generate import shape

    data = json.loads((ROOT / "design.json").read_text())
    generated = json.loads((ROOT / "generated/geometry.json").read_text())
    inputs = dict(generated["source_sha256"])
    inputs[str(Path(__file__).relative_to(REPO))] = sha(Path(__file__))
    assert all(sha(REPO / n) == h for n, h in inputs.items())
    minimum = copy.deepcopy(data)
    b = minimum["bar"]
    coating = data["surface"]["maximum_project_um_each_face"] / 1000
    b["width"] = b["width_range"][0] - 2 * coating
    b["thickness"] = b["thickness_range"][0] - 2 * coating
    b["landing_diameter"] = b["landing_range"][0] - 2 * coating
    b["hole_diameter"] = b["hole_range"][1] + 2 * coating
    results = {}
    for name, row in data["paths"].items():
        solid = shape(minimum, name)
        assert solid.isValid() and len(solid.Solids()) == 1
        points = [np.array(q, dtype=float) for q in row["points"]]
        samples = []
        for i, (a, z) in enumerate(zip(points, points[1:])):
            samples.append(("segment" + str(i), (a + z) / 2, (z - a) / np.linalg.norm(z - a), False))
        for i, q in enumerate(points[1:-1], 1):
            normal = (q - points[i - 1]) / np.linalg.norm(q - points[i - 1]) + (
                points[i + 1] - q
            ) / np.linalg.norm(points[i + 1] - q)
            normal /= np.linalg.norm(normal)
            samples.append(("corner" + str(i), q, normal, False))
        for i in [0, -1]:
            normal = points[1] - points[0] if i == 0 else points[-1] - points[-2]
            normal /= np.linalg.norm(normal)
            samples.append(("hole" + str(i), points[i], normal, True))
        witnesses = []
        for label, q, normal, hole in samples:
            xaxis = np.cross(normal, [0.0, 0.0, 1.0]) if abs(normal[2]) < 0.99 else np.array([1.0, 0.0, 0.0])
            xaxis /= np.linalg.norm(xaxis)
            plane = cq.Plane(origin=tuple(q), xDir=tuple(xaxis), normal=tuple(normal))
            slab = (
                cq.Workplane(plane)
                .box(12 if hole else 8.3, 8.3 if abs(normal[2]) > 0.99 else 4.5, 0.001, centered=True)
                .val()
            )
            raw = solid.intersect(slab).Volume() / 0.001
            corrected = raw - 4 * b["maximum_edge_break"] ** 2
            assert corrected >= b["minimum_net_normal_area"], (name, label, corrected)
            witnesses.append(
                dict(
                    id=label,
                    origin_mm=q.tolist(),
                    normal=normal.tolist(),
                    raw_area_mm2=raw,
                    edge_corrected_area_mm2=corrected,
                )
            )
        amin = min(w["edge_corrected_area_mm2"] for w in witnesses)
        length = math.fsum(math.dist(a, z) for a, z in zip(points, points[1:]))
        rho = 1 / (data["bar"]["conductivity_receiving_allocation_ms_per_m"] * 1e6)
        temperature_factor = 1 + data["bar"]["temperature_coefficient_assumed_per_k"] * (
            data["bar"]["dc_screen_temperature_c"] - 20
        )
        results[name] = dict(
            witnesses=witnesses,
            minimum_witness_area_mm2=amin,
            centreline_length_mm=length,
            conditional_uniform_section_bulk_dc_mohm=rho
            * temperature_factor
            * (length / 1000)
            / (amin * 1e-6)
            * 1000,
        )
        print(name, len(witnesses), "sections; minimum", amin, "mm2", flush=True)
    assert all(sha(REPO / n) == h for n, h in inputs.items())
    result = dict(
        scope=__doc__,
        source_sha256=inputs,
        links=results,
        slab_thickness_mm=0.001,
        finite_witnesses_all_meet_project_minimum=True,
        global_minimum_cross_section_theorem_proved=False,
        three_dimensional_current_crowding_or_joints_validated=False,
        conductivity_and_temperature_are_unaccepted_allocations=True,
        complete_link_resistance_verified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "sections.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
