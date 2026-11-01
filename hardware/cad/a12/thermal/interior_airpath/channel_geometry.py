"""Actual-source opening/Trill projection diagnostic; not a flow solver."""

import json
import math

from .polygon_contract import area, circle, clip
from .stage import MODEL, OUT, ROOT, sha, write


def rounded(x, y, w, h, r):
    result = []
    for cx, cy, start in [
        (x + r, y + r, 180),
        (x + w - r, y + r, 270),
        (x + w - r, y + h - r, 0),
        (x + r, y + h - r, 90),
    ]:
        result += [
            [
                cx + r * math.cos(math.radians(start + 90 * i / 24)),
                cy + r * math.sin(math.radians(start + 90 * i / 24)),
            ]
            for i in range(25)
        ]
    return result


def clip_rect(poly, box):
    for axis, limit, greater in [
        (0, box[0], True),
        (1, box[1], True),
        (0, box[2], False),
        (1, box[3], False),
    ]:
        poly = clip(poly, axis, limit, greater)
    return poly


def build():
    target = OUT / "channel-geometry.json"
    if (ROOT / "handoff.json").exists() or target.exists():
        raise RuntimeError("Channel diagnostic is immutable")
    tc = MODEL / "context/hardware/cad/a12/trill_front_bay/generated/analysis.json"
    tc_scad = tc.with_name("checks.scad")
    origin = json.loads(tc.read_text())["origin_mm"]
    assert origin == [82, 158, 20]
    assert "cube([53.848,21.844,1.6])" in tc_scad.read_text()
    board = [origin[0], origin[1], origin[0] + 53.848, origin[1] + 21.844]
    left = rounded(38, 164, 72, 19, 1)
    right = rounded(231.5, 154, 45, 29, 1)
    island = clip(circle(6, 256, 93.0871, 168.9352), 1, 164, True)
    overlap = area(clip_rect(left, board)) + area(clip_rect(right, board)) - area(clip_rect(island, board))
    total = area(left) + area(right) - area(island)
    report = dict(
        floor_port_net_faceted_mm2=total,
        Trill_board_bbox_XY=board,
        Trill_board_bottom_z=20,
        floor_top_z=2.8,
        nominal_under_Trill_board_gap_mm=17.2,
        nominal_floor_opening_projection_covered_by_Trill_mm2=overlap,
        nominal_vertical_projection_not_covered_by_Trill_mm2=total - overlap,
        interpretation="About335mm2oftheflooropeningliesbelowtheTrillboard:flowmustturnaroundit. Thisprojectionisnotagoverningchannelareaorflowcapacitybound; othercomponents/controls/turns/meshesmayaddloss.",
        target_interior_m3h=8.8,
        target_base_m3h=1.2,
        ideal_mean_floor_opening_speed_mps=(8.8 / 3600) / (total * 1e-6),
        geometric_meter_total_mm2=125,
        base_target_meter_mean_speed_mps=(1.2 / 3600) / (125e-6),
        mean_velocities_are_targets_not_measured_flows=True,
        source_sha256={
            "channel_geometry.py": sha(ROOT / "channel_geometry.py"),
            str(tc.relative_to(ROOT)): sha(tc),
            str(tc_scad.relative_to(ROOT)): sha(tc_scad),
            "geometry.scad": sha(ROOT / "geometry.scad"),
            "generated/current-native/verification.json": sha(OUT / "current-native/verification.json"),
        },
        actual_loss_split_or_installed_heat_transfer_verified=False,
        physical_qualified=False,
        thermal_qualified=False,
    )
    write(target, report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "floor_port_net_faceted_mm2",
                    "nominal_floor_opening_projection_covered_by_Trill_mm2",
                    "nominal_vertical_projection_not_covered_by_Trill_mm2",
                ]
            }
        )
    )


if __name__ == "__main__":
    build()
