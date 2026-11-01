"""Native draft schematic/ERC/export, never a PCB or fabrication receipt."""

import argparse
import json
import subprocess

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist

from .design import ROOT, components


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kicad-cli", required=True)
    args = p.parse_args()
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    parts = components()
    notes = [(20, 45, "N19 - after-bank negative input; defaultOFF"), (20, 540, "N12 - VCC operation HOLD")]
    notes += [
        (20, 1040 + i * 11, note)
        for i, note in enumerate(
            [
                "SC02 NEGATIVE DRAFT: after retained B2B bank; ALL protected reservoir bulk after Q1. No canonical PCB edits.",
                "LM5067 all thresholds/control capacitors are relative to VEE, not AGND. NFET source=SENSE, drain=PROTECTED.",
                "N12 RIN cannot establish recommended2mA VCC operation below13.65V; actual12V operation is an explicit interface hold.",
                "R3/C1 drain feedback + C2 anti-injection is EXPERIMENTAL cross-controller inference from LT4250, not a TI circuit.",
                "Large C2 gate charge delays startup and fault turnoff. Output-only slew arithmetic does NOT prove5s complete startup.",
                "HOST3V3 powers relay LEDs. ENABLE3V3 needs3.0..3.6VHIGH,0..0.1VLOW: E28J9 2.5V is NOT compatible.",
                "PG_RAW is NEGATIVE voltage, NEVER GPIO; PGD also goes high when VCC-VEE<2V. Independent voltage health missing.",
                "Latch reset requires TIMER<0.3V plus input/UV cycle. Charged loads/backfeed/partialpower are unqualified.",
                "C1/C2/C3 exactfilmMPNs and relay footprint remain unselected. Source capacity, timer/SOA/loop stability all open.",
            ]
        )
    ]
    generate(
        ROOT,
        "SC02",
        "negative_startup",
        parts,
        notes,
        (700, 1180),
        [
            ("AGND", 20.32, 25.4),
            ("N19_BANK_OUT", 59.69, 25.4),
            ("N12_BANK_OUT", 100.33, 25.4),
            ("N19_VCC", 149.86, 25.4),
            ("N12_VCC", 199.39, 25.4),
        ],
    )
    schematic = ROOT / "negative_startup.kicad_sch"
    schematic.write_text(
        schematic.read_text()
        .replace("N19_VCC external", "N19_VCC derived UNVERIFIED")
        .replace("N12_VCC external", "N12_VCC derived FAIL recommended ICC")
    )
    version = subprocess.run([args.kicad_cli, "--version"], capture_output=True, text=True, check=True)
    commands = [
        dict(
            argv=[args.kicad_cli, "--version"],
            returncode=version.returncode,
            stdout=version.stdout,
            stderr=version.stderr,
        )
    ]
    for kind, extra, name in [
        ("netlist", ["--format", "kicadxml"], "netlist.xml"),
        ("svg", [], "schematic-svg"),
    ]:
        run = subprocess.run(
            [
                args.kicad_cli,
                "sch",
                "export",
                kind,
                *extra,
                "--output",
                str(out / name),
                str(ROOT / "negative_startup.kicad_sch"),
            ],
            capture_output=True,
            text=True,
        )
        commands.append(dict(argv=run.args, returncode=run.returncode, stdout=run.stdout, stderr=run.stderr))
        (out / (kind + "-log.txt")).write_text(run.stdout + run.stderr)
        assert run.returncode == 0, run.stderr
    erc = subprocess.run(
        [
            args.kicad_cli,
            "sch",
            "erc",
            "--format",
            "json",
            "--output",
            str(out / "erc.json"),
            str(ROOT / "negative_startup.kicad_sch"),
        ],
        capture_output=True,
        text=True,
    )
    commands.append(dict(argv=erc.args, returncode=erc.returncode, stdout=erc.stdout, stderr=erc.stderr))
    (out / "native-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    (out / "erc-log.txt").write_text(erc.stdout + erc.stderr)
    actual_erc = json.loads((out / "erc.json").read_text())
    violations = [v for sheet in actual_erc["sheets"] for v in sheet["violations"]]
    assert all(v["type"] == "footprint_link_issues" and v["severity"] == "warning" for v in violations), (
        "Unexpected nativeERC findings"
    )
    assert len(violations) == 8, "Declared unresolved-footprint inventory changed"

    actual_parts, pins = netlist(out / "netlist.xml")
    expected = {c["ref"]: {p["number"]: p["net"] for p in c["pins"]} for c in parts}
    differences = []
    for ref, need in expected.items():
        if pins.get(ref) != need:
            differences.append(dict(ref=ref, expected=need, actual=pins.get(ref)))
    assert set(actual_parts) == set(expected)
    (out / "pin-parity.json").write_text(
        json.dumps(
            dict(
                differences=differences,
                count=len(parts),
                canonical_boards_modified=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    assert erc.returncode == 0 and not differences, (erc.returncode, differences)


if __name__ == "__main__":
    main()
