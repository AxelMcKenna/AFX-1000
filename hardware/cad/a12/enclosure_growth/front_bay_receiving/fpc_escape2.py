"""Actual-pin local wire escapes replace an opaque bundle-space sensitivity.

Receiving wire OD/bend/process are unselected. These are ONLY initial exits,
not complete fan/sensor/force harnesses or tested current/bend requirements.
"""

import json
import math
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from .capture import ROOT, sha


def build():
    folder = ROOT / "fpc_escape_variant2"
    if folder.exists():
        raise RuntimeError("New escape candidate required")
    pcb = ROOT / "inputs/FPC84/fan_power_health.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    routes = []
    radius = 10.0
    error = radius * (1 - math.cos(math.pi / 256))
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        value = next(p[2] for p in children(fp, "property") if p[1] == "Value")
        if not value.startswith("JST "):
            continue
        for pad in children(fp, "pad"):
            xy = transform(fp, first(pad, "at")[1:3])
            start = [14 + xy[0], 170.0, 3.5 + xy[1]]
            direction = [math.sqrt(0.96), 0.2] if ref == "J3" else [0.0, 1.0]
            angle = math.pi / 4 if ref in ["J2", "J203"] else math.pi / 2
            n = math.ceil(angle / (math.pi / 128))
            points = []
            for i in range(n + 1):
                a = angle * i / n
                shift = radius * (1 - math.cos(a))
                points.append(
                    [
                        start[0] + direction[0] * shift,
                        start[1] - radius * math.sin(a),
                        start[2] + direction[1] * shift,
                    ]
                )
            routes.append(
                dict(
                    id=ref + "." + pad[1],
                    source_native_pad_xy=list(xy),
                    reference_wire_exit=start,
                    turn_direction_XZ=direction,
                    true_centerline_radius_mm=radius,
                    angle_rad=angle,
                    points=points,
                    chord_cover_bound_mm=error,
                    source_normal_tangent=[0, -1, 0],
                    final_tangent=[
                        direction[0] * math.sin(angle),
                        -math.cos(angle),
                        direction[1] * math.sin(angle),
                    ],
                )
            )
    assert len(routes) == 14
    folder.mkdir()
    (folder / "routes.scad").write_text(
        "fr_escape_routes="
        + json.dumps([r["points"] for r in routes])
        + ";\n"
        + """module fr_escape_sweep(points,r){pf_sweep(points,r);}
module fr_escapes(m=.9){for(points=fr_escape_routes)fr_escape_sweep(points,.955+.000753+ m);}
"""
    )
    d = dict(
        routes=routes,
        wire_OD_receiving_max_mm=1.9,
        geometry_reserve_mm=0.005,
        external_independent_pose_mm=0.65,
        external_clearance_mm=0.25,
        local_relative_wire_pose_mm=0.2,
        minimum_bend_radius_is_PROJECT_receiving_requirement_mm=10.0,
        selected_wire_and_manufacturer_bend_limit=None,
        wire_exit_reference_based_on_native_pad_and10p5mm_assembly_receiver=True,
        reference_exit_alignment_and_crimp_tolerances_accepted=False,
        only_initial_local_escapes_not_full_harness=True,
        after_high45degree_exits_C1_continuation_still_required=True,
        source_sha256={str(Path(__file__)): sha(Path(__file__)), str(pcb): sha(pcb)},
        physical_qualified=False,
        electrical_qualified=False,
        full_harness_qualified=False,
    )
    (folder / "contract.json").write_text(json.dumps(d, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                actual_pin_escapes=len(routes),
                continuous_radius_mm=10,
                maximum_chord_cover_mm=error,
                full_harness=False,
            )
        )
    )


if __name__ == "__main__":
    build()
