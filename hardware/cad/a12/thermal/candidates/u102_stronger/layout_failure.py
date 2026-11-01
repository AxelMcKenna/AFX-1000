"""Concrete manufacturer-layout failure in historical c95; raw native closure is insufficient."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.netlists import number
from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent


def facts(pcb, parts_path):
    tree = read_sexpr(pcb.read_text())
    parts = {p["ref"]: p for p in json.loads(parts_path.read_text())}
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    regulator = fps["U102"]
    assert next(p[2] for p in children(regulator, "property") if p[1] == "Value") == "TPS7A1601DGNR"
    rows = []
    input_rows = []
    for ref, part in parts.items():
        if not ref.startswith("C"):
            continue
        fp_actual = fps[ref]
        nets = {str(first(p, "net")[1]).lstrip("/") for p in children(fp_actual, "pad") if children(p, "net")}
        assert nets == {p["net"] for p in part["pins"]}, "BOM/native capacitor-node disagreement"
        assert next(p[2] for p in children(fp_actual, "property") if p[1] == "Value") == part["part"], (
            "BOM/native capacitor-value disagreement"
        )
        if nets == {"VIN_IC", "AGND"}:
            fp = fps[ref]
            input_rows.append(
                dict(
                    ref=ref,
                    part=part["part"],
                    face=first(fp, "layer")[1],
                    nominal_uf=number(part["part"]) * 1e6,
                    native_centre_mm=list(map(float, first(fp, "at")[1:3])),
                    effective_capacitance_lower_uf=None,
                )
            )
        if nets != {"V2V5_AUX", "AGND"}:
            continue
        fp = fps[ref]
        rows.append(
            dict(
                ref=ref,
                part=part["part"],
                face=first(fp, "layer")[1],
                nominal_uf=number(part["part"]) * 1e6,
                native_centre_mm=list(map(float, first(fp, "at")[1:3])),
                effective_capacitance_lower_uf=None,
            )
        )
    c106 = next(r for r in rows if r["ref"] == "C106")
    c107 = next(r for r in rows if r["ref"] == "C107")
    return dict(
        regulator_face=first(regulator, "layer")[1],
        actual_input_node=str(
            first(next(p for p in children(regulator, "pad") if p[1] == "8"), "net")[1]
        ).lstrip("/"),
        actual_input_caps=input_rows,
        nominal_front_input_total_uf=sum(r["nominal_uf"] for r in input_rows if r["face"] == "F.Cu"),
        minimum_effective_input_cap_uf=0.1,
        output_caps=rows,
        intended_bulk_same_face=c106["face"] == first(regulator, "layer")[1],
        C107_front_nominal_uf=c107["nominal_uf"],
        minimum_effective_output_cap_uf=2.2,
        C107_by_itself_can_meet_minimum_even_before_derating=c107["nominal_uf"] >= 2.2,
        actual_minimum_local_effective_capacitance_uf=None,
        locality_and_ground_path_qualified=False,
        regulator_stability_qualified=False,
    )


def main():
    pcb = ROOT / "closed/power_p03.kicad_pcb"
    parts = ROOT / "closed/components.json"
    result = facts(pcb, parts)
    assert result["actual_input_node"] == "VIN_IC"
    assert result["nominal_front_input_total_uf"] == 0
    assert not result["intended_bulk_same_face"]
    assert not result["C107_by_itself_can_meet_minimum_even_before_derating"]
    paths = [
        Path(__file__).resolve(),
        pcb,
        parts,
        ROOT / "sources/TPS7A16-RevF.pdf",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/common/netlists.py",
    ]
    report = dict(
        revision="c95-TPS7A16-local-cap-manufacturer-layout-FAIL",
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        source_pcb_sha256=sha(pcb),
        actual_facts=result,
        manufacturer_source=dict(
            url="https://www.ti.com/lit/ds/symlink/tps7a16.pdf",
            revision="SBVS171F Oct2015",
            locations=[
                "Printedp15 section8.2.1.2.1.3 minimum0.1uFinput/2.2uFoutput;10uFrecommended",
                "Printedp19 section10.1 sameface/close/directOUTcapGND;viasandlongtracesdiscouraged",
            ],
        ),
        status="FAILED manufacturer layout recommendation: missing adequate local same-face input AND output capacitors",
        raw_native_zero_erc_drc_parity_opens_does_not_override_failure=True,
        explicit_missing_evidence=[
            "Real selected sameface local input capacitor with effective>=0.1uF onVIN_IC and local output capacitor with effective>=2.2uF across actual bias/temp/tolerance/ageing envelope",
            "Actual direct OUT-to-localCout-to-regulatorGND loop and appropriate input/ground layout",
            "Renewed native body/thermal void extraction after actual part/pose/routing repair",
            "Actual startup/load-step/PSRR/noise/temperature stability verification",
        ],
        physical_tests_performed=0,
        thermal_design_adopted=False,
        fabrication_released=False,
    )
    (ROOT / "generated/regulator-layout-failure.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])


if __name__ == "__main__":
    main()
