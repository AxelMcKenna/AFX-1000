#!/usr/bin/env python3
"""Check E19's native schematic against independent board/firmware contracts.

This does not certify a PCB, socket stack, complete power budget or hardware.
"""

import argparse
import csv
import datetime
import itertools
import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path

from ..common import netlists as eda
from ..common.placement import footprint_root
from ..common.reports import sha, source_hashes
from ..common.sexpr import children, first, read_sexpr
from .check_board import verify as verify_board

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
FIRMWARE = ROOT.parents[1] / "firmware"
REPO = ROOT.parents[2]
KNOBS = [
    "input",
    "output",
    "low",
    "mid",
    "high",
    "scene_depth",
    "x_level",
    "x_pitch",
    "scene_time",
    "scene_resonance",
]


def circuit(parts, pins):
    """Fixed physical pin contract; deliberately does not import the generator."""
    expected = {}
    values = {}

    def part(ref, value, nets):
        expected[ref] = {str(i + 1): net for i, net in enumerate(nets)}
        values[ref] = value

    module = [
        "CODEC_RUN",
        "SDMMC_D3_SRC",
        "SDMMC_D2_SRC",
        "SDMMC_D1_SRC",
        "SDMMC_D0_SRC",
        "SDMMC_CMD_SRC",
        "SDMMC_CLK_SRC",
        "LED_XLAT_SRC",
        "LED_SCK_SRC",
        "GAIN_REQ",
        "LED_MOSI_SRC",
        "SCL",
        "SDA",
        "HEARTBEAT",
        "LED_BLANK_SRC",
        "unconnected-(U1-AUDIO_IN_L-Pad16)",
        "unconnected-(U1-AUDIO_IN_R-Pad17)",
        "unconnected-(U1-AUDIO_OUT_L-Pad18)",
        "unconnected-(U1-AUDIO_OUT_R-Pad19)",
        "AGND",
        "V3V3_ANALOG",
        *[f"POT_ADC_{i:02d}" for i in range(10)],
        "ADC_DATA",
        "DAC_DATA_SRC",
        "WS",
        "BCLK",
        "MCU_PERMIT",
        "ARMED",
        "V3V3_IO",
        "SEED_VIN",
        "AGND",
    ]
    part("U1", "DaisySeed3", module)
    headers = {
        "J1": ["5V_DIG", "AGND"],
        "J2": ["AGND", "V3V3_IO", "SCL", "SDA", "CODEC_RUN"],
        "J3": ["AGND", "HEARTBEAT", "MCU_PERMIT", "GAIN_REQ", "ARMED", "BYPASS_SENSE"],
        "J4": ["AGND", "MODE_SEND_RETURN", "BYPASS_SENSE", "ANALOG_OK", "INPUT_READY"],
        "J5": ["AGND", "BCLK", "WS", "ADC_DATA", "DAC_DATA"],
        "J6": ["AGND", "V3V3_IO", "SCL", "SDA", "CODEC_RUN", "ANALOG_OK"],
        "J7": ["AGND", "INPUT_READY"],
        "J8": ["AGND", "MODE_SEND_RETURN"],
        "J9": ["AGND", "V3V3_IO", "SCL", "SDA"],
        "J10": ["AGND", "V3V3_IO", "SCL", "SDA"],
        "J11": ["AGND", "5V_DIG", "V3V3_IO", "LED_MOSI", "LED_SCK", "LED_XLAT", "LED_BLANK", "AGND"],
        "J12": ["AGND", "V3V3_IO", "SDMMC_D0", "SDMMC_D1", "SDMMC_D2", "SDMMC_D3", "SDMMC_CMD", "SDMMC_CLK"],
    }
    for ref, sequence in headers.items():
        part(ref, f"Header{len(sequence)}", sequence)
    for ref, value, sequence in [
        ("R1", "0.47R 1% 1W", ["5V_DIG", "SEED_VIN"]),
        ("R2", "10k 1%", ["LED_BLANK", "V3V3_IO"]),
        ("R3", "100k 1%", ["MCU_PERMIT", "AGND"]),
        ("R4", "100k 1%", ["GAIN_REQ", "AGND"]),
        ("R5", "100k 1%", ["ARMED", "AGND"]),
        ("R6", "100k 1%", ["CODEC_RUN", "AGND"]),
    ]:
        part(ref, value, sequence)
    for index, net in enumerate(
        [
            "LED_XLAT",
            "LED_SCK",
            "LED_MOSI",
            "LED_BLANK",
            "DAC_DATA",
            "SDMMC_D0",
            "SDMMC_D1",
            "SDMMC_D2",
            "SDMMC_D3",
            "SDMMC_CMD",
            "SDMMC_CLK",
        ]
    ):
        part(f"R{10 + index}", "33R 1%", [net + "_SRC", net])
    for index, (value, rail) in enumerate(
        [
            ("22uF 25V X7R", "SEED_VIN"),
            ("100nF 16V X7R", "SEED_VIN"),
            ("1uF 16V X7R", "V3V3_ANALOG"),
            ("100nF 16V X7R", "V3V3_ANALOG"),
            ("4.7uF 16V X7R", "V3V3_IO"),
            ("100nF 16V X7R", "V3V3_IO"),
        ]
    ):
        part(f"C{index + 1}", value, [rail, "AGND"])
    for index in range(10):
        raw, adc = f"POT_RAW_{index:02d}", f"POT_ADC_{index:02d}"
        part(f"J{20 + index}", "Header3", ["AGND", raw, "V3V3_ANALOG"])
        part(f"R{31 + index}", "1k 1%", [raw, adc])
        part(f"R{41 + index}", "1M 1%", [adc, "AGND"])
        part(f"C{11 + index}", "100nF 16V X7R", [adc, "AGND"])
    assert len(expected) == 76 and len(module) == 40
    assert pins == expected, (pins, expected)
    assert {ref: c.findtext("value") for ref, c in parts.items()} == values
    # A rail-short check catches unintended label aliases independently of values.
    assert len({pins["U1"][str(i)] for i in (20, 21, 38, 39)}) == 4
    return expected


def firmware_contract(pins):
    board = (FIRMWARE / "BoardIO.h").read_text()
    mapping = {
        "heartbeat": (13, "HEARTBEAT"),
        "gainMode": (9, "GAIN_REQ"),
        "blank": (14, "LED_BLANK_SRC"),
        "latch": (7, "LED_XLAT_SRC"),
    }
    for variable, (gpio, net) in mapping.items():
        assert re.search(rf"\b{variable}\.Init\(seed::D{gpio},", board)
        assert pins["U1"][str(gpio + 1)] == net
    for field, gpio, net in [
        ("sclk", 8, "LED_SCK_SRC"),
        ("mosi", 10, "LED_MOSI_SRC"),
        ("scl", 11, "SCL"),
        ("sda", 12, "SDA"),
    ]:
        assert re.search(rf"pin_config\.{field}\s*=\s*seed::D{gpio}\s*;", board)
        assert pins["U1"][str(gpio + 1)] == net
    profile = (FIRMWARE / "BoardProfile.h").read_text()
    for variable, gpio, physical, net in [
        ("permitPin", 29, 36, "MCU_PERMIT"),
        ("armedPin", 30, 37, "ARMED"),
        ("resetPin", 0, 1, "CODEC_RUN"),
    ]:
        assert re.search(rf"\b{variable}\s*=\s*externalConverter\s*\?\s*{gpio}\s*:", profile)
        assert pins["U1"][str(physical)] == net
    audio = (FIRMWARE / "ExternalAudio.cpp").read_text()
    for field, gpio, physical, net in [
        ("sb", 25, 32, "ADC_DATA"),
        ("sa", 26, 33, "DAC_DATA_SRC"),
        ("fs", 27, 34, "WS"),
        ("sck", 28, 35, "BCLK"),
    ]:
        assert re.search(rf"pin_config\.{field}\s*=\s*seed::D{gpio}\s*;", audio)
        assert pins["U1"][str(physical)] == net
    main = (FIRMWARE / "main.cpp").read_text()
    assert re.search(r"adc\[i\]\.InitSingle\(daisy::DaisySeed::GetPin\(15\s*\+\s*i\)\)", main)
    header = (REPO / "hardware/runtime/include/rmx/controls/HardwareControls.h").read_text()
    ids = re.search(r"\bknobIds\s*\{([^}]+)\}", header, re.S).group(1)
    assert re.findall(r'"([a-z_]+)"', ids) == KNOBS
    external = json.loads((FIRMWARE / "external-profile.json").read_text())
    assert external["revision"] == "F04" and external["build_profile"] == "external"


def passive_screen(parts):
    """Conditional DC/RC screens, without claiming measured ADC performance."""
    load = 0.5
    r_vin = eda.number(parts["R1"].findtext("value")) * 1.01
    minimum_vin = 4.9 - load * r_vin
    assert minimum_vin > 4.0 and load**2 * r_vin < 1.0
    cases = []
    # Pot tolerance +/-20%; capacitor +/-10% is an assembly requirement,
    # not a guarantee supplied by the generic X7R descriptions in this draft BOM.
    for pot, series, bleed, cap in itertools.product(
        (8000, 12000), (990, 1010), (990000, 1010000), (90e-9, 110e-9)
    ):
        rth = pot / 4 + series
        tau = (rth * bleed / (rth + bleed)) * cap
        cases.append((tau, tau * math.log(512), 0.5 * rth / (bleed + rth)))
    assert max(c[1] for c in cases) < 0.003
    return {
        "scope": "Conditional component-level screens; no board, ADC, thermal or supply approval",
        "assumed_seed_branch_current_a": load,
        "assumed_protected_5v_minimum_v": 4.9,
        "seed_vin_minimum_under_assumptions_v": minimum_vin,
        "seed_input_series_resistor_max_power_w": load**2 * r_vin,
        "pot_total_resistance_required_ohm": [8000, 12000],
        "capacitor_effective_required_f": [90e-9, 110e-9],
        "slowest_midpoint_rc_tau_s": max(c[0] for c in cases),
        "largest_midpoint_step_settling_to_1_over_512_s": max(c[1] for c in cases),
        "largest_midpoint_bleed_error_fraction_fullscale": max(c[2] for c in cases),
        "fullscale_end_stop_divider_loss_worst_fraction": 1010 / (990000 + 1010),
        "adc_acquisition_charge_injection_leakage_noise_verified": False,
        "whole_3v3_load_usb_partial_power_verified": False,
        "exact_passive_mpns_selected": False,
    }


def footprint_check(parts, fp_root):
    hashes = {}
    for ref, component in parts.items():
        identifier = component.findtext("footprint")
        lib, name = identifier.split(":")
        base = ROOT if lib.startswith("RMX_") else fp_root
        path = base / (lib + ".pretty") / (name + ".kicad_mod")
        hashes[identifier] = sha(path)
        pads = children(read_sexpr(path.read_text()), "pad")
        expected = 40 if ref == "U1" else int(component.findtext("value")[6:]) if ref.startswith("J") else 2
        assert {str(p[1]) for p in pads} == set(map(str, range(1, expected + 1))), ref
        if ref != "U1":
            continue
        vendor = children(read_sexpr((ROOT / "vendor/DAISY_SEED.kicad_mod").read_text()), "pad")
        assert len(pads) == len(vendor) == 40
        for pad, original in zip(pads, vendor):
            assert all(first(pad, key) == first(original, key) for key in ("at", "size", "layers"))
            n = int(pad[1])
            xy = [0, 2.54 * (n - 1)] if n <= 20 else [15.24, 2.54 * (40 - n)]
            assert all(math.isclose(float(a), b, abs_tol=1e-6) for a, b in zip(first(pad, "at")[1:3], xy))
            # Selected socket's recommended finished-hole nominal; board-fab
            # drill/plating tolerance and real assembly are still unqualified.
            assert float(first(pad, "drill")[1]) == 1.04
            assert list(map(float, first(pad, "size")[1:3])) == [1.7, 1.7]
    return hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    cli = Path(args.kicad_cli).resolve()
    OUT.mkdir(exist_ok=True)
    # Never leave a previous success report behind after a failed fresh audit.
    (OUT / "verification.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e19-check-") as directory:
        temp = Path(directory)
        font = temp / "fonts.conf"
        font.write_text(
            f"<fontconfig><dir>/System/Library/Fonts</dir><cachedir>{temp / 'cache'}</cachedir></fontconfig>"
        )
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            FONTCONFIG_FILE=str(font),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        )

        def run(*arguments):
            result = subprocess.run([str(cli), *map(str, arguments)], env=env, capture_output=True, text=True)
            assert result.returncode == 0, (arguments, result.stdout, result.stderr)
            return result.stdout.strip()

        version = run("version")
        source = ROOT / "processor_carrier.kicad_sch"
        run(
            "sch",
            "erc",
            "--severity-all",
            "--format",
            "json",
            "--exit-code-violations",
            "-o",
            OUT / "erc.json",
            source,
        )
        assert not any(s["violations"] for s in json.loads((OUT / "erc.json").read_text())["sheets"])
        run("sch", "export", "netlist", "--format", "kicadxml", "-o", OUT / "netlist.xml", source)
        parts, pins = eda.netlist(OUT / "netlist.xml")
        circuit(parts, pins)
        firmware_contract(pins)
        screens = passive_screen(parts)
        footprints = footprint_check(parts, footprint_root(str(cli)))
        other = {}
        source_files = []
        for name in ("converter", "sequenced_bypass", "rail_disconnect", "control_inputs"):
            schematic = ROOT.parent / name / (name + ".kicad_sch")
            source_files.append(schematic)
            dest = temp / (name + ".xml")
            run("sch", "export", "netlist", "--format", "kicadxml", "-o", dest, schematic)
            other[name] = eda.netlist(dest)[1]
        assert pins["J1"] == other["rail_disconnect"]["J4"]
        assert pins["J3"] == other["sequenced_bypass"]["J2"]
        assert pins["J7"] == other["sequenced_bypass"]["J6"]
        aliases = {"CONTROL_RESET_N": "CODEC_RUN", "MANUAL_BYPASS": "BYPASS_SENSE"}
        for here, there in [("J2", "J5"), ("J4", "J4")]:
            assert pins[here] == {p: aliases.get(n, n) for p, n in other["control_inputs"][there].items()}
        codec = other["converter"]
        assert pins["J5"] == codec["J3"]
        assert codec["J4"] == {"1": "V5_REG", "2": "AGND", "3": "V3V3_IO"}
        assert [codec["J4"][str(i)] for i in (2, 3)] == [pins["J6"][str(i)] for i in (1, 2)]
        assert [codec["J5"][str(i)] for i in (1, 2, 3, 4, 6)] == [pins["J6"][str(i)] for i in (1, 3, 4, 5, 6)]
        pcb_checks = verify_board(run, pins)
        integration = json.loads((ROOT / "integration.json").read_text())
        assert integration["firmware_profile"] == "external" and integration["firmware_revision"] == "F04"
        assert not integration["onboard_profile_compatible"] and not integration["physical_fit_verified"]
        assert integration["board_size_mm"] == [150, 65, 1.6]
        assert integration["layout_origin_mm"] == [30, 42, 6.5]
        assert integration["socket_finished_hole_nominal_mm"] == 1.04
        for key, ref in [
            ("power_input_J1", "J1"),
            ("hub_J2", "J2"),
            ("relay_J3", "J3"),
            ("hub_rear_J4", "J4"),
            ("converter_sai_J5", "J5"),
            ("converter_split_J6", "J6"),
            ("input_ready_J7", "J7"),
        ]:
            assert integration[key] == [pins[ref][str(i)] for i in range(1, len(pins[ref]) + 1)]
        packet = json.loads((OUT / "placement.json").read_text())
        hub = json.loads((ROOT.parent / "control_inputs/integration.json").read_text())
        assert (
            packet["daughter_mount_centers_layout_mm"]
            == integration["daughter_drill_centers_layout_mm"]
            == hub["carrier_drill_centers_layout_mm"]
        )
        assert (
            integration["daughter_layout_origin_mm"]
            == hub["daughterboard_layout_origin_mm"]
            == [109, 43, 12.1]
        )
        assert not integration["local_i2c_pullups_fitted"] and not integration["full_control_board_complete"]
        with (OUT / "connector-map.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Header", "Pin", "Net", "Knob_id", "Firmware_profile"])
            for ref in sorted((r for r in pins if r.startswith("J")), key=lambda r: int(r[1:])):
                knob = KNOBS[int(ref[1:]) - 20] if int(ref[1:]) >= 20 else ""
                for number, net in sorted(pins[ref].items(), key=lambda pair: int(pair[0])):
                    writer.writerow([ref, number, net, knob, "external only"])
        (OUT / "passive-screen.json").write_text(json.dumps(screens, indent=2) + "\n")
        run("sch", "export", "svg", "--exclude-drawing-sheet", "-o", OUT, source)
        files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix not in (".kicad_prl", ".lck")]
        files += list((ROOT / "vendor").iterdir()) + list((ROOT / "RMX_Carrier.pretty").iterdir())
        files += (
            source_files
            + [
                FIRMWARE / name
                for name in (
                    "BoardIO.h",
                    "BoardProfile.h",
                    "ExternalAudio.cpp",
                    "main.cpp",
                    "external-profile.json",
                )
            ]
            + [
                REPO / "hardware/runtime/include/rmx/controls/HardwareControls.h",
                OUT / "connector-map.csv",
                OUT / "passive-screen.json",
                OUT / "placement.json",
                OUT / "routing-inputs.json",
                ROOT.parent / "control_inputs/board.py",
                ROOT.parent / "control_inputs/integration.json",
                ROOT.parent / "output_stage/check_placement.py",
            ]
        )
        report = {
            "revision": "E19",
            "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kicad_version": version,
            "circuit_components": 76,
            "module_pins": 40,
            "pot_channels": 10,
            "headers": 22,
            "native_erc_violations": 0,
            "independent_pin_contract_passed": True,
            "source_load_interfaces_fresh": True,
            "firmware_profile": "external",
            "firmware_revision": "F04",
            "onboard_profile_compatible": False,
            "official_module_pad_centers_and_numbers_preserved": True,
            "socket_nominal_drill_per_manufacturer_mm": 1.04,
            "specific_socket_landing_pattern_qualified": False,
            "source_footprint_hashes": footprints,
            "pcb_placed": False,
            "pcb_routed": False,
            "pcb_drc_passed": False,
            "full_control_board_complete": False,
            "physical_fit_verified": False,
            "hardware_verified": False,
            "source_sha256": source_hashes(ROOT, files),
        }
        report.update(pcb_checks)
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "E19: 76 parts, 40 module pins, 10 pots; zero native ERC/DRC/parity/open; fresh board and F04 contracts pass. Physical verification remains open."
    )


if __name__ == "__main__":
    main()
