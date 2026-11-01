"""FF01 envelope-constrained passive heat rejection, not installed thermal proof."""

import hashlib
import json
from pathlib import Path

from .physics import air, lid_shell, plate_fins, stack_required_openings

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
OUT = ROOT / "generated"
CONTEXT = ROOT / "sources/context"
DESIGN = CONTEXT / "hardware/cad/a12/thermal/whole_unit/sources/hardware/cad/a12/thermal/design.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def layout():
    result = {}
    for line in (CONTEXT / "hardware/cad/a11/generated/layout.scad").read_text().splitlines():
        if " = " in line:
            key, value = line.split(" = ", 1)
            result[key] = json.loads(value.rstrip(";"))
    return result


def masks(grid):
    import numpy as np

    nx, ny = grid
    x, y = np.meshgrid((np.arange(nx) + 0.5) * 334 / nx, (np.arange(ny) + 0.5) * 157 / ny)
    panel = (x >= 3.1) & (x <= 330.9) & (y >= 3.1) & (y <= 153.9)
    cfg = layout()

    def region(c, caps=False):
        _, kind, cx, cy, w, h, a, b = c
        xx, yy = x - cx, y - cy
        if kind == "sector":
            radius = np.sqrt(xx**2 + yy**2)
            angle = np.degrees(np.arctan2(yy, xx)) % 360
            return (radius >= w) & (radius <= h) & (angle >= a) & (angle <= b)
        if kind == "knob":
            return xx**2 + yy**2 <= (w / 2) ** 2
        return (abs(xx) <= w / 2) & (abs(yy) <= h / 2)

    for c in cfg["openings"]:
        panel &= ~region(c)
    for cx, cy in cfg["fasteners"]:
        panel &= (x - cx) ** 2 + (y - cy) ** 2 > 1.7**2
    exposed = panel.copy()
    for c in cfg["caps"]:
        exposed &= ~region(c, True)
    return panel, exposed


def root_height(n, target, eps, view):
    lo, hi = 1, 200
    for _ in range(45):
        mid = (lo + hi) / 2
        r = plate_fins(n, 3, mid, target)
        capacity = r["convection_w"] + eps * view * r["radiation_black_envelope_upper_w"]
        if capacity < 35.43154587633119:
            lo = mid
        else:
            hi = mid
    return dict(
        height_mm=hi,
        added_height_over22p6mm=hi - 22.6,
        overall_with2p6mm_table_clearance_mm=87.6 + max(0, hi + 2.6 - 22.6),
        extrapolation_beyond_paper25mm_height=hi > 25,
        emissivity_assumed=eps,
        radiation_view_assumed=view,
        free_air_correlation_not_installed_bound=True,
    )


def main():
    import numpy as np

    ledger = read(CONTEXT / "hardware/cad/a12/thermal/whole_unit/generated/ledger.json")
    target = ledger["total_internal_heat_screen_w"]
    native = read(OUT / "native-geometry.json")
    for name, item in native["parts"].items():
        if sha(OUT / (name + ".stl")) != item["sha256"]:
            raise ValueError("Stale native geometry")
    rows = []
    for t in [60, 65]:
        for n in [11, 12, 13, 14]:
            for h in [12, 20, 22.6]:
                r = plate_fins(n, 3, h, t)
                rows.append(
                    dict(
                        r,
                        target_base_c=t,
                        table_gap_mm=22.6 - h,
                        no_installed_lower_h_guarantee=True,
                        capacity_black_aperture_plus20percent_h_control_w=1.2 * r["convection_w"]
                        + r["radiation_black_envelope_upper_w"],
                        capacity_epsilon_point8_view_point5_w=r["convection_w"]
                        + 0.4 * r["radiation_black_envelope_upper_w"],
                    )
                )
    shell = []
    for t in [60, 65]:
        for wall_fraction, eps, k, joint in [
            (1, 0.8, 167, 0),
            (0.7, 0.8, 167, 0),
            (0.7, 0.8, 140, 0.2),
            (0.7, 0.5, 140, 0.2),
        ]:
            panel, exposure = masks((134, 64))
            r, field = lid_shell(t, panel, exposure, wall_fraction, eps, k, joint, grid=(134, 64))
            bottom = next(
                v for v in rows if v["count"] == 14 and v["height_mm"] == 20 and v["target_base_c"] == t
            )
            # Native notched area; correlation still lacks table/cross-channel validation.
            actual = plate_fins(12, 3, 20, t, length_mm=310, width_mm=133)
            actual_area = native["parts"]["bottom"]["wetted_minus_four18mm_foot_disks_m2"]
            actual_conv = actual["correlation"]["h"] * actual["fin_efficiency"] * actual_area * (t - 40)
            bottom_w = actual_conv + 0.5 * eps * bottom["radiation_black_envelope_upper_w"]
            r.update(
                bottom_actual_notched_mesh_assumed_capacity_w=bottom_w,
                bottom_actual_convection_w=actual_conv,
                bottom_h_assumed_from_platefin_correlation=actual["correlation"]["h"],
                complete_same_envelope_capacity_screen_w=bottom_w + r["heat_accepted_from_base_w"],
                retained_heat_w=target,
                heat_rejection_margin_screen_w=bottom_w + r["heat_accepted_from_base_w"] - target,
                no_actual_base_spreading_TIM_or_package_margin=True,
            )
            shell.append(r)
            if t == 65 and wall_fraction == 0.7 and k == 167:
                np.save(OUT / "metal-lid-field.npy", field)
    # Refinement control for only the conditional full-wall zero-seam proposal.
    refinement = []
    for grid in [(67, 32), (134, 64), (267, 126)]:
        p, e = masks(grid)
        r, _ = lid_shell(65, p, e, 1, 0.8, 167, 0, grid=grid)
        refinement.append(r)
    a = dict(
        revision="FF01-private-envelope-feasibility",
        heat_target_w=target,
        ambient_c=40,
        required_base_to_ambient_k_per_w={str(t): (t - 40) / target for t in [60, 65]},
        envelope=dict(
            footprint_mm=[334, 157],
            overall_including_controls_mm=87.6,
            shell_top_z=38,
            max_control_top_z=58.8,
            table_z=-28.8,
            base_underside_z=-6.2,
            available_below_base_to_table_mm=22.6,
            existing_pins_mm=[3, 3, 12],
            existing_pitch_mm=7,
            existing_air_gap_mm=4,
            existing_fin_to_table_nominal_mm=10.6,
            candidate_fin_height_mm=20,
            candidate_fin_to_table_mm=2.6,
            loaded_bumper_compression_bound=None,
        ),
        air_properties_at65_40=air(65),
        bottom_arrays=rows,
        metal_shell_proposals=shell,
        lid_refinement=refinement,
        taller_bottom_proposals={
            str(t): [root_height(14, t, 1, 1), root_height(14, t, 0.8, 0.5)] for t in [60, 65]
        },
        native_geometry=native,
        vent_bounds=[
            stack_required_openings(q, 36, dt, cd)
            for q in [target, 17, 5]
            for dt in [15, 20, 25]
            for cd in [1, 0.6]
        ],
        horizontal_channel_inlet_outlet_same_height_has_no_vertical_chimney_head=True,
        radiator_area_cannot_replace_flow_path_or_correlation=True,
        source_range_and_installation_holds=[
            "Existing square pins are not the plate-fin correlation: no calibrated prediction for original858-pin base.",
            "Downward correlation matched3mmplate fins,8.8..14.7mmgap,5..25mmheight,L250/340,W180. OursW157, fullspanL334; near-table obstacle, feet, notches and edges are not validated.",
            "All bottom radiation is bounded by exterior-aperture/convex-envelope area; internal fin area cannot each see room independently.",
            "Metal-shell study requires replacing insulating plastic sides/lid with a separate conductive structure; actual controls mask exposed lid area. Ideal full-perimeter conduction neglects port cuts/seam resistance unless explicitly added.",
            "Prescribed isothermal base at target is optimistic: actual heat-spreading, board-to-base/package interfaces, inlet air recirculation, table warming, altitude, dust, finish and contact bounds remain missing.",
            "Vent equations use an optimistic uniformly-hot column and zero internal drag; Cd.6 is a scenario, not selected-vent proof. Real boards/wiring can block the required path.",
        ],
        existing_height_receipt_sha256=sha(
            CONTEXT / "hardware/cad/a12/harness/generated/height-envelope/verification.json"
        ),
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in list((ROOT / "sources").rglob("*"))
            + [ROOT / "analyze.py", ROOT / "physics.py", OUT / "native-geometry.json"]
            if p.is_file()
        },
        actual_installed_capacity_upper_or_lower_w=None,
        installed_h_lower_bound=None,
        actual_model_uncertainty_bound_c=None,
        physical_tests_performed=0,
        new_cooling_geometry_adopted=False,
        thermal_qualified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(a, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                bottom_best_at65=max(
                    v["capacity_black_aperture_plus20percent_h_control_w"]
                    for v in rows
                    if v["target_base_c"] == 65
                ),
                shell=[
                    {
                        k: r[k]
                        for k in [
                            "base_prescribed_c",
                            "wall_exposed_fraction_assumed",
                            "k_al_typical_or_sensitivity",
                            "joint_r_assumed_k_per_w",
                            "complete_same_envelope_capacity_screen_w",
                            "heat_rejection_margin_screen_w",
                        ]
                    }
                    for r in shell
                ],
                taller=a["taller_bottom_proposals"],
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
