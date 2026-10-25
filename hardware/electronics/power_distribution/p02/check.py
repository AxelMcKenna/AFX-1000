"""Independent P02 native exported-pin/value check and calculation evidence."""

import argparse
import datetime
import hashlib
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from ...common.netlists import netlist, number
from .spec import ROOT


def contract(parts, pins):
    expected = {
        "U1": (
            "TPSM63606RDLR",
            {
                "1": "VIN_PROTECTED",
                "5": "P02_PRE6V",
                "6": "AGND",
                "8": "P02_PRE6V",
                "9": "P02_PRE6V",
                "10": "P02_PRE_FB",
                "11": "AGND",
                "12": "P02_RT",
                "14": "P02_ENABLE",
                "16": "VIN_PROTECTED",
                "17": "AGND",
                "18": "AGND",
                "19": "AGND",
                "20": "AGND",
            },
        ),
        "U2": (
            "LT3083IQ#PBF",
            {"2": "P02_DIG_SET", "3": "5V_DIG_SRC", "4": "VIN_PROTECTED", "5": "P02_PRE6V"},
        ),
        "U3": (
            "LT3045IDD#PBF",
            {
                "1": "P02_PRE6V",
                "2": "P02_PRE6V",
                "3": "P02_PRE6V",
                "5": "AGND",
                "6": "P02_PRE6V",
                "7": "P02_ANA_SET",
                "8": "AGND",
                "9": "V5_REG_SRC",
                "10": "V5_REG_SRC",
                "11": "AGND",
            },
        ),
        "U4": ("ADR4550BRZ", {"2": "P02_PRE6V", "4": "AGND", "6": "P02_REF5"}),
        "U5": (
            "OPA2192ID",
            {
                "1": "P02_DIG_DRIVE",
                "2": "P02_DIG_FB",
                "3": "P02_REF_FILTER",
                "4": "AGND",
                "5": "P02_REF_FILTER",
                "6": "P02_ANA_FB",
                "7": "P02_ANA_DRIVE",
                "8": "VIN_PROTECTED",
            },
        ),
    }
    for ref, (part, nets) in expected.items():
        assert parts[ref].findtext("value") == part, ref
        connected = {p: n for p, n in pins[ref].items() if not n.startswith("unconnected-")}
        assert connected == nets, ("Manufacturer pin/protected boundary mismatch", ref)
    assert parts["U1"].findtext("footprint", "") == "", "Do not substitute a wrong RDL land pattern"
    assert parts["U2"].findtext("footprint") == "Package_TO_SOT_SMD:TO-263-5_TabPin3"
    passive = [
        ("R1", 50000, "P02_PRE6V", "P02_PRE_FB"),
        ("R2", 10000, "P02_PRE_FB", "AGND"),
        ("R3", 13000, "P02_RT", "AGND"),
        ("R4", 10000, "POWER_READY", "P02_ENABLE"),
        ("R5", 22000, "P02_ENABLE", "AGND"),
        ("R6", 10000, "P02_REF5", "P02_REF_FILTER"),
        ("R7", 6800, "P02_DIG_DRIVE", "P02_DIG_SET"),
        ("R8", 800, "P02_DIG_SET", "P02_DIG_DIV"),
        ("R9", 100000, "P02_DIG_DIV", "AGND"),
        ("R10", 100000, "P02_DIG_DIV", "P02_DIG_FB"),
        ("R11", 6800, "P02_ANA_DRIVE", "P02_ANA_SET"),
        ("R12", 120, "P02_ANA_SET", "P02_ANA_DIV"),
        ("R13", 100000, "P02_ANA_DIV", "AGND"),
        ("R14", 100000, "P02_ANA_DIV", "P02_ANA_FB"),
        ("R15", 909, "5V_DIG_SRC", "AGND"),
        ("R16", 2210, "V5_REG_SRC", "AGND"),
        ("C1", 47e-9, "P02_DIG_DRIVE", "P02_DIG_FB"),
        ("C2", 100e-9, "P02_DIG_SET", "AGND"),
        ("C3", 47e-9, "P02_ANA_DRIVE", "P02_ANA_FB"),
        ("C4", 100e-9, "P02_ANA_SET", "AGND"),
        ("C5", 10e-6, "VIN_PROTECTED", "AGND"),
        ("C6", 10e-6, "VIN_PROTECTED", "AGND"),
        ("C7", 47e-6, "P02_PRE6V", "AGND"),
        ("C8", 47e-6, "P02_PRE6V", "AGND"),
        ("C9", 22e-6, "P02_PRE6V", "AGND"),
        ("C10", 10e-6, "VIN_PROTECTED", "AGND"),
        ("C11", 10e-6, "P02_PRE6V", "AGND"),
        ("C12", 1e-6, "P02_PRE6V", "AGND"),
        ("C13", 1e-6, "P02_REF5", "AGND"),
        *[(f"C{i}", 4.7e-6, "P02_REF_FILTER", "AGND") for i in (14, 15, 16)],
        ("C17", 22e-6, "5V_DIG_SRC", "AGND"),
        ("C18", 22e-6, "V5_REG_SRC", "AGND"),
        ("C19", 100e-9, "VIN_PROTECTED", "AGND"),
        ("C20", 100e-9, "P02_PRE6V", "AGND"),
        ("C21", 18e-12, "P02_PRE6V", "P02_PRE_FB"),
    ]
    for ref, value, a, b in passive:
        assert math.isclose(number(parts[ref].findtext("value")), value, rel_tol=1e-12, abs_tol=0), ref
        assert pins[ref] == {"1": a, "2": b}, ref
    for ref, sequence in (
        ("J1", ["VIN_PROTECTED", "AGND", "POWER_READY"]),
        ("J2", ["5V_DIG_SRC", "AGND"]),
        ("J3", ["V5_REG_SRC", "AGND"]),
        ("J4", ["P02_PRE6V", "AGND"]),
        ("J5", ["AGND"]),
        ("J6", ["AGND"]),
    ):
        assert pins[ref] == dict(zip(map(str, range(1, len(sequence) + 1)), sequence)), ref
    assert set(parts) == set(expected) | {p[0] for p in passive} | {"J1", "J2", "J3", "J4", "J5", "J6"}
    return dict(
        components=len(parts),
        exact_native_pin_value_contract=True,
        unassigned_land_patterns=[
            "U1:TI_RDL20_TPSM63606",
            "C14:C15:C16 selected film packages",
            "J5:J6 source top strap attachments",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    (out / "verification.json").unlink(missing_ok=True)
    cli = Path(args.kicad_cli).resolve()
    with tempfile.TemporaryDirectory(prefix="rmx-p02-check-") as temp:
        temp = Path(temp)
        env = dict(os.environ, KICAD_CONFIG_HOME=str(temp / "config"))

        def run(*cmd):
            p = subprocess.run([str(cli), *map(str, cmd)], env=env, capture_output=True, text=True)
            assert p.returncode == 0, (cmd, p.stdout, p.stderr)
            return p.stdout.strip()

        version = run("version")
        run(
            "sch",
            "erc",
            "--severity-all",
            "--format",
            "json",
            "-o",
            out / "erc.json",
            ROOT / "power_p02.kicad_sch",
        )
        erc = json.loads((out / "erc.json").read_text())
        issues = [v for sheet in erc.get("sheets", []) for v in sheet.get("violations", [])]
        assert not issues, [(i.get("type"), i.get("description")) for i in issues[:8]]
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            out / "netlist.xml",
            ROOT / "power_p02.kicad_sch",
        )
        parts, pins = netlist(out / "netlist.xml")
        proof = contract(parts, pins)
        run("sch", "export", "svg", "--exclude-drawing-sheet", "-o", out, ROOT / "power_p02.kicad_sch")
    sources = [p for p in ROOT.iterdir() if p.is_file() and p.suffix not in (".kicad_prl", ".lck")]
    sources += [out / "netlist.xml", out / "erc.json"]
    sources += [ROOT.parents[1] / "common" / n for n in ("flat_schematic.py", "symbols.py", "netlists.py")]
    record = dict(
        revision="P02",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        kicad_version=version,
        native_erc_violations=0,
        **proof,
        source_sha256={os.path.relpath(p, ROOT): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        native_pcb_implemented=False,
        complete_unit_qualified=False,
        physical_fit_verified=False,
        physical_power_verified=False,
        fabrication_released=False,
        build_ready=False,
    )
    (out / "verification.json").write_text(json.dumps(record, indent=2) + "\n")
    print(
        "P02:",
        proof["components"],
        "parts; zero native ERC; independent pin/value contract passes; U1 land, PCB/thermal/system qualification open",
    )


if __name__ == "__main__":
    main()
