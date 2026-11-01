"""Fresh native paired schematic inputs retaining all84 parent circuit identities."""

import json
import os
import subprocess

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist

from .circuit import ROOT, components


def main():
    assert not (ROOT / "handoff.json").exists()
    parts = components()
    generate(
        ROOT,
        "FPC01",
        "fan_power_health",
        parts,
        [
            (
                20,
                2210,
                "FPC_M2 private successor: third protected NF RAW5 leaf; all84 parent circuits/poses unchanged.",
            ),
            (
                20,
                2220,
                "RAW5 operating P03J23/J21 ONLY, neverTESTJ3. No full-source/inrush/physical/PDN acceptance.",
            ),
        ],
        (760, 2260),
        [("FAN5V_IN", 20.32, 20.32), ("GND", 60.96, 20.32)],
    )
    (ROOT / "fp-lib-table").write_text(
        '(fp_lib_table (version 7) (lib (name "FPC01") (type "KiCad") (uri "${KIPRJMOD}/FPC01.pretty") (options "") (descr "Captured manufacturer candidate lands")))\n'
    )
    # Keep the M1 accepted-rule intent; the flat-schematic helper supplies a
    # generic project, which must not silently restore old ignored checks.
    (ROOT / "fan_power_health.kicad_pro").write_bytes(
        (ROOT / "sources/M1/fan_power_health.kicad_pro").read_bytes()
    )
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env = dict(os.environ, KICAD_CONFIG_HOME="/private/tmp/afx-fpc-m2-kicad-config")
    runs = []
    for label, args in [
        (
            "netlist",
            [
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "--output",
                str(ROOT / "generated/netlist.xml"),
            ],
        ),
        ("erc", ["sch", "erc", "--format", "json", "--output", str(ROOT / "generated/erc.json")]),
    ]:
        cmd = [cli, *args, str(ROOT / "fan_power_health.kicad_sch")]
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
        runs.append(dict(command=cmd, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr))
        assert p.returncode == 0, runs[-1]
    actual, pins = netlist(ROOT / "generated/netlist.xml")
    for c in parts:
        assert actual[c["ref"]].findtext("value") == c["part"]
        assert actual[c["ref"]].findtext("footprint") == c["footprint"]
        for p in c["pins"]:
            got = pins[c["ref"]][p["number"]]
            assert got == p["net"] if p["net"] is not None else got.startswith("unconnected-"), (
                c["ref"],
                p["number"],
            )
    findings = [
        v for s in json.loads((ROOT / "generated/erc.json").read_text())["sheets"] for v in s["violations"]
    ]
    assert not findings, findings
    (ROOT / "generated/schematic-commands.json").write_text(json.dumps(runs, indent=2) + "\n")
    print("91parts/ERC0/actualpin-value-footprint0")


if __name__ == "__main__":
    main()
