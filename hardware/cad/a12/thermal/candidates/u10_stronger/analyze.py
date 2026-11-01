"""Compare actual eight-via/cleared-field source with sealed U10; identical material allowances."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.candidates.u10.analyze import ep_contract, required_path
from hardware.cad.a12.thermal.candidates.u10.network import read_construction, solve
from hardware.cad.a12.thermal.generate import REPO, sha

from .synthesize import BASE, CONTACT, ROOT


def main():
    pcb = ROOT / "variant/power_p03.kicad_pcb"
    contract = read_construction(ROOT / "variant/construction.json", sha(pcb))
    receipt = json.loads((ROOT / "variant/receipt.json").read_text())
    assert receipt["candidate_pcb_sha256"] == sha(pcb)
    assert receipt["hard_drc"] == receipt["parity"] == receipt["native_erc_issues"] == 0
    paths = [
        Path(__file__).resolve(),
        ROOT / "synthesize.py",
        pcb,
        ROOT / "variant/construction.json",
        ROOT / "variant/receipt.json",
        BASE / "network.py",
        BASE / "analyze.py",
        BASE / "generated/analysis.json",
        BASE / "handoff.json",
        REPO / "hardware/cad/a12/thermal/analyze.py",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}
    dielectric = contract["dielectric_nominal_mm"]
    scenarios = []
    for grid in [160, 320]:
        for sensitivity in [False, True]:
            result = solve(
                CONTACT,
                grid=grid,
                pcb_path=pcb,
                via_wall_um=50,
                power=0.6292218937818581,
                tim_k=4 if sensitivity else 6,
                tim_gap_mm=1.5 if sensitivity else 1.22,
                contact_c_per_w=2 if sensitivity else 0.8,
                copper_k=350 if sensitivity else 385,
                dielectric_override_mm=[v * (1.76 - 0.45) / sum(dielectric) for v in dielectric]
                if sensitivity
                else None,
            )
            scenarios.append(
                dict(
                    grid=grid,
                    scenario="unchanged_sensitivity" if sensitivity else "unchanged_nominal",
                    result=result,
                )
            )
    high = scenarios[-1]["result"]
    total = high["conditional_total_junction_to_base_c_per_w"]
    allowances = []
    for base, u in [(60, 2), (65, 2)]:
        required = required_path(base, u)
        allowances.append(
            dict(
                base_scenario_c=base,
                expanded_uncertainty_allocation_c=u,
                required_total_path_upper_k_per_w=required,
                sensitivity_reference_total_k_per_w=total,
                remaining_additional_path_margin_k_per_w=required - total,
                maximum_combined_package_and_extra_contact_if_other_terms_bounded_k_per_w=required
                - (total - 5.5 - 2),
                conditional_temperature_including_allocated_uncertainty_c=base
                + 0.6292218937818581 * total
                + u,
                manufacturer_guaranteed=False,
                guardbanded_acceptance=False,
            )
        )
    assert all(sha(REPO / p) == h for p, h in hashes.items())
    report = dict(
        revision="U10-eight-EP-full-existing-land-actual-copper",
        source_sha256=hashes,
        actual_ep=ep_contract(pcb),
        native_electrical=receipt,
        isolated_changes="8 direct EP barrels replace4; foreign routing and barrels removed from local thermal field with exact reroute ledger. No pose/XYland/material/gap/temperature/uncertainty allocation reduced",
        baseline_report=str((BASE / "generated/analysis.json").relative_to(REPO)),
        scenarios=scenarios,
        comparison_allocations=allowances,
        package_reference_k_per_w=5.5,
        package_upper_k_per_w=None,
        unchanged_sensitivity=dict(
            copper_k_unverified=350,
            tim_k_unverified=4,
            gap_mm=1.5,
            interface_assumed_k_per_w=2,
            board_thickness_allocation_mm=1.76,
            via_wall_minimum_required_um=50,
        ),
        actual_TIM="Existing selected1.524mm TGP6000ULM sheet2195667; received thickness/compression/contact proof remains open",
        rejected_thin_TIM=dict(
            proposed_grade="Henkel TGP7000ULM0.020in standard sheet",
            primary_url="https://datasheets.tdx.henkel.com/BERGQUIST-GAP-PAD-TGP-7000ULM-en_GL.pdf",
            pdf_sha256=sha(ROOT / "sources/TGP7000ULM.pdf"),
            reason="A0.508mm pad cannot span0.4064mm nominal+0.28mm unchanged gap variation. No heat-bridge credit without actual matched-height construction; not selected for this candidate",
            reference_k_typical=7,
            minimum_k=None,
            pressure_qualified=False,
        ),
        acceptance=dict(
            thermal_path_qualified=False,
            base_upper_c=None,
            power_upper_w=None,
            total_path_upper_k_per_w=None,
            positive_expanded_uncertainty_c=None,
        ),
        holds=[
            "Restore all19 actual electrical opens and local N19 SET/output/AGNDquiet/decoupling loops before any operational use",
            "Fresh actual-copper solve and return path analysis after electrical owner reroutes; never inherit removed-track path",
            "C50 plating, drill web, annulus, fill/cap flatness, actual native8 EP vias and full source-bound fabricated stack require approved DFM/microsections",
            "Package reference5.5 is not an upper bound; package+solder+interface upper or whole-path junction measurement required",
            "TIM4 and Cu350 are declared sensitivities, not vendor minima; actual pressure/compression/wetting/isolation/ageing unknown",
            "All localbase scenarios remain hypothetical until whole10.557757W heat/base/ambient model and measurements close",
            "Current native XYclearance is nominal only; no factory position/trim/seat/diecut tolerance acceptance",
        ],
        canonical_modified=False,
        frozen_u10_modified=False,
        physical_tests_performed=0,
        thermal_path_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "generated").mkdir(exist_ok=True)
    (ROOT / "generated/analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            [
                dict(
                    grid=r["grid"],
                    scenario=r["scenario"],
                    path=r["result"]["conditional_total_junction_to_base_c_per_w"],
                    c=r["result"]["conditional_junction_at_60c_base_c"],
                    bottom_area=r["result"]["sink_area_under_matching_bottom_copper_mm2"],
                )
                for r in scenarios
            ],
            indent=2,
        )
    )
    print(json.dumps(allowances, indent=2))


if __name__ == "__main__":
    main()
