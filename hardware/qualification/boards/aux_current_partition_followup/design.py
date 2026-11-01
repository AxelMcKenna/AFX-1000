"""AX02 voltage-RCB integrated leaf. Native schematic only, parents immutable."""

import json
import os
import re
import subprocess
from pathlib import Path

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def components():
    parent = json.loads((ROOT / "sources/AX01/components.json").read_text())
    parts = [p for p in parent if p["ref"] not in ["Q1", "Q2", "Q3", "D1", "R3"]]
    c = next(p for p in parts if p["ref"] == "C1")
    c.update(
        part="10uF 25V X7R C3225X7R1E106K250AC",
        footprint="Capacitor_SMD:C_1210_3225Metric",
        source="https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3225X7R1E106K250AC",
        note="Selected known native P03 part; new same-face input capacitor. EffectiveC>=1uF and source10:1 to actualoutputC remain receiving.",
    )
    r = next(p for p in parts if p["ref"] == "R4")
    r["pins"][0]["net"] = "SWITCHED_AUX"
    parts.insert(
        1,
        dict(
            ref="U2",
            part="TPS22913CYZVR",
            footprint="RMX_AX02:YZV_4_Receiving",
            source="https://www.ti.com/lit/ds/symlink/tps22910a.pdf",
            note="Active-HIGH C variant; voltage-basedRCB, QOD. All switching times/RCBthreshold/leak remain typical or condition-specific. No physicalacceptance.",
            pins=[
                dict(number=n, name=name, net=net, kind=kind, side="R" if kind == "output" else "L")
                for n, name, net, kind in [
                    ("A1", "VOUT", "SWITCHED_AUX", "passive"),
                    ("A2", "VIN", "AUX", "power_in"),
                    ("B1", "GND", "AGND", "power_in"),
                    ("B2", "ON", "RUN_GATE_COMMAND", "input"),
                ]
            ],
        ),
    )
    for k, p in enumerate(parts):
        p.update(x=55.88 + (k % 4) * 121.92, y=66.04 + (k // 4) * 91.44)
    return parts


def footprint():
    lib = ROOT / "RMX_AX02.pretty"
    lib.mkdir(exist_ok=True)
    text = [
        '(footprint "YZV_4_Receiving" (version 20250108) (generator pcbnew) (layer "F.Cu")',
        '(descr "TIYZV maxbody0.918mm/height0.5/pitch0.5; 0.23NSMDlands are RECEIVING, not manufacturer land approval")',
        "(attr smd)",
        '(property "Reference" "REF**" (at 0 -1.2 0) (layer "F.SilkS") (effects (font (size .6 .6))))',
        '(property "Value" "TPS22913CYZVR" (at 0 1.2 0) (layer "F.Fab") (effects (font (size .6 .6))))',
        '(fp_rect (start -.459 -.459) (end .459 .459) (stroke (width .05) (type default)) (fill none) (layer "F.Fab"))',
        '(fp_rect (start -.71 -.71) (end .71 .71) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))',
        '(fp_circle (center -.57 -.57) (end -.52 -.57) (stroke (width .05) (type default)) (fill none) (layer "F.SilkS"))',
    ]
    for n, x, y in [("A1", -0.25, -0.25), ("A2", 0.25, -0.25), ("B1", -0.25, 0.25), ("B2", 0.25, 0.25)]:
        text.append(
            f'(pad "{n}" smd circle (at {x} {y}) (size .23 .23) (layers "F.Cu" "F.Paste" "F.Mask") (solder_mask_margin .05))'
        )
    path = lib / "YZV_4_Receiving.kicad_mod"
    path.write_text("\n".join(text) + ")\n")
    assert set(re.findall(r'\(pad "([^\"]+)"', path.read_text())) == {"A1", "A2", "B1", "B2"}


def build():
    assert not (ROOT / "handoff.json").exists()
    footprint()
    parts = components()
    generate(
        ROOT,
        "AX02",
        "power_run_integrated_leaf",
        parts,
        [
            (
                20,
                350,
                "AX02: Original internalPOWER_RUN/PG/R113 unchanged; only externalJ106.3 receives newleaf.",
            ),
            (
                20,
                360,
                "Independent100k pullup and1M pulldown defineON. No weakinternalpulldown assumed; no discreteMOSbootstrap.",
            ),
            (
                20,
                370,
                "RCB/hotOFF/partialpower/cutoff/shorttransient remain unqualified. NativeERCzero is schematic scope only.",
            ),
        ],
        (550, 400),
        [("AUX", 20.32, 20.32), ("AGND", 60.96, 20.32)],
    )
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config",
        FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
    )
    commands = []
    for n, args in [
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
        ("svg", ["sch", "export", "svg", "--output", str(ROOT / "generated/svg")]),
    ]:
        cmd = [cli, *args, str(ROOT / "power_run_integrated_leaf.kicad_sch")]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        (ROOT / "generated" / f"{n}.log").write_text(result.stdout + result.stderr)
        commands.append(dict(command=cmd, returncode=result.returncode))
        if result.returncode:
            raise RuntimeError((n, result.returncode))
    actual, pins = netlist(ROOT / "generated/netlist.xml")
    mismatch = [
        p["ref"]
        for p in parts
        if actual[p["ref"]].findtext("value") != p["part"]
        or pins[p["ref"]] != {x["number"]: x["net"] for x in p["pins"]}
    ]
    findings = [
        v for s in json.loads((ROOT / "generated/erc.json").read_text())["sheets"] for v in s["violations"]
    ]
    result = dict(
        parts=len(parts),
        integrated_new_parts=len(parts) - 2,
        bench_headers=2,
        native_commands=commands,
        pin_value_mismatches=mismatch,
        erc_findings=findings,
        original_PCB_edited=False,
        physical_qualified=False,
        PCB_implemented=False,
    )
    (ROOT / "generated/native.json").write_text(json.dumps(result, indent=2) + "\n")
    assert not mismatch and not findings
    print(json.dumps(result))


if __name__ == "__main__":
    build()
