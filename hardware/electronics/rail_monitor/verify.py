#!/usr/bin/env python3
"""E13 native ERC, independent package/value/net contracts and rail qualification.

Static/allocated calculations only: no supply generation or physical fault proof.
"""

import argparse
import datetime
import hashlib
import itertools
import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path

from ..common import netlists as eda
from ..common.reports import source_hashes
from ..dac_receiver import verify as e08
from ..sequenced_bypass import verify as other
from . import analyze

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

NAMES = ["P19", "N19", "P12", "N12", "NBIAS_L", "NBIAS_R", "V5_REG", "5V_DIG"]
NORMAL = [[18.81, 19.19]] * 2 + [[11.88, 12.12]] * 2 + [[0.1838, 0.256]] * 2 + [[4.975, 5.025], [4.9, 5.1]]
VALID = [[18.392, 19.608]] * 2 + [[11.616, 12.384]] * 2 + [[0.16, 0.27]] * 2 + [[4.9, 5.1], [4.7, 5.3]]
TOPS = [
    (3570, 3010),
    (3400, 2870),
    (11500, 10604),
    (11300, 10412),
    (8200, 1780),
    (8200, 1780),
    (374, 127),
    (768, 270),
]
CONTRACT = {
    "U5": {
        "1": "N19_INV",
        "2": "N19_FB",
        "3": "AGND",
        "4": "V5_REG",
        "5": "AGND",
        "6": "N12_FB",
        "7": "N12_INV",
        "8": "NBIAS_L_INV",
        "9": "NBIAS_L_FB",
        "10": "AGND",
        "11": "AGND",
        "12": "AGND",
        "13": "NBIAS_R_FB",
        "14": "NBIAS_R_INV",
    },
    "U6": {
        "1": "V5_REG",
        "2": "V5_REG",
        "3": "unconnected-(U6-TEMP-Pad3)",
        "4": "AGND",
        "5": "unconnected-(U6-NR-Pad5)",
        "6": "REF_2V5",
        "7": "unconnected-(U6-DNC7-Pad7)",
        "8": "unconnected-(U6-DNC8-Pad8)",
    },
    "U7": {
        "1": "LOCAL_RAIL_OK",
        "2": "AGND",
        "3": "V3V3_IO",
        "4": "STARTUP_CT",
        "5": "V5_COARSE_SENSE",
        "6": "V3V3_IO",
    },
    "U8": {
        "1": "LOCAL_RAIL_OK",
        "2": "AGND",
        "3": "V3V3_IO",
        "4": "unconnected-(U8-CT-Pad4)",
        "5": "V3V3_IO",
        "6": "V3V3_IO",
    },
    "J1": {"1": "5V_DIG", "2": "V3V3_IO", "3": "AGND"},
    "J2": {"1": "P19", "2": "AGND", "3": "N19", "4": "P12", "5": "N12", "6": "V5_REG"},
    "J3": {"1": "AGND", "2": "NBIAS_L", "3": "NBIAS_R"},
    "J4": {"1": "AGND", "2": "PRE_ANALOG_OK"},
}
for i in range(4):
    pins = {"3": "V5_REG", "12": "AGND"}
    for j, (p, n, o) in enumerate([("5", "4", "2"), ("7", "6", "1"), ("9", "8", "14"), ("11", "10", "13")]):
        wi = i * 2 + j // 2
        mode = "UV" if j % 2 == 0 else "OV"
        name = NAMES[wi] + "_" + mode
        pins[p] = name + ("_SENSE" if mode == "UV" else "_REF")
        pins[n] = name + ("_REF" if mode == "UV" else "_SENSE")
        pins[o] = name + "_OK"
    CONTRACT["U" + str(i + 1)] = pins
logic = [
    [(name + "_UV_OK", name + "_OV_OK", name + "_WINDOW_OK") for name in NAMES[:4]],
    [(name + "_UV_OK", name + "_OV_OK", name + "_WINDOW_OK") for name in NAMES[4:]],
    [
        ("P19_WINDOW_OK", "N19_WINDOW_OK", "HV_OK"),
        ("P12_WINDOW_OK", "N12_WINDOW_OK", "LV_OK"),
        ("NBIAS_L_WINDOW_OK", "NBIAS_R_WINDOW_OK", "BIAS_OK"),
        ("V5_REG_WINDOW_OK", "5V_DIG_WINDOW_OK", "FIVES_OK"),
    ],
    [
        ("HV_OK", "LV_OK", "ANALOG_WINDOWS_OK"),
        ("BIAS_OK", "FIVES_OK", "LOWV_WINDOWS_OK"),
        ("ANALOG_WINDOWS_OK", "LOWV_WINDOWS_OK", "WINDOWS_OK"),
        ("WINDOWS_OK", "LOCAL_RAIL_OK", "PRE_ANALOG_OK"),
    ],
]
for i, groups in enumerate(logic):
    pins = {"14": "V3V3_IO", "7": "AGND"}
    for (a, b, y), (pa, pb, py) in zip(
        groups, [("1", "2", "3"), ("4", "5", "6"), ("9", "10", "8"), ("12", "13", "11")]
    ):
        pins[pa] = a
        pins[pb] = b
        pins[py] = y
    CONTRACT["U" + str(i + 9)] = pins


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def and_gate_network(pins, inputs, refs):
    values = dict(inputs)
    for ref in refs:
        for a, b, y in [("1", "2", "3"), ("4", "5", "6"), ("9", "10", "8"), ("12", "13", "11")]:
            values[pins[ref][y]] = values[pins[ref][a]] and values[pins[ref][b]]
    return values


def contracts(parts, pins, mapping):
    assert len(parts) == 181
    for ref, expected in CONTRACT.items():
        assert pins[ref] == expected, (ref, pins[ref], expected)
    values = {
        "U1": "TLV1824IDR",
        "U2": "TLV1824IDR",
        "U3": "TLV1824IDR",
        "U4": "TLV1824IDR",
        "U5": "OPA4192ID",
        "U6": "REF5025EIDR",
        "U7": "TPS3808G01DBVR",
        "U8": "TPS3808G33DBVR",
        **{f"U{i}": "SN74LVC08APWR" for i in range(9, 13)},
    }
    for ref, value in values.items():
        assert parts[ref].findtext("value") == value
    for i, (name, normal, valid, tops) in enumerate(zip(NAMES, NORMAL, VALID, TOPS)):
        w = mapping["windows"][i]
        assert w["name"] == w["rail"] == name and w["normal"] == normal and w["valid"] == valid
        assert [w["uv_top"], w["ov_top"]] == list(tops)
        inverted = name in ("N19", "N12", "NBIAS_L", "NBIAS_R")
        assert w["kind"] == ("inverted" if inverted else "positive")
        for j, mode in enumerate(("UV", "OV")):
            row = mapping["comparators"][i * 2 + j]
            assert row["name"] == name + "_" + mode
            if inverted:
                sense = [10000]
            else:
                top = (
                    11500
                    if name == "5V_DIG" and mode == "OV"
                    else (10499 if name in ("V5_REG", "5V_DIG") else 91000)
                )
                sense = ([10000, 499] if top == 10499 else [top]) + [10000]
            top = tops[j]
            threshold = list({10604: (10000, 604), 10412: (10000, 412)}.get(top, (top,))) + [10000]
            for refs, expected in [(row["sense_parts"], sense), (row["threshold_parts"], threshold)]:
                assert len(refs) == len(expected)
                for ref, value in zip(refs, expected):
                    assert e08.number(parts[ref].findtext("value")) == value
                    assert parts[ref].findtext("value").endswith("0.01% 5ppm")
            for key, value in [("feedback", 20e6), ("pull", 10000)]:
                assert e08.number(parts[row[key]].findtext("value")) == value
                assert parts[row[key]].findtext("value").endswith("1%")
            if mode == "OV":
                assert e08.number(parts[row["threshold_series"]].findtext("value")) == 10000
                assert parts[row["threshold_series"]].findtext("value").endswith("0.01% 5ppm")
    for a, (name, rin, rf) in zip(
        mapping["amplifiers"],
        [
            ("N19", 100000, 10000),
            ("N12", 100000, 10000),
            ("NBIAS_L", 10000, 80600),
            ("NBIAS_R", 10000, 80600),
        ],
    ):
        assert a["window"] == name
        for key, value in [("input_ref", rin), ("feedback_ref", rf)]:
            assert e08.number(parts[a[key]].findtext("value")) == value
            assert parts[a[key]].findtext("value").endswith("0.01% 5ppm")
    for ref, value, pair in [
        ("R110", 105000, ("V5_REG", "V5_COARSE_SENSE")),
        ("R111", 10000, ("V5_COARSE_SENSE", "AGND")),
        ("R112", 100000, ("V3V3_IO", "STARTUP_CT")),
        ("R113", 10000, ("V3V3_IO", "LOCAL_RAIL_OK")),
        ("R114", 330000, ("PRE_ANALOG_OK", "AGND")),
    ]:
        assert e08.number(parts[ref].findtext("value")) == value and analyze.pair(pins, ref) == pair
    caps = []
    for row in mapping["comparators"]:
        caps += [
            (row["name"] + "_SENSE", "AGND", "100pF C0G 5%"),
            (row["name"] + "_REF", "AGND", "100pF C0G 5%"),
        ]
    for name in ["N19", "N12", "NBIAS_L", "NBIAS_R"]:
        caps.append((name + "_INV", name + "_FB", "100pF C0G 5%"))
    for i in range(1, 13):
        caps.append(("V5_REG" if i <= 6 else "V3V3_IO", "AGND", "100nF 16V X7R"))
    caps += [
        ("REF_2V5", "AGND", "2.2uF 16V X7R"),
        ("V5_REG", "AGND", "10uF 16V X7R"),
        ("V3V3_IO", "AGND", "1uF 16V X7R"),
    ]
    assert len(caps) == 51
    for i, (a, b, value) in enumerate(caps, 1):
        ref = "C" + str(i)
        assert analyze.pair(pins, ref) == (a, b) and parts[ref].findtext("value") == value
    assert set(parts) == set(CONTRACT) | {f"R{i}" for i in range(1, 115)} | {f"C{i}" for i in range(1, 52)}


def powered_logic(pins):
    names = [n + "_" + m + "_OK" for n in NAMES for m in ("UV", "OV")] + ["LOCAL_RAIL_OK"]
    result = hashlib.sha256()
    cases = 0
    for bits in itertools.product((False, True), repeat=17):
        v = and_gate_network(pins, dict(zip(names, bits)), [f"U{i}" for i in range(9, 13)])
        good = v["PRE_ANALOG_OK"]
        assert good == all(bits)
        result.update(bytes([good]))
        cases += 1
    return dict(
        powered_cases=cases,
        actual_exported_gate_outputs_match_all17_inputs=True,
        result_vector_sha256=result.hexdigest(),
        propagation_or_unpowered_behavior_simulated=False,
    )


def chain_checks(monitor, e09, e11):

    result = []
    for pre in (False, True):
        state = dict(
            CODEC_PGOOD=True, PRE_ANALOG_OK=pre, CODEC_RUN=True, CLK_VALID=True, RAMP_DONE=True, TIMER_OK=True
        )
        state = and_gate_network(e09, state, ["U7"])
        state[e09["U9"]["4"]] = state[e09["U9"]["1"]] and state[e09["U9"]["2"]]
        actual = other.gates(
            e11,
            dict(
                LOCAL_OK=True,
                ANALOG_OK=state["ANALOG_OK"],
                PROCESS_OK=True,
                MCU_PERMIT=True,
                ARMED=True,
                GAIN_REQ=False,
                GAIN_DELAY=False,
                TIMER_INPUT_OK=True,
            ),
        )
        assert state["CHIP_EN"] == state["ANALOG_OK"] == actual["BYPASS_LOW_energized"] == pre
        assert actual["INPUT_LOW_energized"] == pre
        result.append(
            dict(
                pre_analog_ok=pre,
                chip_en=state["CHIP_EN"],
                analog_ok=state["ANALOG_OK"],
                input_energized=actual["INPUT_LOW_energized"],
                wet_output=actual["BYPASS_LOW_energized"],
            )
        )
    sequences = []
    names = [name + "_" + mode + "_OK" for name in NAMES for mode in ("UV", "OV")] + ["LOCAL_RAIL_OK"]
    for failed in names:
        sequence = other.Sequence(e11)
        sequence.boot()
        inputs = dict.fromkeys(names, True)
        inputs[failed] = False
        pre = and_gate_network(monitor, inputs, ["U9", "U10", "U11", "U12"])["PRE_ANALOG_OK"]
        assert not pre
        # E09's timers/flags remain high in this deliberately fastest-recovery
        # model; the actual monitor path must still clear the E11 latch.
        state = and_gate_network(
            e09,
            dict(
                CODEC_PGOOD=True,
                PRE_ANALOG_OK=pre,
                CODEC_RUN=True,
                CLK_VALID=True,
                RAMP_DONE=True,
                TIMER_OK=True,
            ),
            ["U7"],
        )
        state[e09["U9"]["4"]] = state[e09["U9"]["1"]] and state[e09["U9"]["2"]]
        off = sequence.step(2100, ANALOG_OK=state["ANALOG_OK"])
        assert not off["INPUT_LOW_energized"] and not off["BYPASS_LOW_energized"] and not sequence.q
        inputs[failed] = True
        assert and_gate_network(monitor, inputs, ["U9", "U10", "U11", "U12"])["PRE_ANALOG_OK"]
        sequence.step(2101, ANALOG_OK=True)
        assert not sequence.step(4109)["INPUT_READY"]
        recovered = sequence.step(4110)
        assert recovered["INPUT_READY"] and not recovered["BYPASS_LOW_energized"]
        assert not sequence.step(4200)["BYPASS_LOW_energized"]
        sequence.step(4201, MCU_PERMIT=False)
        assert sequence.step(4202, MCU_PERMIT=True)["BYPASS_LOW_energized"]
        sequences.append(
            dict(
                failed=failed,
                input_and_wet_drop=True,
                latch_cleared=True,
                full_input_timer_restarted=True,
                held_permit_cannot_rearm=True,
                fresh_permit_edge_rearms=True,
            )
        )
    return dict(
        settled_chain_cases=result,
        stateful_single_fault_recovery_cases=sequences,
        scope="Actual exported monitor/E09/E11 gates; E09 timer outputs held high for fastest recovery, E11 nominal discrete timer/latch model; no physical timing proof",
    )


def headroom(external):
    # Re-evaluate the wider fault envelope without weakening the normal1% rail
    # regulation requirement or overwriting historical E05/E08/E10/E12 records.
    p = ROOT.parent / "output_stage/generated/circuit-analysis.json"
    down = json.loads(p.read_text())
    rows = []
    for row in down["voltage_screen"]:
        rail = row["rail_nominal_v"]
        minimum = rail * 0.968
        maximum = rail * 1.032
        margin = (
            minimum
            - row["assumed_output_rail_reserve_v"]
            - row["required_peak_v"]
            - 0.025 * row["worst_feedback_tolerance_gain"]
        )
        assert margin > 0 and 2 * maximum < row["recommended_max_total_supply_v"]
        rows.append(
            dict(
                mode=row["mode"],
                channel=row["channel"],
                minimum_rail_v=minimum,
                maximum_total_supply_v=maximum * 2,
                remaining_peak_margin_with_receiver_dc_v=margin,
                output_swing_limit_manufacturer_guaranteed_at_this_load=False,
            )
        )
    p10 = ROOT.parent / "input_range/generated/circuit-analysis.json"
    r10 = json.loads(p10.read_text())["voltage_screen"]
    assert 12 * 0.968 - 1.3 - r10["maximum_preamp_peak_v"] - 0.025 > 0
    assert 12 * 0.968 - 2.25 - r10["maximum_input_peak_v"] - 0.014 > 0
    # Existing E08 hypothetical raw DAC scale/current models, at their source
    # common-mode endpoints. This cannot establish actual converter scale.
    parts, pins = external["dac_receiver"]
    base = ROOT.parent / "dac_receiver/generated/circuit-analysis.json"
    record = json.loads(base.read_text())
    scale = record["dac_scale"]["differential_current_rms_a_for_2v_at_1khz"]
    maxima = {}
    count = 0
    for ch, base_r, sp, sn, f, dc in itertools.product(
        ("L", "R"), (195, 390), (0.85, 1.15), (0.85, 1.15), (20, 1000, 20000), (0, 1.65)
    ):
        rd = (base_r * sp, base_r * sn)
        ac = e08.Circuit(parts, pins, ch, f, rdac=rd, finite=True)
        ax = ac.solve(idiff=scale)
        steady = e08.Circuit(parts, pins, ch, 0, rdac=rd, finite=True)
        dx = steady.solve(dc_voltage=dc, rdac=rd)
        for ref, pos, neg, out in ac.amps:
            voltage = abs(steady.voltage(dx, out)) + math.sqrt(2) * abs(ac.voltage(ax, out)) + 0.025
            maxima[ref] = max(maxima.get(ref, 0), voltage)
            assert voltage < 12 * 0.968 - 1.3, (ref, voltage)
        count += 1
    return dict(
        normal_analog_regulation_fraction=0.01,
        conditional_fault_envelope_fraction=0.032,
        output_stage=rows,
        dac_receiver_hypothetical_cases=count,
        dac_receiver_max_amp_output_magnitude_v=maxima,
        e10_preamp_peak_margin_v=12 * 0.968 - 1.3 - r10["maximum_preamp_peak_v"] - 0.025,
        e12_buffer_peak_margin_v=12 * 0.968 - 1.3 - 4.06 * math.sqrt(2),
        e12_vocm_series_fault_current_a=(12 * 1.032) / (10000 * 0.99),
        interpretation="Conditional linear/swing-allocation screen; no proof of THD/noise, actual DAC current scale, rail ripple, fast decay or bypass timing. Normal generation remains1%; regulator/physical validation open.",
        inherited_record_sha256={os.path.relpath(q, ROOT): sha(q) for q in [p, p10, base]},
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", type=Path, required=True)
    p.add_argument(
        "--footprints",
        type=Path,
        default=Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
    )
    args = p.parse_args()
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e13-") as temporary:
        temp = Path(temporary)
        env = os.environ.copy()
        env["KICAD_CONFIG_HOME"] = str(temp / "config")
        env["KICAD10_FOOTPRINT_DIR"] = str(args.footprints)
        env["FONTCONFIG_FILE"] = str(ROOT.parents[2] / "build-hardware/kicad-fonts.conf")

        def run(*command):
            r = subprocess.run(
                [str(args.kicad_cli), *map(str, command)], capture_output=True, text=True, env=env
            )
            if r.returncode:
                raise RuntimeError(str(command) + "\n" + r.stdout + "\n" + r.stderr)
            return r.stdout.strip()

        version = run("version")
        sheet = ROOT / "rail_monitor.kicad_sch"
        run(
            "sch",
            "erc",
            "--severity-all",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            OUT / "erc.json",
            sheet,
        )
        assert all(not v["violations"] for v in json.loads((OUT / "erc.json").read_text())["sheets"])
        run("sch", "export", "netlist", "--format", "kicadxml", "-o", OUT / "netlist.xml", sheet)
        parts, pins = eda.netlist(OUT / "netlist.xml")
        mapping = json.loads((ROOT / "monitor-map.json").read_text())
        contracts(parts, pins, mapping)
        screen = analyze.screen(parts, pins, mapping, e08.number)
        assert set(screen["all_window_resistors_used"]) | {f"R{i}" for i in range(110, 115)} == {
            f"R{i}" for i in range(1, 115)
        }
        screen["logic"] = powered_logic(pins)
        external = {}
        interfaces = {}
        for name in ["converter", "sequenced_bypass", "adc_driver", "dac_receiver", "output_stage"]:
            source = ROOT.parent / name / (name + ".kicad_sch")
            target = temp / (name + ".xml")
            run("sch", "export", "netlist", "--format", "kicadxml", "-o", target, source)
            external[name] = eda.netlist(target)
            _, other = external[name]
            if name == "converter":
                assert (
                    other["J5"]["1"] == pins["J4"]["1"] == "AGND"
                    and other["J5"]["5"] == pins["J4"]["2"] == "PRE_ANALOG_OK"
                )
                assert set(other["R6"].values()) == {"PRE_ANALOG_OK", "AGND"}
                assert math.isclose(e08.number(external[name][0]["R6"].findtext("value")), 47000)
            elif name == "adc_driver":
                assert [other["J4"][str(i)] for i in (3, 4)] == [pins["J3"][str(i)] for i in (2, 3)]
            elif name == "output_stage":
                assert [other["J4"][str(i)] for i in (1, 2, 3, 4, 5)] == [
                    pins["J2"][str(i)] for i in (1, 2, 3, 4, 5)
                ]
            interfaces[name] = dict(schematic_sha256=sha(source), fresh_export=True)
        screen["direct_fault_chain"] = chain_checks(
            pins, external["converter"][1], external["sequenced_bypass"][1]
        )
        screen["inherited_headroom"] = headroom(external)
        plan = json.loads((ROOT / "integration.json").read_text())
        assert (
            plan["monitored_rails"] == NAMES
            and not plan["power_generation_implemented"]
            and not plan["physical_timing_verified"]
        )
        # Count source/reference load at maximum VREF, then include a small
        # feedback-current allowance. Enhanced reference is rated to10mA.
        load = 0
        for row in mapping["comparators"]:
            load += 2.5025 / (
                sum(e08.number(parts[r].findtext("value")) for r in row["threshold_parts"]) * 0.999
            )
        load += 10e-6
        assert load < 0.010
        screen["reference_load_screen"] = dict(
            maximum_allocated_source_a=load,
            ref5025e_limit_a=0.010,
            effective_output_cap_min_f=1e-6,
            effective_output_cap_max_f=100e-6,
            initial_ppm=250,
            temperature_ppm=250,
            line_ppm=12,
            load_regulation_ppm=load * 1000 * 35,
            allocated_aging_thermal_ppm=300,
            total_reference_error_limit_ppm=1000,
        )
        assert 250 + 250 + 12 + load * 1000 * 35 + 300 < 1000
        # Each new negative-bias sense amplifier adds a10k load to one E12
        # pump. Keep that real load in the inherited20mA characterized screen.
        adc_screen = json.loads((ROOT.parent / "adc_driver/generated/circuit-analysis.json").read_text())
        bias = next(v for v in adc_screen.values() if isinstance(v, dict) and "conservative_bias_load_a" in v)
        sense_load = 0.27 / (10000 * 0.999)
        combined = bias["conservative_bias_load_a"] + sense_load
        assert combined < bias["lm7705_characterized_load_a"]
        screen["negative_bias_loading"] = dict(
            per_channel_monitor_load_max_a=sense_load,
            inherited_per_channel_load_a=bias["conservative_bias_load_a"],
            combined_per_channel_load_a=combined,
            characterized_load_a=bias["lm7705_characterized_load_a"],
            physical_current_ripple_verified=False,
            inherited_analysis_sha256=sha(ROOT.parent / "adc_driver/generated/circuit-analysis.json"),
        )
        footprints = {}
        for ref, part in parts.items():
            identifier = part.findtext("footprint")
            library, name = identifier.split(":")
            path = args.footprints / (library + ".pretty") / (name + ".kicad_mod")
            text = path.read_text()
            assert set(pins[ref]) <= set(re.findall(r'\(pad\s+"([^"]+)"', text)), (ref, identifier)
            footprints[identifier] = sha(path)
        (OUT / "electrical-screens.json").write_text(json.dumps(screen, indent=2) + "\n")
        run("sch", "export", "svg", "--exclude-drawing-sheet", "-o", str(OUT) + os.sep, sheet)
        files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix not in (".kicad_prl", ".prl", ".lck")]
        files += [
            ROOT.parent / "dac_receiver/verify.py",
            ROOT.parent / "output_stage/verify.py",
            ROOT.parent / "sequenced_bypass/verify.py",
            ROOT.parent / "adc_driver/generated/circuit-analysis.json",
        ]
        report = dict(
            revision="E13",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            physical_components=181,
            native_erc_violations=0,
            exported_all_component_contracts=True,
            window_channels=8,
            threshold_corners=screen["threshold_corners"],
            powered_logic_cases=screen["logic"]["powered_cases"],
            stateful_monitor_fault_recovery_cases=len(
                screen["direct_fault_chain"]["stateful_single_fault_recovery_cases"]
            ),
            interfaces=interfaces,
            native_footprint_library_hashes=footprints,
            independent_rail_windows_schematic_implemented=True,
            negative_bias_windows_schematic_implemented=True,
            power_generation_implemented=False,
            overvoltage_disconnect_implemented=False,
            pcb_routed=False,
            enclosure_placement_complete=False,
            physical_timing_verified=False,
            physical_audio_verified=False,
            source_hashes=source_hashes(ROOT, sorted(files)),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad {version}: zero ERC;181 exported component contracts;eight windows;{screen['threshold_corners']} threshold corners;131072 powered logic cases;fresh E09/E11/E12 interfaces. Supply generation/physical timing unverified."
    )


if __name__ == "__main__":
    main()
