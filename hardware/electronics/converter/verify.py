#!/usr/bin/env python3
"""E09 native ERC, independent pin audit, supply/timing and logic screens.

The checks use exported nets and datasheet bounds. They do not establish
physical bus timing, analog performance, subthreshold behavior or PCB fit.
"""

import argparse
import datetime
import hashlib
import itertools
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..common import netlists as eda
from ..common.reports import source_hashes

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

CONTRACT = {
    "U1": {
        str(k): v
        for k, v in {
            1: "CHIP_EN",
            2: "AGND",
            3: "AGND",
            4: "DAC_LN",
            5: "DAC_LP",
            6: "REF_DAC_BUF",
            7: "DAC_RN",
            8: "DAC_RP",
            9: "AGND",
            10: "REF_DAC_LN",
            11: None,
            12: "A4V5",
            13: "REF_ADC_LN",
            14: "REF_ADC1",
            15: "ADC_LP",
            16: "ADC_LN",
            17: "AGND",
            18: "AGND",
            19: "ADC_RN",
            20: "ADC_RP",
            21: "REF_ADC2",
            22: "AGND",
            23: "REF_PLL_LN",
            24: "REF_PLL",
            25: "A3V3",
            26: "MCLK",
            27: "AGND",
            28: "DVDD_CORE",
            29: "AGND",
            30: "V3V3_IO",
            31: "BCLK_SRC",
            32: "WS_SRC",
            33: "ADC_DATA_SRC",
            34: None,
            35: "DAC_DATA",
            36: None,
            37: "CLK_VALID",
            38: "RAMP_DONE",
            39: None,
            40: None,
            41: None,
            42: None,
            43: None,
            44: "SDA",
            45: "SCL",
            46: "AGND",
            47: "AGND",
            48: "AGND",
            49: "AGND",
        }.items()
    },
    "U2": {"1": "V5_REG", "2": "AGND", "3": "V5_REG", "4": None, "5": "A3V3"},
    "U3": {"1": "V5_REG", "2": "AGND", "3": "V5_REG", "4": None, "5": "A4V5"},
    "Y1": {"1": "V3V3_IO", "2": "AGND", "3": "MCLK_SRC", "4": "V3V3_IO"},
    "U4": {"1": "V3V3_IO", "2": "AGND", "3": "V3V3_IO", "4": "V3V3_IO", "5": None, "6": "CODEC_PGOOD"},
    "U5": {"1": "A3V3", "2": "AGND", "3": "V3V3_IO", "4": "V3V3_IO", "5": None, "6": "CODEC_PGOOD"},
    "U6": {"1": "SENSE_4V5", "2": "AGND", "3": "V3V3_IO", "4": "V3V3_IO", "5": None, "6": "CODEC_PGOOD"},
    "U8": {
        "1": "V3V3_IO",
        "2": "AGND",
        "3": "SETTLE_ENABLE",
        "4": "V3V3_IO",
        "5": "CT_SETTLE",
        "6": "TIMER_OK",
    },
    "U7": {
        "1": "CODEC_PGOOD",
        "2": "PRE_ANALOG_OK",
        "3": "SUPPLY_OK",
        "4": "SUPPLY_OK",
        "5": "CODEC_RUN",
        "6": "CHIP_EN",
        "7": "AGND",
        "8": "CODEC_FLAGS",
        "9": "CLK_VALID",
        "10": "RAMP_DONE",
        "11": "SETTLE_ENABLE",
        "12": "CHIP_EN",
        "13": "CODEC_FLAGS",
        "14": "V3V3_IO",
    },
    "U9": {"1": "SETTLE_ENABLE", "2": "TIMER_OK", "3": "AGND", "4": "ANALOG_OK", "5": "V3V3_IO"},
    "J1": dict(zip(map(str, range(1, 6)), ["DAC_LP", "DAC_LN", "AGND", "DAC_RP", "DAC_RN"])),
    "J2": dict(
        zip(map(str, range(1, 8)), ["ADC_LP", "ADC_LN", "AGND", "ADC_RP", "ADC_RN", "REF_ADC1", "REF_ADC2"])
    ),
    "J3": dict(zip(map(str, range(1, 6)), ["AGND", "BCLK", "WS", "ADC_DATA", "DAC_DATA"])),
    "J4": {"1": "V5_REG", "2": "AGND", "3": "V3V3_IO"},
    "J5": dict(
        zip(
            map(str, range(1, 9)),
            ["AGND", "SCL", "SDA", "CODEC_RUN", "PRE_ANALOG_OK", "ANALOG_OK", "CODEC_PGOOD", "CHIP_EN"],
        )
    ),
}
R_PARTS = [
    (2000, "SCL", "V3V3_IO"),
    (2000, "SDA", "V3V3_IO"),
    (10000, "CODEC_PGOOD", "V3V3_IO"),
    (10000, "TIMER_OK", "V3V3_IO"),
    (47000, "CODEC_RUN", "AGND"),
    (47000, "PRE_ANALOG_OK", "AGND"),
    (100000, "CLK_VALID", "AGND"),
    (100000, "RAMP_DONE", "AGND"),
    (100000, "CHIP_EN", "AGND"),
    (100000, "ANALOG_OK", "AGND"),
    (27700, "A4V5", "SENSE_4V5"),
    (10000, "SENSE_4V5", "AGND"),
    (33, "MCLK_SRC", "MCLK"),
    (33, "BCLK_SRC", "BCLK"),
    (33, "WS_SRC", "WS"),
    (33, "ADC_DATA_SRC", "ADC_DATA"),
]
C_PARTS = [
    (1e-6, "V3V3_IO"),
    (1e-6, "DVDD_CORE"),
    (100e-9, "REF_DAC_BUF"),
    (1e-6, "REF_DAC_BUF"),
    (1e-6, "A3V3"),
    (1e-6, "REF_DAC_LN"),
    (1e-6, "A4V5"),
    (1e-6, "REF_ADC_LN"),
    (1e-6, "REF_PLL_LN"),
    (100e-9, "REF_PLL"),
    (1e-6, "REF_PLL"),
    (100e-9, "REF_ADC1"),
    (1e-6, "REF_ADC1"),
    (100e-9, "REF_ADC2"),
    (1e-6, "REF_ADC2"),
    (2.2e-6, "V5_REG"),
    (10e-6, "A3V3"),
    (2.2e-6, "V5_REG"),
    (10e-6, "A4V5"),
    *[(100e-9, "V3V3_IO") for _ in range(7)],
    (2.2e-6, "CT_SETTLE"),
    (100e-9, "V3V3_IO"),
    (100e-9, "A3V3"),
]
for i, (_, a, b) in enumerate(R_PARTS, 1):
    CONTRACT["R" + str(i)] = {"1": a, "2": b}
for i, (_, a) in enumerate(C_PARTS, 1):
    CONTRACT["C" + str(i)] = {"1": a, "2": "AGND"}
EXPECTED_PARTS = {
    "U1": "ES9292QPRO",
    "U2": "TPS7A2033PDBVR",
    "U3": "TPS7A2045PDBVR",
    "U4": "TPS389033DSET",
    "U5": "TPS389033DSET",
    "U6": "TPS389001DSET",
    "U8": "TPS389033DSET",
    "U7": "SN74HCS08DR",
    "U9": "SN74LVC1G08DCKR",
    "Y1": "ECS-2520MVLC-245.7-BN-TR",
}


def logic(pins, values, timer):
    state = dict(values, TIMER_OK=timer)
    gates = [
        ("U7", a, b, y)
        for a, b, y in [("1", "2", "3"), ("4", "5", "6"), ("9", "10", "8"), ("12", "13", "11")]
    ]
    gates.append(("U9", "1", "2", "4"))
    for _ in range(8):
        for ref, a, b, y in gates:
            if pins[ref][a] in state and pins[ref][b] in state:
                state[pins[ref][y]] = state[pins[ref][a]] and state[pins[ref][b]]
    return state


def electrical_screens(parts, pins):
    r = {f"R{i}": eda.number(parts[f"R{i}"].findtext("value")) for i in range(1, 17)}
    # Fixed 3.3V supervisor: worst negative trip and conservative positive trip.
    fixed_low = 3.17 * 0.99
    fixed_high = 3.17 * 1.01 * (1 + 0.00825)
    assert 3.3 * 0.95 < fixed_low < fixed_high < 3.3 * 0.985
    # Adjustable 4.5V threshold: reference, independent divider signs, hysteresis,
    # and both directions of a conservative 100nA sense-current bound.
    thresholds = []
    for st, sb, sv, si in itertools.product((-1, 1), repeat=4):
        top = r["R11"] * (1 + st * 0.001)
        bottom = r["R12"] * (1 + sb * 0.001)
        vref = 1.15 * (1 + sv * 0.01)
        low = vref * (1 + top / bottom) + si * 100e-9 * top
        high = vref * (1 + 0.00825) * (1 + top / bottom) + si * 100e-9 * top
        thresholds.append((low, high))
    low = min(v[0] for v in thresholds)
    high = max(v[1] for v in thresholds)
    assert 4.5 * 0.95 < low < high < 4.5 * 0.985, (low, high)
    supplies = []
    for voltage, allocation in [(3.3, 0.03), (4.5, 0.1)]:
        vmin, vmax = voltage * 0.985, voltage * 1.015
        assert vmin >= voltage * 0.95 and vmax <= voltage * 1.05
        assert 4.9 >= voltage + 0.3 and 4.9 - vmax >= 0.145
        supplies.append(
            dict(
                nominal_v=voltage,
                dc_range_v=[vmin, vmax],
                ldo_input_range_v=[4.9, 5.1],
                minimum_input_above_high_output_v=4.9 - vmax,
                ldo_accuracy_condition_input_min_v=voltage + 0.3,
                allocated_load_a=allocation,
                maximum_dissipation_at_allocation_w=(5.1 - vmin) * allocation,
                dropout_reference_v=0.145,
                dropout_reference_condition="300mA, VOUT in2.5..5.5V, SOT23-5; load/temperature review still required",
            )
        )
    # CT capacitance must be qualified, not inferred from nominal MLCC value.
    cmin, cmax, ileak = 1.5e-6, 2.8e-6, 100e-9
    delay_min = cmin * 1.17 / (1.35e-6 + ileak)
    delay_max = cmax * 1.29 / (0.90e-6 - ileak) + 25e-6
    delay_nom = eda.number(parts["C27"].findtext("value")) * 1.23 / 1.15e-6 + 25e-6
    assert delay_min >= 1
    cases = 0
    for flags in itertools.product((False, True), repeat=8):
        io, analog3, analog4, pre, run, clock, ramp, timer = flags
        pg = io and analog3 and analog4
        state = logic(
            pins,
            dict(CODEC_PGOOD=pg, PRE_ANALOG_OK=pre, CODEC_RUN=run, CLK_VALID=clock, RAMP_DONE=ramp),
            timer,
        )
        assert state["CHIP_EN"] == (pg and pre and run)
        assert state["SETTLE_ENABLE"] == (pg and pre and run and clock and ramp)
        assert state["ANALOG_OK"] == all(flags)
        cases += 1
    # Event-level model: any qualified condition loss removes output immediately
    # and resets the timer. It does not simulate supervisor glitch immunity/CT
    # discharge or sub-microsecond faults.
    events = []
    for fault in ("CODEC_PGOOD", "PRE_ANALOG_OK", "CODEC_RUN", "CLK_VALID", "RAMP_DONE"):
        inputs = {n: True for n in ("CODEC_PGOOD", "PRE_ANALOG_OK", "CODEC_RUN", "CLK_VALID", "RAMP_DONE")}
        assert logic(pins, inputs, True)["ANALOG_OK"]
        inputs[fault] = False
        assert not logic(pins, inputs, True)["ANALOG_OK"]
        inputs[fault] = True
        assert not logic(pins, inputs, False)["ANALOG_OK"]
        assert logic(pins, inputs, True)["ANALOG_OK"]
        events.append(dict(fault=fault, drop_without_waiting_for_timer=True, requalification_required=True))
    mclk = 24.576e6
    ppm = 53e-6
    mc_range = [mclk * (1 - ppm), mclk * (1 + ppm)]
    assert mc_range[0] > 22.5792e6 and mc_range[1] < 49.152e6
    assert mclk / 8 == 3072000 and mclk / 8 / 64 == 48000
    # Shared pullups: prove only the declared lumped capacitance/current contract.
    rise_cap = 300e-9 / (0.8473 * r["R1"] * 1.01)
    pull_current = 3.465 / (r["R1"] * 0.99)
    assert pull_current < 0.003
    # Analog PG wired-AND has three open drains. Worst leakage plus one gate input
    # remains comfortably high; actual bus/flag edges are not measured.
    pg_high = 3.135 - (3 * 250e-9 + 1e-6) * r["R3"] * 1.01
    assert pg_high > 2.5
    return dict(
        revision="E09",
        supervisors=dict(
            fixed_3v3_falling_trip_min_v=fixed_low,
            fixed_3v3_rising_trip_max_v=fixed_high,
            adjustable_4v5_falling_trip_min_v=low,
            adjustable_4v5_rising_trip_max_v=high,
            divider_corner_cases=len(thresholds),
            pg_high_min_with_leakage_v=pg_high,
            limit="UV qualification only; finite response/ramp/glitch behavior and overvoltage protection not verified",
        ),
        local_supplies=supplies,
        qualification=dict(
            required_from_e08_s=1,
            minimum_delay_s=delay_min,
            nominal_delay_s=delay_nom,
            maximum_delay_s=delay_max,
            ct_effective_range_f=[cmin, cmax],
            allowed_total_ct_injected_leakage_a=ileak,
            current_bounds_a=[0.9e-6, 1.35e-6],
            threshold_bounds_v=[1.17, 1.29],
            native_logic_combinations=cases,
            event_level_fault_cases=events,
            limits=[
                "Timing bound conditional on qualified capacitor/leakage",
                "Event model assumes recognized reset intervals",
                "No CT discharge, power-ramp, glitch, clock-loss or transistor simulation",
                "No MCU permit until ANALOG_OK is read high; current prototype firmware does not implement this interface",
            ],
        ),
        clock=dict(
            source="ECS-2520MVLC-245.7-BN-TR",
            nominal_hz=mclk,
            combined_first_year_frequency_screen_ppm=53,
            mclk_range_hz=mc_range,
            codec_is_master=True,
            bclk_divisor=8,
            bclk_hz=mclk / 8,
            bits_per_frame=64,
            frame_rate_hz=mclk / 8 / 64,
            frame_rate_range_hz=[v / 512 for v in mc_range],
            oscillator_duty_range_percent=[45, 55],
            maximum_declared_clock_load_pf=15,
            startup_datasheet_max_s=0.005,
            jitter_actual_at_24m576_verified=False,
            note="150fs typical jitter is specified at50MHz; do not claim it at24.576MHz. MCLK and serial clocks share this source.",
        ),
        i2c=dict(
            seven_bit_address=0x18,
            wire_write=0x30,
            wire_read=0x31,
            chip_id_register=225,
            chip_id_expected=0xAF,
            bus_clock_hz=400000,
            single_pair_pullup_ohm=r["R1"],
            maximum_lumped_capacitance_f=rise_cap,
            worst_single_pair_sink_current_a=pull_current,
            other_known_seven_bit_addresses=[0x20, 0x21, 0x22, 0x30, 0x36],
            note="Figure4 distinguishes write0x30/read0x31; divide wire address by2. Include all module pullups and wiring in actual bus budget.",
        ),
        codec_footprint_qualified=False,
        pcb_routed=False,
        complete_converter_implemented=False,
        physical_audio_verified=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    parser.add_argument("--footprint-dir", type=Path)
    args = parser.parse_args()
    cli = Path(shutil.which(args.kicad_cli) or args.kicad_cli).resolve()
    fp = args.footprint_dir or cli.parents[1] / "SharedSupport/footprints"
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e09-") as temporary:
        temp = Path(temporary)
        env = dict(os.environ, KICAD_CONFIG_HOME=str(temp / "config"), KICAD10_FOOTPRINT_DIR=str(fp))
        if Path("/System/Library/Fonts").is_dir():
            (temp / "cache").mkdir()
            font = temp / "fonts.conf"
            font.write_text(
                '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>/System/Library/Fonts</dir><dir>/Library/Fonts</dir><cachedir>'
                + str(temp / "cache")
                + "</cachedir></fontconfig>"
            )
            env["FONTCONFIG_FILE"] = str(font)

        def run(*command):
            r = subprocess.run([str(cli), *map(str, command)], capture_output=True, text=True, env=env)
            if r.returncode:
                raise RuntimeError(f"{command}: {r.returncode}\n{r.stdout}\n{r.stderr}")
            return r.stdout.strip()

        version = run("version")
        run(
            "sch",
            "erc",
            "--severity-all",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            OUT / "erc.json",
            ROOT / "converter.kicad_sch",
        )
        assert not any(s["violations"] for s in json.loads((OUT / "erc.json").read_text())["sheets"])
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            ROOT / "converter.kicad_sch",
        )
        parts, pins = eda.netlist(OUT / "netlist.xml")
        for ref, expected in CONTRACT.items():
            for pin, net in expected.items():
                if net is None:
                    actual = pins.get(ref, {}).get(pin)
                    assert actual is None or actual.startswith("unconnected-"), (ref, pin, actual)
                    pins.setdefault(ref, {})[pin] = None
        assert pins == CONTRACT, (pins, CONTRACT)
        assert len(parts) == 60
        for ref, name in EXPECTED_PARTS.items():
            assert parts[ref].findtext("value") == name
        for i, (value, *_) in enumerate(R_PARTS, 1):
            assert math.isclose(eda.number(parts["R" + str(i)].findtext("value")), value, rel_tol=1e-12)
        for i, (value, *_) in enumerate(C_PARTS, 1):
            assert math.isclose(eda.number(parts["C" + str(i)].findtext("value")), value, rel_tol=1e-12)
        external = {}
        for name, filename in [("dac_receiver", "dac_receiver"), ("bypass", "bypass")]:
            sheet = ROOT.parent / name / (filename + ".kicad_sch")
            path = temp / (name + ".xml")
            run("sch", "export", "netlist", "--format", "kicadxml", "-o", path, sheet)
            other_parts, other = eda.netlist(path)
            if name == "dac_receiver":
                assert pins["J1"] == other["J1"]
            else:
                assert pins["J5"]["6"] == other["J3"]["3"] == "ANALOG_OK"
            external[name] = dict(
                schematic_sha256=hashlib.sha256(sheet.read_bytes()).hexdigest(), interface_matches=True
            )
        e08 = ROOT.parent / "dac_receiver/generated/circuit-analysis.json"
        earlier = json.loads(e08.read_text())
        assert earlier["dc_block"]["required_stable_analog_qualification_s"] == 1
        screens = electrical_screens(parts, pins)
        (OUT / "electrical-screens.json").write_text(json.dumps(screens, indent=2) + "\n")
        plan = json.loads((ROOT / "interface-plan.json").read_text())
        assert set(plan["module_gpio"]) == {f"D{i}" for i in range(31)}
        assert len({v["net"] for v in plan["module_gpio"].values()}) == 31
        assert len({v["stm32_pin"] for v in plan["module_gpio"].values()}) == 31
        for n, net in [
            (0, "CODEC_RUN"),
            (25, "ADC_DATA"),
            (26, "DAC_DATA"),
            (27, "WS"),
            (28, "BCLK"),
            (29, "MCU_PERMIT"),
            (30, "ARMED"),
        ]:
            assert plan["module_gpio"][f"D{n}"]["net"] == net
        assert plan["codec"]["address_seven_bit"] == screens["i2c"]["seven_bit_address"]
        assert not plan["firmware_adapter_implemented"] and not plan["hardware_verified"]
        sdk_root = ROOT.parents[2] / "build-hardware/libDaisy"
        sdk_checked = False
        if sdk_root.is_dir():
            header = (sdk_root / "src/daisy_seed.h").read_text()
            for key, entry in plan["module_gpio"].items():
                match = re.search(r"constexpr Pin " + key + r"\s*= Pin\(PORT([A-Z]), (\d+)\);", header)
                assert match and entry["stm32_pin"] == "P" + match.group(1) + match.group(2), key
            for p, h in plan["sdk_source_sha256"].items():
                assert hashlib.sha256((ROOT.parents[2] / p).read_bytes()).hexdigest() == h, p
            sdk_checked = True
        footprints = {}
        unassigned = []
        pad_geometry = {}
        for ref, part in parts.items():
            identifier = part.findtext("footprint") or ""
            if not identifier:
                unassigned.append(ref)
                continue
            library, name = identifier.split(":")
            path = (
                (ROOT if library == "RMX_Converter" else fp) / (library + ".pretty") / (name + ".kicad_mod")
            )
            text = path.read_text()
            pads = set(re.findall(r'\(pad\s+"([^"]+)"', text))
            assert set(pins[ref]) <= pads, (ref, pads)
            if ref in ("U4", "U5", "U6", "U8", "Y1"):
                fields = re.findall(
                    r'\(pad\s+"([^"]+)"\s+smd\s+\w+\s+\(at\s+([-.0-9]+)\s+([-.0-9]+)\)\s+\(size\s+([-.0-9]+)\s+([-.0-9]+)\)',
                    text,
                )
                actual = {n: list(map(float, (x, y, w, h))) for n, x, y, w, h in fields}
                if ref == "Y1":
                    expected = {
                        "1": [-0.725, -0.925, 0.8, 0.9],
                        "2": [-0.725, 0.925, 0.8, 0.9],
                        "3": [0.725, 0.925, 0.8, 0.9],
                        "4": [0.725, -0.925, 0.8, 0.9],
                    }
                else:
                    expected = {
                        str(n): [x, y, 0.8 if n == 2 else 0.7, 0.25]
                        for n, x, y in [
                            (1, -0.6, -0.5),
                            (2, -0.6, 0),
                            (3, -0.6, 0.5),
                            (4, 0.6, 0.5),
                            (5, 0.6, 0),
                            (6, 0.6, -0.5),
                        ]
                    }
                assert actual == expected, (ref, actual, expected)
                pad_geometry[ref] = dict(
                    copper_matches_reviewed_drawing=True, pads_mm=actual, mask_paste_assembly_qualified=False
                )
            footprints[identifier] = hashlib.sha256(path.read_bytes()).hexdigest()
        assert unassigned == ["U1"], unassigned
        run(
            "sch",
            "export",
            "svg",
            "--exclude-drawing-sheet",
            "-o",
            str(OUT) + os.sep,
            ROOT / "converter.kicad_sch",
        )
        files = [
            "spec.py",
            "generate.py",
            "verify.py",
            "converter.kicad_sch",
            "converter.kicad_pro",
            "RMX_E09.kicad_sym",
            "sym-lib-table",
            "fp-lib-table",
            "components.json",
            "bom.csv",
            "../output_stage/verify.py",
            "RMX_Converter.pretty/TI_DSE0006A_TPS3890.kicad_mod",
            "dependencies.json",
            "interface-plan.json",
        ]
        report = dict(
            revision="E09",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            physical_components=60,
            native_erc_violations=0,
            exact_exported_pin_and_value_contract=True,
            codec_physical_pins_checked=49,
            external_interfaces=external,
            powered_logic_cases=256,
            divider_corner_cases=screens["supervisors"]["divider_corner_cases"],
            minimum_conditional_settling_s=screens["qualification"]["minimum_delay_s"],
            footprint_library_hashes=footprints,
            reviewed_pad_geometry=pad_geometry,
            unassigned_footprints=unassigned,
            codec_footprint_qualified=False,
            pcb_routed=False,
            enclosure_placement_complete=False,
            external_mcu_adapter_implemented=False,
            physical_audio_verified=False,
            proposed_pin_plan_resource_audit=True,
            pinned_sdk_source_checked=sdk_checked,
            e08_settling_requirement_source_sha256=hashlib.sha256(e08.read_bytes()).hexdigest(),
            source_hashes=source_hashes(ROOT, files),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"E09 KiCad {version}: zero ERC, 60 exact component contracts, 49 codec pins, 256 powered logic cases, conditional settling >= {screens['qualification']['minimum_delay_s']:.3f}s. Codec footprint/PCB/MCU/bench integration unfinished."
    )


if __name__ == "__main__":
    main()
