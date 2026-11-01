"""Source-bound gate/energy screens; no waveform or physical test is inferred."""

import argparse
import hashlib
import json
from pathlib import Path

from ...common.netlists import netlist
from ...common.sexpr import children, first, read_sexpr
from ..verify import contract

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
SOURCES = {
    "driver": {
        "url": "https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/Si8751-2.pdf",
        "revision": "206331A, 27 July 2022",
        "pages": [6, 8, 9],
        "facts": {
            "gate_test_load_f": 100e-12,
            "tt_10k_gate_min_v": 9,
            "tt_10k_gate_max_v": 13,
            "tt_10k_on_impedance_max_ohm": 370000,
            "tt_10k_supply_max_a": 0.0095,
            "off_time_test_max_s": 35e-6,
            "miller_input_max_a": 0.006,
        },
    },
    "digital_fet": {
        "url": "https://www.ti.com/lit/ds/symlink/csd18510q5b.pdf",
        "revision": "SLPS632, March 2017",
        "pages": [1, 3, 6, 8, 9],
        "facts": {
            "qg_10v_max_c": 153e-9,
            "qg_test_vds_v": 20,
            "qg_test_current_a": 32,
            "vds_max_v": 40,
            "vgs_abs_max_v": 20,
            "rds_4v5_25c_max_ohm": 0.0016,
            "igss_25c_max_a": 100e-9,
        },
    },
    "bipolar_fet": {
        "url": "https://www.ti.com/lit/ds/symlink/csd18540q5b.pdf",
        "revision": "SLPS488B, April 2017",
        "pages": [1, 3, 6, 8, 9],
        "facts": {
            "qg_10v_max_c": 53e-9,
            "qg_test_vds_v": 30,
            "qg_test_current_a": 28,
            "vds_max_v": 60,
            "vgs_abs_max_v": 20,
            "rds_4v5_25c_max_ohm": 0.0033,
            "igss_25c_max_a": 100e-9,
        },
    },
}


def charge_screen(capacitance_f, voltage_v, ramp_s):
    assert capacitance_f > 0 and voltage_v > 0 and ramp_s > 0
    return dict(
        capacitor_energy_j=0.5 * capacitance_f * voltage_v**2,
        ideal_average_charging_a=capacitance_f * voltage_v / ramp_s,
        hypothetical_linear_ramp_s=ramp_s,
        peak_current_bounded=False,
        mosfet_soa_qualified=False,
    )


def gate_screen(devices, charge_max, leakage_allocation):
    assert devices > 0 and charge_max > 0 and leakage_allocation >= 0
    minimum = (9 - 370000 * leakage_allocation) / (1 + 370000 / 20e6)
    return dict(
        devices=devices,
        charge_at_manufacturer_test_c=devices * charge_max,
        equivalent_10v_capacitance_f=devices * charge_max / 10,
        test_load_scale=devices * charge_max / (100e-12 * 10),
        minimum_loaded_gate_v_with_allocations=minimum,
        hot_leakage_allocation_a=leakage_allocation,
        leakage_temperature_allocation_guaranteed=False,
        actual_turnon_or_turnoff_bound_s=None,
        manufacturer_100pf_timing_applies=False,
    )


def analyze():
    parts, pins = netlist(PARENT / "revision26/generated/netlist.xml")
    contract(parts, pins)
    for ref in ("Q9", "Q10", "Q11", "Q12", "Q13", "Q14"):
        assert parts[ref].findtext("value") == "CSD18510Q5B"
    assert pins["Q11"]["3"] == pins["Q13"]["3"] == "5V_DIG_SRC"
    assert pins["Q12"]["3"] == pins["Q14"]["3"] == "5V_DIG"
    assert (
        pins["R42"] == {"1": "5V_DIG_GATE", "2": "5V_DIG_COMMON"}
        and parts["R42"].findtext("value") == "20M 1%"
    )
    tree = read_sexpr((ROOT / "rail_disconnect.kicad_pcb").read_text())
    lands = []
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref.startswith("Q"):
            small = [
                tuple(map(float, first(p, "size")[1:3])) for p in children(fp, "pad") if p[1] in ("1", "2")
            ]
            lands.append(
                dict(
                    ref=ref,
                    source_and_gate_lands_mm=small,
                    recommended_source_gate_lands_mm=[1.1, 0.71],
                    recommended_pattern_matched=all(
                        abs(w - 1.1) < 1e-6 and abs(h - 0.71) < 1e-6 for w, h in small
                    ),
                    alternate_manufacturer_or_assembly_approval_present=False,
                )
            )
    rows = {
        "bipolar_pair": gate_screen(2, 53e-9, 2e-6),
        "analog_5v_pair": gate_screen(2, 153e-9, 2e-6),
        "digital_four": gate_screen(4, 153e-9, 4e-6),
    }
    # These are existing 1ms hypothetical ramp comparisons, not selected bounds.
    digital = charge_screen(0.0047 * 1.2, 5.1, 0.001)
    analog = charge_screen(0.0015 * 1.2, 5.025, 0.001)
    return dict(
        revision="E27-device-review",
        sources=SOURCES,
        original_164_pin_value_contract_passed=True,
        mosfet_land_review=lands,
        gate_load_screens=rows,
        board_local_bulk={"digital": digital, "analog": analog},
        downstream_capacitors_included_in_local_energy=False,
        ov_only=True,
        undervoltage_interlock=False,
        fault_latch_on_this_board=False,
        independent_current_limit_on_this_board=False,
        protected_bulk_rapid_discharge=False,
        body_diode_orientation_does_not_prove_signal_pin_backfeed_isolation=True,
        return_strap_attachments_implemented=False,
        manufacturer_soa_plot_is_not_avalanche_energy_rating=True,
        scope="Manufacturer table and native netlist consistency; hypothetical energy/current comparisons only",
        physical_fault_or_startup_verified=False,
        thermal_qualified=False,
        build_ready=False,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    report = analyze()
    repo = ROOT.parents[3]
    files = [
        Path(__file__),
        PARENT / "verify.py",
        PARENT / "components.json",
        PARENT / "rail_disconnect.kicad_sch",
        PARENT / "revision26/generated/netlist.xml",
        ROOT / "rail_disconnect.kicad_pcb",
    ]
    report["source_sha256"] = {
        str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
    }
    content = json.dumps(report, indent=2) + "\n"
    output = ROOT / "generated/device-review.json"
    if args.check:
        assert output.read_text() == content, "Stale device review"
    else:
        output.write_text(content)
    print(
        "Actual digital gate-load table comparison:",
        report["gate_load_screens"]["digital_four"]["test_load_scale"],
        "times 100pF test charge; no system timing/SOA qualification",
    )


if __name__ == "__main__":
    main()
