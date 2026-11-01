"""Provisional whole-unit heat rejection screen; no temperature upper established."""

import copy
import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha

from .base_geometry import lands, pin_centres
from .ledger import OUT, ROOT, SOURCES, read
from .plate import plate_scenario


def placement(ledger, design, mode):
    sites = lands(design)
    placed = []
    for row in ledger["leaf_heat_rows"]:
        rect = row["known_projected_rect_housing_mm"]
        site = next((s for s in sites if row["source_part_ref"] in s["refs"]), None)
        method = row["heat_placement_basis"]
        if site is not None:
            rect = site["metal_global"]
            method = "Actual existing T01 metal contact projection; perfect source-to-contact transfer is an assumed idealization"
        if rect is None:
            rect = [0, 0, 334, 157] if mode == "unplaced_uniform" else [273, 112, 8, 8]
            method = (
                "Unplaced endpoint distributed uniformly over entire base"
                if mode == "unplaced_uniform"
                else "Unplaced endpoint placed in declared8x8mm P03 hot-cluster projection"
            )
        assert rect[0] >= 0 and rect[1] >= 0 and rect[0] + rect[2] <= 334 and rect[1] + rect[3] <= 157
        placed.append(
            dict(
                id=row["id"],
                watts=row["watts"],
                rect_housing_mm=rect,
                notched_land=site if site and "corner_relief" in site else None,
                placement_basis=method,
            )
        )
    assert math.isclose(sum(r["watts"] for r in placed), ledger["total_internal_heat_screen_w"], abs_tol=1e-9)
    return placed


def source_consistent_points(ledger, analysis, feed):
    # AUXbranch is after Q101 and before U101 in actual native topology.
    core = sum(
        ledger["blocks"][k]
        for k in [
            "digital_input_w",
            "analog_prereg_input_w",
            "bipolar_converter_input_w",
            "other_VIN_control_reserve_w",
        ]
    )
    total_r = feed["project"]["complete_feed_scenario_ohm"]
    separate_r = 0.053  # U101 carries protected load, not AUXbranch.
    common_r = total_r - separate_r
    aux_i = 0.0901
    results = []
    for voltage in analysis["selected_input_chain"]["static_plug_terminal_interval_v"]:
        effective_v = voltage - common_r * aux_i
        disc = effective_v**2 - 4 * total_r * core
        assert disc > 0
        protected_i = 2 * core / (effective_v + math.sqrt(disc))
        total_i = protected_i + aux_i
        aux_v = voltage - total_i * common_r
        protected_v = aux_v - protected_i * separate_r
        feed_heat = total_i**2 * common_r + protected_i**2 * separate_r
        aux_heat = aux_v * aux_i
        total = core + aux_heat + feed_heat
        assert math.isclose(total, voltage * total_i, abs_tol=1e-10)
        results.append(
            dict(
                plug_voltage_v=voltage,
                protected_current_a=protected_i,
                common_feed_current_a=total_i,
                AUX_input_v=aux_v,
                protected_input_v=protected_v,
                source_consumption_w=core,
                complete_AUX_input_heat_w=aux_heat,
                complete_feed_heat_w=feed_heat,
                total_input_heat_w=total,
                energy_residual_w=total - voltage * total_i,
                normal4A_provision_satisfied=total_i <= 4,
                protected9v8_floor_satisfied=protected_v >= 9.8,
                qualifications=False,
            )
        )
    return dict(
        scope="Steady constant-power diagnostic on the same assumed source/current/efficiency/resistance tree; not measured and not a new heat upper",
        protected_constant_power_w=core,
        AUX_input_current_a=aux_i,
        common_upstream_plus_Q101_resistance_ohm=common_r,
        separate_U101_resistance_ohm=separate_r,
        points=results,
    )


def main():
    ledger = read(OUT / "ledger.json")
    design = read(SOURCES / "hardware/cad/a12/thermal/design.json")
    source_analysis = read(SOURCES / "hardware/electronics/power_distribution/p03/generated/analysis.json")
    feed = read(SOURCES / "hardware/cad/a12/harness/input-feed.json")
    heat = ledger["total_internal_heat_screen_w"]
    cases = []
    placements = {}
    thresholds = []
    for mode in ["unplaced_uniform", "unplaced_hotcluster"]:
        inputs = placement(ledger, design, mode)
        placements[mode] = inputs
        for epsilon in [0.8, 0.05]:
            for h in [1, 2, 3]:
                result = plate_scenario(design, inputs, h, epsilon)
                cases.append(dict(placement=mode, result=result))
                print(mode, epsilon, h, "peak", result["plate_max_c"], flush=True)
        for target in [60, 65]:
            for epsilon in [0.8, 0.05]:
                low, high = 0.1, 40.0
                assert plate_scenario(design, inputs, high, epsilon)["plate_max_c"] < target
                for _ in range(14):
                    mid = (low + high) / 2
                    result = plate_scenario(design, inputs, mid, epsilon)
                    if result["plate_max_c"] > target:
                        low = mid
                    else:
                        high = mid
                thresholds.append(
                    dict(
                        placement=mode,
                        target_base_c=target,
                        emissivity_assumed=epsilon,
                        required_uniform_h_bracket_w_per_m2k=[low, high],
                        installed_h_is_bounded=False,
                        heat_transfer_qualified=False,
                    )
                )
    mesh = []
    for mode in placements:
        fine = plate_scenario(design, placements[mode], 3, 0.8, grid=(134, 64))
        old = next(
            c["result"]
            for c in cases
            if c["placement"] == mode
            and c["result"]["h_assumed_w_per_m2k"] == 3
            and c["result"]["emissivity_assumed"] == 0.8
        )
        mesh.append(
            dict(
                placement=mode,
                coarse_grid_peak_c=old["plate_max_c"],
                fine=fine,
                peak_delta_c=fine["plate_max_c"] - old["plate_max_c"],
            )
        )
    # Diagnostic only: remove unknown upstream losses to show why they are not the sole blocker.
    no_upstream = copy.deepcopy(placements["unplaced_uniform"])
    for source in no_upstream:
        if source["id"] == "inlet_wire_fuse_and_contacts":
            source["watts"] = 0
    excluded_case = plate_scenario(design, no_upstream, 3, 0.8)
    paths = [Path(__file__).resolve(), ROOT / "plate.py", ROOT / "base_geometry.py", OUT / "ledger.json"]
    paths += [p for p in SOURCES.rglob("*") if p.is_file()]
    historical = read(
        SOURCES
        / "hardware/cad/a12/thermal/candidates/u102_stronger/sources/base-model/generated/analysis.json"
    )
    historical_sources = []
    for ref, (x, y, watts) in historical["actual_native_heat_assignment"].items():
        site = next((z for z in lands(design) if ref in z["refs"]), None)
        historical_sources.append(
            dict(
                id=ref,
                watts=watts,
                rect_housing_mm=site["metal_global"] if site else [168 + x - 1.5, 108 + y - 1.5, 3, 3],
                notched_land=site if site and "corner_relief" in site else None,
            )
        )
    controls = []
    for old in historical["conditional_plate_scenarios"]:
        actual = plate_scenario(
            design, historical_sources, old["h_assumed_w_per_m2k"], old["emissivity_assumed"]
        )
        change = actual["plate_max_c"] - old["plate_max_c"]
        assert abs(change) < 1e-7, "New explicit-source interface changed historical plate equations"
        controls.append(
            dict(
                h=old["h_assumed_w_per_m2k"],
                emissivity=old["emissivity_assumed"],
                old_peak_c=old["plate_max_c"],
                actual_replayed_peak_c=actual["plate_max_c"],
                delta_c=change,
            )
        )
    report = dict(
        revision="WU01-existing-passive-base-whole-unit-replay",
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        historical_equation_controls=controls,
        total_internal_heat_screen_w=heat,
        actual_whole_unit_heat_upper_w=None,
        required_peak_base_to40C_ambient_k_per_w=dict(at60C=20 / heat, at65C=25 / heat),
        source_placements=placements,
        cases=cases,
        required_uniform_h=thresholds,
        refinement_diagnostics=mesh,
        pin_fin_count=len(pin_centres(design)),
        steady_source_consistent_diagnostic=source_consistent_points(ledger, source_analysis, feed),
        omit_unknown_external_feed_heat_diagnostic=dict(
            excluded_w=heat - excluded_case["total_w"],
            result=excluded_case,
            export_credit_is_adopted=False,
            reason="Physical internal/external feed-loss partition unproved; full unknown loss remains internal in primary screen",
        ),
        findings=[
            "Every declaredh1/h2/h3 scenario exceeds both60/65C at40C assumed ambient; uniform h must be increased substantially within this same model",
            "Same footprint/fin geometry has not demonstrated required installed transfer; greater cooling or a proven lower complete source-power envelope is the next design action",
            "Moving the small unplaced subset does not recover the supply-only thermal result; no optical/export credit exists",
            "All power is ideally injected directly into metal. Real board/package/internal-air paths and mutual heating can further limit junctions and are not solved",
            "Static source-consistent electrical points are diagnostic; complete capacitance/startup/load trajectories/adapter dynamics/limits remain unqualified",
        ],
        next_design_action=dict(
            required_peak_base_to_ambient_at35v4315W_60C_k_per_w=20 / heat,
            required_peak_base_to_ambient_at35v4315W_65C_k_per_w=25 / heat,
            installed_cooling_test_load_w=heat,
            required_actions=[
                "Reconcile and measure complete simultaneous actual loads/reserves/source efficiencies, including effectiveSeed3V3/SD/LED/AUX/bipolar startup-controller loads",
                "Develop a substantially stronger installed heat-rejection architecture, such as controlled airflow across external fins or a separately reviewed larger passive external sink; localTIM repair alone does not supply this missing base cooling",
                "Bench the installed base/orientation/loadedfeet/tableclearance/finish at whole-unit distributed heat with localbase/ambient/radiative-surrounding measurement and positive expanded uncertainty",
                "Do not convert uniformh to fanCFM or area scaling without a validated flow/thermal model and actual installed measurement",
            ],
            geometry_changed=False,
            production_cooling_selected=False,
        ),
        domain_limitations=[
            "Cases exceeding material/component temperature ranges are fixed-coefficient mathematical failure screens, not physically valid high-temperature predictions",
            "Power4A/feed.36ohm/load/efficiency/reserve inputs are requirements/assumptions, not complete guaranteed upper bounds",
            "Uniformh and emissivity/viewfactor are uncalibrated. Neighboringboards/internalair and real interfaces are unsolved",
            "No optical/audio/external export reduction is adopted. Counting all uncertain feedheat inside is conservative placement, not proof its physical location",
        ],
        ambient_assumed_c=40,
        actual_ambient_upper_established=False,
        actual_local_base_upper_c=None,
        installed_h_lower_w_per_m2k=None,
        whole_base_qualified=False,
        physical_tests_performed=0,
        canonical_modified=False,
        frozen_heat_kit_modified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                total=heat,
                thresholds=thresholds,
                refinement=[dict(placement=r["placement"], delta=r["peak_delta_c"]) for r in mesh],
                coupled=report["steady_source_consistent_diagnostic"],
            ),
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
