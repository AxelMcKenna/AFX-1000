"""Actual LED/Seed power roles and allocation provenance, no reduced load promises."""

import ast
import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.netlists import netlist, number
from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources/repository"
OUT = ROOT / "generated"


def read(path):
    return json.loads(path.read_text())


def arithmetic(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (float, int)):
        return float(node.value)
    if isinstance(node, ast.BinOp):
        left, right = arithmetic(node.left), arithmetic(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
    raise ValueError("Not a literal arithmetic allocation")


def captured_board(folder, tag):
    base = SOURCES / "hardware/electronics" / folder
    parts, pins = netlist(OUT / (tag + "-netlist.xml"))
    metadata = {p["ref"]: p for p in read(base / "components.json")}
    assert set(parts) == set(metadata), "Native/BOM part-count mismatch"
    for ref, m in metadata.items():
        assert parts[ref].findtext("value") == m["part"], "Native/BOM selected value disagreement"
        for pin in m["pins"]:
            if pin["net"] is not None:
                assert pins[ref][pin["number"]] == pin["net"], "Native/BOM power or signal disagreement"
    filename = "led_driver" if tag == "E20" else "processor_carrier"
    tree = read_sexpr((base / (filename + ".kicad_pcb")).read_text())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net") if len(n) > 2}
    fp = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    pcbpins = {}
    for ref, f in fp.items():
        pcbpins[ref] = {}
        for pad in children(f, "pad"):
            if str(pad[1]) and children(pad, "net"):
                raw = str(first(pad, "net")[1])
                pcbpins[ref][str(pad[1])] = names.get(raw, raw.lstrip("/"))
    return parts, pins, metadata, pcbpins


def role_errors(led, carrier):
    errors = []
    for name, pins in [("exported", led[1]), ("PCB", led[3])]:
        if any(pins[f"U{i}"]["32"] != "5V_DIG" for i in range(1, 5)):
            errors.append(name + ": TLC supply domain changed")
        if any(
            pins[f"U{i}"][str(5 + n)] != f"LED_{(i - 1) * 24 + n:02d}" for i in range(1, 5) for n in range(24)
        ):
            errors.append(name + ": sink count/order changed")
        if any(pins[f"J{j}"][n] != "5V_DIG" for j in range(2, 6) for n in ["25", "26"]):
            errors.append(name + ": LED anode source changed")
        if pins["U5"]["1"] != "V3V3_IO" or pins["U5"]["23"] != "5V_DIG" or pins["U5"]["24"] != "5V_DIG":
            errors.append(name + ": translator power-domain mismatch")
    for name, pins in [("exported", carrier[1]), ("PCB", carrier[3])]:
        if pins["R1"] != {"1": "5V_DIG", "2": "SEED_VIN"} or pins["U1"]["39"] != "SEED_VIN":
            errors.append(name + ": Seed input path changed")
        if pins["J11"]["2"] != "5V_DIG" or pins["J11"]["3"] != "V3V3_IO":
            errors.append(name + ": LED branch is not the declared upstream5V/Seed3V3 pair")
        if pins["U1"]["21"] != "V3V3_ANALOG" or pins["U1"]["38"] != "V3V3_IO":
            errors.append(name + ": Seed output-only domains changed")
    return errors


def ICC4_conditions_match(actual):
    return (
        actual["RIREF_ohm"] == 1600
        and actual["BLANK"] == 0
        and actual["VOUT_v"] == 1
        and actual["GSn"] == "FFFh"
        and actual["SIN_SCLK_XLAT"] == 0
        and 3 <= actual["VCC_v"] <= 5.5
        and -40 <= actual["TA_c"] <= 85
    )


def provenance():
    led = ast.parse((SOURCES / "hardware/electronics/led_driver/verify.py").read_text())
    allocated = next(
        n.value
        for n in ast.walk(led)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "allocated" for t in n.targets)
    )
    e14 = ast.parse((SOURCES / "hardware/electronics/power_supply/verify.py").read_text())
    digital = next(
        n.value
        for n in ast.walk(e14)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "digital" for t in n.targets)
        and isinstance(n.value, ast.Call)
        and any(k.arg == "seed_and_its_3v3_load_allocation_a" for k in n.value.keywords)
    )
    old = {k.arg: arithmetic(k.value) for k in digital.keywords}
    p02 = ast.parse((SOURCES / "hardware/electronics/power_distribution/p02/distribution.py").read_text())
    loads = next(
        n.value
        for n in ast.walk(p02)
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "LOADS" for t in n.targets)
    )
    seed = next(
        arithmetic(v.elts[2])
        for k, v in zip(loads.keys, loads.values)
        if isinstance(k, ast.Constant) and k.value == "seed_local"
    )
    e19 = ast.parse((SOURCES / "hardware/electronics/processor_carrier/verify.py").read_text())
    screen = next(n for n in e19.body if isinstance(n, ast.FunctionDef) and n.name == "passive_screen")
    check = next(
        arithmetic(n.value)
        for n in screen.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "load" for t in n.targets)
    )
    return dict(
        led_driver_total_from_actual_screen_a=arithmetic(allocated),
        old_E14_digital_terms_a=old,
        E14_seed_and_its_3v3_allocation_a=old["seed_and_its_3v3_load_allocation_a"],
        P02_seed_allocation_a=seed,
        E19_passive_filter_screen_assumption_a=check,
        any_is_a_measured_or_vendor_module_current_bound=False,
    )


def analyze():
    led = captured_board("led_driver", "E20")
    carrier = captured_board("processor_carrier", "E19")
    assert not role_errors(led, carrier)
    facts = read(ROOT / "sources/primary-facts.json")
    for f in facts.values():
        assert sha(ROOT / "sources/primary" / f["pdf"]) == f["local_pdf_sha256"]
    assert len(led[0]) == 49 and len(carrier[0]) == 76
    rrefs = [number(led[0][f"R{i}"].findtext("value")) for i in range(1, 5)]
    assert rrefs == [16500] * 4
    nominal = 41 * 1.20 / rrefs[0]
    actual = dict(RIREF_ohm=rrefs[0], BLANK=0, VOUT_v=1, GSn="FFFh", SIN_SCLK_XLAT=0, VCC_v=5, TA_c=40)
    sources = []
    for board, data in [("E20", led[2]), ("E19", carrier[2])]:
        for ref, m in data.items():
            if ref.startswith("J"):
                continue
            direct = [
                dict(pin=p["number"], role=p["kind"], net=p["net"])
                for p in m["pins"]
                if p["net"] in {"V3V3_IO", "V3V3_ANALOG"}
            ]
            if direct:
                sources.append(dict(board=board, ref=ref, part=m["part"], pins=direct))
    for name in ["converter", "control_inputs", "rail_monitor"]:
        for m in read(SOURCES / "hardware/electronics" / name / "components.json"):
            direct = [
                dict(pin=p["number"], role=p["kind"], net=p["net"])
                for p in m["pins"]
                if p["net"] in {"V3V3_IO", "V3V3_ANALOG"}
            ]
            if direct and not m["ref"].startswith("J"):
                sources.append(dict(board=name, ref=m["ref"], part=m["part"], pins=direct))
    # Direct-rail pullups and driven-domain pulldowns only. IREF paths are already insideTLCICC.
    static = []
    driven = {
        "DATA_5V": "5V_DIG",
        "CLOCK_5V": "5V_DIG",
        "LATCH_5V": "5V_DIG",
        "BLANK_5V": "5V_DIG",
        "PG_5V": "5V_DIG",
        "LED_MOSI": "V3V3_IO",
        "LED_SCK": "V3V3_IO",
        "LED_XLAT": "V3V3_IO",
        "LED_BLANK": "V3V3_IO",
        "PG_3V3": "V3V3_IO",
        "OE_N": "V3V3_IO",
    }
    for ref, m in led[2].items():
        if not ref.startswith("R") or ref in {"R1", "R2", "R3", "R4"}:
            continue
        nets = {p["net"] for p in m["pins"]}
        domain = next((r for r in ["5V_DIG", "V3V3_IO"] if r in nets), None)
        if domain is None and "AGND" in nets:
            domain = next((driven[n] for n in nets if n in driven), None)
        if domain:
            voltage = 5.1 if domain == "5V_DIG" else 3.3
            resistance = number(m["part"])
            static.append(
                dict(
                    ref=ref,
                    domain=domain,
                    voltage_assumed_v=voltage,
                    nominal_ohm=resistance,
                    initial_resistor_tolerance=0.01,
                    independent_full_voltage_current_a=voltage / (resistance * 0.99),
                    actually_simultaneous=False,
                    hot_lifetime_resistance_guaranteed=False,
                )
            )
    p = provenance()
    assert math.isclose(p["led_driver_total_from_actual_screen_a"], 0.764)
    assert p["P02_seed_allocation_a"] == 1
    assert "BaudPrescaler::PS_64" in (SOURCES / "hardware/firmware/BoardIO.h").read_text()
    report = dict(
        revision="PA01-actual-LED-Seed-power-provenance",
        native_contract_errors=[],
        native_component_counts=dict(E20=49, E19=76),
        native_export_is_power_pin_evidence_not_ERC_DRC=True,
        actual_LED_power_roles=dict(
            VCCpin32_all_four="5V_DIG",
            LED_anode_supply="5V_DIG",
            sink_count=96,
            translator_VCCA="V3V3_IO",
            translator_VCCB="5V_DIG",
            carrier_J11_5v_bypasses_Seed_R1=True,
            LED_5v_is_separate_from_Seed_input_current=True,
        ),
        provenance=p,
        retained_current_allocations_a=dict(
            LED_ICC_four=0.360,
            LED_misc_unpartitioned=0.020,
            LED_logic_label=0.380,
            LED_sink_each=0.004,
            LED_sink_24_each_group=0.096,
            LED_sink96=0.384,
            LED_5v_total=0.764,
            Seed_parent5v=1.0,
        ),
        actual_RIREF_ohm=rrefs,
        nominal_sink_a=nominal,
        nominal_all96_a=nominal * 96,
        sink4mA_allocation_is_manufacturer_guaranteed_at_actual_setting=False,
        nominal_resistor_only_1percent_current_sensitivity_a=[
            41 * 1.2 / (16500 * 1.01),
            41 * 1.2 / (16500 * 0.99),
        ],
        ICC90mA_is_a_manufacturer_maximum_at_named_test_row=True,
        actual_setting_matches_that_row=ICC4_conditions_match(actual),
        actual_LED_all_state_ICC_upper_a=None,
        actual_3v3_child_pins=sources,
        E20_resistive_normal_state_requirements=static,
        E20_resistive_5v_independent_subtotal_a=sum(
            r["independent_full_voltage_current_a"] for r in static if r["domain"] == "5V_DIG"
        ),
        E20_resistive_3v3_independent_subtotal_a=sum(
            r["independent_full_voltage_current_a"] for r in static if r["domain"] == "V3V3_IO"
        ),
        E20_misc20mA_verified_against_all_components_states=False,
        internal_IREF_resistors_added_to_ICC_again=False,
        partially_omitted_child_names_from_P02_75mA_diagnostic=[
            "E20translatorVCCA/U6/pulls",
            "TrillCraft",
            "AS5600sensor",
            "SDcard",
            "E19analogpotexcitation",
            "E19localpulls/GPIOdrive",
        ],
        missing_child_names_are_proof_Seed1A_envelope_exceeded=False,
        module_input_max_current_from_reviewed_primary_a=None,
        module_3v3_output_max_current_from_reviewed_primary_a=None,
        analog_pot_declared3v3_10x8kohm_current_a=10 * 3.3 / 8000,
        resistor1_at_1A_initial1percent_drop_v=0.47 * 1.01,
        resistor1_at_1A_initial1percent_power_w=0.47 * 1.01,
        filter0v5A_screen_is_1A_validation=False,
        actual_SPI_prescaler="PS_64",
        actual_SPI_clock_upper_hz=None,
        no_actual_LED_supply_sink_double_count_detected=True,
        no_reserves_removed=True,
        whole_unit_35v4315_heat_target_revised=False,
        actual_power_qualified=False,
        physical_tests_performed=0,
        unresolved=[
            "TI90mAICC4 appliesR1.6k/staticlowserialinputs/fullGS/VOUT1V; actual16.5k/current/dynamicloads do not match. No guarantee or downward rescaling inferred",
            "4mA sink is engineeringceiling; selected16.5k nominal formula and30mA accuracy/VIREFtest rows do not prove a hot low-currentmaximum",
            "20mA misc is unpartitioned reserve across a mixed3v3/5V board, not measured component sum or proof of cross-pool duplication",
            "Seed1A,older.6A andcarrier.5A are differentprojectassumptions; USBdefault500mA configuration is not a measured/currentcapacitybound",
            "Seed3V3/SD/sensor/translator/control/analogpot childinventory and regulatorcapacity/efficiency/loadsteps remain open; no childpower is added twice to fullSeedinput",
            "ActualfirmwareSPIsourceclock/loading/edgepatterns and allblank/fault/brownout states remain unmeasured",
        ],
    )
    paths = [
        Path(__file__).resolve(),
        ROOT / "capture.json",
        ROOT / "native_export.py",
        OUT / "native-export.json",
        ROOT / "sources/primary-facts.json",
        REPO / "hardware/electronics/common/netlists.py",
        REPO / "hardware/electronics/common/sexpr.py",
    ]
    paths += [q for q in (ROOT / "sources").rglob("*") if q.is_file()]
    paths += [OUT / (t + "-netlist.xml") for t in ["E20", "E19"]]
    report["source_sha256"] = {str(q.relative_to(REPO)): sha(q) for q in sorted(set(paths))}
    return report


def main():
    report = analyze()
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "native_component_counts",
                    "provenance",
                    "actual_setting_matches_that_row",
                    "nominal_sink_a",
                    "E20_resistive_5v_independent_subtotal_a",
                    "E20_resistive_3v3_independent_subtotal_a",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
