"""Bounded actual closed-U10 thermal replay; frozen U10 packets remain unchanged."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.candidates.u10.analyze import ep_contract
from hardware.cad.a12.thermal.candidates.u10.network import read_construction, solve
from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent


def main():
    source = ROOT / "sources/closed-U10"
    pcb = source / "power_p03.kicad_pcb"
    c = read_construction(source / "construction.json", sha(pcb))
    native = json.loads((source / "generated/complete-scratch-verification.json").read_text())
    assert (
        native["pcb_sha256"] == sha(pcb)
        and native["ERC"] == native["DRC"] == native["parity"] == native["opens"] == 0
    )
    ep = ep_contract(pcb)
    assert ep["U10"]["face"] == "F.Cu" and tuple(ep["U10"]["native_xy_mm"]) == (194.2, 129.3)
    tree = read_sexpr(pcb.read_text())
    void = next(v for v in children(tree, "via") if list(map(float, first(v, "at")[1:3])) == [192, 129.3])
    assert str(first(void, "net")[1]).lstrip("/") == "AGND"
    assert float(first(void, "size")[1]) == 0.55 and float(first(void, "drill")[1]) == 0.20
    ledger = json.loads((source / "generated/heatmap.json").read_text())
    power = next(r["conservative_loss_allocation_w"] for r in ledger["thermal_regions"] if r["ref"] == "U10")
    paths = [
        Path(__file__).resolve(),
        *source.rglob("*.json"),
        pcb,
        REPO / "hardware/cad/a12/thermal/candidates/u10/network.py",
        REPO / "hardware/cad/a12/thermal/candidates/u10/analyze.py",
        REPO / "hardware/cad/a12/thermal/analyze.py",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}
    d = c["dielectric_nominal_mm"]
    rows = []
    for grid in [160, 320]:
        for sensitive in [False, True]:
            r = solve(
                [190.1, 127.7, 193.75, 131.4],
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
            rows.append(dict(grid=grid, scenario="sensitivity" if sensitive else "nominal", result=r))
    high = rows[-1]["result"]
    report = dict(
        revision="Closed-U10-f94c-actual-restored-field-replay",
        source_sha256=hashes,
        actual_source_pcb_sha256=sha(pcb),
        actual_ep=ep,
        raw_native_closed=True,
        actual_foreign_AGND_void=dict(
            native_xy_mm=[192, 129.3], land_mm=0.55, finished_bore_mm=0.20, RAW_N22_thermal_credit=False
        ),
        scenarios=rows,
        conditional_temperature_at65c_base_plus2c_uncertainty_c=65
        + power * high["conditional_total_junction_to_base_c_per_w"]
        + 2,
        source_power_allocation_w=power,
        package_reference_k_per_w=5.5,
        package_upper_k_per_w=None,
        total_path_upper_k_per_w=None,
        actual_base_upper_c=None,
        actual_positive_measurement_uncertainty_c=None,
        physical_tests_performed=0,
        thermal_path_qualified=False,
        canonical_modified=False,
        geometry_scope="No new MCAD claim. Parent separatelychecked actualclosedU10bodies/case; original LAND/TIMshape unchanged but source-bound finalintegration and real pressure/isolation/tolerance remain open",
        holds=[
            "All actual0.55/0.20quiet AGND holes and restored foreign-net copper remain voids in RAW_N22 extraction",
            "Package/TIM/contact/plating/material/source/whole-base upper bounds and positive measurement uncertainty are unestablished",
            "Neighbouring-device PCB cross-heating and complete enclosure power partition are not solved by this single-source path",
            "Native closure is not electrical loop/stability/physical qualification",
        ],
    )
    assert all(sha(REPO / p) == h for p, h in hashes.items())
    (ROOT / "generated/closed-U10-replay.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            [
                dict(
                    grid=r["grid"],
                    scenario=r["scenario"],
                    path=r["result"]["conditional_total_junction_to_base_c_per_w"],
                    c=r["result"]["conditional_junction_at_60c_base_c"],
                    area=r["result"]["sink_area_under_matching_bottom_copper_mm2"],
                )
                for r in rows
            ],
            indent=2,
        )
    )
    print("65Cbase+2Cuncertainty:", report["conditional_temperature_at65c_base_plus2c_uncertainty_c"])


if __name__ == "__main__":
    main()
