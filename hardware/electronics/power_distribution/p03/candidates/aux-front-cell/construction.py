"""Canonical P03 custom construction requirements, never a vendor acceptance."""

import collections
import hashlib
import json

from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import transform
from .spec import REPO, ROOT

COPPER_MINIMUM_MM = {
    "F.Cu": 0.085,
    "In1.Cu": 0.070,
    "In2.Cu": 0.070,
    "In3.Cu": 0.070,
    "In4.Cu": 0.070,
    "B.Cu": 0.085,
}
DIELECTRIC_MM = [0.10, 0.34, 0.27, 0.34, 0.10]
VIA_WALL_MINIMUM_UM = 50
EP_VIA_LAND_MM = 0.70


def validate(tree):
    layers = children(first(first(tree, "setup"), "stackup"), "layer")
    actual = {str(l[1]): float(first(l, "thickness")[1]) for l in layers}
    assert abs(sum(actual.values()) - 1.6) < 1e-6, "Canonical P03 total stack is not1.6mm"
    for name, minimum in COPPER_MINIMUM_MM.items():
        assert actual[name] >= minimum - 1e-9, f"{name}: source does not implement required minimum copper"
    return actual


def direct_ep_inventory(tree):
    names = {str(n[1]): str(n[2]) for n in children(tree, "net") if len(n) > 2}

    def netname(obj):
        n = first(obj, "net")
        return names.get(str(n[1]), str(n[-1])).lstrip("/")

    fp = next(
        fp
        for fp in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "U13"] for p in children(fp, "property"))
    )
    ep = next(p for p in children(fp, "pad") if str(p[1]) == "11")
    assert netname(ep) == "AGND"
    x, y = transform(fp, first(ep, "at")[1:3])
    sx, sy = map(float, first(ep, "size")[1:3])
    if len(first(fp, "at")) > 3 and int(float(first(fp, "at")[3])) % 180:
        sx, sy = sy, sx
    rows = []
    for via in children(tree, "via"):
        vx, vy = map(float, first(via, "at")[1:3])
        if abs(vx - x) <= sx / 2 and abs(vy - y) <= sy / 2 and netname(via) == "AGND":
            rows.append(
                dict(
                    at_mm=[vx - 100, vy - 100],
                    land_mm=float(first(via, "size")[1]),
                    finished_bore_mm=float(first(via, "drill")[1]),
                )
            )
    return dict(
        required_count=12,
        actual_count=len(rows),
        actual_vias=rows,
        implements_required_count_and_geometry=len(rows) == 12
        and all(r["land_mm"] >= 0.70 - 1e-9 and abs(r["finished_bore_mm"] - 0.25) < 1e-9 for r in rows),
    )


def monitor_vip_inventory(tree):
    names = {str(n[1]): str(n[2]) for n in children(tree, "net") if len(n) > 2}

    def netname(obj):
        n = first(obj, "net")
        return names.get(str(n[1]), str(n[-1])).lstrip("/")

    fp = next(
        fp
        for fp in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "U25"] for p in children(fp, "property"))
    )
    pad = next(p for p in children(fp, "pad") if str(p[1]) == "3")
    assert netname(pad) == "P03_MON_P19"
    x, y = transform(fp, first(pad, "at")[1:3])
    rows = []
    for v in children(tree, "via"):
        vx, vy = map(float, first(v, "at")[1:3])
        if abs(vx - x) < 1e-6 and abs(vy - y) < 1e-6:
            land = float(first(v, "size")[1])
            bore = float(first(v, "drill")[1])
            rows.append(
                dict(
                    net=netname(v),
                    at_mm=[vx - 100, vy - 100],
                    land_mm=land,
                    finished_bore_mm=bore,
                    native_annulus_mm=(land - bore) / 2,
                    preplate_ring_at_minimum_wall_mm=(land - bore - 0.100) / 2,
                )
            )
    return dict(
        ref="U25",
        pin="3",
        required_land_mm=0.55,
        required_finished_bore_mm=0.20,
        nominal_adjacent_pad_copper_clearance_mm=0.160,
        actual_vias=rows,
        implements_required_geometry=len(rows) == 1
        and rows[0]["net"] == "P03_MON_P19"
        and abs(rows[0]["land_mm"] - 0.55) < 1e-9
        and abs(rows[0]["finished_bore_mm"] - 0.20) < 1e-9,
        filled_resin_copper_capped_and_planarized_required=True,
        drill_etch_and_registration_tolerances_approved=False,
    )


def write_contract():
    pcb = ROOT / "power_p03.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    actual = validate(tree)
    vias = collections.Counter(
        (float(first(v, "size")[1]), float(first(v, "drill")[1])) for v in children(tree, "via")
    )
    rows = [
        dict(
            land_nominal_mm=land,
            finished_bore_nominal_mm=drill,
            count=count,
            preplate_drill_example_at_min_wall_mm=drill + 0.1,
            preplate_radial_ring_example_mm=(land - drill - 0.1) / 2,
        )
        for (land, drill), count in sorted(vias.items())
    ]
    report = dict(
        revision="P03-C50-canonical-unreleased",
        pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
        board_nominal_thickness_mm=1.6,
        board_thickness_approved_range_mm=None,
        via_wall_minimum_required_um=VIA_WALL_MINIMUM_UM,
        via_wall_maximum_approved_um=None,
        via_wall_requirement_applies_to_all_plated_through_holes=True,
        outer_finished_copper_minimum_required_um=85,
        outer_finished_copper_maximum_approved_um=None,
        inner_finished_copper_minimum_required_um=70,
        inner_finished_copper_maximum_approved_um=None,
        actual_native_stack_mm=actual,
        dielectric_nominal_mm=DIELECTRIC_MM,
        native_stack_is_accepted_fabricator_template=False,
        direct_ep_land_nominal_mm=EP_VIA_LAND_MM,
        direct_ep_pitch_mm=0.5,
        direct_ep_finished_bore_nominal_mm=0.25,
        direct_ep_preplate_drill_example_mm=0.35,
        direct_ep_preplate_radial_ring_example_mm=0.175,
        direct_ep_preplate_drill_web_example_mm=0.15,
        actual_direct_ep_array=direct_ep_inventory(tree),
        actual_monitor_via_in_pad=monitor_vip_inventory(tree),
        minimum_finished_through_hole_requirement_mm=0.20,
        actual_via_land_bore_inventory=rows,
        preplate_drill_approved_range_mm=None,
        finished_bore_approved_range_mm=None,
        drill_position_registration_approved_mm=None,
        land_minimum_after_etch_mm=None,
        minimum_preplate_drill_web_approved_mm=None,
        routed_clearance_requirement_mm=0.16,
        manufacturer_TI_RPY_same_package_pad_exception_mm=0.15,
        via_fill="Resin filled and copper capped, planarized; not solid copper filled",
        fill_cap_flatness_approved_mm=None,
        fabricator_dfm_approved=False,
        actual_microsection_verified=False,
        prior_construction_snapshot="construction50/ is immutable initial C50 comparison; source25 archives are undergenerated/history",
        physical_tests_performed=0,
        thermal_qualified=False,
        fabrication_released=False,
        build_ready=False,
        requirement_source_sha256={
            str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT / "construction.py", ROOT / "board.py", ROOT / "thermal.py", ROOT / "spec.py"]
        },
    )
    (ROOT / "construction.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    write_contract()
