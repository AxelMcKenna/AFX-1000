"""Fresh native schematic/ERC for the NF03 monitor, latch and independent clamp cell.

This does NOT implement the linear power controller or E28 series insertion.
"""

import json
import os
from pathlib import Path
import subprocess

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist
from .circuit import ROOT, components


def main():
    parts = components()
    # Correct electrical power direction without treating a floating minus
    # terminal as an independent absolute-voltage source.
    for c in parts:
        if c["part"] == "TMR 1-1213":
            for p in c["pins"]:
                if p["number"] == "4":
                    p["kind"] = "power_out"
                if p["number"] == "6":
                    p["kind"] = "passive"
        if c["part"] == "TPS7A1650DGNR":
            next(p for p in c["pins"] if p["number"] == "1")["kind"] = "power_out"
    flags = [
        ("AGND", 20, 20),
        ("GUARDED_12V_FORCE", 60, 20),
        ("DIG5_FORCE", 110, 20),
        ("AUX2V6", 160, 20),
        ("N19_BANK_OUT", 210, 20),
        ("N12_BANK_OUT", 270, 20),
        ("N19_INTVCC", 330, 20),
        ("N12_INTVCC", 390, 20),
    ]
    flags = [
        (name, round(round(x / 2.54) * 2.54, 4), round(round(y / 2.54) * 2.54, 4)) for name, x, y in flags
    ]
    generate(
        ROOT,
        "NF03",
        "monitor_cutoff",
        parts,
        [
            (20, 45, "NF03 PRIVATE MONITOR/LATCH/NC-CLAMP CELL. NOT A COMPLETE SUPPLY OR BUILD RELEASE."),
            (
                20,
                55,
                "External INTVCC/ON/gate interfaces belong to the not-yet-native NF02 linear controller. Protected bulk stays downstream.",
            ),
            (
                20,
                65,
                "Both NC clamps release with ARM; independent translated ON staysLOW until START/PERMIT. No single-fault-safe enable claim.",
            ),
        ],
        (1100, 4150),
        flags,
    )
    kicad = Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
    repo = ROOT.parents[3]
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config",
        FONTCONFIG_FILE=str(repo / "build-hardware/kicad-fonts.conf"),
    )
    commands = []
    out = ROOT / "generated"
    for args in [
        [str(kicad), "--version"],
        [
            str(kicad),
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "--output",
            str(out / "netlist.xml"),
            str(ROOT / "monitor_cutoff.kicad_sch"),
        ],
        [
            str(kicad),
            "sch",
            "erc",
            "--format",
            "json",
            "--output",
            str(out / "erc.json"),
            str(ROOT / "monitor_cutoff.kicad_sch"),
        ],
    ]:
        r = subprocess.run(args, env=env, text=True, capture_output=True, timeout=120)
        commands.append(dict(command=args, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr))
        assert r.returncode == 0, (r.stdout, r.stderr)
    (out / "native-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    actual, pins = netlist(out / "netlist.xml")
    # KiCad exports deliberately NC pads as unique unconnected-* nets. Preserve
    # and audit these separately; never silently filter a real circuit node.
    nc = []
    for c in parts:
        for p in c["pins"]:
            if p["net"] is None:
                exported = pins[c["ref"]].pop(p["number"])
                assert exported.startswith("unconnected-("), (c["ref"], p, exported)
                nc.append(dict(ref=c["ref"], pin=p["number"], exported=exported))
    (out / "native-nc-inventory.json").write_text(json.dumps(nc, indent=2) + "\n")
    expected = {c["ref"]: {p["number"]: p["net"] for p in c["pins"] if p["net"] is not None} for c in parts}
    differences = [
        dict(ref=r, expected=p, actual=pins.get(r)) for r, p in expected.items() if p != pins.get(r)
    ]
    assert set(actual) == set(expected)
    (out / "pin-parity.json").write_text(
        json.dumps(
            dict(
                differences=differences,
                parts=len(parts),
                power_controller_implemented=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    assert not differences, differences
    erc = json.loads((out / "erc.json").read_text())
    issues = [v for s in erc["sheets"] for v in s["violations"]]
    counts = {k: sum(v["severity"] == k for v in issues) for k in ("error", "warning")}
    print("NF03 monitor/latch/clamp native", len(parts), "parts", counts)


if __name__ == "__main__":
    main()
