"""Actual native-copper comparison on a closed coordinated U102 source, no upper-bound claim."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.candidates.u10.candidate import geometry_inventory
from hardware.cad.a12.thermal.candidates.u10_stronger.u102_network_corrected import read_construction, solve
from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import read_sexpr

from .synthesize import METAL, ROOT, SOURCE


def main():
    baseline = SOURCE / "power_p03.kicad_pcb"
    candidate = ROOT / "variant/power_p03.kicad_pcb"
    original = geometry_inventory(read_sexpr(baseline.read_text()))
    changed = geometry_inventory(read_sexpr(candidate.read_text()))
    assert original["footprints"] == changed["footprints"]
    assert original["vias"] == changed["vias"], "Every actual source and foreign barrel must be retained"
    construction = read_construction(ROOT / "variant/construction.json", sha(candidate))
    receipt = json.loads((ROOT / "variant/receipt.json").read_text())
    assert receipt["opens"] == 3 and receipt["hard_drc"] == receipt["parity"] == receipt["erc"] == 0
    assert {r["node"] for r in receipt["removed_objects"]} == {"V2V5_AUX", "AUX_FB"}
    ledger = json.loads((SOURCE / "generated/heatmap.json").read_text())
    power = next(r["conservative_loss_allocation_w"] for r in ledger["thermal_regions"] if r["ref"] == "U102")
    assert abs(power - 0.961306923312642) < 1e-12
    paths = [
        Path(__file__).resolve(),
        ROOT / "synthesize.py",
        baseline,
        candidate,
        ROOT / "variant/receipt.json",
        ROOT / "variant/construction.json",
        SOURCE / "capture.json",
        SOURCE / "generated/heatmap.json",
        REPO / "hardware/cad/a12/thermal/candidates/u10_stronger/u102_network_corrected.py",
        REPO / "hardware/cad/a12/thermal/analyze.py",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}
    dielectric = construction["dielectric_nominal_mm"]
    scenarios = []
    for grid in [160, 320]:
        for case, pcb in [("closed_source", baseline), ("preferred_B_only", candidate)]:
            for sensitive in [False, True]:
                result = solve(
                    METAL,
                    grid=grid,
                    pcb_path=pcb,
                    via_wall_um=50,
                    power=power,
                    tim_k=4 if sensitive else 6,
                    tim_gap_mm=1.5 if sensitive else 1.22,
                    contact_c_per_w=2 if sensitive else 0.8,
                    copper_k=350 if sensitive else 385,
                    dielectric_override_mm=[v * (1.76 - 0.45) / sum(dielectric) for v in dielectric]
                    if sensitive
                    else None,
                )
                scenarios.append(
                    dict(
                        grid=grid,
                        case=case,
                        scenario="sensitivity" if sensitive else "nominal",
                        result=result,
                    )
                )
    aggressive = ROOT / "trials/aggressive/power_p03.kicad_pcb"
    comparison = solve(
        METAL,
        grid=320,
        pcb_path=aggressive,
        via_wall_um=50,
        power=power,
        tim_k=4,
        tim_gap_mm=1.5,
        contact_c_per_w=2,
        copper_k=350,
        dielectric_override_mm=[v * (1.76 - 0.45) / sum(dielectric) for v in dielectric],
    )
    hashes[str(aggressive.relative_to(REPO))] = sha(aggressive)
    high = scenarios[-1]["result"]
    allocations = []
    for base, u in [(60, 2), (65, 2)]:
        required = (110 - base - u) / power
        allocations.append(
            dict(
                base_scenario_c=base,
                positive_uncertainty_allocation_c=u,
                required_total_path_upper_k_per_w=required,
                reference_sensitivity_total_k_per_w=high["conditional_total_junction_to_base_c_per_w"],
                reference_temperature_including_allocated_uncertainty_c=base
                + power * high["conditional_total_junction_to_base_c_per_w"]
                + u,
                guardbanded_acceptance=False,
            )
        )
    report = dict(
        revision="U102-preferred-B-only-retained-control-and-vias",
        source_sha256=hashes,
        original_native_closed_pcb_sha256=sha(baseline),
        candidate_pcb_sha256=sha(candidate),
        actual_electrical_receipt=receipt,
        all_original_vias_and_footprints_unchanged=True,
        actual_foreign_AUX_FB_source_VIP_retained=dict(
            native_xy_mm=[124.1, 119.675], land_mm=0.55, finished_bore_mm=0.20, AGND_thermal_credit=False
        ),
        scenarios=scenarios,
        rejected_aggressive_comparison=dict(
            result=comparison,
            electrically_acceptable=False,
            reason="13 foreign via endpoints removed, including original control/supply/status connections;12opens. Only a thermal comparison, never selected for adoption",
        ),
        unchanged_sensitivity=dict(
            tim_k_unverified=4,
            copper_k_unverified=350,
            gap_mm=1.5,
            extra_contact_assumed_k_per_w=2,
            board_thickness_allocation_mm=1.76,
            required_minimum_wall_um=50,
            package_theta_reference_k_per_w=14.9,
        ),
        project_allocations=allocations,
        whole_base_report="generated/base-model-audit.json",
        package_upper_k_per_w=None,
        total_path_upper_k_per_w=None,
        local_base_upper_c=None,
        power_upper_w=None,
        positive_expanded_measurement_uncertainty_c=None,
        physical_tests_performed=0,
        thermal_path_qualified=False,
        canonical_modified=False,
        holds=[
            "Restore three actual output/feedback opens around retained foreign barrels, then renew native and thermal/return checks",
            "Actual closed-source In1/In4 corridors and all foreign holes remain model inputs; they cannot be replaced with ideal AGND",
            "DGN14.9 metric is a reference, not a guaranteed upper; actual package/solder/contact/TIM/received wall and source power require bounds or whole-path measurement",
            "Source nine0.70mm lands span1.70mm versus nativeEP1.68mm; physical minimumEP1.34x1.66 source injection does not approve stencil/VIP/annulus/manufacturing",
            "No actual localbase60/65 upper: supply-only heat, delivered downstream power, airflow, emissivity, ambient and plate assumptions remain open",
            "Native nominal fit and positive-control witnesses do not establish factory or assembled XY/Z/pressure/lead tolerances",
        ],
    )
    assert all(sha(REPO / p) == h for p, h in hashes.items())
    (ROOT / "generated").mkdir(exist_ok=True)
    (ROOT / "generated/analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            [
                dict(
                    grid=r["grid"],
                    case=r["case"],
                    scenario=r["scenario"],
                    temperature=r["result"]["conditional_junction_at_60c_base_c"],
                    area=r["result"]["sink_area_under_matching_bottom_copper_mm2"],
                )
                for r in scenarios
            ],
            indent=2,
        )
    )
    print("Aggressive rejected:", comparison["conditional_junction_at_60c_base_c"])
    print(json.dumps(allocations, indent=2))


if __name__ == "__main__":
    main()
