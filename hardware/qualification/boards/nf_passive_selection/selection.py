"""NP01 passive candidates; catalog order codes are not assembled guarantees."""

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def resistance(part):
    m = re.match(r"([\d.]+)\s*([kM]?)", part)
    if not m:
        raise ValueError(part)
    return float(m[1]) * {"": 1, "k": 1000, "M": 1e6}[m[2]]


def rcode(value):
    for scale, letter in [(1e6, "M"), (1000, "K"), (1, "R")]:
        if value >= scale:
            n = value / scale
            digits = 3 - len(str(int(n)))
            if digits < 0:
                continue
            return f"{n:.{digits}f}".replace(".", letter) if digits else str(int(n)) + letter
    raise ValueError("Shunts use their separate published code")


def precision_candidate(value):
    if 500 <= value <= 20000:
        return "TNPU0805" + rcode(value) + "HWEN00", "TNPU0805", 0.0002, 2
    if 100 <= value <= 200000:
        return "TNPU0805" + rcode(value) + "HZEN00", "TNPU0805", 0.0002, 5
    if 24.9 <= value < 100:
        return "TNPU0603" + rcode(value) + "AZEN00", "TNPU0603", 0.0005, 5
    raise ValueError("No ultra-precision candidate in the checked range")


def scenario(value, initial, tcr, hours):
    # Do NOT promote sums of separate qualification tests to an installed
    # combined-environment/lifetime guarantee. This is a receiving scenario.
    life = {1000: (0.0005, 0.01), 8000: (0.001, 0.02), 225000: (0.003, 0)}[hours]
    terms = dict(
        initial=initial,
        temperature_20_to85=tcr * 65e-6,
        endurance=life[0] + life[1] / value,
        solder_heat=0.0002 + 0.01 / value,
        damp_heat=0.001 + 0.01 / value,
    )
    return dict(
        terms=terms,
        total_fraction=sum(terms.values()),
        hours=hours,
        temperature_is_unaccepted_film_enclosure_C=[0, 85],
        sum_of_separate_test_limits_NOT_joint_installed_guarantee=True,
        complete_0p1pct_met=sum(terms.values()) <= 0.001,
        complete_0p25pct_planning_met=sum(terms.values()) <= 0.0025,
        complete_0p5pct_planning_met=sum(terms.values()) <= 0.005,
    )


FAMILIES = {
    "TNPU0805": dict(
        body_max_mm=[2.15, 1.4, 0.55],
        P70_W=0.125,
        Umax_V=150,
        Tfilm_max_C=125,
        land="TNPU0805_IPC28950",
        source="vishay-TNPU-28779.pdf",
    ),
    "TNPU0603": dict(
        body_max_mm=[1.7, 0.95, 0.55],
        P70_W=0.1,
        Umax_V=75,
        Tfilm_max_C=125,
        land="TNPU0603_IPC28950",
        source="vishay-TNPU-28779.pdf",
    ),
    "TNPW0805": dict(
        body_max_mm=[2.1, 1.4, 0.55],
        P70_W=0.14,
        Umax_V=150,
        Tfilm_max_C=125,
        land="TNPW0805_IPC28950",
        source="vishay-TNPW-28758.pdf",
    ),
    "TNPW1206": dict(
        body_max_mm=[3.3, 1.75, 0.65],
        P70_W=0.27,
        Umax_V=200,
        Tfilm_max_C=125,
        land="TNPW1206_IPC28950",
        source="vishay-TNPW-28758.pdf",
    ),
    "CRCW2010": dict(
        body_max_mm=[5.15, 2.65, 0.7],
        P70_W=0.75,
        Umax_V=400,
        Tfilm_max_C=155,
        land="CRCW2010_reflow20035",
        source="vishay-CRCW-20035.pdf",
    ),
    "PRG5025_OPTION": dict(
        body_max_mm=[5.2, 2.7, 0.60],
        P70_W=None,
        Umax_V=200,
        Tfilm_max_C=None,
        land="PRG_LONG_SIDE_FACTORY_REVIEW",
        source="susumu-current-catalog.pdf",
        operating_temperature_C=[-55, 155],
        catalog_power_W=[1.5, 2],
        power_test_board_and_derating_must_be_obtained=True,
    ),
    "WSL2512": dict(
        body_max_mm=[6.604, 3.434, 0.889],
        P70_W=1,
        Umax_V=None,
        Tfilm_max_C=170,
        land="WSL2512_7m_to500m",
        source="vishay-WSL-30100.pdf",
    ),
}


def capacitor(part):
    if "MKS2" in part:
        return dict(
            MPN="MKS2C042201K00JSSD",
            family="WIMA_MKS2",
            nominal_F=2.2e-6,
            rated_V=63,
            initial_fraction=0.05,
            body_max_mm=None,
            body_nominal_mm=[7.2, 7.2, 13],
            seat_requirement_mm=0.5,
            body_plus_seat_max_mm=None,
            land="WIMA_P5_D0p5_FACTORY_TOLERANCE_REVIEW",
            source="wima-MKS2.pdf",
            effective_complete_tolerance_accepted=False,
            nominal_lead_diameter_mm=0.5,
            pin_pitch_at_exit_mm=[4.5, 5.5],
            holds=[
                "Case max/tolerances missing from public table",
                "PET temperature/process/aging and installed CF effective10% require evidence",
                "Vendor pitch5 +/-0.5mm at pin exits needs lead forming and underside trim/fillet process",
            ],
        )
    if re.match(r"10uF", part):
        return dict(
            MPN="C3216X7R1E106K160AB",
            family="TDK1206_X7R",
            nominal_F=10e-6,
            rated_V=25,
            initial_fraction=0.1,
            body_max_mm=[3.4, 1.8, 1.8],
            seat_requirement_mm=0.1,
            body_plus_seat_max_mm=1.9,
            land="TDK1206_reflow_PA_PB_PC",
            source="https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3216X7R1E106K160AB",
            verified_manufacturer_product_record=True,
            effective_complete_tolerance_accepted=False,
            holds=[
                "Effective C versus DCbias/temperature/aging not bounded",
                "Input inrush and TMR input domain must be reanalyzed",
                "25V transient maximum and source guard not qualified",
            ],
        )
    if re.match(r"1uF", part):
        return dict(
            MPN="C3216X7R1H105K160AB",
            family="TDK1206_X7R",
            nominal_F=1e-6,
            rated_V=50,
            initial_fraction=0.1,
            body_max_mm=[3.4, 1.8, 1.8],
            seat_requirement_mm=0.1,
            body_plus_seat_max_mm=1.9,
            land="TDK1206_reflow_PA_PB_PC",
            source="https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3216X7R1H105K160AB",
            verified_manufacturer_product_record=True,
            effective_complete_tolerance_accepted=False,
            holds=[
                "Not guaranteed1uF effective even before DCbias",
                "Same-size50V proposal replaces25V localVIN item; not adopted",
                "Required regulator/module Cmin/ESR and startup tests",
            ],
        )
    if "X7R" in part:
        return dict(
            MPN="C0603C104K5RACTU",
            family="KEMET0603_X7R",
            nominal_F=1e-7,
            rated_V=50,
            initial_fraction=0.1,
            body_max_mm=[1.75, 0.95, 0.95],
            seat_requirement_mm=0.1,
            body_plus_seat_max_mm=1.05,
            land="KEMET0603_LevelB",
            source="kemet-X7R-2026.pdf",
            table="1A-CJ/2A",
            no_bias_no_aging_only_lower_factor=0.9 * 0.85,
            effective_complete_tolerance_accepted=False,
            holds=[
                "Aging rate/referee time and effectiveC require exact product test",
                "DCbias/PDN/local placement remains open",
            ],
        )
    if "56nF" in part:
        pn, nom, V, T, code = "C1206C563J5GACTU", 56e-9, 50, 1.35, "EF"
    elif "33nF" in part:
        pn, nom, V, T, code = "C1206C333J5GACTU", 33e-9, 50, 1.0, "EC"
    elif "47nF" in part:
        pn, nom, V, T, code = "C1206C473J5GACTU", 47e-9, 50, 1.2, "EE"
    elif "10nF" in part:
        pn, nom, V, T, code = "C1206C103J5GACTU", 10e-9, 50, 1.1, "ED"
    elif "C1210" in part:
        pn, nom, V, T, code = "C1210C104J5GACTU", 100e-9, 50, 1.4, "FG"
    elif "100nF" in part:
        pn, nom, V, T, code = "C1206C104J3GACTU", 100e-9, 25, 1.8, "EH"
    else:
        raise ValueError(part)
    large = "C1210" in pn
    return dict(
        MPN=pn,
        family="KEMET1210_C0G" if large else "KEMET1206_C0G",
        nominal_F=nom,
        rated_V=V,
        initial_fraction=0.05,
        body_max_mm=[3.5, 2.8, T] if large else [3.5, 1.8, T],
        seat_requirement_mm=0.1,
        body_plus_seat_max_mm=T + 0.1,
        land="KEMET1210_LevelB" if large else "KEMET1206_LevelB",
        source="kemet-C0G-2025.pdf",
        table="1A/1B-" + code + "/2A",
        manufacturer_catalog_supported_order_code=True,
        individual_product_record_confirmed=False,
        initial_plus_65K_TCC_fraction=0.05 + 30e-6 * 65,
        complete6pct_remaining_process_life_fraction=0.06 - (0.05 + 30e-6 * 65),
        optional_1pct_order_code=pn.replace("J", "F", 1),
        optional_1pct_catalog_supported=True,
        optional_1pct_adopted=False,
        effective_complete_tolerance_accepted=False,
        holds=[
            "Complete6/10% not guaranteed by initial5%",
            "Actual solder/process/lifetime/leakage/PCB stray requirements",
            "1%F option requires timing/inrush/charge and source BOM rerun",
        ],
    )


def build(out=None):
    out = Path(out) if out else ROOT / "generated"
    if out.exists():
        raise RuntimeError("Use new outputs; preserve all parent sources")
    out.mkdir()
    parts = json.loads((ROOT / "sources/NF261/components.json").read_text())
    rows = []
    for p in parts:
        ref = p["ref"]
        if ref[0] not in "RC":
            continue
        row = dict(
            ref=ref,
            old_part=p["part"],
            old_footprint=p["footprint"],
            native_nets={str(q["number"]): q["net"] for q in p["pins"]},
            selected_for_production=False,
        )
        if ref.startswith("C"):
            row.update(capacitor(p["part"]))
        else:
            value = resistance(p["part"])
            row["ohm"] = value
            precise = "COMPLETE0.1%" in p["part"]
            if ref in ["R69", "R86"]:
                row.update(
                    MPN="WSL2512" + ("R3300" if value == 0.33 else "R1200") + "DEA",
                    family="WSL2512",
                    initial_fraction=0.005,
                    TCR_ppm_per_K=75,
                    holds=[
                        "0.5% D-grade catalog option, not oldgeneric body qualification",
                        "Fault pulse/SOA/currentwaveform not bounded",
                        "Recommended lands and Kelvin takeoffs must replace generic2512",
                    ],
                )
            elif ref in ["R56", "R57", "R73", "R74"]:
                row.update(
                    MPN="CRCW2010402RFKEF",
                    family="CRCW2010",
                    initial_fraction=0.01,
                    TCR_ppm_per_K=100,
                    alternative=dict(
                        MPN="PRG5025P-4020-B-T4",
                        family="PRG5025_OPTION",
                        initial_fraction=0.001,
                        TCR_ppm_per_K=25,
                        supported_by_primary_catalog_ordering_range=True,
                        individual_product_record_confirmed=False,
                        drop_in=False,
                        long_side_terminals_require_new_land_orientation=True,
                    ),
                    holds=[
                        "COMPLETE3% lifetime/process enclosure not demonstrated for CRCW",
                        "Actual feed startup duration and resistor local temperature",
                        "PRG alternative requires manufacturer power-test-board and land information",
                    ],
                )
            elif precise:
                pn, family, initial, tcr = precision_candidate(value)
                row.update(
                    MPN=pn,
                    family=family,
                    initial_fraction=initial,
                    TCR_ppm_per_K=tcr,
                    same_nominal_package=family == "TNPU0805",
                    complete_receiving_original_fraction=0.001,
                    planning_error_scenarios=[scenario(value, initial, tcr, h) for h in [1000, 8000, 225000]],
                    holds=[
                        "COMPLETE0.1% not closed",
                        "Listed test-limit sums are a planning model, not a combined-lifetime guarantee",
                        "Monitor windows/bias-valid/source protections must rerun at0.25/0.5%",
                        "Low-value0603 option requires a new actual footprint",
                    ],
                )
            else:
                family = "TNPW1206" if ref == "R97" else "TNPW0805"
                row.update(
                    MPN=family + rcode(value) + "BEEA",
                    family=family,
                    initial_fraction=0.001,
                    TCR_ppm_per_K=25,
                    holds=["Complete0.5/3% requires actual thermal/process/lifetime envelope"],
                )
                if ref in ["R6", "R7", "R13", "R14", "R70", "R87", "R72", "R89"]:
                    row["holds"] += [
                        "Gate/ramp pulse voltage, energy and repetition not bounded; steady power rating is insufficient proof"
                    ]
            row.update(FAMILIES[row["family"]])
            row["seat_requirement_mm"] = 0.1
            row["body_plus_seat_max_mm"] = row["body_max_mm"][2] + 0.1
            row["manufacturer_catalog_supported_order_code"] = True
            row["individual_product_record_confirmed"] = False
        rows.append(row)
    assert len(rows) == 196 and len({r["ref"] for r in rows}) == 196
    d = dict(
        revision="NP01-passive-selection-proposal",
        sources=dict(
            NF249="frozen NC01 copy", NF261="provisional pre-TPS3890 correction; passive audit only"
        ),
        rows=rows,
        selected_passive_refs=196,
        resistor_refs=97,
        capacitor_refs=99,
        all_parent_or_PCB_files_edited=False,
        catalog_order_codes_are_NOT_stock_or_factory_acceptance=True,
        body_plus_seat_is_RECEIVING_requirement_not_measurement=True,
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
        primary_sha256={str(p): sha(p) for p in (ROOT / "sources/primary").glob("*.pdf")},
        source_sha256={
            str(p): sha(p)
            for p in [
                Path(__file__),
                ROOT / "capture.json",
                ROOT / "sources/NF261/components.json",
                ROOT / "electrical-pin-erratum.json",
            ]
        },
    )
    (out / "selections.json").write_text(json.dumps(d, indent=2) + "\n")
    columns = [
        "ref",
        "old_part",
        "old_footprint",
        "MPN",
        "family",
        "body_plus_seat_max_mm",
        "initial_fraction",
        "TCR_ppm_per_K",
        "rated_V",
        "P70_W",
        "Umax_V",
        "source",
        "holds",
    ]
    with (out / "selections.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in row.items()})
    print(json.dumps(dict(passives=len(rows), resistors=97, capacitors=99, physical_qualified=False)))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Fresh output directory; all inputs are captured files")
    args = parser.parse_args()
    build(args.output)
