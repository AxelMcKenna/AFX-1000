"""Bounded source-loaded CH20 scenarios; no spatial/optimization sweep."""

import copy
import hashlib
import json
import platform

import numpy as np
import scipy
import shapely

from .coupled import solve
from .geometry import ROOT, build
from .reference_plate import plate_scenario


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def main():
    c = read(ROOT / "geometry-contract.json")
    dims = read(ROOT / "sources/dimensions.json")
    d = read(ROOT / "sources/base-design.json")
    d["housing"] = dims["candidate_outer_shell"]
    d["shell_fasteners"] = dims["candidate_shell_fasteners_xy"]
    d["feet"]["centres"] = dims["new_feet_candidate_xy"]
    wu = read(ROOT / "sources/wu-analysis.json")
    h20 = read(ROOT / "sources/h20-thermal.json")
    heat = c["retained_heat_w"]
    assert heat == wu["total_internal_heat_screen_w"]
    placements = wu["source_placements"]
    files = (
        [p for p in (ROOT / "sources").iterdir() if p.is_file()]
        + list(ROOT.glob("*.py"))
        + [ROOT / "geometry-contract.json", ROOT / "capture.json"]
    )
    captured = {str(p.relative_to(ROOT)): sha(p) for p in files}
    g = build(c, tuple(c["coarse_grid"]))
    (ROOT / "generated/geometry.json").write_text(json.dumps(g["metadata"], indent=2) + "\n")
    controls = []
    for k in [167, 140]:
        cp = copy.deepcopy(c)
        cp["k_metal_w_per_mk"] = k
        dd = copy.deepcopy(d)
        dd["scenario_aluminum_k"] = k
        for mode in ["unplaced_uniform", "unplaced_hotcluster"]:
            result, _ = solve(cp, dd, placements[mode], g, 3, 1, decoupled=True)
            ref = plate_scenario(dd, placements[mode], 3, 0.8, grid=tuple(c["coarse_grid"]))
            delta = result["base_peak_c"] - ref["plate_max_c"]
            assert abs(delta) < 1e-7
            saved = None
            if k == 167:
                saved = next(
                    r["result"]["plate_max_c"]
                    for r in h20["enlarged_base_cases"]
                    if r["fin_mode"] == "extended_pin_proposal"
                    and r["placement"] == mode
                    and r["result"]["h_assumed_w_per_m2k"] == 3
                    and r["result"]["emissivity_assumed"] == 0.8
                )
                assert abs(result["base_peak_c"] - saved) < 1e-7
            controls.append(
                dict(
                    k=k,
                    placement=mode,
                    decoupled=result,
                    reference_base_only_peak_c=ref["plate_max_c"],
                    saved_H20_coarse_peak_c=saved,
                    delta_c=delta,
                )
            )
            print("CONTROL", k, mode, result["base_peak_c"], delta, flush=True)
    cases = []
    for mode in ["unplaced_uniform", "unplaced_hotcluster"]:
        for h in [3, 2]:
            for face in [1.0, 0.5]:
                for scale in [1.0, 1.2]:
                    result, fields = solve(c, d, placements[mode], g, h, face, heat_scale=scale)
                    cases.append(dict(placement=mode, result=result))
                    print(
                        "LOADED",
                        mode,
                        h,
                        face,
                        scale,
                        "base",
                        result["base_peak_c"],
                        "lid",
                        result["lid_peak_c"],
                        "residual",
                        result["energy_residual_w"],
                        flush=True,
                    )
                    if mode == "unplaced_hotcluster" and h == 3 and face == 1 and scale == 1:
                        np.save(ROOT / "generated/reference-base.npy", fields["base"])
                        np.save(ROOT / "generated/reference-lid.npy", fields["lid"])
                        np.save(ROOT / "generated/reference-wall.npy", fields["wall"])
                        (ROOT / "generated/first-case.json").write_text(json.dumps(result, indent=2) + "\n")
    extra, fields = solve(
        c, d, placements["unplaced_hotcluster"], g, 3, 1, heat_scale=1.2, contact_r=(0.2, 0.2)
    )
    print("DOUBLE-JOINT-SENSITIVITY", extra["base_peak_c"], flush=True)
    env = dict(
        python=platform.python_version(),
        numpy=np.__version__,
        scipy=scipy.__version__,
        shapely=shapely.__version__,
        geos=shapely.geos_version_string,
        isolated_geometry_package_location="/private/tmp/afx-coupled-geometry",
        no_existing_scientific_environment_mutation=True,
    )
    report = dict(
        scope=__doc__,
        source_sha256=captured,
        geometry_contract_sha256=sha(ROOT / "geometry-contract.json"),
        geometry=g["metadata"],
        runtime=env,
        retained_heat_w=heat,
        stress_heat_w=heat * 1.2,
        stress_is_planning_diagnostic_not_measured_upper=True,
        ambient_c=40,
        decoupled_controls=controls,
        loaded_cases=cases,
        double_joint_single_sensitivity=dict(placement="unplaced_hotcluster", result=extra),
        source_loaded_coupling_solved=True,
        prescribed_uniform_base_temperature=False,
        contact_normalization_required_under_any_refinement=True,
        no_link_across_separate_same_cell_lid_components=True,
        rear_cassette_and_front_vent_cuts_explicit=True,
        heat_path_scope="All retained consumed power is idealized into base projections. Real package/board/TIM/internalair heat paths are not solved. Native structuralblank seat/lid projections define contact geometry only; replacement conducting walls/ledge/lid/base have no accepted matched manufactured construction.",
        source_placement_scope="Captured WU positions unchanged; unplaced heat stays uniformly overoldfootprint oroldhotcluster, not silently moved into new front strip. Later control/integration poses require source-ledger renewal.",
        limitations=[
            "Allh/emissivity/material/ambient/contact values are scenarios, not installedbounds.",
            "Fourwall model is a declaredthinwall rectangle/corner approximation; R7nativecorner conduction/ports/fasteners/pressure/isolation need physicalconstruction.",
            "Actual cassetteopening has NO conductingcassette bridge or internalair coolingcredit. No boss/screwheat path credited.",
            "Lid contact uses actual nativeshellseat/lid overlap excludingbossdisks; finite2mmconductiveledge bridge is proposed, absent fromcurrentplasticblankmaterial.",
            "Oldactualtopfins moveup7.6mm only; no newfrontfins or finradiationcredit. Neighborplume/hot-touch/control/service integration remainsunqualified.",
            "Finite-volume cutcell/TPFA, localcontactspreading, uniformbottomh/groupnaturalconvection approximations need later spatial/modeluncertainty assessment.",
            "Base projections are notjunctiontemperatures; no old U13/U102/U10temperature orpackagepath qualification is inherited.",
        ],
        spatial_refinement_performed=False,
        optimization_performed=False,
        new_native_metal_parts_matched=False,
        actual_load_material_contact_h_ambient_or_model_bounds_established=False,
        physical_tests_performed=0,
        qualified20percent_margin=False,
        thermal_qualified=False,
        fabrication_released=False,
        all_old_seals_modified=False,
    )
    assert all(sha(ROOT / p) == h for p, h in captured.items())
    (ROOT / "generated/analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "generated/environment.json").write_text(json.dumps(env, indent=2) + "\n")


if __name__ == "__main__":
    main()
