#!/usr/bin/env python3
"""Check E03 with native ERC, exported nets, relay states and E02 interface.

The connectivity model covers settled contacts only. It does not model the
coil electrically, contact bounce/overlap, audio or unpowered active devices.
"""

import argparse
import datetime
import hashlib
import itertools
import json
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from ..common.footprints import footprint_review as footprint_review
from ..common.reports import source_hashes

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

# Independent pin contract from Omron's page-6 TOP-view drawing and the harness
# contract. Do not import generator mappings into these checks.
CONTRACT = {
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
        "8": "BYPASS_LOW",
        "3": "PROC_IN_L",
        "2": None,
        "4": "IN_L",
        "6": "PROC_IN_R",
        "7": None,
        "5": "IN_R",
    },
    "J1": {"1": "IN_L", "2": "AGND", "3": "IN_R"},
    "J2": {"1": "OUT_L", "2": "AGND", "3": "OUT_R"},
    "J3": {
        "1": "PROC_IN_L",
        "2": "AGND",
        "3": "PROC_IN_R",
        "4": "PROC_OUT_L",
        "5": "AGND",
        "6": "PROC_OUT_R",
    },
    "J4": {"1": "5V", "2": "BYPASS_LOW"},
}


def exported_pins(path):
    tree = ET.parse(path)
    pins = {}
    for net in tree.findall("./nets/net"):
        name = net.attrib["name"].lstrip("/")
        if name.startswith("unconnected-"):
            name = None
        for node in net.findall("node"):
            pins.setdefault(node.attrib["ref"], {})[node.attrib["pin"]] = name
    return tree, pins


def contacts(pins):
    """Independent mechanical pole map: COM 3/6, NC 2/7, NO 4/5."""
    cases = []
    for output_on, input_on in itertools.product((False, True), repeat=2):
        parent = {}

        def root(node):
            parent.setdefault(node, node)
            if parent[node] != node:
                parent[node] = root(parent[node])
            return parent[node]

        def terminal(ref, pin):
            return pins[ref][pin] or f"NC:{ref}.{pin}"

        for ref, on in [("K1", output_on), ("K2", input_on)]:
            for common, nc, no in [("3", "2", "4"), ("6", "7", "5")]:
                a, b = terminal(ref, common), terminal(ref, no if on else nc)
                parent[root(a)] = root(b)

        def connected(a, b):
            return root(a) == root(b)

        for channel in ("L", "R"):
            line, output, proc_in, proc_out = [
                n + "_" + channel for n in ("IN", "OUT", "PROC_IN", "PROC_OUT")
            ]
            assert connected(output, proc_out if output_on else line)
            assert not connected(output, line if output_on else proc_out)
            assert connected(proc_in, line) == input_on
            assert not connected(line, proc_out), "Dry and processed sources shorted"
            for other in ("IN", "OUT", "PROC_IN", "PROC_OUT"):
                assert not connected(output, other + "_" + ("R" if channel == "L" else "L"))
            for audio in (line, output, proc_in, proc_out):
                for supply in ("5V", "BYPASS_LOW", "AGND"):
                    assert not connected(audio, supply), (audio, supply)
        assert not connected("5V", "BYPASS_LOW")
        cases.append(
            dict(
                output_relay_energized=output_on,
                input_relay_energized=input_on,
                output_source="processed" if output_on else "dry",
                processing_inputs_connected=input_on,
                checks_passed=True,
            )
        )
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    parser.add_argument("--footprint-dir", type=Path)
    parser.add_argument("--driver-schematic", type=Path, default=ROOT.parent / "bypass/bypass.kicad_sch")
    args = parser.parse_args()
    cli = Path(shutil.which(args.kicad_cli) or args.kicad_cli).resolve()
    footprints = args.footprint_dir
    if not footprints:
        for path in [cli.parents[1] / "SharedSupport/footprints", Path("/usr/share/kicad/footprints")]:
            if path.is_dir():
                footprints = path
                break
    if not footprints:
        raise RuntimeError("Pass --footprint-dir for the installed KiCad libraries")
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-contacts-kicad-") as temporary:
        temp = Path(temporary)
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprints.resolve()),
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
            result = subprocess.run([str(cli), *map(str, command)], capture_output=True, text=True, env=env)
            if result.returncode:
                raise RuntimeError(f"{command}: exit {result.returncode}\n{result.stdout}\n{result.stderr}")
            return result.stdout.strip()

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
            ROOT / "audio_bypass.kicad_sch",
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
            ROOT / "audio_bypass.kicad_sch",
        )
        tree, pins = exported_pins(OUT / "netlist.xml")
        assert pins == CONTRACT, (pins, CONTRACT)
        values = {c.attrib["ref"]: c.findtext("value") for c in tree.findall("./components/comp")}
        assert values["K1"] == values["K2"] == "G6K-2F-Y DC5"
        cases = contacts(pins)
        (OUT / "contact-states.json").write_text(json.dumps(cases, indent=2) + "\n")
        # Fresh export of the actual driver sheet; do not trust an old report.
        driver_netlist = temp / "driver.xml"
        run("sch", "export", "netlist", "--format", "kicadxml", "-o", driver_netlist, args.driver_schematic)
        _, driver = exported_pins(driver_netlist)
        assert driver["J4"] == pins["J4"], "Coil harness pin order differs from E02"
        assert driver["Q1"]["3"] == driver["D1"]["1"] == pins["K1"]["8"] == pins["K2"]["8"]
        assert driver["Q1"]["2"] == driver["D1"]["2"] == "GND"
        review = footprint_review(footprints / "Relay_SMD.pretty/Relay_DPDT_Omron_G6K-2F-Y.kicad_mod")
        run(
            "sch",
            "export",
            "svg",
            "--exclude-drawing-sheet",
            "-o",
            str(OUT) + os.sep,
            ROOT / "audio_bypass.kicad_sch",
        )
        sources = [
            ROOT / f
            for f in [
                "generate.py",
                "verify.py",
                "audio_bypass.kicad_sch",
                "audio_bypass.kicad_pro",
                "RMX_E03.kicad_sym",
                "sym-lib-table",
                "fp-lib-table",
                "components.json",
                "bom.csv",
                "dependencies.json",
            ]
        ]
        report = dict(
            revision="E03",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            erc_violations=0,
            physical_component_count=len(values),
            actual_exported_pin_contract_matches=True,
            settled_contact_cases_passed=len(cases),
            e02_coil_interface_matches=True,
            driver_schematic_sha256=hashlib.sha256(args.driver_schematic.read_bytes()).hexdigest(),
            relay_footprint=review,
            pcb_routed=False,
            assembled=False,
            limits=[
                "Settled contact connectivity only; no timing, bounce or contact-overlap simulation",
                "No coil-current, suppression, audio or physical-fit measurements",
                "Analog stages, input-source selection, gain switching and full PCB remain external",
            ],
            source_hashes=source_hashes(ROOT, sources),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad {version}: zero ERC; 4 settled relay states pass; fresh E02 coil interface matches; relay land pattern matches drawing."
    )


if __name__ == "__main__":
    main()
