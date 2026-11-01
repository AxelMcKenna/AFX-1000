"""Conditional normal-start slew requirements for the four retained bipolar rails.

This is an unimplemented circuit study. A slow gate command is not assumed to
prove a load-voltage slew bound. Fault limiting, late bank closure and all
partial-power paths require separate native design and physical validation.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

from hardware.electronics.common.netlists import netlist, number
from hardware.electronics.common.sexpr import children, read_sexpr

REPO = Path(__file__).resolve().parents[3]
PSU = REPO / "hardware/electronics/power_distribution/p03"
DISCONNECT = REPO / "hardware/electronics/rail_disconnect/revision28"
OUT = REPO / "hardware/validation/board-qualification/generated/bipolar-slew"
PRIMARY = {
    "LM5069-1": {
        "url": "https://www.ti.com/lit/ds/symlink/lm5069.pdf",
        "revision": "SNVS452G, January2020, sections7.5/9; front-page dVdt circuit",
        "external_pdf_sha256": "d60d8106a6e8113900ff8b9576dd959942fa7169742baf0beeb30684d4d64681",
        "table_gate_source_interval_a": [10e-6, 22e-6],
        "reference_design_gate_source_planning_upper_a": 40e-6,
        "reference_design_source": "https://www.ti.com/lit/ug/tidues3/tidues3.pdf",
        "reference_design_section": "TIDA-010070, TIDUES3 December2019, section2.4.1.4 equation6; design value is not a new component guarantee",
        "table_conditions": "VIN48V unless noted; source current at GATE-OUT5V; actual12/19V full gate trajectory not established by this study",
    },
    "LM5067-1": {
        "url": "https://www.ti.com/lit/ds/symlink/lm5067.pdf",
        "revision": "SNVS532D, August2020, sections7.5/8.3/9",
        "external_pdf_sha256": "22ff73cee2c83f169155ded519adb19202d87c2b525d62cc6412df10d8377bc1",
        "table_gate_source_interval_a": [32e-6, 72e-6],
        "table_conditions": "ICC2mA/OUT48VaboveVEE unless noted; actual12/19V full gate trajectory not established by this study",
    },
}


def screen(voltage, capacitance, load, gate_current, ramp_capacitance, ceiling, shunt):
    """Ideal ramp scenario; every interval must be supplied explicitly in SI units."""
    for interval in (gate_current, ramp_capacitance, shunt):
        assert len(interval) == 2 and 0 < interval[0] <= interval[1]
    assert shunt[1] <= 0.1, "LM5067/69 shunt upper corner exceeds 100 milliohm"
    assert all(math.isfinite(x) and x >= 0 for x in (voltage, capacitance, load, ceiling))
    rates = [gate_current[0] / ramp_capacitance[1], gate_current[1] / ramp_capacitance[0]]
    charging = capacitance * rates[1]
    current = load + charging
    # For a linear voltage ramp with a constant live load, the pass device
    # dissipates both capacitor charging energy and VDS*Iload over the ramp.
    duration = voltage / rates[0]
    return dict(
        assumed_output_slew_interval_v_per_s=rates,
        assumed_effective_ramp_capacitance_interval_f=ramp_capacitance,
        net_gate_current_scenario_interval_a=gate_current,
        local_bulk_initial_tolerance_only_f=capacitance,
        external_load_plus_native_bleeds_a=load,
        local_bulk_charge_current_scenario_upper_a=charging,
        local_bulk_plus_live_load_current_scenario_upper_a=current,
        provisional_external_current_ceiling_a=ceiling,
        local_only_current_margin_a=ceiling - current,
        complete_downstream_capacitance_allowed_by_scenario_f=max(0, (ceiling - load) / rates[1]),
        remaining_capacitance_after_local_initial_tolerance_f=max(0, (ceiling - load) / rates[1])
        - capacitance,
        output_ramp_only_time_s=[voltage / rates[1], duration],
        capacitor_charge_energy_j=0.5 * capacitance * voltage**2,
        live_constant_load_pass_energy_at_slowest_ideal_ramp_j=0.5 * load * voltage * duration,
        ideal_ramp_initial_pass_power_scenario_w=voltage * current,
        shunt_resistance_interval_ohm=shunt,
        shunt_steady_drop_scenario_upper_v=load * shunt[1],
        overall_startup_time_bound_s=None,
        full_capacitance_and_current_bounds_verified=False,
        output_slew_network_implemented_or_verified=False,
        fault_pulse_soa_qualified=False,
        startup_qualified=False,
    )


def native_values_match(path, parts, references):
    tree = read_sexpr(path.read_text())
    values = {}
    for fp in children(tree, "footprint"):
        props = {row[1]: row[2] for row in children(fp, "property")}
        if props.get("Reference") in references:
            values[props["Reference"]] = props.get("Value")
    assert set(values) == set(references)
    for ref, value in values.items():
        assert value == parts[ref].findtext("value"), (ref, "Native PCB/netlist value mismatch")


def native_parts_pins(path):
    values, pins = {}, {}
    for fp in children(read_sexpr(path.read_text()), "footprint"):
        props = {row[1]: row[2] for row in children(fp, "property")}
        ref = props["Reference"]
        values[ref] = props["Value"]
        pins[ref] = {}
        for pad in children(fp, "pad"):
            nets = children(pad, "net")
            if nets:
                net = nets[0]
                name = str(net[2]).removeprefix("/")
                pin = str(pad[1])
                if pin in pins[ref]:
                    assert pins[ref][pin] == name, (ref, pin, "Multiple pad nets")
                pins[ref][pin] = name
    return values, pins


def generate():
    from hardware.electronics.power_distribution.p03.bipolar import ledger

    paths = [
        PSU / "power_p03.kicad_pcb",
        PSU / "generated/netlist.xml",
        DISCONNECT / "rail_disconnect.kicad_pcb",
    ]
    # Record all actually imported project helpers, including the source-current
    # model. Dependencies are captured before reading mutable native inputs.
    for module in list(sys.modules.values()):
        file = getattr(module, "__file__", None)
        if file and Path(file).resolve().is_relative_to(REPO / "hardware"):
            paths.append(Path(file).resolve())
    paths = sorted(set(paths))
    inputs = {path: path.read_bytes() for path in paths}
    source_parts, _ = netlist(PSU / "generated/netlist.xml")
    parts, pins = native_parts_pins(DISCONNECT / "rail_disconnect.kicad_pcb")
    cap_refs = {"P19": "C4", "N19": "C8", "P12": "C12", "N12": "C16"}
    source_refs = {
        "R20",
        "R21",
        "R22",
        "R24",
        "R25",
        "R26",
        "R27",
        "R29",
        "R34",
        "R35",
        "R36",
        "R38",
        "R39",
        "R40",
        "R41",
        "R43",
    }
    native_values_match(PSU / "power_p03.kicad_pcb", source_parts, source_refs)
    source = ledger(source_parts)
    rows = {}
    # Extra2uA is an unverified leakage/injection allowance. Bounds at the
    # actual12/19V operating points still require manufacturer/application proof.
    for rail, cap_nominal, ceiling in [
        ("P19", 4.7e-6, 0.050),
        ("N19", 1.5e-6, 0.150),
        ("P12", 0.68e-6, 0.210),
        ("N12", 1e-6, 0.220),
    ]:
        cap = cap_refs[rail]
        assert set(pins[cap].values()) == {"AGND", rail}
        cnom = number(parts[cap])
        assert "20%" in parts[cap]
        voltage = source["rails"][rail]["source_magnitude_v"][1]
        bleeds = [ref for ref in parts if ref.startswith("R") and set(pins[ref].values()) == {"AGND", rail}]
        bleed = sum(voltage / (number(parts[ref]) * 0.97) for ref in bleeds)
        load = source["rails"][rail]["external_current_allocation_a"] + bleed
        controller = "LM5067-1" if rail.startswith("N") else "LM5069-1"
        gate_spec = PRIMARY[controller]["table_gate_source_interval_a"]
        planning_upper = max(
            gate_spec[1],
            PRIMARY[controller].get("reference_design_gate_source_planning_upper_a", gate_spec[1]),
        )
        gate = [gate_spec[0] - 2e-6, planning_upper + 2e-6]
        row = screen(
            voltage,
            cnom * 1.2,
            load,
            gate,
            [cap_nominal * 0.9, cap_nominal * 1.1],
            ceiling,
            [0.0909 * 0.98, 0.0909 * 1.02],
        )
        row.update(
            protected_bulk_ref=cap,
            native_bulk_value=parts[cap],
            native_ground_bleed_refs=bleeds,
            native_ground_bleed_current_scenario_a=bleed,
            candidate_controller=controller,
            controller_table_conditions=PRIMARY[controller]["table_conditions"],
            controller_gate_source_current_table_interval_a=gate_spec,
            gate_source_planning_upper_before_extra_allowance_a=planning_upper,
            additional_unverified_gate_current_allowance_a=2e-6,
            ramp_capacitor_exact_mpn_selected=False,
            new_controller_current_is_not_in_downstream_load=True,
            new_controller_input_current_reserve_in_source_model_a=source["rails"][rail][
                "new_controller_source_current_reserved_a"
            ],
            complete_input_power_and_source_good_waveforms_verified=False,
        )
        rows[rail] = row
    hashes = {str(path.relative_to(REPO)): hashlib.sha256(data).hexdigest() for path, data in inputs.items()}
    key = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:16]
    output = OUT / key
    output.mkdir(parents=True, exist_ok=True)
    frozen = {}
    for path, data in inputs.items():
        target = output / "inputs" / path.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        frozen[str(target.relative_to(REPO))] = hashes[str(path.relative_to(REPO))]
    report = dict(
        scope="Unimplemented normal-ramp alternative with supported small shunts; not low-current fault-limit selection",
        source_sha256=hashes,
        frozen_input_sha256=frozen,
        rail_scenarios=rows,
        primary_sources={
            "LM5069": "https://www.ti.com/lit/ds/symlink/lm5069.pdf",
            "LM5067": "https://www.ti.com/lit/ds/symlink/lm5067.pdf",
            "LTC4218": "https://www.analog.com/media/en/technical-documentation/data-sheets/4218fh.pdf",
            "LTC4252A": "https://www.analog.com/media/en/technical-documentation/data-sheets/425212fe.pdf",
            "LM5069_reference_ramp_design": "https://www.ti.com/lit/ug/tidues3/tidues3.pdf",
        },
        controller_table_provenance=PRIMARY,
        constraints=[
            "No change to native circuits is made by this analysis",
            "Actual output slew must be bounded by a stable feedback/ramp network, not merely a slow gate waveform",
            "LM5069 datasheet front-page Q2/diode/Cdvdt network is a starting circuit; its transfer and negative counterpart remain to be designed",
            "The5V-gate-difference table's22uA upper value is not a full startup-trajectory bound: TI TIDA-010070 uses40uA for ramp design, now the stronger positive planning value before2uA extra allowance",
            "A late retained-bank closure after a charged limiter defeats the ramp: hard-off bank must precede limiter, or its ON state must be proved before enabling an upstream limiter",
            "Moving the limiter after the bank requires explicit charged-load/reverse/partial-power and isolated-negative enable/PG analysis",
            "The chosen91mohm nominal shunt plus2percent allocation stays below100mohm; no oversized-shunt exception is used",
            "Large fault currents may cause source shutdown; precision source regulation during faults is not assumed",
            "N19 provisional150mA ramp ceiling increases the old50mA phase; raw-source hot capacity, transient heat, and total input chain must be recomputed",
            "Local bulk plus initial20percent tolerance does not bound the complete downstream capacitance",
            "A slowed live-load ramp increases pass-device energy; capacitor energy alone cannot prove SOA",
            "LTC4252A TIMER voltage/current/acceleration entries are typical-only; no guaranteed timeout is inferred",
            "LTC4218 output-derived FB folds back strongly at zero output; full constant load cannot be omitted or FB defeat silently assumed",
        ],
        native_repair_implemented=False,
        manufacturer_application_bounds_complete=False,
        physical_tests_performed=0,
        fabrication_released=False,
        build_ready=False,
    )
    assert all(path.read_bytes() == data for path, data in inputs.items()), (
        "Native/model inputs changed during capture"
    )
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(output)
    return report


if __name__ == "__main__":
    generate()
