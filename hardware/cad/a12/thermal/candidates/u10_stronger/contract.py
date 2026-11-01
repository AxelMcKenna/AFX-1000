"""Portable checks of the actual native source and fabrication-relevant via geometry."""

import math

from hardware.electronics.common.sexpr import children, first
from hardware.electronics.output_stage.check_placement import transform

from .synthesize import EP


def ep_vias(tree):
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "U10"] for p in children(f, "property"))
    )
    assert first(fp, "layer")[1] == "F.Cu", "Real source must be on front"
    assert next(p[2] for p in children(fp, "property") if p[1] == "Value") == "LT3090IDD#PBF"
    ep = next(p for p in children(fp, "pad") if p[1] == "11")
    assert str(first(ep, "net")[1]).lstrip("/") == "RAW_N22", "EP/IN cannot be AGND"
    xy = transform(fp, first(ep, "at")[1:3])
    actual = []
    for via in children(tree, "via"):
        centre = list(map(float, first(via, "at")[1:3]))
        if math.dist(centre, xy) > 2:
            continue
        if str(first(via, "net")[1]).lstrip("/") != "RAW_N22":
            continue
        if abs(centre[0] - xy[0]) > 1.55 / 2 or abs(centre[1] - xy[1]) > 2.28 / 2:
            continue
        size = float(first(via, "size")[1])
        drill = float(first(via, "drill")[1])
        assert first(via, "layers")[1:] == ["F.Cu", "B.Cu"]
        assert math.isclose(size, 0.6) and math.isclose(drill, 0.25)
        assert abs(centre[0] - xy[0]) + size / 2 <= 1.55 / 2 + 1e-9
        assert abs(centre[1] - xy[1]) + size / 2 <= 2.28 / 2 + 1e-9
        actual.append(centre)
    assert sorted(actual) == sorted([list(p) for p in EP]), "Missing/misnetted/moved actual8 EP barrels"
    for i, a in enumerate(actual):
        for b in actual[i + 1 :]:
            assert math.dist(a, b) - 0.25 >= 0.25 - 1e-9, "Finished-hole edge gap below .25mm"
    return dict(
        actual_ep_via_count=len(actual),
        minimum_finished_bore_edge_gap_mm=min(
            math.dist(a, b) - 0.25 for i, a in enumerate(actual) for b in actual[i + 1 :]
        ),
        required_minimum_wall_um=50,
        predrill_at_required_min_wall_mm=0.35,
        minimum_nominal_predrill_web_mm=0.15,
        nominal_preplate_annulus_mm=0.125,
        factory_plating_maximum_um=None,
        drill_registration_bound_mm=None,
        process_approved=False,
    )
