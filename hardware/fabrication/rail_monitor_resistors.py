"""Source-bound E13 resistor candidates; never a released procurement BOM."""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

REPO = Path(__file__).resolve().parents[2]
COMPONENTS = Path("hardware/electronics/rail_monitor/components.json")
BOARD = Path(
    "hardware/fabrication/staging/rail-monitor-reserved-closed-native-02/rail_monitor.kicad_pcb"
)
SOURCES = {
    "PLT": {
        "url": "https://www.vishay.com/docs/60030/plt.pdf",
        "revision": "11-May-2026, document 60030, pages 1-2",
        "document_sha256": "67a3288cc599e975ea20e403f26cafb14ab488e8c2d13dec757ccdf13a52607f",
        "limits": "0805 100..260000 ohm; 0.01% only above 250 ohm; 5 ppm/C",
    },
    "CRT": {
        "url": "https://www.bourns.com/docs/product-datasheets/crt.pdf",
        "revision": "01C; pages 1-2; retrieved 2026-11-01",
        "document_sha256": "094e3bd73684274232f29cce9861062555f18e8316d0c974fe295f4adee46457",
        "limits": "0805 24.9..30000 ohm at 0.01%, 2 ppm/C",
    },
    "HVC": {
        "url": "https://www.ohmite.com/assets/images/res-hvc.pdf?r=false",
        "revision": "6/20-3, pages 1-2; retrieved 2026-11-01",
        "document_sha256": "ef1991b39fc58c8fc37270b282d584f6fb7fe184751477ae1257736fc35da22d",
        "limits": "0805 includes 20 Mohm, 1%, 50 ppm/C; combinations need confirmation",
    },
    "CRCW": {
        "url": "https://www.vishay.com/docs/20035/dcrcwe3.pdf",
        "revision": "14-Apr-2026, document 20035, pages 1-3",
        "document_sha256": "d3b4c334e24f2de719c30979f24ca25d2d77d813f8f02603614e0b68ee5efd4c",
        "limits": "0805 includes 10k/100k/330k at 1%, 100 ppm/C; EA reel packaging",
    },
}


def ohms(value):
    token = value.split()[0]
    multipliers = {"k": 1000, "M": 1000000}
    return Decimal(token[:-1]) * multipliers[token[-1]] if token[-1] in multipliers else Decimal(token)


def four_digit(value):
    """Three significant digits and a nonnegative decimal multiplier."""
    value = Decimal(value)
    for exponent in range(10):
        significant = value / (Decimal(10) ** exponent)
        if significant == significant.to_integral() and 100 <= significant <= 999:
            return f"{int(significant):03d}{exponent}"
    raise ValueError(f"Not exactly representable by this ordering code: {value}")


def precision_candidate(value):
    value = Decimal(value)
    if 250 < value <= 260000:
        return "PLT", f"PLT0805Z{four_digit(value)}LSTS", 5
    if Decimal("24.9") <= value <= 30000:
        return "CRT", f"CRT0805-PT-{four_digit(value)}ELF", 2
    raise ValueError(f"No reviewed candidate for {value} ohm")


def shunted_minimum(nominal, intrinsic_error, parallel_ohm):
    """Lowest effective resistance for a bounded part and passive shunt."""
    if nominal <= 0 or not 0 <= intrinsic_error < 1 or parallel_ohm <= 0:
        raise ValueError("Require positive resistances and a fractional error below one")
    minimum = nominal * (1 - intrinsic_error)
    return minimum / (1 + minimum / parallel_ohm)


def combined_error(*bounds):
    """Symmetric enclosure retaining products of fractional drift limits."""
    upper = Decimal(1)
    for bound in bounds:
        bound = Decimal(str(bound))
        if not 0 <= bound < 1:
            raise ValueError("Fractional bounds must be nonnegative and below one")
        upper *= 1 + bound
    return upper - 1


def ordinary_logic_screen(error=0.05, receiver_error=0.05):
    """Check a proposed drift envelope against the existing E13 DC limits."""
    if not 0 <= error < 1 or not 0 <= receiver_error < 1:
        raise ValueError("Require fractional resistor errors below one")
    load = 5e-6 + 1e-6 + 3.55 / (20e6 * 0.95)
    high_min = 3.135 - load * 10000 * (1 + error)
    high_max = 3.465 + load * 10000 * (1 + error)
    low_sink = 3.465 / (10000 * (1 - error)) + 3.55 / (20e6 * 0.95)
    final_load = 3.465 / (47000 * (1 - receiver_error)) + 3.465 / (330000 * (1 - error)) + 1e-6
    return {
        "proposed_ordinary_total_error": error,
        "conditional_E09_47k_total_error": receiver_error,
        "comparator_high_min_v": high_min,
        "comparator_high_max_v": high_max,
        "comparator_low_sink_a": low_sink,
        "final_output_load_a": final_load,
        "inside_existing_DC_enclosure": high_min > 3.04 and high_max < 3.55 and low_sink < 0.004 and final_load < 100e-6,
        "timer_mode_process_and_lifetime_qualified": False,
    }


def build(repo=REPO):
    components = json.loads((repo / COMPONENTS).read_text())
    resistors = [c for c in components if c["ref"].startswith("R")]
    board = read_sexpr((repo / BOARD).read_text())
    footprints = {}
    for footprint in children(board, "footprint"):
        properties = {p[1]: p[2] for p in children(footprint, "property")}
        footprints[properties.get("Reference")] = (footprint, properties)
    rows = []
    for component in resistors:
        ref = component["ref"]
        footprint, properties = footprints[ref]
        if properties["Value"] != component["part"] or footprint[1] != component["footprint"]:
            raise ValueError(f"PCB/source identity changed at {ref}")
        pads = {p[1]: p for p in children(footprint, "pad")}
        for pin in component["pins"]:
            actual = first(pads[pin["number"]], "net")[-1].removeprefix("/")
            if actual != pin["net"]:
                raise ValueError(f"PCB/source net changed at {ref}.{pin['number']}")
        family, code, tcr = "", "", None
        if "0.01%" in component["part"]:
            group = "precision"
            family, code, tcr = precision_candidate(ohms(component["part"]))
        elif component["part"] == "20M 1%":
            group, family, code, tcr = "feedback", "HVC", "HVC0805V2005FET", 50
        else:
            ordinary = {
                "10k 1%": "CRCW080510K0FKEA",
                "100k 1%": "CRCW0805100KFKEA",
                "330k 1%": "CRCW0805330KFKEA",
            }
            group, family, code, tcr = "ordinary", "CRCW", ordinary[component["part"]], 100
        rows.append({
            "ref": ref, "source_value": component["part"],
            "nominal_ohm": int(ohms(component["part"])), "group": group,
            "family": family, "candidate_order_code": code,
            "tcr_ppm_per_c": tcr, "order_code_status": "derived_from_manufacturer_syntax" if code else "unselected",
            "catalog_or_supplier_confirmation": False,
            "installed_error_budget_qualified": False,
        })
    r83, _ = footprints["R83"]
    if footprints["R83"][1]["Value"] != "127 0.01% 5ppm":
        raise ValueError("Re-evaluate the R83-specific budget before accepting a changed value")
    pad_geometry = [{
        "number": p[1], "at_mm": list(map(float, first(p, "at")[1:3])),
        "size_mm": list(map(float, first(p, "size")[1:3])),
    } for p in children(r83, "pad")]
    left, right = sorted(pad_geometry, key=lambda p: p["at_mm"][0])
    inner_gap = right["at_mm"][0] - right["size_mm"][0] / 2 - left["at_mm"][0] - left["size_mm"][0] / 2
    delta_c = Decimal(100)  # 25 C nominal to -55..125 C body-temperature envelope.
    plt_error = combined_error("0.0001", Decimal("0.000005") * delta_c, "0.0002", "0.0001")
    r83_error = combined_error("0.0001", Decimal("0.000002") * delta_c, "0.0005", "0.0005")
    screened_r83_error = combined_error("0.0002", Decimal("0.000002") * delta_c, "0.0005")
    report = {
        "schema": "E13-resistor-candidates-1",
        "source_sha256": {
            str(p): hashlib.sha256((repo / p).read_bytes()).hexdigest()
            for p in (COMPONENTS, BOARD, Path("hardware/electronics/rail_monitor/analyze.py"))
        },
        "manufacturer_sources": SOURCES,
        "counts": dict(Counter(r["group"] for r in rows)),
        "parts": rows,
        "conditional_budget_screens": {
            "body_temperature_c": [-55, 125],
            "temperature_envelope_is_product_requirement": False,
            "precision_total_error_limit": 0.001,
            "PLT_combined_initial_TCR_2000h70C_one_year25C": float(plt_error),
            "PLT_remaining_fractional_error_limit": float((1 + Decimal("0.001")) / (1 + plt_error) - 1),
            "R83_combined_initial_TCR_solder_heat_1000h_load_life": float(r83_error),
            "R83_unscreened_bound_fits": False,
            "R83_post_reflow_acceptance_including_measurement_uncertainty": 0.0002,
            "R83_combined_post_reflow_TCR_1000h_load_life": float(screened_r83_error),
            "feedback_intrinsic_error_requirement": 0.04,
            "feedback_parallel_resistance_requirement_ohm": 2000000000,
            "feedback_minimum_effective_ohm": shunted_minimum(20000000, 0.04, 2000000000),
            "feedback_maximum_intrinsic_ohm": 20800000,
            "feedback_total_limit": 0.05,
            "ordinary_combined_initial_TCR_1000h_standard_mode": float(combined_error("0.01", "0.01", "0.01")),
            "ordinary_timing_and_logic_over_full_error_qualified": False,
            "feedback_model_scope": "one passive parallel leakage path only; other-node leakage and input bias remain separate",
            "mission_lifetime_and_combined_stresses_qualified": False,
        },
        "R83_land_comparison": {
            "actual_pads": pad_geometry,
            "actual_inner_gap_mm": round(inner_gap, 9),
            "CRT_recommended_inner_gap_mm": 1.0,
            "CRT_recommended_pad_size_mm": [1.0, 1.35],
            "existing_land_matches_manufacturer_recommendation": False,
            "assembly_process_accepted": False,
        },
        "ordinary_logic_screen": ordinary_logic_screen(),
        "procurement_BOM_released": False,
        "electrical_qualified": False,
        "fabrication_approved": False,
    }
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["references", "quantity_per_unit", "source_value", "family", "candidate_order_code", "status"])
    groups = {}
    for row in rows:
        key = (row["source_value"], row["family"], row["candidate_order_code"], row["order_code_status"])
        groups.setdefault(key, []).append(row["ref"])
    for (value, family, code, status), refs in groups.items():
        writer.writerow([" ".join(refs), len(refs), value, family, code, status])
    return report, stream.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report, table = build()
    files = {"candidates.json": json.dumps(report, indent=2) + "\n", "candidates.csv": table}
    if args.check:
        for name, content in files.items():
            if (args.output / name).read_text() != content:
                raise SystemExit(f"Stale candidate evidence: {name}")
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, content in files.items():
            (args.output / name).write_text(content)
    print(json.dumps({"counts": report["counts"], "fabrication_approved": False}))


if __name__ == "__main__":
    main()
