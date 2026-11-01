"""Independent local BREP section witnesses and conditional DC arithmetic."""

import copy
import json

from .generate import OUT, ROOT, load, sha, shape


def area_screens(d):
    b = d["bar"]
    coat = d.get("surface", {}).get("maximum_project_um_each_face", 0) / 1000
    edge = 4 * b["maximum_edge_break"] ** 2
    return {
        "bulk": (b["width_range"][0] - 2 * coat) * (b["thickness_range"][0] - 2 * coat) - edge,
        "hole_neck": (b["landing_range"][0] - b["hole_range"][1] - 4 * coat)
        * (b["thickness_range"][0] - 2 * coat)
        - edge,
    }


def main():
    import cadquery as cq
    import numpy as np

    d = load()
    mini = copy.deepcopy(d)
    b = mini["bar"]
    b["width"] = b["width_range"][0]
    b["thickness"] = b["thickness_range"][0]
    b["landing_diameter"] = b["landing_range"][0]
    b["hole_diameter"] = b["hole_range"][1]
    # Finished sizes include tin. Give its conductivity no copper credit.
    coat = d.get("surface", {}).get("maximum_project_um_each_face", 0) / 1000
    for key in ("width", "thickness", "landing_diameter"):
        b[key] -= 2 * coat
    b["hole_diameter"] += 2 * coat
    results = {}
    for name, row in d["paths"].items():
        obj = shape(mini, name)
        p = [np.array(q, dtype=float) for q in row["points"]]
        witness = []
        samples = []
        for i, (a, z) in enumerate(zip(p, p[1:])):
            samples.append(("segment" + str(i), (a + z) / 2, (z - a) / np.linalg.norm(z - a), False))
        for i, q in enumerate(p[1:-1], 1):
            before = (q - p[i - 1]) / np.linalg.norm(q - p[i - 1])
            after = (p[i + 1] - q) / np.linalg.norm(p[i + 1] - q)
            normal = before + after
            normal /= np.linalg.norm(normal)
            samples.append(("corner" + str(i), q, normal, False))
        for i, q in [(0, p[0]), (-1, p[-1])]:
            normal = p[1] - q if i == 0 else q - p[-2]
            normal /= np.linalg.norm(normal)
            samples.append(("hole" + str(i), q, normal, True))
        for label, q, n, hole in samples:
            u = np.cross(n, [0.0, 0.0, 1.0]) if abs(n[2]) < 0.99 else np.array([1.0, 0.0, 0.0])
            u /= np.linalg.norm(u)
            plane = cq.Plane(origin=tuple(q), xDir=tuple(u), normal=tuple(n))
            # Finite local window prevents distant return branches inflating a section.
            slab = (
                cq.Workplane(plane)
                .box(12 if hole else 8.3, 8.3 if abs(n[2]) > 0.99 else 4.5, 0.001, centered=True)
                .val()
            )
            area = obj.intersect(slab).Volume() / 0.001
            # Edge-break term is a conservative square-corner removal allocation.
            corrected = area - 4 * b["maximum_edge_break"] ** 2
            witness.append(
                dict(
                    id=label,
                    origin=q.tolist(),
                    normal=n.tolist(),
                    slab_thickness_mm=0.001,
                    raw_area_mm2=area,
                    edge_corrected_area_mm2=corrected,
                    meets_project_minimum=corrected >= b["minimum_net_normal_area"],
                )
            )
        length = sum(float(np.linalg.norm(z - a)) for a, z in zip(p, p[1:]))
        amin = min(q["edge_corrected_area_mm2"] for q in witness)
        rho = 1 / (d["bar"]["conductivity_receiving_allocation_ms_per_m"] * 1e6)
        factor = 1 + d["bar"]["temperature_coefficient_assumed_per_k"] * (
            d["bar"]["dc_screen_temperature_c"] - 20
        )
        results[name] = dict(
            witnesses=witness,
            minimum_witness_area_mm2=amin,
            all_witnesses_meet_project_minimum=all(q["meets_project_minimum"] for q in witness),
            centreline_length_mm=length,
            conditional_uniform_section_dc_mohm=rho * factor * (length / 1000) / (amin * 1e-6) * 1000,
            copper_conductivity_certified=False,
            joint_resistance_included=False,
            bend_crowding_and_3d_current_distribution_validated=False,
        )
    report = dict(
        source_sha256={
            str(q.relative_to(ROOT)): sha(q)
            for q in [ROOT / "design.json", ROOT / "generate.py", ROOT / "analysis.py"]
        },
        analytical_minimum_area_mm2=area_screens(d),
        links=results,
        witness_scope="Finite local 0.001mm BREP slabs at every straight midpoint, orthogonal corner bisector and terminal-hole plane; not a global minimum theorem or an electrical crowding solve",
        physical_qualified=False,
        complete_link_resistance_verified=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {n: {k: v for k, v in r.items() if k != "witnesses"} for n, r in results.items()}, indent=2
        )
    )


if __name__ == "__main__":
    main()
