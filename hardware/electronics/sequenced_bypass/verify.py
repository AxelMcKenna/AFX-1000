#!/usr/bin/env python3
"""Native E11 ERC, exported contracts, powered logic and conditional timing screens.

No relay dynamics, unpowered transistor behavior, PCB or physical proof.
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

from ..common import footprints as relay
from ..common import netlists as eda
from ..common.reports import source_hashes

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

CONTRACT = {
    "U1": {
        "1": "3V3",
        "2": "CWD",
        "3": "3V3",
        "4": "AGND",
        "5": "3V3",
        "6": "HEARTBEAT",
        "7": "LOCAL_OK",
        "8": "LOCAL_OK",
        "9": "AGND",
    },
    "U2": {
        "1": "LOCAL_OK",
        "2": "ANALOG_OK",
        "3": "INPUT_ENABLE",
        "4": "INPUT_ENABLE",
        "5": "PROCESS_OK",
        "6": "PROCESS_HEALTH",
        "9": "ARMED",
        "10": "PERMIT_CLEAN",
        "8": "COIL_ENABLE",
        "12": "MCU_PERMIT",
        "13": "MCU_PERMIT",
        "11": "PERMIT_CLEAN",
        "14": "3V3",
        "7": "AGND",
    },
    "U3": {
        "1": "PERMIT_CLEAN",
        "2": "3V3",
        "6": "CLEAR_N",
        "7": "3V3",
        "8": "3V3",
        "3": "ARMED",
        "4": "AGND",
        "5": "unconnected-(U3-Q_N-Pad5)",
    },
    "U4": {"6": "3V3", "5": "3V3", "3": "3V3", "2": "AGND", "1": "LOCAL_OK", "4": "STARTUP_CT"},
    "U5": {"6": "3V3", "5": "5V", "3": "3V3", "2": "AGND", "1": "LOCAL_OK", "4": "unconnected-(U5-CT-Pad4)"},
    "U6": {
        "1": "TIMER_ENABLE",
        "2": "TIMER_INPUT_OK",
        "3": "INPUT_READY",
        "4": "COIL_ENABLE",
        "5": "CLEAR_N",
        "6": "FINAL_ENABLE",
        "9": "INPUT_READY",
        "10": "PROCESS_HEALTH",
        "8": "CLEAR_N",
        "12": "INPUT_ENABLE",
        "13": "GAIN_STABLE",
        "11": "TIMER_ENABLE",
        "14": "3V3",
        "7": "AGND",
    },
    "U7": {
        "1": "TIMER_ENABLE",
        "2": "AGND",
        "3": "TIMER_SET",
        "4": "TIMER_DIV",
        "5": "3V3",
        "6": "TIMER_INPUT_OK",
    },
    "U8": {
        "1": "GAIN_REQ",
        "2": "GAIN_DELAY",
        "3": "GAIN_EDGE",
        "4": "GAIN_EDGE",
        "5": "3V3",
        "6": "GAIN_STABLE",
        "9": "AGND",
        "10": "AGND",
        "12": "AGND",
        "13": "AGND",
        "14": "3V3",
        "7": "AGND",
        "8": "unconnected-(U8-3Y-Pad8)",
        "11": "unconnected-(U8-4Y-Pad11)",
    },
    "Q1": {"1": "BYPASS_GATE", "2": "AGND", "3": "BYPASS_LOW"},
    "Q2": {"1": "GAIN_GATE", "2": "AGND", "3": "GAIN_LOW"},
    "Q3": {"1": "INPUT_GATE", "2": "AGND", "3": "INPUT_LOW"},
    "K1": {
        "1": "5V",
        "8": "BYPASS_LOW",
        "3": "OUT_L",
        "2": "IN_L",
        "4": "PROC_OUT_L",
        "6": "OUT_R",
        "7": "IN_R",
        "5": "PROC_OUT_R",
    },
    "K2": {
        "1": "5V",
        "8": "INPUT_LOW",
        "3": "PROC_IN_L",
        "4": "IN_L",
        "6": "PROC_IN_R",
        "5": "IN_R",
        "2": "unconnected-(K2-L_NC-Pad2)",
        "7": "unconnected-(K2-R_NC-Pad7)",
    },
}
for ref, nets in {
    "J1": ["5V", "AGND", "3V3"],
    "J2": ["AGND", "HEARTBEAT", "MCU_PERMIT", "GAIN_REQ", "ARMED", "BYPASS_SENSE"],
    "J3": ["3V3", "PROCESS_OK", "ANALOG_OK", "AGND", "BYPASS_SENSE"],
    "J4": ["5V", "BYPASS_LOW", "5V", "INPUT_LOW"],
    "J5": ["5V", "GAIN_LOW"],
    "J6": ["AGND", "INPUT_READY"],
    "J7": ["IN_L", "AGND", "IN_R"],
    "J8": ["OUT_L", "AGND", "OUT_R"],
    "J9": ["PROC_IN_L", "AGND", "PROC_IN_R", "PROC_OUT_L", "AGND", "PROC_OUT_R"],
}.items():
    CONTRACT[ref] = {str(i + 1): net for i, net in enumerate(nets)}
VALUES = {}
for ref, value, a, b in [
    ("C1", "150pF C0G 5%", "CWD", "AGND"),
    *[(f"C{i}", "100nF X7R", "3V3", "AGND") for i in range(2, 7)],
    ("C7", "1uF 16V X7R", "3V3", "AGND"),
    ("C8", "22uF 16V X7R", "5V", "AGND"),
    ("C9", "1uF 16V X7R 10%", "GAIN_DELAY", "AGND"),
    *[(f"C{i}", "100nF 16V X7R", "3V3", "AGND") for i in range(10, 13)],
    ("R1", "10k 1%", "3V3", "LOCAL_OK"),
    ("R2", "100k 1%", "HEARTBEAT", "AGND"),
    ("R3", "47k 1%", "MCU_PERMIT", "AGND"),
    ("R4", "47k 1%", "PROCESS_OK", "AGND"),
    ("R5", "47k 1%", "ANALOG_OK", "AGND"),
    ("R6", "10k 1%", "3V3", "BYPASS_SENSE"),
    ("R7", "47k 1%", "GAIN_REQ", "AGND"),
    ("R8", "4.7k 1%", "FINAL_ENABLE", "BYPASS_GATE"),
    ("R9", "270k 1%", "BYPASS_GATE", "AGND"),
    ("R10", "4.7k 1%", "GAIN_REQ", "GAIN_GATE"),
    ("R11", "270k 1%", "GAIN_GATE", "AGND"),
    ("R12", "4.7k 1%", "INPUT_ENABLE", "INPUT_GATE"),
    ("R13", "270k 1%", "INPUT_GATE", "AGND"),
    ("R14", "383k 0.1% 25ppm", "TIMER_SET", "AGND"),
    ("R15", "47k 1%", "GAIN_REQ", "GAIN_DELAY"),
    ("R16", "147k 1%", "3V3", "TIMER_DIV"),
    ("R17", "100k 1%", "TIMER_DIV", "AGND"),
    ("R18", "100k 1%", "3V3", "STARTUP_CT"),
    ("D1", "SMF9.0A", "BYPASS_LOW", "AGND"),
    ("D2", "SMF9.0A", "GAIN_LOW", "AGND"),
    ("D3", "SMF9.0A", "INPUT_LOW", "AGND"),
]:
    CONTRACT[ref] = {"1": a, "2": b}
    VALUES[ref] = value
VALUES.update(
    U1="TPS3431SDRBR",
    U2="SN74HCS08DR",
    U3="SN74LVC1G74DCTR",
    U4="TPS3808G33DBVR",
    U5="TPS3808G50DBVR",
    U6="SN74HCS08DR",
    U7="LTC6994HS6-1#TRMPBF",
    U8="SN74HCS86DR",
    Q1="AO3400A",
    Q2="AO3400A",
    Q3="AO3400A",
    K1="G6K-2F-Y DC5",
    K2="G6K-2F-Y DC5",
)
for ref in CONTRACT:
    if ref.startswith("J"):
        VALUES[ref] = "Conn_01x" + str(len(CONTRACT[ref])).zfill(2)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gates(pins, inputs):
    nets = {"3V3": True, "AGND": False, **inputs}
    for unused in range(5):
        for ref, xor in [("U2", False), ("U6", False), ("U8", True)]:
            for a, b, y in [("1", "2", "3"), ("4", "5", "6"), ("9", "10", "8"), ("12", "13", "11")]:
                if y not in pins[ref]:
                    continue
                av = nets.get(pins[ref][a], False)
                bv = nets.get(pins[ref][b], False)
                nets[pins[ref][y]] = (av != bv) if xor else (av and bv)
    # Ideal static gate-divider drive only; MOSFET/relay dynamics excluded.
    for ref, resistor in [("Q1", "R8"), ("Q2", "R10"), ("Q3", "R12")]:
        assert pins[ref]["1"] == pins[resistor]["2"]
        nets[pins[ref]["3"] + "_energized"] = nets.get(pins[resistor]["1"], False)
    return nets


def truth_table(pins):
    names = [
        "LOCAL_OK",
        "ANALOG_OK",
        "PROCESS_OK",
        "MCU_PERMIT",
        "GAIN_REQ",
        "GAIN_DELAY",
        "TIMER_INPUT_OK",
        "ARMED",
    ]
    cases = []
    for bits in itertools.product((False, True), repeat=len(names)):
        i = dict(zip(names, bits))
        n = gates(pins, i)
        health = i["LOCAL_OK"] and i["ANALOG_OK"]
        stable = i["GAIN_REQ"] == i["GAIN_DELAY"]
        ready = health and stable and i["TIMER_INPUT_OK"]
        wet = ready and i["PROCESS_OK"] and i["MCU_PERMIT"] and i["ARMED"]
        assert n["INPUT_LOW_energized"] == health and n["GAIN_LOW_energized"] == i["GAIN_REQ"]
        assert n["INPUT_READY"] == ready and n["CLEAR_N"] == (ready and i["PROCESS_OK"])
        assert n["BYPASS_LOW_energized"] == wet
        cases.append(dict(inputs=i, input_energized=health, input_ready=ready, wet_output=wet))
    return cases


class Sequence:
    def __init__(self, pins):
        self.pins = pins
        self.q = False
        self.oldclock = False
        self.timer_start = None
        self.timer = False
        self.inputs = dict(
            LOCAL_OK=True, ANALOG_OK=True, PROCESS_OK=True, MCU_PERMIT=False, GAIN_REQ=False, GAIN_DELAY=False
        )
        self.history = []

    def step(self, t, **changes):
        self.inputs.update(changes)
        n = gates(self.pins, {**self.inputs, "ARMED": self.q, "TIMER_INPUT_OK": self.timer})
        if not n[self.pins["U7"]["1"]]:
            self.timer = False
            self.timer_start = None
        else:
            if self.timer_start is None:
                self.timer_start = t
            self.timer = t - self.timer_start >= 2009  # ceil nominal, not a component guarantee
        n = gates(self.pins, {**self.inputs, "ARMED": self.q, self.pins["U7"]["6"]: self.timer})
        clock = n[self.pins["U3"]["1"]]
        if not n[self.pins["U3"]["6"]]:
            self.q = False
        elif clock and not self.oldclock:
            self.q = True
        self.oldclock = clock
        n = gates(self.pins, {**self.inputs, "ARMED": self.q, self.pins["U7"]["6"]: self.timer})
        result = {k: n[k] for k in ["INPUT_READY", "INPUT_LOW_energized", "BYPASS_LOW_energized", "CLEAR_N"]}
        self.history.append(dict(t_ms=t, inputs=dict(self.inputs), armed=self.q, **result))
        return result

    def boot(self):
        assert not self.step(0, MCU_PERMIT=True)["BYPASS_LOW_energized"]
        assert not self.step(2009)["BYPASS_LOW_energized"]  # held high may not arm
        self.step(2010, MCU_PERMIT=False)
        assert self.step(2011, MCU_PERMIT=True)["BYPASS_LOW_energized"]


def sequences(pins):
    cases = []
    # U7 copies IN without an additional delay at the end of its startup.
    # The U4 guard must hold IN low through that startup (allocated <=100ms),
    # then release no earlier than180ms so a real rising edge starts the timer.
    s = Sequence(pins)
    assert not s.step(0, LOCAL_OK=False, MCU_PERMIT=True)["INPUT_READY"]
    assert not s.step(100)["INPUT_READY"]
    assert not s.step(180, LOCAL_OK=True)["INPUT_READY"]
    assert not s.step(2188)["INPUT_READY"] and s.step(2189)["INPUT_READY"]
    assert not s.step(2190)["BYPASS_LOW_energized"]
    cases.append(dict(name="startup_low_guard_then_full_rising_delay", trace=s.history))
    for fault in ["LOCAL_OK", "ANALOG_OK", "PROCESS_OK"]:
        s = Sequence(pins)
        s.boot()
        off = s.step(2100, **{fault: False})
        assert not off["BYPASS_LOW_energized"]
        assert off["INPUT_LOW_energized"] == (fault == "PROCESS_OK")
        recover = s.step(2101, **{fault: True})
        assert not recover["BYPASS_LOW_energized"]
        if fault == "PROCESS_OK":
            assert recover["INPUT_READY"]  # no cold input on manual bypass
        else:
            assert not s.step(4109)["INPUT_READY"]
            assert s.step(4110)["INPUT_READY"]
        assert not s.step(4200)["BYPASS_LOW_energized"]
        s.step(4201, MCU_PERMIT=False)
        assert s.step(4202, MCU_PERMIT=True)["BYPASS_LOW_energized"]
        cases.append(dict(name=fault + "_one_ms_loss_and_fresh_edge", trace=s.history))
    for initial in [False, True]:
        s = Sequence(pins)
        s.inputs.update(GAIN_REQ=initial, GAIN_DELAY=initial)
        s.boot()
        edge = s.step(2100, GAIN_REQ=not initial)
        assert not edge["INPUT_READY"] and not edge["BYPASS_LOW_energized"] and edge["INPUT_LOW_energized"]
        assert not s.step(2150, GAIN_DELAY=not initial)["INPUT_READY"]
        assert not s.step(4158)["INPUT_READY"] and s.step(4159)["INPUT_READY"]
        assert not s.step(4200)["BYPASS_LOW_energized"]
        s.step(4201, MCU_PERMIT=False)
        assert s.step(4202, MCU_PERMIT=True)["BYPASS_LOW_energized"]
        cases.append(dict(name="gain_" + ("fall" if initial else "rise"), trace=s.history))
    s = Sequence(pins)
    s.boot()
    for t in range(2100, 5000, 100):
        assert not s.step(t, ANALOG_OK=False)["INPUT_READY"]
        assert not s.step(t + 1, ANALOG_OK=True)["INPUT_READY"]
    assert not s.step(6909)["INPUT_READY"] and s.step(6910)["INPUT_READY"]
    assert not s.step(7000)["BYPASS_LOW_energized"]
    cases.append(dict(name="repeated_faults_restart_full_timer", trace=s.history))
    return cases


def screens(parts):
    def value(ref):
        return eda.number(parts[ref].findtext("value"))

    # The full-temperature delay error is 3.0%, not the 25C 2.3% headline.
    nominal = 262144 * value("R14") / 50000 * 1e-6
    low = nominal * 0.99 * 0.97
    high = nominal * 1.01 * 1.03
    mechanical = 0.050
    required = 1.2
    assert low - mechanical > required
    divider = []
    for st, sb, leak, vio in itertools.product((-1, 1), repeat=4):
        top = value("R16") * (1 + st * 0.015)
        bot = value("R17") * (1 + sb * 0.015)
        v = 3.3 * (1 + vio * 0.05)
        ratio = (v / top + leak * 10e-9) / (1 / top + 1 / bot) / v
        assert abs(ratio - 6.5 / 16) < 0.015 and 1 / (1 / top + 1 / bot) < 500000
        divider.append(ratio)
    # Conditional gain-edge pulse: 3.3V thresholds aren't specified in HCS86's
    # threshold table. This envelope must be qualified; it is not a TI guarantee.
    pulse = []
    for sr, cap, vio, initial_leak, final_leak, threshold, rising in itertools.product(
        (-1, 1), (0.7e-6, 1.3e-6), (3.135, 3.465), (-1e-6, 1e-6), (-1e-6, 1e-6), (0.25, 0.75), (False, True)
    ):
        for lo, hi in itertools.product((0, 0.4), (vio - 0.4, vio)):
            r = value("R15") * (1 + sr * 0.01)
            initial = (lo if rising else hi) + initial_leak * r
            final = (hi if rising else lo) + final_leak * r
            target = vio * threshold
            t = r * cap * math.log((final - initial) / (final - target))
            assert t > 0.0001
            pulse.append(t)
    gate = (2.9 / (4700 * 1.01) - 100e-9) / (1 / (4700 * 1.01) + 1 / (270000 * 0.99))
    static = 3.465 / (4700 * 0.99 + 270000 * 0.99) + 100e-9
    # INPUT_ENABLE also drives two HCS inputs; include 2x1uA leakage.
    assert gate > 2.5 and static + 2e-6 < 20e-6
    ready_load = 3.465 / (270000 * 0.99) + 2e-6  # one HCS input and future MCP input allocation
    assert ready_load < 20e-6
    assert 40000 < value("R18") * 0.99 and value("R18") * 1.01 < 200000
    return dict(
        startup=dict(
            u4_release_min_s=0.180,
            u4_release_max_s=0.420,
            u7_startup_max_allocation_s=0.100,
            u7_startup_max_manufacturer_specified=False,
            interpretation="LTC6994 transfers IN at startup without a full delay. U4 holds TIMER_ENABLE low; verify startup <=100ms over supply ramps/dips before accepting hardware.",
            supply_ramp_dip_bench_verified=False,
        ),
        timer=dict(
            part=parts["U7"].findtext("value"),
            divider_code=6,
            polarity=0,
            n_div=262144,
            nominal_s=nominal,
            total_resistor_error_allocation=0.01,
            full_temperature_ic_error_fraction=0.03,
            conditional_minimum_s=low,
            conditional_maximum_s=high,
            mechanical_close_bounce_allocation_s=mechanical,
            minimum_after_contact_close_s=low - mechanical,
            required_e10_input_settling_s=required,
            external_timing_capacitor=False,
            hardware_timing_verified=False,
        ),
        divider=dict(
            corners=len(divider),
            min_fraction=min(divider),
            max_fraction=max(divider),
            code6_valid_fraction=[6.5 / 16 - 0.015, 6.5 / 16 + 0.015],
            total_each_resistor_error_allocation=0.015,
        ),
        gain_edge=dict(
            corners=len(pulse),
            conditional_minimum_pulse_s=min(pulse),
            conditional_maximum_pulse_s=max(pulse),
            scope="Isolated gain steps from settled RC state; rapid edge trains and real gain-contact bounce need bench verification",
            threshold_envelope_fraction=[0.25, 0.75],
            mcu_low_max_v=0.4,
            mcu_high_min="VIO-0.4V",
            input_leakage_a=1e-6,
            effective_capacitance_f=[0.7e-6, 1.3e-6],
            required_recognized_low_pulse_s=0.0001,
            envelope_manufacturer_guaranteed_at_3v3=False,
            pulse_recognition_bench_verified=False,
            note="LTC6994 lists typical 5ns at3.3V, without a full-temperature limit. Allocate/measure <=100us recognition; no arbitrary-glitch guarantee.",
        ),
        driver=dict(
            minimum_screened_gate_v=gate,
            maximum_static_hcs_load_a=static + 2e-6,
            output_coils=1,
            input_coils=1,
            gain_coils=2,
            maximum_gain_coil_pair_current_allocation_a=0.06,
            ao3400a_rds25c_ohm=0.048,
            tvs_clamp_datasheet_v=15.4,
            coil_transient_verified=False,
        ),
        status=dict(
            receiving_pulldown_ohm=270000,
            maximum_screened_ready_load_a=ready_load,
            control_pcb_implemented=False,
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, required=True)
    parser.add_argument(
        "--footprints",
        type=Path,
        default=Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
    )
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e11-") as temporary:
        temp = Path(temporary)
        env = os.environ.copy()
        env["KICAD_CONFIG_HOME"] = str(temp / "config")
        env["KICAD10_FOOTPRINT_DIR"] = str(args.footprints)
        font = ROOT.parents[2] / "build-hardware/kicad-fonts.conf"
        if font.exists():
            env["FONTCONFIG_FILE"] = str(font)

        def run(*command):
            result = subprocess.run(
                [str(args.kicad_cli), *map(str, command)], capture_output=True, text=True, env=env
            )
            if result.returncode:
                raise RuntimeError(f"{command}\n{result.stdout}\n{result.stderr}")
            return result.stdout.strip()

        version = run("version")
        sheet = ROOT / "sequenced_bypass.kicad_sch"
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
        assert all(not s["violations"] for s in json.loads((OUT / "erc.json").read_text())["sheets"])
        run("sch", "export", "netlist", "--format", "kicadxml", "-o", OUT / "netlist.xml", sheet)
        parts, pins = eda.netlist(OUT / "netlist.xml")
        assert pins == CONTRACT, (pins, CONTRACT)
        assert len(parts) == 55
        assert {ref: part.findtext("value") for ref, part in parts.items()} == VALUES
        external = {}
        for name in ["input_range", "output_stage", "converter"]:
            source = ROOT.parent / name / (name + ".kicad_sch")
            net = temp / (name + ".xml")
            run("sch", "export", "netlist", "--format", "kicadxml", "-o", net, source)
            _, other = eda.netlist(net)
            if name == "input_range":
                assert other["J1"] == {str(i): pins["J9"][str(i)] for i in (1, 2, 3)}
                assert other["J4"] == pins["J5"]
            elif name == "output_stage":
                assert other["J2"] == {str(i): pins["J9"][str(i + 3)] for i in (1, 2, 3)}
                assert other["J3"] == pins["J5"]
            else:
                assert other["J5"]["6"] == pins["J3"]["3"] == "ANALOG_OK"
            external[name] = dict(schematic_sha256=sha(source), exported_interface_matches=True)
        plan = json.loads((ROOT / "integration.json").read_text())
        e10 = ROOT.parent / "input_range/integration.json"
        input_plan = json.loads(e10.read_text())
        assert (
            plan["required_input_settling_s"] == input_plan["required_independent_input_precharge_s"] == 1.2
        )
        assert plan["status_receiving_pulldown_ohm"] == 270000 and plan["third_mcp_input"] == "GPA3"
        footprints = {}
        for ref, part in parts.items():
            identifier = part.findtext("footprint")
            library, name = identifier.split(":")
            path = args.footprints / (library + ".pretty") / (name + ".kicad_mod")
            text = path.read_text()
            assert set(pins[ref]) <= set(re.findall(r'\(pad\s+"([^"]+)"', text)), (ref, identifier)
            footprints[identifier] = sha(path)

        land = relay.footprint_review(
            args.footprints / "Relay_SMD.pretty/Relay_DPDT_Omron_G6K-2F-Y.kicad_mod"
        )
        truth = truth_table(pins)
        sequence = sequences(pins)
        screen = screens(parts)
        for name, data in [
            ("powered-logic", truth),
            ("fault-sequences", sequence),
            ("electrical-screens", screen),
        ]:
            (OUT / (name + ".json")).write_text(json.dumps(data, indent=2) + "\n")
        run("sch", "export", "svg", "--exclude-drawing-sheet", "-o", str(OUT) + os.sep, sheet)
        files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix not in (".prl",)]
        files += [ROOT.parent / "output_stage/verify.py", ROOT.parent / "audio_bypass/verify.py", e10]
        report = dict(
            revision="E11",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            physical_components=55,
            native_erc_violations=0,
            exact_exported_pin_value_contract=True,
            powered_truth_cases=len(truth),
            stateful_fault_sequences=len(sequence),
            external_interfaces=external,
            electrical_screens="electrical-screens.json",
            relay_land_pattern_review=land,
            native_footprint_library_hashes=footprints,
            independent_input_sequence_schematic_implemented=True,
            firmware_evidence="../../../validation/external-firmware.json",
            pcb_routed=False,
            enclosure_placement_complete=False,
            physical_audio_verified=False,
            source_hashes=source_hashes(ROOT, sorted(files)),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad {version}: zero ERC;55 exact contracts;256 powered cases;{len(sequence)} stateful sequences;fresh E10/E05/E09 interfaces. No PCB/bench proof."
    )


if __name__ == "__main__":
    main()
