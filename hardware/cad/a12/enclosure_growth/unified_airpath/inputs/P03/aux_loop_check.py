"""Actual copper check for local U102 capacitor loops, never a stability pass."""

import math
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr
from .aux_loops import LOOPS
from .route import PowerRouter, coded

GROUND = [
    (
        "C106",
        "2",
        "4",
        "AGND",
        0.5,
        [(27.575, 23.6), (25.65, 23.6), (25.65, 21.8), (24.1, 21.8), (24.1, 20.975)],
    ),
    (
        "C110",
        "2",
        "4",
        "AGND",
        0.25,
        [(29.3, 24.175), (29.3, 24.2), (25.55, 24.2), (25.55, 21.9), (24.1, 21.9), (24.1, 20.975)],
    ),
]


def covered(a, b, lines, width):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    intervals = []
    for g in lines:
        if g["width"] < width - 1e-8:
            continue
        p, q = g["start"], g["end"]
        if max(abs(dx * (v[1] - a[1]) - dy * (v[0] - a[0])) / length for v in (p, q)) > 1e-5:
            continue
        u, v = sorted(((p[0] - a[0]) * dx + (p[1] - a[1]) * dy, (q[0] - a[0]) * dx + (q[1] - a[1]) * dy))
        lo, hi = max(0, u / length**2), min(1, v / length**2)
        if hi >= lo:
            intervals.append((lo, hi))
    end = 0
    for lo, hi in sorted(intervals):
        if lo > end + 1e-5:
            return False
        end = max(end, hi)
    return end >= 1 - 1e-5


def validate(root):
    root = Path(root)
    tree = coded(read_sexpr((root / "power_p03.kicad_pcb").read_text()))
    r = PowerRouter(tree)
    # Input has an independent local capacitor on VIN_IC, never a capacitor on
    # the guard's downstream VIN_PROTECTED node substituted by name similarity.
    for ref in ("U102", "C106", "C113", "C110"):
        fp = next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", ref] for p in children(f, "property"))
        )
        assert first(fp, "layer")[1] == "F.Cu", (ref, "Required regulator cell is not front-side")
    for ref, pin, net in [
        ("C106", "1", "V2V5_AUX"),
        ("C113", "1", "VIN_IC"),
        ("C110", "1", "AUX_START_DELAY"),
    ]:
        p = next(p for p in r.by_ref[ref] if p["pin"] == pin)
        g = next(p for p in r.by_ref[ref] if p["pin"] == "2")
        assert p["net"] == net and g["net"] == "AGND" and p["layers"] == g["layers"] == (0,), ref
    rows = []
    for ref, pin, upin, net, width, points in list(LOOPS) + GROUND:
        lines = [g for g in r.geometry if g["kind"] == "line" and g["net"] == net and 0 in g["layers"]]
        assert all(covered(a, b, lines, width) for a, b in zip(points, points[1:])), (
            ref,
            pin,
            "Required directF local path was removed or narrowed",
        )
        rows.append(
            dict(
                cap=ref,
                pin=pin,
                U102_pin=upin,
                net=net,
                layer="F.Cu",
                minimum_authored_width_mm=width,
                centreline_length_mm=sum(math.dist(a, b) for a, b in zip(points, points[1:])),
            )
        )
    return dict(
        actual_direct_front_paths=rows,
        buried_via_needed_in_local_loop=False,
        manufacturer_minimum_effective_input_f=0.1e-6,
        manufacturer_minimum_effective_output_f=2.2e-6,
        actual_bias_temp_aging_effective_capacitance_lower_bound_f=None,
        independent_stability_and_loadstep_qualified=False,
        physical_qualified=False,
    )
