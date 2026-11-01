"""Source-bound rejected baseline; reports screens rather than guarantees."""

import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha

from .baseline import METAL, OUT, ROOT
from .network import read_construction, solve


def path_budget(power, base=60, ceiling=110):
    if (
        any(type(v) not in (int, float) or not math.isfinite(v) for v in [power, base, ceiling])
        or power <= 0
        or ceiling <= base
    ):
        raise ValueError("Finite positive heat and positive temperature headroom required")
    return (ceiling - base) / power


def qualified_acceptance(power_upper, base_upper, path_upper, uncertainty_c, ceiling=110):
    # Missing bounds are not zero. This baseline has no such validated inputs.
    if any(v is None for v in [power_upper, base_upper, path_upper, uncertainty_c]):
        return False
    path_budget(power_upper, base_upper, ceiling)
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in [path_upper, uncertainty_c]):
        raise ValueError("Nonnegative finite path and uncertainty required")
    return base_upper + power_upper * path_upper + uncertainty_c <= ceiling


def main():
    pcb = ROOT / "sources/power_p03.kicad_pcb"
    construction = ROOT / "sources/construction.json"
    contract = read_construction(construction, sha(pcb))
    components = json.loads((ROOT / "sources/components.json").read_text())
    component = next(c for c in components if c["ref"] == "U102")
    assert (
        "TPS7A1601DGNR" in component["part"]
        and component["footprint"] == "Package_SO:MSOP-8-1EP_3x3mm_P0.65mm_EP1.68x1.88mm"
    )
    heat = json.loads((ROOT / "sources/heatmap.json").read_text())
    row = next(r for r in heat["thermal_regions"] if r["ref"] == "U102")
    power = row["conservative_loss_allocation_w"]
    assert abs(power - 0.961306923312642) < 1e-12
    pdf = Path("/private/tmp/afx-tps7a16.pdf")
    primary = dict(
        url="https://www.ti.com/lit/ds/symlink/tps7a16.pdf",
        sha256=sha(pdf),
        metric_basis="RevF Table6.4 DGN junction-to-case-bottom14.9K/W. Package metric has no production upper tolerance. DRB4.7K/W is a different package.",
        drawing_basis="Appended DGN0008C4218838/A11/2017: package EP1.34..1.60 by1.66..1.92; image page34 inspected. Native EP pad1.68x1.88; minimum-package EP used for injected source.",
        external_copy_path=str(pdf),
        manufacturer_guaranteed_upper_path=False,
    )
    source_paths = [
        ROOT / "analyze.py",
        ROOT / "network.py",
        ROOT / "baseline.py",
        construction,
        pcb,
        ROOT / "sources/components.json",
        ROOT / "sources/heatmap.json",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in source_paths}
    scenarios = []
    for gap, k, contact in [(1.22, 6, 0.8), (1.5, 4, 2)]:
        scenarios.append(
            solve(
                METAL,
                grid=160,
                pcb_path=pcb,
                via_wall_um=contract["via_wall_minimum_required_um"],
                tim_gap_mm=gap,
                tim_k=k,
                contact_c_per_w=contact,
                power=power,
            )
        )
    fine = solve(
        METAL,
        grid=320,
        pcb_path=pcb,
        via_wall_um=contract["via_wall_minimum_required_um"],
        tim_gap_mm=1.22,
        tim_k=6,
        contact_c_per_w=0.8,
        power=power,
    )
    assert all(sha(REPO / p) == h for p, h in hashes.items()), "Inputs changed during numerical run"
    native = json.loads((OUT / "verification.json").read_text())
    report = dict(
        revision="U102-baseline-rejected",
        source_sha256=hashes,
        primary_source=primary,
        conservative_heat_allocation_w=power,
        project_junction_allocation_c=110,
        assumed_local_base_c=60,
        required_total_path_before_uncertainty_k_per_w=path_budget(power),
        scenarios=scenarios,
        finer_grid=fine,
        coarse_fine_peak_difference_k_per_w=abs(
            fine["ep_peak_to_land_network_c_per_w"] - scenarios[0]["ep_peak_to_land_network_c_per_w"]
        ),
        convergence_basis="Linear KCL residual is checked. Two mesh results differ; no error-bound/spatial-convergence guarantee. Mesh refinement cannot repair missing material/contact bounds.",
        native_candidate_failed_cases=native["failed_cases"],
        native_verification_sha256=sha(OUT / "verification.json"),
        decision="REJECTED: actual J106tail collision and inadequate declared copper/TIM screen. Do not fabricate this trial.",
        next_candidate=dict(
            metal_native_mm=[123.25, 117.5, 129.25, 122.5],
            tim_native_mm=[122.25, 116.5, 130.25, 123.5],
            requirements=[
                "Actual localAGND bottom/inner spreader, respecting foreign-net voids",
                "Nine directEP vias only after native pad/hole clearance and fullC50DFM approval",
                "R110/R130/C109 and any other actual interfering Bparts moved and quiet auxiliary routes repaired",
                "Newland/TIM floorwindow geometry checked against J106tails,bothfaces,links,retainedcase andcontrols",
            ],
            actual_new_pcb_available=False,
            approved=False,
        ),
        acceptance=dict(
            bounded_power_upper_w=None,
            bounded_base_upper_c=None,
            bounded_total_path_upper_k_per_w=None,
            expanded_uncertainty_c=None,
            guardbanded_project_acceptance=qualified_acceptance(None, None, None, None),
            missing_bounds_are_not_zero=True,
        ),
        limitations=[
            "Adiabatic12x12mm localdomain; noFR4 orparallelair credit",
            "TIM conduction vertical only under matching savedBAGND copper; lateralTIM/boardoutsidepatch omitted",
            "Same-net filledpolygon,pad,straighttrack masks plus actualthrough-barrel annuli; unsupportedAGND arcs rejected",
            "Barrel radial/cap conduction, soldervoids, interfaceandmask resistance not physically bounded",
            "C50wall requirement isnot receivedmicrosection; resin haszero solidCu credit",
            "Package14.9 and TIMk6 are reference/typical inputs,not guaranteedupperpath/minimumconductivity",
            "No physicalovertemperature inference from this conditional screen",
        ],
        physical_tests_performed=0,
        physical_fit_verified=False,
        thermal_path_qualified=False,
        base_modified=False,
        pcb_modified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
