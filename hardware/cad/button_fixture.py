#!/usr/bin/env python3
"""B01 guided button fit kit: geometry, stack calculation and drill template.

The return spring and silicone are specification targets pending physical
selection. These calculations do not establish switch life or actuation force.
"""

import json
import math
from pathlib import Path

from . import generate

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
VALUES = dict(
    panel_thick=2,
    board_drop=8.8,
    mount_pitch=22,
    cap_under=3.2,
    cap_thick=2.4,
    stem_d=5,
    stem_flat=2,
    stem_bottom=-3,
    groove_d=4,
    clip_bottom=-2.4,
    clip_thick=1,
    guide_thick=1.4,
    travel=1.2,
    switch_height=4.3,
    switch_case=3.4,
    switch_pt=0.25,
    puck_d=3,
    puck_pocket_d=2.8,
    puck_height=2,
    puck_insert=0.7,
    spring_od=6,
    spring_id=5.4,
    spring_free=4.5,
    spring_solid_max=1.2,
    spring_rate_target=0.2,
)


def stack():
    v = VALUES
    top = -v["board_drop"] + v["switch_height"]
    rigid = v["stem_bottom"] - v["travel"]
    puck = v["stem_bottom"] + v["puck_insert"] - v["puck_height"]
    gap = puck - top
    spring_rest = v["clip_bottom"] + v["board_drop"] - v["switch_case"]
    spring_pressed = spring_rest - v["travel"]
    assert math.isclose(gap, 0.2, abs_tol=1e-12)
    assert math.isclose(v["cap_under"] - v["panel_thick"], v["travel"], abs_tol=1e-12)
    assert rigid > top + 0.2  # highest unpressed switch from manufacturer height tolerance
    case_tolerance = 0.4  # general drawing tolerance on the unqualified 3.4 dimension
    assert spring_pressed - case_tolerance > v["spring_solid_max"]
    # At maximum switch height, there is nominally zero gap. Manufacturing
    # stack tolerances remain unmeasured and must be established on the coupon.
    assert gap - 0.2 >= -1e-12
    return dict(
        revision="B01",
        datum="panel underside Z=0; housing datum would be Z=34",
        fixture_only=True,
        assembled_or_force_tested=False,
        switch=dict(
            part="B3F-1000",
            height_mm=4.3,
            height_tolerance_mm=0.2,
            pretravel_range_mm=[0.15, 0.45],
            operating_force_range_n=[0.69, 1.27],
            case_height_nominal_mm=3.4,
            case_height_drawing_tolerance_mm=case_tolerance,
        ),
        nominal_actuator_gap_mm=round(gap, 3),
        gap_range_from_switch_height_only_mm=[0, 0.4],
        guided_cap_travel_mm=v["travel"],
        rigid_stem_clearance_to_highest_unpressed_switch_at_stop_mm=round(rigid - (top + 0.2), 3),
        silicone=dict(
            diameter_mm=3,
            thickness_mm=2,
            pocket_depth_mm=0.7,
            material="soft silicone, approximately 30 Shore A trial; supplier and measured stiffness pending",
            nominal_compression_at_stop_mm=round(v["travel"] - gap - v["switch_pt"], 3),
            required_stiffness_min_n_per_mm_for_worst_switch_only=round(
                1.27 / (v["travel"] - (gap + 0.2) - 0.45), 3
            ),
        ),
        return_spring=dict(
            selected_part=None,
            outside_diameter_max_mm=6,
            inside_diameter_min_mm=5.4,
            free_length_target_mm=4.5,
            solid_height_max_mm=v["spring_solid_max"],
            working_height_mm=[round(spring_pressed, 3), round(spring_rest, 3)],
            nominal_preloaded_working_height_mm=[round(spring_pressed + 0.2, 3), round(spring_rest, 3)],
            minimum_height_from_case_tolerance_only_mm=round(spring_pressed - case_tolerance, 3),
            rate_target_n_per_mm=v["spring_rate_target"],
            nominal_return_force_n=[
                round((v["spring_free"] - spring_rest) * v["spring_rate_target"], 3),
                round((v["spring_free"] - spring_pressed - 0.2) * v["spring_rate_target"], 3),
            ],
            seat="switch metal cover; verify cover load, alignment and electrical isolation",
        ),
        limits=[
            "No printed fit, friction, return or switch-life evidence",
            "No measured silicone compression or force/displacement model",
            "PCB and print tolerances, clip fatigue and cap edge loading not verified",
            "Fixture PCB top is 2 mm below current A02 switch placement; not yet installed across panel",
        ],
    )


def drill_svg():
    s = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="52mm" height="36mm" viewBox="-26 -18 52 36">',
        "<title>B01 32 by 16 mm tactile-switch fixture PCB drill template — verify print scale</title>",
        '<rect x="-26" y="-18" width="52" height="36" fill="white"/>',
        '<g fill="none" stroke="#222" stroke-width="0.15">',
        '<rect x="-16" y="-8" width="32" height="16"/>',
    ]
    for x in (-11, 11):
        s.append(f'<circle cx="{x}" cy="0" r="1.2"/>')
    for x in (-3.25, 3.25):
        for y in (-2.25, 2.25):
            s.append(f'<circle cx="{x}" cy="{y}" r="0.5"/>')
    for x in (-1.27, 1.27):
        s.append(f'<circle cx="{x}" cy="6" r="0.5"/>')
    s += [
        '<path d="M-16 11H16M-16 10V12M16 10V12"/>',
        "</g>",
        '<g font-family="Arial,sans-serif" font-size="1.8" text-anchor="middle" fill="#222">',
        '<text x="0" y="-12">B01 · TOP VIEW · B3F-1000</text>',
        '<text x="0" y="14">32 mm — print at 100%</text>',
        '<text x="0" y="-9">Signal: upper pair · GND: lower pair</text>',
        "</g></svg>",
    ]
    return "\n".join(s)


def main():
    controls = {c["id"]: c for c in generate.CONTROLS}
    v = dict(VALUES)
    for name, id in [("pad", "pad_0"), ("nudge", "nudge_down")]:
        c = controls[id]
        v[name + "_width"] = c["w"]
        v[name + "_depth"] = c["h"]
    v["nominal_gap"] = stack()["nominal_actuator_gap_mm"]
    OUT.mkdir(exist_ok=True)
    (OUT / "button-fixture.scad").write_text(
        "// Generated by ../button_fixture.py; do not edit.\n"
        + "\n".join(f"{key} = {json.dumps(value)};" for key, value in v.items())
        + "\n"
    )
    (OUT / "button-stack.json").write_text(json.dumps(stack(), indent=2) + "\n")
    (OUT / "button-pcb-drill.svg").write_text(drill_svg())
    print(
        "B01 stack: 1.2 mm cap travel; 0.2 mm nominal actuator gap; 0.1 mm rigid-stop clearance at tallest switch."
    )


if __name__ == "__main__":
    main()
