"""H20 separate enlarged-geometry thermal scenarios; no installed cooling bound."""

import copy
import hashlib
import json
from pathlib import Path

from .base_geometry import pin_centres
from .fin_surface import extract
from .lid import lid_shell
from .plate import plate_scenario

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "sources"
WU = SRC / "hardware/cad/a12/thermal/whole_unit"
FF = SRC / "hardware/cad/a12/thermal/fanless_top_fins"


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def masks(grid, width, depth, fasteners):
    import numpy as np

    cfg = {}
    path = (
        SRC
        / "hardware/cad/a12/thermal/fanless_feasibility/sources/context/hardware/cad/a11/generated/layout.scad"
    )
    for line in path.read_text().splitlines():
        if " = " in line:
            key, value = line.split(" = ", 1)
            cfg[key] = json.loads(value.rstrip(";"))
    nx, ny = grid
    x, y = np.meshgrid((np.arange(nx) + 0.5) * width / nx, (np.arange(ny) + 0.5) * depth / ny)
    panel = (x >= 3.1) & (x <= width - 3.1) & (y >= 3.1) & (y <= depth - 3.1)

    def region(c):
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
    for cx, cy in fasteners:
        panel &= (x - cx) ** 2 + (y - cy) ** 2 > 1.7**2
    exposed = panel.copy()
    for c in cfg["caps"]:
        exposed &= ~region(c)
    return panel, exposed


def main():
    import numpy as np

    cfg = read(ROOT / "dimensions.json")
    saved = read(WU / "generated/analysis.json")
    heat = saved["total_internal_heat_screen_w"]
    d = read(WU / "sources/hardware/cad/a12/thermal/design.json")
    assert heat == cfg["retained_heat_target_w"]
    original_pins = pin_centres(d)
    controls = []
    for mode in ["unplaced_uniform", "unplaced_hotcluster"]:
        actual = plate_scenario(d, saved["source_placements"][mode], 3, 0.8)
        old = next(
            r["result"]
            for r in saved["cases"]
            if r["placement"] == mode
            and r["result"]["h_assumed_w_per_m2k"] == 3
            and r["result"]["emissivity_assumed"] == 0.8
        )
        delta = actual["plate_max_c"] - old["plate_max_c"]
        assert abs(delta) < 1e-8
        controls.append(dict(mode=mode, peak_c=actual["plate_max_c"], delta_to_sealed_WU01_c=delta))
    newd = copy.deepcopy(d)
    newd["housing"] = cfg["candidate_outer_shell"]
    newd["shell_fasteners"] = cfg["candidate_shell_fasteners_xy"]
    newd["feet"]["centres"] = cfg["new_feet_candidate_xy"]
    rows = []
    for finmode in ["retained_original_pins", "extended_pin_proposal"]:
        variant = copy.deepcopy(newd)
        if finmode == "retained_original_pins":
            variant["pin_centres_override"] = original_pins
        for mode in ["unplaced_uniform", "unplaced_hotcluster"]:
            # Keep ALL heat projections at their captured positions, including
            # unplaced-uniform alternative over the old footprint. New front
            # area does not automatically gain a moved heat source or heat path.
            sources = copy.deepcopy(saved["source_placements"][mode])
            for h in [3] if finmode == "retained_original_pins" else [2, 3]:
                for eps in [0.8] if finmode == "retained_original_pins" else [0.8, 0.05]:
                    result = plate_scenario(variant, sources, h, eps, grid=(67, 38))
                    rows.append(
                        dict(
                            fin_mode=finmode,
                            placement=mode,
                            pin_count=len(pin_centres(variant)),
                            result=result,
                        )
                    )
                    print("PLATE", finmode, mode, h, eps, result["plate_max_c"], flush=True)
    refined = []
    for mode in ["unplaced_uniform", "unplaced_hotcluster"]:
        coarse = next(
            r
            for r in rows
            if r["fin_mode"] == "extended_pin_proposal"
            and r["placement"] == mode
            and r["result"]["h_assumed_w_per_m2k"] == 3
            and r["result"]["emissivity_assumed"] == 0.8
        )
        fine = plate_scenario(newd, saved["source_placements"][mode], 3, 0.8, grid=(134, 76))
        refined.append(
            dict(mode=mode, fine=fine, peak_delta_c=fine["plate_max_c"] - coarse["result"]["plate_max_c"])
        )
        print("FINE", mode, fine["plate_max_c"], flush=True)
    # Prescribed-base side/lid alternatives are separate from the above plate
    # boundary. Do not add their heat rejection to a nonisothermal plate result.
    shell = []
    finpath = FF / "generated/fins.stl"
    old_panel, old_exposed = masks((134, 64), 334, 157, d["shell_fasteners"])
    old_fa, old_roots, _ = extract((134, 64), finpath, 334, 157)
    old_exposed = np.maximum(0, old_exposed.astype(float) - old_roots)
    old_lid, _ = lid_shell(65, old_panel, old_exposed, 0.7, 0.8, 140, 0.2, grid=(134, 64), fin_areas=old_fa)
    saved_ff = read(FF / "generated/analysis.json")
    expected = next(
        v
        for v in saved_ff["cases"]
        if v["base_prescribed_c"] == 65
        and v["wall_exposed_fraction_assumed"] == 0.7
        and v["joint_r_assumed_k_per_w"] == 0.2
        and v["extra_fin_face_fraction_assumed"] == 1
    )
    lid_control_delta = old_lid["heat_accepted_from_base_w"] - expected["heat_accepted_from_base_w"]
    assert abs(lid_control_delta) < 1e-8

    for grid in [(67, 38), (134, 76), (267, 150)]:
        panel, exposed = masks(grid, 334, 188.4, cfg["candidate_shell_fasteners_xy"])
        fin_area, roots, area = extract(grid, finpath, 334, 188.4)
        exposed = np.maximum(0, exposed.astype(float) - roots)
        for target in [60, 65] if grid != (267, 150) else [65]:
            settings = (
                [(1, 167, 0, 1), (0.7, 140, 0.2, 1), (0.7, 140, 0.2, 0.5)]
                if grid == (67, 38)
                else (
                    [(0.7, 140, 0.2, 1), (0.7, 140, 0.2, 0.5)] if grid == (134, 76) else [(0.7, 140, 0.2, 1)]
                )
            )
            for wall, k, joint, face in settings:
                result, field = lid_shell(
                    target,
                    panel,
                    exposed,
                    wall,
                    0.8,
                    k,
                    joint,
                    grid=grid,
                    fin_areas=fin_area,
                    fin_face_fraction=face,
                    width_mm=334,
                    depth_mm=188.4,
                    wall_height_mm=43.6,
                )
                shell.append(
                    dict(
                        result=result,
                        actual_captured_fin_projection=area,
                        old_FF02_fins_XY_unchanged_no_front_fins=True,
                        fin_z_translation_required_mm=7.6,
                        new_native_fin_geometry_or_control_clearance_pass=False,
                    )
                )
                if grid == (134, 76) and target == 65:
                    np.save(ROOT / "generated/lid-field.npy", field)
                print(
                    "SHELL", grid, target, wall, joint, face, result["heat_accepted_from_base_w"], flush=True
                )
    isothermal = []
    for bottom_h in [2, 3]:
        base_ref = next(
            r["result"]
            for r in rows
            if r["fin_mode"] == "extended_pin_proposal"
            and r["placement"] == "unplaced_uniform"
            and r["result"]["h_assumed_w_per_m2k"] == bottom_h
            and r["result"]["emissivity_assumed"] == 0.8
        )
        for row in shell:
            t = row["result"]["base_prescribed_c"]
            sigma = 5.670374419e-8
            bottom = bottom_h * base_ref["outside_convection_effective_area_m2"] * (
                t - 40
            ) + 0.8 * 0.5 * sigma * base_ref["lower_projected_radiation_area_m2"] * (
                (t + 273.15) ** 4 - 313.15**4
            )
            capacity = bottom + row["result"]["heat_accepted_from_base_w"]
            isothermal.append(
                dict(
                    grid=row["result"]["grid"],
                    base_prescribed_c=t,
                    wall_exposed_fraction=row["result"]["wall_exposed_fraction_assumed"],
                    wall_joint_r=row["result"]["joint_r_assumed_k_per_w"],
                    fin_face_fraction=row["result"]["extra_fin_face_fraction_assumed"],
                    bottom_uniform_h_assumed=bottom_h,
                    bottom_capacity_w=bottom,
                    combined_conditional_capacity_w=capacity,
                    margin_to_retained_heat_w=capacity - heat,
                    capacity_ratio_to_retained=capacity / heat,
                    not_a_distributed_coupled_plate_or_installed_bound=True,
                )
            )
    files = (
        [p for p in (ROOT / "sources").rglob("*") if p.is_file()]
        + list(ROOT.glob("*.py"))
        + [ROOT / "dimensions.json", ROOT / "capture.json"]
    )
    report = dict(
        scope=__doc__,
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in files},
        heat_target_w=heat,
        extra_20percent_heat_target_selected=False,
        baseline_replay_controls=controls,
        FF02_baseline_lid_replay_delta_w=lid_control_delta,
        isothermal_same_base_conditional_capacity=isothermal,
        shell_growth_only_with_retained_thermal_assembly="Same boundary and source placement as sealed WU01; no cooling gain credited",
        enlarged_base_cases=rows,
        enlarged_base_refinement=refined,
        new_metal_shell_prescribed_base_cases=shell,
        pin_centres_extended_proposal_mm=pin_centres(newd),
        complete_new_geometry_or_conjugate_cooling_solution=False,
        plate_boundary="334x188.4 rectangular 6.2mm metal plate, all edge losses adiabatic, bottom-only h/radiation, captured contacts/source positions, retained versus extended actual listed pin coordinates, new proposed foot exclusions",
        shell_boundary="Separate conductive2.8mm sides/2mm lid43.6mm height. Captured original aperture/capXY masks plus9fasteners. Actual old FF02finSTL surface projected at unchangedXY; raisedZ requires new MCAD/controls verification. Prescribed isothermal base, no nonuniform-base coupling.",
        no_extra_fin_radiation_credit=True,
        no_source_to_plate_contact_drop_solved=True,
        rounded_corners_ports_seams_and_new_support_holes_not_fully_discretized=True,
        shell_capacities_not_addable_to_plate_temperature_results=True,
        actual_thermal_capacity_upper_or_lower_w=None,
        installed_h_lower_bound=None,
        material_contact_or_model_uncertainty_bound=None,
        new_geometry_native_fit_passed=False,
        thermal_qualified=False,
        physical_tests_performed=0,
        fabrication_released=False,
        canonical_or_sealed_files_modified=False,
    )
    (ROOT / "generated/thermal.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
