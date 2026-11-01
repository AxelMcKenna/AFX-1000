"""Outside-component witness for clipped closed triangle sets, including contact edges.

The mathematical zero-radius witness starts below all captured solids. It is
not a proposed wire path or permission to leave the routing window. Together
with a positive unsigned-distance cover, it avoids relying only on the return
mesh's pseudonormal sign at its nonmanifold assembly-contact edges.
"""

import json
from pathlib import Path

import numpy as np
from search import FACE, ROOT, STARTS, Surface, sha

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform


def run():
    tree = read_sexpr((ROOT / "inputs/fed-source.kicad_pcb").read_text())
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "J4"] for p in children(f, "property"))
    )
    assert first(fp, "layer")[1] == "F.Cu"
    assert abs(float(first(first(tree, "general"), "thickness")[1]) + 5 - FACE) < 1e-9
    for pad in children(fp, "pad"):
        pin = str(pad[1])
        xy = transform(fp, first(pad, "at")[1:3])
        actual = np.array([xy[0] - 100 + 8, xy[1] - 100 + 108.5, FACE])
        assert np.allclose(actual, STARTS[pin], atol=1e-9)
    surfaces = {name: Surface(ROOT / "inputs" / f"{name}.stl") for name in ["case", "return", "positive"]}
    rows = []
    for pin, start in STARTS.items():
        count = 1000
        pts = np.tile(start, (count + 1, 1))
        pts[:, 2] = np.linspace(0, FACE, count + 1)
        cover = FACE / count / 2
        for name, surf in surfaces.items():
            assert surf.mesh.GetBounds()[4] >= 3 - 1e-6
            v = surf.values(pts)
            gap = float(np.abs(v).min() - cover)
            assert gap > 0, (pin, name, gap)
            rows.append(
                dict(
                    pin=pin,
                    solid=name,
                    zero_radius_witness_from_mm=pts[0].tolist(),
                    to_mm=start.tolist(),
                    unsigned_surface_distance_lower_estimate_mm=gap,
                    continuous_sample_cover_mm=cover,
                    source_signed_distance_mm=float(v[-1]),
                    source_connected_to_below_bound_outside_without_crossing_surface=True,
                )
            )
    report = dict(
        scope=__doc__,
        source_code_sha256={p.name: sha(p) for p in [Path(__file__), ROOT / "search.py"]},
        input_capture_sha256=sha(ROOT / "capture.json"),
        source_port_centres_derived_from_actual_fed_J4=True,
        witnesses=rows,
        does_not_exempt_actual_wire_from_clipped_window_rule=True,
        selected_wire_must_have_positive_surface_clearance_cover_everywhere=True,
        native_case_hardware_joint_and_full_path_still_required=True,
        physical_fit_verified=False,
    )
    (ROOT / "outside-witness.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "Outsidewitnesses",
        [(r["pin"], r["solid"], r["unsigned_surface_distance_lower_estimate_mm"]) for r in rows],
    )


if __name__ == "__main__":
    run()
