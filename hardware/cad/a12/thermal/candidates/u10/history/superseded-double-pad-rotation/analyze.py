"""U10 source-bound thermal feasibility, preserving routing/physical failures."""

import json
import math

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from .generate import METAL, OUT, ROOT
from .network import REPO, read_construction, sha, solve


def ep_contract(pcb):
    tree = read_sexpr(pcb.read_text())
    result = {}
    for ref, node in [("U10", "RAW_N22"), ("U11", "RAW_N17")]:
        f = next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", ref] for p in children(f, "property"))
        )
        ep = next(p for p in children(f, "pad") if str(p[1]) == "11")
        assert first(f, "layer")[1] in first(ep, "layers")[1:], "EP face does not match actual footprint"
        assert next(p[2] for p in children(f, "property") if p[1] == "Value") == "LT3090IDD#PBF", (
            "Wrong actual manufacturer device"
        )
        assert str(first(ep, "net")[1]).lstrip("/") == node, "Live LT3090 EP is IN, never AGND"
        assert str(f[1]) == "Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm"
        result[ref] = dict(
            face=first(f, "layer")[1],
            native_xy_mm=transform(f, [0, 0]),
            housing_xy_mm=[v + d for v, d in zip(transform(f, [0, 0]), [68, 8])],
            ep_native_size_mm=list(map(float, first(ep, "size")[1:3])),
            ep_node=node,
            package="LT3090IDD#PBF / DD",
            package_theta_jc_reference_k_per_w=5.5,
        )
    return result


def required_path(base, uncertainty=0, power=0.6292218937818581):
    if (
        not all(math.isfinite(x) for x in [base, uncertainty, power])
        or power <= 0
        or uncertainty < 0
        or base + uncertainty >= 110
    ):
        raise ValueError("Invalid project temperature allocation")
    return (110 - base - uncertainty) / power


def main():
    source = ROOT / "sources/power_p03.kicad_pcb"
    candidate = ROOT / "variant/power_p03.kicad_pcb"
    construction = read_construction(ROOT / "variant/construction.json", sha(candidate))
    assert construction["via_wall_minimum_required_um"] == 50
    baseline_ep, candidate_ep = ep_contract(source), ep_contract(candidate)
    assert baseline_ep["U10"]["face"] == "B.Cu" and candidate_ep["U10"]["face"] == "F.Cu"
    heat = json.loads((ROOT / "sources/heatmap.json").read_text())
    # Heatmap schema is preserved from the actual canonical generator.
    rows = next(
        v
        for v in heat.values()
        if isinstance(v, list) and any(isinstance(r, dict) and r.get("ref") == "U10" for r in v)
    )
    power = next(r["conservative_loss_allocation_w"] for r in rows if r["ref"] == "U10")
    assert math.isclose(power, 0.6292218937818581, rel_tol=1e-12)
    native = json.loads((ROOT / "variant/receipt.json").read_text())
    drc = json.loads((ROOT / "variant/drc.json").read_text())
    hard = [v for v in drc["violations"] if v["type"] not in {"track_dangling", "via_dangling"}]
    assert not hard and native["native_erc_issues"] == 0 and native["parity_issues"] == 0
    paths = [
        ROOT / "analyze.py",
        ROOT / "network.py",
        ROOT / "candidate.py",
        ROOT / "relocation-clearance-plan.json",
        source,
        candidate,
        ROOT / "sources/heatmap.json",
        ROOT / "variant/construction.json",
        ROOT / "variant/receipt.json",
        REPO / "hardware/cad/a12/thermal/analyze.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
        REPO / "hardware/electronics/common/sexpr.py",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}
    rejected = []
    for grid in [160, 320]:
        try:
            solve([190.1, 131.5, 193.75, 135.5], grid=grid, pcb_path=source, via_wall_um=50)
        except AssertionError as e:
            rejected.append(dict(grid=grid, result="rejected", reason=str(e), temperature_c=None))
        else:
            raise AssertionError("Baseline missing-contact failure unexpectedly changed")
    stack = construction["dielectric_nominal_mm"]
    # 1.76 is root's engineering thickness envelope, not an approved factory stack.
    max_stack = [v * (1.76 - 0.45) / sum(stack) for v in stack]
    nominal = []
    sensitivity = []
    for grid in [160, 320]:
        nominal.append(
            solve(
                METAL,
                grid=grid,
                pcb_path=candidate,
                via_wall_um=50,
                power=power,
                tim_k=6,
                tim_gap_mm=1.22,
                contact_c_per_w=0.8,
                copper_k=385,
            )
        )
        sensitivity.append(
            solve(
                METAL,
                grid=grid,
                pcb_path=candidate,
                via_wall_um=50,
                power=power,
                tim_k=4,
                tim_gap_mm=1.5,
                contact_c_per_w=2,
                copper_k=350,
                dielectric_override_mm=max_stack,
            )
        )
    assert all(sha(REPO / p) == h for p, h in hashes.items()), "Input changed during solve"
    report = dict(
        revision="U10-F-pose-thermal-feasibility-only",
        source_sha256=hashes,
        primary_source=dict(
            url="https://www.analog.com/media/en/technical-documentation/data-sheets/3090fa.pdf",
            revision="3090fa RevA Jan2014",
            locations=[
                "p2 DD package thetaJC5.5,EP11=IN must solderPCB",
                "p19-20 thermal discussion and board-test conditions",
                "p33 DD drawing1.65+/-0.10 by2.38+/-0.10;0.75+/-0.05body",
            ],
            package_metric_is_guaranteed_path_upper_bound=False,
            contacting_plastic_top_is_equivalent=False,
            downloaded_local_pdf=False,
            access="Official primary PDF parsed via web; direct download timed out; no invented PDFhash",
        ),
        original_package_contract=baseline_ep,
        candidate_package_contract=candidate_ep,
        original_proposed_contact_baseline_rejected=rejected,
        original_B_pose_unmodified_in_canonical=True,
        candidate_pose_requires_routing_reconstruction=True,
        source_power_allocation_w=power,
        project_junction_allocation_c=110,
        manufacturer_Igrade_operating_Tj_max_c=125,
        nominal=dict(
            inputs=dict(
                copper_k=385,
                tim_k_typical=6,
                gap_mm=1.22,
                extra_contact_assumed_k_per_w=0.8,
                package_reference_k_per_w=5.5,
                board_nominal_mm=1.6,
            ),
            results=nominal,
        ),
        illustrative_sensitivity=dict(
            inputs=dict(
                copper_k_unverified=350,
                tim_k_unverified=4,
                gap_mm=1.5,
                extra_contact_assumed_k_per_w=2,
                package_reference_k_per_w=5.5,
                board_total_allocation_mm=1.76,
                dielectric_override_mm=max_stack,
            ),
            manufacturer_guaranteed_enclosure=False,
            results=sensitivity,
        ),
        mesh_peak_difference_k_per_w=dict(
            nominal=abs(
                nominal[0]["ep_peak_to_land_network_c_per_w"] - nominal[1]["ep_peak_to_land_network_c_per_w"]
            ),
            sensitivity=abs(
                sensitivity[0]["ep_peak_to_land_network_c_per_w"]
                - sensitivity[1]["ep_peak_to_land_network_c_per_w"]
            ),
        ),
        actual_native_electrical=dict(
            erc=0,
            hard_drc=0,
            parity=0,
            opens=len(drc["unconnected_items"]),
            dangling_warnings=len(drc["violations"]),
            electrically_complete=False,
        ),
        bench_allocation_scenarios=[
            dict(
                base_upper_c=b,
                positive_expanded_uncertainty_allocation_c=u,
                required_total_path_upper_k_per_w=required_path(b, u, power),
                approved=False,
            )
            for b, u in [(60, 0), (60, 2), (65, 0), (65, 2)]
        ],
        acceptance=dict(
            formula="Tbase_upper + Pupper*Rpath_upper + expanded_uncertainty <=110C",
            base_upper_c=None,
            power_upper_w=None,
            path_upper_k_per_w=None,
            expanded_uncertainty_c=None,
            guardbanded_project_acceptance=False,
            thermal_path_qualified=False,
        ),
        holds=[
            "Restore exact localN19output/SET/AGNDquietreturn/decoupling loops and all native opens; the draft cannot operate as-is",
            "No TIMminimumconductivity/contact/package/solderjoint upper bounds or receivedC50microsections",
            "Actual paths omitFR4/outside-domain/air and do not model package3Dconjugate spreading or filled-via cap/radial details",
            "Two meshes/KCLenergy do not bound model/discretization uncertainty",
            "DATUMXY/tailtrim/seat/registration/pressure/warp require production tolerance and assembly proof",
            "FloatingCHASSIS remains electrically insulated fromliveRAW_N22; no soldermask/anodize insulationcredit",
            "Localbase60C is onlyscenario; wholeP03heat/baseconvection and neighbouringpath changes need renewed independent analysis",
            "All thermal source annotations must be renewed if owner reroutes/merges this candidate",
        ],
        physical_tests_performed=0,
        physical_fit_verified=False,
        thermal_path_qualified=False,
        canonical_pcb_modified=False,
        frozen_heat_kit_modified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
