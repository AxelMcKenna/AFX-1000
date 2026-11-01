"""Native isolated manufacturer-land clearance check and a failing control.

This is a two-footprint fixture, never the NF05H board or its routing proof.
Run with the KiCad-bundled Python (pcbnew).
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated/package-fixture"
CLI = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    assert not (ROOT / "handoff.json").exists()
    OUT.mkdir(exist_ok=True)
    (OUT / "fp-lib-table").write_text(
        '(fp_lib_table (lib (name "NF05H_Manufacturer")(type "KiCad")(uri "${KIPRJMOD}/../../NF05H_Manufacturer.pretty")(options "")(descr "Actual TI manufacturer lands")))\n'
    )
    b = pcbnew.BOARD()
    for i, name in enumerate(["TI_DCU0008A", "TI_DCK0006A"]):
        fp = pcbnew.FootprintLoad(str(ROOT / "NF05H_Manufacturer.pretty"), name)
        assert fp
        fp.SetReference(f"U{i + 1}")
        fp.SetValue(name)
        fp.SetFPID(pcbnew.LIB_ID("NF05H_Manufacturer", name))
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(10 + 12 * i), pcbnew.FromMM(10)))
        b.Add(fp)
        for pad in fp.Pads():
            n = pcbnew.NETINFO_ITEM(b, f"FIXTURE_{i}_{pad.GetNumber()}")
            b.Add(n)
            pad.SetNet(n)
    for (x, y), (xx, yy) in zip([(0, 0), (32, 0), (32, 20), (0, 20)], [(32, 0), (32, 20), (0, 20), (0, 0)]):
        edge = pcbnew.PCB_SHAPE()
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        edge.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(xx), pcbnew.FromMM(yy)))
        edge.SetWidth(pcbnew.FromMM(0.05))
        b.Add(edge)
    project = {
        "board": {
            "design_settings": {
                "rules": {"min_clearance": 0.2},
                "rule_severities": {
                    "footprint_type_mismatch": "error",
                    "footprint_missing_courtyard": "error",
                    "track_dangling": "error",
                    "track_unconnected": "error",
                },
            }
        },
        "net_settings": {
            "classes": [
                {
                    "name": "Default",
                    "clearance": 0.2,
                    "track_width": 0.2,
                    "via_diameter": 0.65,
                    "via_drill": 0.3,
                }
            ]
        },
    }
    results = {}
    for label in ["manufacturer", "enlarged_DCU_pad_rejected"]:
        if label.startswith("enlarged"):
            fp = next(f for f in b.GetFootprints() if f.GetReference() == "U1")
            pad = next(p for p in fp.Pads() if p.GetNumber() == "1")
            old = pad.GetSize()
            pad.SetSize(pcbnew.VECTOR2I(old.x, pcbnew.FromMM(0.4)))
        pcb = OUT / (label + ".kicad_pcb")
        pcbnew.SaveBoard(str(pcb), b)
        (OUT / (label + ".kicad_pro")).write_text(json.dumps(project))
        report = OUT / (label + "-drc.json")
        cmd = [
            CLI,
            "pcb",
            "drc",
            "--all-track-errors",
            "--severity-all",
            "--format",
            "json",
            "--output",
            str(report),
            str(pcb),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env=dict(os.environ, KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config"),
        )
        (OUT / (label + "-command.json")).write_text(
            json.dumps(
                dict(command=cmd, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr),
                indent=2,
            )
            + "\n"
        )
        assert proc.returncode == 0, proc.stderr
        r = json.loads(report.read_text())
        results[label] = dict(
            violations=r["violations"],
            unconnected_items=r["unconnected_items"],
            pcb_sha256=sha(pcb),
            report_sha256=sha(report),
        )
    assert not results["manufacturer"]["violations"], results["manufacturer"]["violations"]
    assert not results["manufacturer"]["unconnected_items"]
    assert any(v["type"] == "clearance" for v in results["enlarged_DCU_pad_rejected"]["violations"])
    receipt = dict(
        scope="Two isolated manufacturer footprint fixture ONLY; not NF05 PCB",
        min_clearance_mm=0.2,
        results=results,
        source_sha256={
            "package_check.py": sha(Path(__file__)),
            **{
                str(p.relative_to(ROOT)): sha(p)
                for p in (ROOT / "NF05H_Manufacturer.pretty").glob("*.kicad_mod")
            },
        },
        actual_NF05_board_implemented=False,
        manufacturer_process_accepted=False,
        physical_qualified=False,
    )
    (OUT / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Actual manufacturer-land fixture zero native violations/opens; enlarged pad control rejected")


if __name__ == "__main__":
    run()
