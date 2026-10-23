#!/usr/bin/env python3
"""Native E12 contracts/interfaces and conditional ADC-driver linear screens."""

import argparse
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path

from ..common import netlists as eda
from ..common.reports import source_hashes
from . import analyze

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
CONTRACT = {
    "U3": {
        "1": "BUF_L",
        "2": "BUF_L",
        "3": "PRE_OUT_L",
        "4": "N12",
        "5": "PRE_OUT_R",
        "6": "BUF_R",
        "7": "BUF_R",
        "8": "P12",
    },
    "U4": {
        "1": "REF_HALF_L",
        "2": "REF_HALF_L",
        "3": "REF_DIV_L",
        "4": "P12",
        "5": "REF_HALF_L",
        "6": "CM_SENSE_L",
        "7": "CM_DRIVE_L",
        "8": "REF_HALF_R",
        "9": "REF_HALF_R",
        "10": "REF_DIV_R",
        "11": "N12",
        "12": "REF_HALF_R",
        "13": "CM_SENSE_R",
        "14": "CM_DRIVE_R",
    },
}
VALUES = {
    "U1": "THS4551IDGKR",
    "U2": "THS4551IDGKR",
    "U3": "OPA1656ID",
    "U4": "OPA4192ID",
    "U5": "LM7705MM/NOPB",
    "U6": "LM7705MM/NOPB",
    "D1": "BAT54S,215",
    "D2": "BAT54S,215",
}
for ci, ch in enumerate(("L", "R")):

    def n(s):
        return s + "_" + ch

    CONTRACT["U" + str(ci + 1)] = {
        "1": n("FB_N"),
        "2": n("VOCM"),
        "3": "V5_REG",
        "4": "DRV_" + ch + "P",
        "5": "DRV_" + ch + "N",
        "6": n("NBIAS"),
        "7": n("PD"),
        "8": n("FB_P"),
    }
    CONTRACT["U" + str(ci + 5)] = {
        "1": n("FLY_P"),
        "2": "AGND",
        "3": "AGND",
        "4": "V5_REG",
        "5": "AGND",
        "6": n("NPUMP"),
        "7": n("RES"),
        "8": n("FLY_N"),
    }
    CONTRACT["D" + str(ci + 1)] = {"1": "AGND", "2": "V5_REG", "3": n("VOCM")}
    pairs = [
        (n("BUF"), n("FB_P")),
        ("AGND", n("FB_N")),
        ("ADC_" + ch + "N", n("FB_P")),
        ("ADC_" + ch + "P", n("FB_N")),
        ("DRV_" + ch + "P", "ADC_" + ch + "P"),
        ("DRV_" + ch + "N", "ADC_" + ch + "N"),
        (n("PRE_OUT"), "AGND"),
        ("REF_ADC" + str(ci + 1), n("REF_DIV")),
        (n("REF_DIV"), "AGND"),
        ("ADC_" + ch + "P", n("CM_SENSE")),
        ("ADC_" + ch + "N", n("CM_SENSE")),
        (n("CM_DRIVE"), n("CM_SENSE")),
        (n("CM_DRIVE"), n("VOCM")),
        ("DRV_ENABLE", n("PD")),
        (n("PD"), "AGND"),
        (n("NPUMP"), n("NBIAS")),
    ]
    values = (
        ["2.49k 0.1%"] * 2
        + ["1.21k 0.1%"] * 2
        + ["3.32R 0.1%"] * 2
        + ["1M 1%"]
        + ["1M 0.1%"] * 2
        + ["100k 0.1%"] * 2
        + ["100M 1%", "10k 1%", "4.7k 1%", "100k 1%", "1R 1%"]
    )
    for k, (pair, value) in enumerate(zip(pairs, values), 1):
        ref = "R" + str(ci * 16 + k)
        CONTRACT[ref] = dict(zip(("1", "2"), pair))
        VALUES[ref] = value
    pairs = [
        ("DRV_" + ch + "N", n("FB_P")),
        ("DRV_" + ch + "P", n("FB_N")),
        ("ADC_" + ch + "P", "ADC_" + ch + "N"),
        ("ADC_" + ch + "P", "AGND"),
        ("ADC_" + ch + "N", "AGND"),
        (n("REF_DIV"), "AGND"),
        (n("CM_DRIVE"), n("CM_SENSE")),
        (n("FLY_P"), n("FLY_N")),
        (n("RES"), "AGND"),
        (n("NPUMP"), "AGND"),
        (n("NBIAS"), "AGND"),
        ("V5_REG", "AGND"),
        ("V5_REG", "AGND"),
        (n("NBIAS"), "AGND"),
    ]
    values = (
        ["1pF C0G +/-0.1pF"] * 2
        + ["47pF C0G 5%"]
        + ["22pF C0G 5%"] * 2
        + ["100nF 25V X7R", "1uF 63V film 10%", "10uF 16V X7R", "47uF 16V X7R"]
        + ["47uF 6.3V X7R"] * 2
        + ["2.2uF 16V X7R"]
        + ["100nF 16V X7R"] * 2
    )
    for k, (pair, value) in enumerate(zip(pairs, values), 1):
        ref = "C" + str(ci * 14 + k)
        CONTRACT[ref] = dict(zip(("1", "2"), pair))
        VALUES[ref] = value
CONTRACT["R33"] = {"1": "V5_REG", "2": "AGND"}
VALUES["R33"] = "1k 1%"
for i in range(29, 35):
    CONTRACT["C" + str(i)] = {"1": "P12" if i % 2 else "N12", "2": "AGND"}
    VALUES["C" + str(i)] = "100nF 50V X7R" if i < 33 else "10uF 50V X7R"
for ref, nets in {
    "J1": ["PRE_OUT_L", "AGND", "PRE_OUT_R"],
    "J2": ["ADC_LP", "ADC_LN", "AGND", "ADC_RP", "ADC_RN", "REF_ADC1", "REF_ADC2"],
    "J3": ["P12", "AGND", "N12", "V5_REG"],
    "J4": ["AGND", "DRV_ENABLE", "NBIAS_L", "NBIAS_R"],
}.items():
    CONTRACT[ref] = {str(i + 1): net for i, net in enumerate(nets)}
    VALUES[ref] = "Conn_01x" + str(len(nets)).zfill(2)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def power_screen(analysis):
    # LM7705 limits at5V and0/-20mA test points, plus explicit interpolation,
    # ripple and post-filter allocations; actual transient load needs measurement.
    bias_min = -0.251 - 0.005
    bias_max = -0.209 + 0.020 * 1.01 + 0.005
    current = analysis["voltage_current_screen"]["maximum_output_current_a"] + 0.001 + 0.00192
    assert (
        current < 0.020
        and bias_max <= analysis["voltage_current_screen"]["minimum_bias_rail_for_screen_v"]
        and 5.1 - bias_min < 5.4
    )
    # Limit calculations use only supply-bounded outputs, not a proven fault
    # response. A failed regulator, external short or stored charge needs bench
    # qualification and the future rail-monitor/protection implementation.
    clamp_current = 12.12 / (10000 * 0.99)
    source_peak = 12.12 / (2490 * 0.999)
    assert clamp_current < 0.002 and source_peak < 0.010
    return dict(
        qualified_v5_input_v=[4.90, 5.10],
        negative_bias_window_required_v=[-0.27, -0.16],
        allocated_filtered_negative_bias_v=[bias_min, bias_max],
        maximum_amplifier_total_supply_v=5.1 - bias_min,
        fda_specified_supply_max_v=5.4,
        conservative_bias_load_a=current,
        lm7705_characterized_load_a=0.020,
        pump_cap_effective_min_f=dict(flying=5e-6, reserve=22e-6, output=22e-6),
        fda_input_series_only_12v_fault_current_a=source_peak,
        vocm_series_only_12v_fault_current_a=clamp_current,
        complete_pin_fault_current_proof=False,
        reverse_power_or_short_tested=False,
        raw_adc_voltage_bounds_if_outputs_remain_within_valid_rails_v=[-0.27, 5.1],
        raw_adc_abs_limits_v=[-0.4, 6.0],
        supply_dv_dt_max_required_v_per_us=1,
        independent_negative_bias_monitor_implemented=False,
        note="No manufacturer max startup/ripple/transient interpolation guarantee. Qualify actual current/ripple/overshoot, reference loading, clamps and partial power; no fabricated fail-safe claim.",
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
    with tempfile.TemporaryDirectory(prefix="rmx-e12-") as temporary:
        temp = Path(temporary)
        env = os.environ.copy()
        env["KICAD_CONFIG_HOME"] = str(temp / "config")
        env["KICAD10_FOOTPRINT_DIR"] = str(args.footprints)
        env["FONTCONFIG_FILE"] = str(ROOT.parents[2] / "build-hardware/kicad-fonts.conf")

        def run(*command):
            result = subprocess.run(
                [str(args.kicad_cli), *map(str, command)], capture_output=True, text=True, env=env
            )
            if result.returncode:
                raise RuntimeError(str(command) + "\n" + result.stdout + "\n" + result.stderr)
            return result.stdout.strip()

        version = run("version")
        sheet = ROOT / "adc_driver.kicad_sch"
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
        assert pins == CONTRACT, (pins, CONTRACT)
        assert len(parts) == 79 and {r: c.findtext("value") for r, c in parts.items()} == VALUES
        external = {}
        for name in ["input_range", "converter"]:
            source = ROOT.parent / name / (name + ".kicad_sch")
            target = temp / (name + ".xml")
            run("sch", "export", "netlist", "--format", "kicadxml", "-o", target, source)
            _, other = eda.netlist(target)
            if name == "input_range":
                assert pins["J1"] == other["J2"]
            else:
                assert pins["J2"] == other["J2"] and other["J5"]["8"] == "CHIP_EN"
                assert other["J4"] == {"1": "V5_REG", "2": "AGND", "3": "V3V3_IO"}
            external[name] = dict(schematic_sha256=sha(source), exported_interface_matches=True)
        footprints = {}
        for ref, part in parts.items():
            identifier = part.findtext("footprint")
            library, name = identifier.split(":")
            path = args.footprints / (library + ".pretty") / (name + ".kicad_mod")
            text = path.read_text()
            assert set(pins[ref]) <= set(re.findall(r'\(pad\s+"([^"]+)"', text)), (ref, identifier)
            footprints[identifier] = sha(path)
        analysis = analyze.analyze(parts, pins)
        analysis["own_noise_screen"] = analyze.noise(parts, pins)
        analysis["power_fault_screen"] = power_screen(analysis)
        # The unchanged E10 screen bounds BUF_OUT before its passive33.2Ohm
        # output resistor. A following1M/FET load cannot exceed this ideal
        # pre-resistor voltage, so4.06Vrms covers the inherited gain corners.
        e10_root = ROOT.parent / "input_range"
        e10_record = json.loads((e10_root / "generated/verification.json").read_text())
        for name, expected in e10_record["source_hashes"].items():
            assert sha(e10_root / name) == expected, name
        e10_analysis = e10_root / "generated/circuit-analysis.json"
        e10_bound = json.loads(e10_analysis.read_text())["voltage_screen"][
            "maximum_preamp_peak_v"
        ] / math.sqrt(2)
        assert e10_bound < 4.06
        analysis["e10_inherited_voltage_bound"] = dict(
            maximum_buf_out_rms_v=e10_bound,
            allocated_pre_out_rms_v=4.06,
            source_sha256=sha(e10_analysis),
            interpretation="Ideal bounded BUF_OUT before passive output R; native E10 circuit sources unchanged; not physical overload/swing proof",
        )
        plan = json.loads((ROOT / "integration.json").read_text())
        assert (
            plan["nominal_raw_differential_gain"] == 1210 / 2490 and plan["minimum_input_load_ohm"] == 100000
        )
        assert (
            not plan["pcb_routed"]
            and not plan["physical_audio_verified"]
            and not plan["negative_bias_monitor_implemented"]
        )
        (OUT / "circuit-analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
        run("sch", "export", "svg", "--exclude-drawing-sheet", "-o", str(OUT) + os.sep, sheet)
        files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix not in (".kicad_prl", ".prl", ".lck")]
        files += [ROOT.parent / "dac_receiver/verify.py", ROOT.parent / "output_stage/verify.py"]
        files += [e10_root / "generated/verification.json", e10_analysis]
        report = dict(
            revision="E12",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            physical_components=79,
            native_erc_violations=0,
            exact_exported_pin_value_contract=True,
            ideal_ac_cases=analysis["ideal_ac_cases"],
            mode_resistor_load_corners=analysis["mode_resistor_load_corners"],
            allocated_dc_cases=analysis["allocated_dc_cases"],
            finite_model_sensitivity_cases=analysis["finite_model_sensitivity"]["cases"],
            independent_dc_superposition_corners=analysis["independent_dc_superposition_bounds"][
                "resistor_reference_corners"
            ],
            external_interfaces=external,
            native_footprint_library_hashes=footprints,
            adc_driver_schematic_implemented=True,
            reference_bias_servo_schematic_implemented=True,
            pcb_routed=False,
            enclosure_placement_complete=False,
            negative_bias_monitor_implemented=False,
            manufacturer_macromodel_stability_verified=False,
            physical_audio_verified=False,
            adc_scale_calibrated=False,
            source_hashes=source_hashes(ROOT, sorted(files)),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad {version}: zero ERC;79 exact contracts;18 ideal AC,192 resistor/load corners,128 allocated DC,512 DC superposition bounds and36 finite-model cases. Native ADC driver prototype; power/stability/scale/noise/PCB/bench gates remain open."
    )


if __name__ == "__main__":
    main()
