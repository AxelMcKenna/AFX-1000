"""AX01 leaf schematic; conditional receiving proposal, not adopted hardware."""

import json
import os
import subprocess
from pathlib import Path

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]


def components():
    out = []

    def add(ref, part, footprint, entries, source, note=""):
        k = len(out)
        out.append(
            dict(
                ref=ref,
                part=part,
                footprint=footprint,
                pins=[
                    dict(
                        number=str(n),
                        name=name,
                        net=net,
                        kind=kind,
                        side="R" if kind in ["output", "open_collector"] else "L",
                    )
                    for n, name, net, kind in entries
                ],
                source=source,
                note=note,
                x=55.88 + (k % 4) * 121.92,
                y=66.04 + (k // 4) * 91.44,
            )
        )

    def passive(ref, part, fp, a, b, source):
        add(ref, part, fp, [(1, "1", a, "passive"), (2, "2", b, "passive")], source)

    ti = "https://www.ti.com/lit/ds/symlink/tps3890.pdf"
    add(
        "U1",
        "TPS389001DSET",
        "Package_SON:WSON-6_1.5x1.5mm_P0.5mm",
        [
            (1, "SENSE", "POWER_RUN_INTERNAL", "input"),
            (2, "GND", "AGND", "power_in"),
            (3, "MR", "AUX", "input"),
            (4, "VDD", "AUX", "power_in"),
            (5, "CT", "RUN_CT", "passive"),
            (6, "RESET_N", "RUN_GATE_COMMAND", "open_collector"),
        ],
        ti,
        "Physical TPS3890 pin4 VDD and pin6 RESET_N. Adjustable1.15V option directly senses internal RUN.",
    )
    add(
        "Q1",
        "DMN2056U-7",
        "Package_TO_SOT_SMD:SOT-23",
        [
            (1, "G", "RUN_GATE_COMMAND", "input"),
            (2, "S", "AGND", "passive"),
            (3, "D", "PMOS_GATES", "passive"),
        ],
        "https://www.diodes.com/assets/Datasheets/DMN2056U.pdf",
    )
    for ref, drain in [("Q2", "AUX"), ("Q3", "PRELIMIT")]:
        add(
            ref,
            "PMV65XP,215",
            "Package_TO_SOT_SMD:SOT-23",
            [
                (1, "G", "PMOS_GATES", "input"),
                (2, "S", "PMOS_COMMON_SOURCE", "passive"),
                (3, "D", drain, "passive"),
            ],
            "https://assets.nexperia.com/documents/data-sheet/PMV65XP.pdf",
            "Common-source B2B. Self-start requires separate diode/VGS/charge receiving proof; no -2.5V RON bootstrap inference.",
        )
    source = "https://www.vishay.com/docs/28758/tnpw_e3.pdf"
    for ref, value, a, b, mpn, fp in [
        ("R1", "100k", "AUX", "RUN_GATE_COMMAND", "TNPW0805100KBEEA", "0805_2012"),
        ("R2", "1M", "RUN_GATE_COMMAND", "AGND", "TNPW08051M00BEEA", "0805_2012"),
        ("R3", "1k", "PMOS_COMMON_SOURCE", "PMOS_GATES", "TNPW08051K00BEEA", "0805_2012"),
        ("R4", "100", "PRELIMIT", "POWER_RUN_E28_LEAF", "TNPW1206100RBEEA", "1206_3216"),
    ]:
        passive(ref, value + " ohm " + mpn, "Resistor_SMD:R_" + fp + "Metric", a, b, source)
    for ref in ["C1", "C2"]:
        passive(
            ref,
            "100nF 50V X7R C0603C104K5RACTU",
            "Capacitor_SMD:C_0603_1608Metric",
            "AUX",
            "AGND",
            "https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf",
        )
    passive(
        "C3",
        "10nF 50V C0G C0603C103J5GACTU",
        "Capacitor_SMD:C_0603_1608Metric",
        "RUN_CT",
        "AGND",
        "https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf",
    )
    add(
        "D1",
        "BAT54H,115",
        "Diode_SMD:D_SOD-123F",
        [(1, "K", "AUX", "passive"), (2, "A", "RUN_GATE_COMMAND", "passive")],
        "https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf",
        "Gate-to-AUX clamp. Hot low-current VF/IR requirements not guaranteed by 25C table.",
    )
    add(
        "J1",
        "BENCH INPUT AUX/AGND/INTERNAL_RUN",
        "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
        [
            (1, "AUX", "AUX", "passive"),
            (2, "AGND", "AGND", "passive"),
            (3, "RUN", "POWER_RUN_INTERNAL", "passive"),
        ],
        "",
        "Bench-only logical header, no physical interface selected. Omit on integrated P03.",
    )
    add(
        "J2",
        "BENCH OUTPUT LEAF/AGND",
        "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        [(1, "LEAF", "POWER_RUN_E28_LEAF", "passive"), (2, "AGND", "AGND", "passive")],
        "",
        "Bench-only logical header, no physical interface selected. Omit on integrated P03.",
    )
    return out


def build():
    assert not (ROOT.parent / "handoff.json").exists()
    parts = components()
    generate(
        ROOT,
        "AX01L",
        "power_run_leaf",
        parts,
        [
            (
                20,
                430,
                "Conditional receiving proposal only. Internal P03R113 stays3.3k; original PG sink is not overloaded.",
            ),
            (
                20,
                440,
                "Only external J106.3 leaf is replaced. Common-source bootstrap, below0.8V supply, hot leakage and loaded cutoff remain unproved.",
            ),
        ],
        (550, 465),
        [("AUX", 20.32, 20.32), ("AGND", 60.96, 20.32)],
    )
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config",
        FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
    )
    output = ROOT / "generated"
    commands = []
    for name, args in [
        (
            "netlist",
            ["sch", "export", "netlist", "--format", "kicadxml", "--output", str(output / "netlist.xml")],
        ),
        ("erc", ["sch", "erc", "--format", "json", "--output", str(output / "erc.json")]),
        ("svg", ["sch", "export", "svg", "--output", str(output / "svg")]),
    ]:
        cmd = [cli, *args, str(ROOT / "power_run_leaf.kicad_sch")]
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        (output / (name + ".log")).write_text(r.stdout + r.stderr)
        commands.append(dict(command=cmd, returncode=r.returncode))
        if r.returncode:
            raise RuntimeError((name, r.returncode))
    actual, pins = netlist(output / "netlist.xml")
    errors = []
    for p in parts:
        if actual[p["ref"]].findtext("value") != p["part"]:
            errors.append(p["ref"] + " value")
        if pins[p["ref"]] != {p["number"]: p["net"] for p in p["pins"]}:
            errors.append(p["ref"] + " pins")
    findings = [v for s in json.loads((output / "erc.json").read_text())["sheets"] for v in s["violations"]]
    result = dict(
        parts=len(parts),
        integrated_new_parts=len(parts) - 2,
        bench_only_unselected_headers=2,
        command_results=commands,
        native_pin_value_mismatches=errors,
        erc_findings=findings,
        PCB_implemented=False,
        physical_qualified=False,
        bootstrap_qualified=False,
        partial_power_qualified=False,
    )
    (output / "native.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    assert not errors and not findings


if __name__ == "__main__":
    build()
