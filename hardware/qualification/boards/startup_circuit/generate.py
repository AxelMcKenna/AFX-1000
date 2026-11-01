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
    notes = [
        (20, 45, "P19 stage - default OFF; after-bank input / all protected bulk after Q1"),
        (20, 485, "P12 stage - default OFF; after-bank input / all protected bulk after Q101"),
        (
            20,
            955,
            "SC01 DRAFT: LM5069-1 after retained B2B bank; ALL retained bulk downstream. Canonical P03/E28 unchanged.",
        ),
        (
            20,
            966,
            "C1/C2 exactfilmMPNs unresolved; TLP170GM footprint and operating ports unreviewed. No fabrication/PCB claim.",
        ),
        (
            20,
            977,
            "ENABLE from separate3V3digitaldomain; localrail supplies LED. No V2V5_AUX load. Full source/digital budgets still open.",
        ),
        (
            20,
            988,
            "PG_RAW can equal12/19V: NEVER connect directly to MCU. ENABLE3V3 is NOT E28 J9 2.5V; translator/sequencer missing.",
        ),
        (
            20,
            999,
            "Q1 bodydiode permits reverse backfeed from charged load. Partial-power/restart/fault paths unverified.",
        ),
        (
            20,
            1010,
            "P19 4.7uF/50mA planning case misses provisional5s target. Faster1.2uF/100mA is study only, NOT this schematic.",
        ),
        (
            20,
            1021,
            "Current/power/timer tabulated limits mostly at VIN48V;12/19V fulltrajectory, SOA/cooling and timeout coordination open.",
        ),
    ]
    generate(
        ROOT,
        "SC01",
        "positive_startup",
        parts,
        notes,
        (700, 1060),
        [("AGND", 20.32, 25.4), ("P19_BANK_OUT", 59.69, 25.4), ("P12_BANK_OUT", 100.33, 25.4)],
    )
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
                str(ROOT / "positive_startup.kicad_sch"),
            ],
            capture_output=True,
            text=True,
        )
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
            str(ROOT / "positive_startup.kicad_sch"),
        ],
        capture_output=True,
        text=True,
    )
    (out / "erc-log.txt").write_text(erc.stdout + erc.stderr)
    actual_erc = json.loads((out / "erc.json").read_text())
    violations = [v for sheet in actual_erc["sheets"] for v in sheet["violations"]]
    assert all(v["type"] == "footprint_link_issues" and v["severity"] == "warning" for v in violations), (
        "Unexpected nativeERC findings"
    )
    assert len(violations) == 6, "Declared unresolved-footprint inventory changed"

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
