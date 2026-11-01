"""Actual-nine-via source comparison; no ideal blanket copper or physical pass."""

import json
import math

from hardware.cad.a12.thermal.generate import REPO, sha

from ..network import read_construction, solve
from .generate import METAL, OUT, ROOT, TIM


def required_path(base_c, uncertainty_c=0, power=0.961306923312642):
    if (
        not all(math.isfinite(x) for x in [base_c, uncertainty_c, power])
        or power <= 0
        or uncertainty_c < 0
        or base_c + uncertainty_c >= 110
    ):
        raise ValueError("Invalid project allocation scenario")
    return (110 - base_c - uncertainty_c) / power


def main():
    pcb = ROOT / "sources/power_p03.kicad_pcb"
    contract = ROOT / "sources/construction.json"
    construction = read_construction(contract, sha(pcb))
    assert construction["via_wall_minimum_required_um"] == 50
    receipt = json.loads((ROOT / "sources/u102-candidate.json").read_text())
    assert receipt["candidate_pcb_sha256"] == sha(pcb)
    geometry = json.loads((OUT / "geometry.json").read_text())
    assert (
        geometry["candidate_pcb_sha256"] == sha(pcb)
        and geometry["metal_native_mm"] == METAL
        and geometry["tim_native_mm"] == TIM
    )
    source_paths = [
        ROOT / "analyze.py",
        ROOT / "generate.py",
        ROOT.parent / "network.py",
        pcb,
        contract,
        ROOT / "sources/u102-candidate.json",
        ROOT / "sources/components.json",
        ROOT.parent / "generated/analysis.json",
        OUT / "geometry.json",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in source_paths}
    power = 0.961306923312642
    nominal = []
    sensitivity = []
    for grid in [160, 320]:
        nominal.append(
            solve(
                METAL,
                grid=grid,
                pcb_path=pcb,
                via_wall_um=50,
                tim_gap_mm=1.22,
                tim_k=6,
                contact_c_per_w=0.8,
                copper_k=385,
                power=power,
            )
        )
        sensitivity.append(
            solve(
                METAL,
                grid=grid,
                pcb_path=pcb,
                via_wall_um=50,
                tim_gap_mm=1.5,
                tim_k=4,
                contact_c_per_w=2,
                copper_k=350,
                power=power,
            )
        )
    assert all(sha(REPO / p) == h for p, h in hashes.items()), "Inputchanged duringrun"
    native = json.loads((OUT / "verification.json").read_text())
    prior = json.loads((ROOT.parent / "generated/analysis.json").read_text())
    report = dict(
        revision="U102-actual-nine-via-wider-unreleased",
        source_sha256=hashes,
        native_verification_sha256=sha(OUT / "verification.json"),
        native_candidate_pcb_sha256=sha(pcb),
        inherited_dgn_primary_source=prior["primary_source"],
        source_power_allocation_w=power,
        actual_dgn_package="TPS7A1601DGNR; native EP1.68x1.88, injected minimum manufacturer EP1.34x1.66",
        nominal_scenario=dict(
            inputs=dict(
                copper_k_w_per_mk=385,
                tim_k_typical_w_per_mk=6,
                tim_gap_mm=1.22,
                extra_contact_assumed_k_per_w=0.8,
                package_theta_reference_k_per_w=14.9,
                via_wall_minimum_required_um=50,
            ),
            results=nominal,
        ),
        illustrative_lower_conductivity_sensitivity=dict(
            inputs=dict(
                copper_k_w_per_mk=350,
                tim_k_unverified_w_per_mk=4,
                tim_gap_mm=1.5,
                extra_contact_assumed_k_per_w=2,
                package_theta_reference_k_per_w=14.9,
                via_wall_minimum_required_um=50,
            ),
            results=sensitivity,
            manufacturer_guaranteed_enclosure=False,
        ),
        nominal_mesh_peak_difference_k_per_w=abs(
            nominal[0]["ep_peak_to_land_network_c_per_w"] - nominal[1]["ep_peak_to_land_network_c_per_w"]
        ),
        sensitivity_mesh_peak_difference_k_per_w=abs(
            sensitivity[0]["ep_peak_to_land_network_c_per_w"]
            - sensitivity[1]["ep_peak_to_land_network_c_per_w"]
        ),
        previous_rejected_six_via_trial=dict(
            report_sha256=sha(ROOT.parent / "generated/analysis.json"),
            path_k_per_w=prior["finer_grid"]["conditional_total_junction_to_base_c_per_w"],
            temperature_at60base_c=prior["finer_grid"]["conditional_junction_at_60c_base_c"],
            native_tail_collision_still_rejected=True,
        ),
        proposed_contact=dict(
            metal_native_mm=METAL,
            tim_native_mm=TIM,
            metal_nominal_area_mm2=(METAL[2] - METAL[0]) * (METAL[3] - METAL[1]),
            frozen_base_modified=False,
            difference_from_owner_initial_contact="Metal left edge123.25→121.75; TIMleft122.25→120.75, preserving.35mm nominalJ106tailgap. Uses actual existing savedBspreader border; no newPCB copper assumed.",
        ),
        project_allocation_scenarios=[
            dict(
                base_upper_c=base,
                uncertainty_allocation_c=u,
                required_total_path_k_per_w=required_path(base, u),
                allocation_is_approved=False,
            )
            for base, u in [(60, 0), (60, 2), (65, 0), (65, 2)]
        ],
        native_geometry_accepted_as_declared=native["accepted_native_evidence"],
        whole_path_acceptance=dict(
            formula="Tbase_upper + Pupper*Rpath_upper + expanded_uncertainty <=110C",
            base_temperature_upper_bound_c=None,
            ic_power_upper_bound_w=None,
            path_upper_bound_k_per_w=None,
            expanded_uncertainty_c=None,
            actual_received_via_wall_microsection_approved=False,
            thermal_path_qualified=False,
            guardbanded110c_accepted=False,
        ),
        remaining_holds=[
            "ActualU102candidate still25opens andmustnotbeusedascompletePCB",
            "MinimumTIMk/contact andDGNpackagepath tolerances missing",
            "C50wallmax/predrill/web/annulus/fill/registration/finishedCu process not approved ormicrosectioned",
            "Localspreadermodel excludesFR4/parallelair/outside-domain spreading; radialcap/barrel conduction andnonuniformpackagesource not solved",
            "Two meshes andKCL residual do not bound discretization/model uncertainty",
            "Newfifthpad requires matchedcompression/clampforce/boarddeflection verification andfullcaseintegration",
            "Localbase60C is a scenario; priorwholebaseconvection/emissivity areunverified",
            "Bothface body/tail classes,XYmanufacturing/seat tolerances andactualdriver/serviceaccess remainunqualified",
            "Noelectricalisolationcreditfrom soldermask; selectedinsulatingTIM/pressure/wear/hipot require actualtests",
        ],
        physical_tests_performed=0,
        physical_fit_verified=False,
        thermal_path_qualified=False,
        pcb_released=False,
        frozen_heat_kit_modified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
