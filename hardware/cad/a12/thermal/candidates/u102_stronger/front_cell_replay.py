"""Actual repaired local-cap cell; necessary layout correction is not analog qualification."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.candidates.u10_stronger.u102_network_corrected import read_construction, solve
from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent


def main():
    folder = ROOT / "repaired"
    pcb = folder / "power_p03.kicad_pcb"
    native = json.loads((folder / "generated/complete-scratch-verification.json").read_text())
    assert (
        native["pcb_sha256"] == sha(pcb)
        and native["ERC"] == native["DRC"] == native["parity"] == native["opens"] == 0
    )
    construction = read_construction(folder / "construction.json", sha(pcb))
    tree = read_sexpr(pcb.read_text())
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    parts = {p["ref"]: p for p in json.loads((folder / "components.json").read_text())}
    assert len(parts) == 256
    for ref in ["U102", "C106", "C113", "C110"]:
        assert first(fps[ref], "layer")[1] == "F.Cu"
    for ref, mpn in [
        ("C106", "C3225X7R1E106K250AC"),
        ("C113", "C2012X7S2A105K125AE"),
        ("C110", "C0603C103J3GACTU"),
    ]:
        assert mpn in parts[ref]["part"]
    loop_path = folder / "generated/aux-local-loop-verification.json"
    loops = json.loads(loop_path.read_text())
    assert loops["pcb_sha256"] == sha(pcb) and len(loops["actual_direct_front_paths"]) == 6
    # This is U102 PG/pin3 (logical POWER_RUN enable), not its EN/pin5.
    hole = next(
        v
        for v in children(tree, "via")
        if abs(float(first(v, "at")[1]) - 124.925) < 1e-8 and abs(float(first(v, "at")[2]) - 120.325) < 1e-8
    )
    assert (
        str(first(hole, "net")[1]).lstrip("/") == "POWER_RUN"
        and float(first(hole, "size")[1]) == 0.55
        and float(first(hole, "drill")[1]) == 0.20
    )
    assert (
        str(first(next(p for p in children(fps["U102"], "pad") if p[1] == "3"), "net")[1]).lstrip("/")
        == "POWER_RUN"
    )
    ledger = json.loads((folder / "generated/heatmap.json").read_text())
    power = next(r["conservative_loss_allocation_w"] for r in ledger["thermal_regions"] if r["ref"] == "U102")
    d = construction["dielectric_nominal_mm"]
    paths = [
        Path(__file__).resolve(),
        pcb,
        folder / "construction.json",
        folder / "components.json",
        folder / "component-selections.json",
        folder / "generated/heatmap.json",
        folder / "generated/current-native.json",
        folder / "generated/complete-scratch-verification.json",
        loop_path,
        REPO / "hardware/cad/a12/thermal/candidates/u10_stronger/u102_network_corrected.py",
        REPO / "hardware/cad/a12/thermal/analyze.py",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}
    rows = []
    for grid in [160, 320]:
        for sensitive in [False, True]:
            result = solve(
                [121.75, 117.5, 128.75, 122.5],
                grid=grid,
                pcb_path=pcb,
                via_wall_um=50,
                power=power,
                tim_k=4 if sensitive else 6,
                tim_gap_mm=1.5 if sensitive else 1.22,
                contact_c_per_w=2 if sensitive else 0.8,
                copper_k=350 if sensitive else 385,
                dielectric_override_mm=[v * (1.76 - 0.45) / sum(d) for v in d] if sensitive else None,
            )
            rows.append(dict(grid=grid, scenario="sensitivity" if sensitive else "nominal", result=result))
    result = rows[-1]["result"]
    required = (110 - 65 - 2) / power
    report = dict(
        revision="U102-sameface-cell37fd-actual-field-replay",
        source_sha256=hashes,
        pcb_sha256=sha(pcb),
        raw_native_zero_erc_drc_parity_opens=True,
        selected_local_caps_sameface=True,
        actual_front_paths=loops["actual_direct_front_paths"],
        necessary_face_and_input_output_nominal_capacitance_repair_implemented=True,
        physical_loop_length_and_stability_acceptance=False,
        actual_PG_POWER_RUN_foreign_via=dict(
            native_xy_mm=[124.925, 120.325], land_mm=0.55, finished_bore_mm=0.20, AGND_thermal_credit=False
        ),
        scenarios=rows,
        conditional65base_plus2uncertainty_c=65
        + power * result["conditional_total_junction_to_base_c_per_w"]
        + 2,
        derived_required_total_path_upper_k_per_w_at65base_plus2uncertainty=required,
        remaining_reference_path_margin_k_per_w=required
        - result["conditional_total_junction_to_base_c_per_w"],
        package_theta_reference_k_per_w=14.9,
        package_upper_k_per_w=None,
        total_path_upper_k_per_w=None,
        actual_local_base_upper_c=None,
        actual_positive_expanded_uncertainty_c=None,
        physical_tests_performed=0,
        thermal_path_qualified=False,
        stability_qualified=False,
        fabrication_released=False,
        canonical_modified=False,
        holds=[
            "Effective input/output capacitance under actual bias/temp/tolerance/ageing and source impedance is not bounded by nominal value",
            "Six direct sameface paths implement the necessary repair, but4.45..9.40mm authored paths are not a measured ESL/ESR/loop-stability or shortest-possible-layout qualification",
            "Package/TIM/contact/plating/material and loss-allocation upper bounds plus positive measurement uncertainty remain unestablished",
            "Actual localbase60/65 is unbounded by incomplete supply-only whole-base heat/airflow/radiation model",
            "Single-source local matrix excludes neighbouring-device PCB cross-heating; worst simultaneous assembly verification required",
            "Native closure/body-envelope checks cannot qualify solder/VIP/capcompression/flatness/cleanliness/isolation/ageing",
        ],
    )
    assert all(sha(REPO / p) == h for p, h in hashes.items())
    (ROOT / "generated/front-cell-thermal.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            [
                dict(
                    grid=r["grid"],
                    scenario=r["scenario"],
                    temperature=r["result"]["conditional_junction_at_60c_base_c"],
                    path=r["result"]["conditional_total_junction_to_base_c_per_w"],
                    Barea=r["result"]["sink_area_under_matching_bottom_copper_mm2"],
                )
                for r in rows
            ],
            indent=2,
        )
    )
    print("65base+2:", report["conditional65base_plus2uncertainty_c"])


if __name__ == "__main__":
    main()
