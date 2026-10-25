#!/usr/bin/env python3
"""Native E02 ERC, pin/footprint audit and netlist-driven ideal fault sequences.

This does not simulate analog levels, reset/propagation timing or coil mechanics.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from ..common.reports import source_hashes
from .spec import COMPONENTS, ROOT

OUT = ROOT / "generated"

# Independent terminal contract, checked against the actual exported schematic.
# Numbers are the selected manufacturer package pins, not symbol drawing order.
CONTRACT = {
    "U1": {
        "1": "3V3",
        "2": "CWD",
        "3": "3V3",
        "4": "GND",
        "5": "3V3",
        "6": "HEARTBEAT",
        "7": "LOCAL_OK",
        "8": "LOCAL_OK",
        "9": "GND",
    },
    "U2": {
        "1": "LOCAL_OK",
        "2": "ANALOG_OK",
        "3": "HEALTH_A",
        "4": "HEALTH_A",
        "5": "PROCESS_OK",
        "6": "CLEAR_N",
        "7": "GND",
        "8": "COIL_ENABLE",
        "9": "ARMED",
        "10": "PERMIT_CLEAN",
        "11": "PERMIT_CLEAN",
        "12": "MCU_PERMIT",
        "13": "MCU_PERMIT",
        "14": "3V3",
    },
    "U3": {
        "1": "PERMIT_CLEAN",
        "2": "3V3",
        "3": "ARMED",
        "4": "GND",
        "5": None,
        "6": "CLEAR_N",
        "7": "3V3",
        "8": "3V3",
    },
    "U4": {"1": "LOCAL_OK", "2": "GND", "3": "3V3", "4": None, "5": "3V3", "6": "3V3"},
    "U5": {"1": "LOCAL_OK", "2": "GND", "3": "3V3", "4": None, "5": "5V", "6": "3V3"},
    "Q1": {"1": "BYPASS_GATE", "2": "GND", "3": "BYPASS_LOW"},
    "Q2": {"1": "GAIN_GATE", "2": "GND", "3": "GAIN_LOW"},
    "D1": {"1": "BYPASS_LOW", "2": "GND"},
    "D2": {"1": "GAIN_LOW", "2": "GND"},
    "R1": {"1": "3V3", "2": "LOCAL_OK"},
    "R2": {"1": "HEARTBEAT", "2": "GND"},
    "R3": {"1": "MCU_PERMIT", "2": "GND"},
    "R4": {"1": "PROCESS_OK", "2": "GND"},
    "R5": {"1": "ANALOG_OK", "2": "GND"},
    "R6": {"1": "3V3", "2": "BYPASS_SENSE"},
    "R7": {"1": "GAIN_REQ", "2": "GND"},
    "R8": {"1": "COIL_ENABLE", "2": "BYPASS_GATE"},
    "R9": {"1": "BYPASS_GATE", "2": "GND"},
    "R10": {"1": "GAIN_REQ", "2": "GAIN_GATE"},
    "R11": {"1": "GAIN_GATE", "2": "GND"},
    "C1": {"1": "CWD", "2": "GND"},
    "J1": {"1": "5V", "2": "GND", "3": "3V3"},
    "J2": {
        "1": "GND",
        "2": "HEARTBEAT",
        "3": "MCU_PERMIT",
        "4": "GAIN_REQ",
        "5": "ARMED",
        "6": "BYPASS_SENSE",
    },
    "J3": {"1": "3V3", "2": "PROCESS_OK", "3": "ANALOG_OK", "4": "GND", "5": "BYPASS_SENSE"},
    "J4": {"1": "5V", "2": "BYPASS_LOW"},
    "J5": {"1": "5V", "2": "GAIN_LOW"},
}


def read_netlist():
    tree = ET.parse(OUT / "netlist.xml")
    pins = {}
    for net in tree.findall("./nets/net"):
        name = net.attrib["name"].lstrip("/")
        if name.startswith("unconnected-"):
            name = None
        for node in net.findall("node"):
            pins.setdefault(node.attrib["ref"], {})[node.attrib["pin"]] = name
    for ref, expected in CONTRACT.items():
        actual = pins.get(ref, {})
        for pin, net in expected.items():
            assert actual.get(pin) == net, (ref, pin, actual.get(pin), net)
        assert set(actual) <= set(expected), (ref, "unexpected pins", actual)
    return tree, pins


def fault_sequences(pins):
    q = False
    previous = False
    rows = []
    cases = [
        ("startup faults", False, False, False, False, False),
        ("all hardware good; permit low", True, True, True, False, False),
        ("healthy permit rising edge", True, True, True, True, True),
        ("permit low gates coils immediately", True, True, True, False, False),
        ("new permit edge", True, True, True, True, True),
        ("watchdog timeout; permit frozen high", False, True, True, True, False),
        ("watchdog reset interval ends; still frozen", True, True, True, True, False),
        ("watchdog times out again", False, True, True, True, False),
        ("second watchdog recovery; still frozen", True, True, True, True, False),
        ("MCU finally drops permit", True, True, True, False, False),
        ("fresh healthy edge rearms", True, True, True, True, True),
        ("analog-good wire disconnects", True, False, True, True, False),
        ("analog good returns without permit edge", True, True, True, True, False),
        ("drop after analog fault", True, True, True, False, False),
        ("rearm after analog fault", True, True, True, True, True),
        ("manual process loop opens", True, True, False, True, False),
        ("manual loop returns; permit stuck", True, True, True, True, False),
        ("drop after manual bypass", True, True, True, False, False),
        ("rearm after manual bypass", True, True, True, True, True),
        ("5V supervisor asserts local fault", False, True, True, True, False),
        ("5V recovers while permit high", True, True, True, True, False),
        ("3.3V supervisor asserts while logic still valid", False, True, True, True, False),
        ("3.3V recovers while permit high", True, True, True, True, False),
        ("permit low before final recovery", True, True, True, False, False),
        ("final healthy permit edge", True, True, True, True, True),
    ]
    gates = [("1", "2", "3"), ("4", "5", "6"), ("9", "10", "8"), ("12", "13", "11")]
    for event, local_ok, analog_ok, process_ok, permit, expected in cases:
        state = {
            "3V3": True,
            "5V": True,
            "GND": False,
            pins["U1"]["7"]: local_ok,
            pins["J3"]["3"]: analog_ok,
            pins["J3"]["2"]: process_ok,
            pins["J2"]["3"]: permit,
            pins["U3"]["3"]: q,
        }

        def settle():
            for _ in range(8):
                for a, b, y in gates:
                    an, bn, yn = (pins["U2"][p] for p in (a, b, y))
                    if an in state and bn in state:
                        state[yn] = state[an] and state[bn]

        settle()
        clock = state[pins["U3"]["1"]]
        clear_n = state[pins["U3"]["6"]]
        assert state[pins["U3"]["7"]], "Preset must remain inactive"
        if not clear_n:
            q = False
        elif clock and not previous:
            q = state[pins["U3"]["2"]]
        previous = clock
        state[pins["U3"]["3"]] = q
        settle()
        drive = state[pins["R8"]["1"]]
        assert drive == expected, (event, drive, expected)
        rows.append(
            dict(
                event=event,
                local_ok=local_ok,
                analog_ok=analog_ok,
                process_ok=process_ok,
                mcu_permit=permit,
                clear_n=clear_n,
                armed=q,
                coil_enable=drive,
            )
        )
    return dict(
        passed=True,
        scenarios=len(rows),
        events=rows,
        scope="ideal valid-voltage gate/D-flop behavior using actual exported pin nets",
        excludes=[
            "unpowered IC behavior",
            "voltage thresholds and propagation/recovery timing",
            "watchdog/supervisor timer simulation",
            "coil/TVS dynamics",
            "contact motion and audio",
        ],
    )


def dc_screen():
    series_max = 4700 * 1.01
    down_min = 270000 * 0.99
    gate_leak = 100e-9
    assumed_logic_min = 3.0
    hcs_voh_min = assumed_logic_min - 0.1
    gate_min = (hcs_voh_min / series_max - gate_leak) / (1 / series_max + 1 / down_min)
    load_max = 3.465 / (4700 * 0.99 + down_min) + gate_leak
    assert gate_min > 2.5
    assert load_max < 20e-6
    return dict(
        scope="DC screening with specified values; no switching or thermal simulation",
        assumed_logic_supply_min_v=assumed_logic_min,
        assumed_logic_supply_max_v=3.465,
        assumed_hcs_static_voh_min_v=hcs_voh_min,
        gate_leakage_max_a=gate_leak,
        resistor_tolerance=0.01,
        gate_voltage_min_v=gate_min,
        static_output_load_max_a=load_max,
        ao3400a_rds_at_2v5_25c_max_ohm=0.048,
        coil_pair_design_current_a=0.06,
        mosfet_conduction_loss_at_25c_w=0.06**2 * 0.048,
        tvs_datasheet_max_clamp_v=15.4,
        tvs_datasheet_test_current_a=13,
        tvs_datasheet_pulse_us=[10, 1000],
        actual_coil_clamp_measured=False,
        required_measurements=[
            "Minimum drive high and gate voltage",
            "Coil current and inductance",
            "Drain clamp/overshoot and pulse energy",
            "Relay operate/release time",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    parser.add_argument("--footprint-dir", type=Path)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    cli = Path(args.kicad_cli).resolve()
    footprint_root = args.footprint_dir
    if not footprint_root:
        for path in [cli.parents[1] / "SharedSupport/footprints", Path("/usr/share/kicad/footprints")]:
            if path.is_dir():
                footprint_root = path
                break
    if not footprint_root:
        raise RuntimeError("Pass --footprint-dir for the installed standard KiCad libraries")
    footprint_root = footprint_root.resolve()
    with tempfile.TemporaryDirectory(prefix="rmx-bypass-kicad-") as temporary:
        temp = Path(temporary)
        env = dict(
            os.environ, KICAD_CONFIG_HOME=str(temp / "config"), KICAD10_FOOTPRINT_DIR=str(footprint_root)
        )
        if Path("/System/Library/Fonts").is_dir():
            (temp / "cache").mkdir()
            fonts = temp / "fonts.conf"
            fonts.write_text(
                '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>/System/Library/Fonts</dir><dir>/Library/Fonts</dir><cachedir>'
                + str(temp / "cache")
                + "</cachedir></fontconfig>"
            )
            env["FONTCONFIG_FILE"] = str(fonts)

        def run(*command):
            p = subprocess.run([str(cli), *map(str, command)], capture_output=True, text=True, env=env)
            if p.returncode:
                raise RuntimeError(f"{command}: {p.returncode}\n{p.stdout}\n{p.stderr}")
            return p.stdout.strip()

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
            ROOT / "bypass.kicad_sch",
        )
        erc = json.loads((OUT / "erc.json").read_text())
        for sheet in erc["sheets"]:
            assert not sheet["violations"], sheet["violations"]
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            ROOT / "bypass.kicad_sch",
        )
        tree, pins = read_netlist()
        values = {c.attrib["ref"]: c.findtext("value") for c in tree.findall("./components/comp")}
        assert values["C1"] == "150pF C0G 5%" and values["R1"] == "10k 1%"
        assert values["R8"] == values["R10"] == "4.7k 1%"
        assert values["R9"] == values["R11"] == "270k 1%"
        footprints = {}
        for c in COMPONENTS:
            library, name = c["footprint"].split(":")
            path = footprint_root / (library + ".pretty") / (name + ".kicad_mod")
            text = path.read_text()
            pads = set(re.findall(r'\(pad\s+"([^"]+)"', text))
            expected = {p["number"] for p in c["pins"]}
            assert expected <= pads, (c["ref"], expected, pads)
            footprints[c["ref"]] = dict(
                candidate=c["footprint"],
                pad_numbers=sorted(pads),
                library_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                dimensional_fit_reviewed=False,
            )
        logic = fault_sequences(pins)
        (OUT / "fault-sequences.json").write_text(json.dumps(logic, indent=2) + "\n")
        run(
            "sch",
            "export",
            "svg",
            "--exclude-drawing-sheet",
            "-o",
            str(OUT) + os.sep,
            ROOT / "bypass.kicad_sch",
        )
        sources = [
            ROOT / f
            for f in [
                "spec.py",
                "generate.py",
                "verify.py",
                "bypass.kicad_sch",
                "bypass.kicad_pro",
                "RMX_E02.kicad_sym",
                "sym-lib-table",
                "fp-lib-table",
                "components.json",
                "bom.csv",
            ]
        ]
        report = dict(
            revision="E02",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            physical_component_count=len(COMPONENTS),
            erc_violations=0,
            manufacturer_pin_contract="matched actual exported netlist",
            ideal_fault_scenarios_passed=logic["scenarios"],
            candidate_footprints=footprints,
            dc_screen=dc_screen(),
            pcb_routed=False,
            prototype_assembled=False,
            physical_fault_response_verified=False,
            limits=[
                "All required analog-rail supervisors external/unselected; E05 needs four rails",
                "Coil energy/clamp/timing unmeasured",
                "Footprint pad counts checked; manufacturer land-pattern fit not established",
            ],
            source_hashes=source_hashes(ROOT, sources),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad {version}: zero ERC issues, manufacturer pin contract matches, {logic['scenarios']} netlist-driven ideal fault cases passed."
    )


if __name__ == "__main__":
    main()
