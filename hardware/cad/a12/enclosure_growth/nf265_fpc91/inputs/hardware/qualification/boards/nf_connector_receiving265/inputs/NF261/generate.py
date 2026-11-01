"""Generate only NF05H successor schematic and fresh native proof."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist

from .circuit import components

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (ROOT / "handoff.json").exists(), "Preserve sealed successor"
    parts, delta = components()
    generate(
        ROOT,
        "NF05H",
        "negative_startup_hardgate",
        parts,
        [
            (
                20,
                45,
                "NF05H: independent RAW5-powered absolute-AUX UV clamp supply gating; inherited sequential standalone startup.",
            ),
            (
                20,
                55,
                "NO external MCU/PC ARM/START requirement. J1formercommands are output monitors only; no external drives.",
            ),
            (20, 65, "All partial-power/current/source/faultenergy/physical/PCB acceptance remains FALSE."),
        ],
        (1100, 4400),
        [
            (n, x, 20.32)
            for n, x in [
                ("AGND", 20.32),
                ("GUARDED_12V_FORCE", 91.44),
                ("DIG5_FORCE", 172.72),
                ("AUX2V6", 254),
                ("N19_P03_SRC", 330.2),
                ("N12_P03_SRC", 411.48),
                ("N19_VIN", 490.22),
                ("N12_VIN", 568.96),
                ("MODULE_INPUT_GND", 650.24),
            ]
        ],
    )
    table = ROOT / "fp-lib-table"
    table.write_text(
        table.read_text().replace(
            "${KICAD10_FOOTPRINT_DIR}/NF05H_Manufacturer.pretty", "${KIPRJMOD}/NF05H_Manufacturer.pretty"
        )
    )
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env = dict(os.environ, KICAD_CONFIG_HOME="/private/tmp/afx-nf05-kicad-config")
    commands = []
    for label, args in [
        ("version", ["--version"]),
        (
            "netlist",
            [
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "--output",
                str(out / "netlist.xml"),
                str(ROOT / "negative_startup_hardgate.kicad_sch"),
            ],
        ),
        (
            "erc",
            [
                "sch",
                "erc",
                "--format",
                "json",
                "--output",
                str(out / "erc.json"),
                str(ROOT / "negative_startup_hardgate.kicad_sch"),
            ],
        ),
    ]:
        run = subprocess.run([cli, *args], capture_output=True, text=True, env=env, timeout=120)
        commands.append(
            dict(
                label=label,
                command=[cli, *args],
                returncode=run.returncode,
                stdout=run.stdout,
                stderr=run.stderr,
            )
        )
        assert run.returncode == 0, commands[-1]
    (out / "native-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    actual, pins = netlist(out / "netlist.xml")
    for c in parts:
        assert actual[c["ref"]].findtext("value") == c["part"]
        for p in c["pins"]:
            n = pins[c["ref"]][p["number"]]
            assert n == p["net"] if p["net"] is not None else n.startswith("unconnected-"), (
                c["ref"],
                p["number"],
            )
    assert {r: set(p) for r, p in pins.items()} == {c["ref"]: {p["number"] for p in c["pins"]} for c in parts}
    issues = [v for s in json.loads((out / "erc.json").read_text())["sheets"] for v in s["violations"]]
    counts = {k: sum(v["severity"] == k for v in issues) for k in ["error", "warning"]}
    assert counts == dict(error=0, warning=2), issues
    assert all(v["type"] == "ground_pin_not_ground" for v in issues), issues
    assert {v["items"][0]["description"].split()[1] for v in issues} == {"U19", "U24"}, issues
    result = dict(
        revision="NF05H-absolute-AUX-hardgate-native-draft",
        parts=len(parts),
        kicad_cli_sha256=sha(Path(cli)),
        ERC=counts,
        pin_parity_differences=0,
        component_values_exact=True,
        delta=delta,
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                ROOT / "circuit.py",
                ROOT / "generate.py",
                ROOT / "sources/manifest.json",
                ROOT / "components.json",
            ]
        },
        artifact_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                ROOT / "negative_startup_hardgate.kicad_sch",
                out / "netlist.xml",
                out / "erc.json",
                out / "native-commands.json",
            ]
        },
        PCB_implemented=False,
        full_schematic_PCB_native_parity_performed=False,
        physical_qualified=False,
        startup_qualified=False,
        partial_power_qualified=False,
        fabrication_released=False,
    )
    (out / "native-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(len(parts), counts, "nativepins/values exact")


if __name__ == "__main__":
    main()
