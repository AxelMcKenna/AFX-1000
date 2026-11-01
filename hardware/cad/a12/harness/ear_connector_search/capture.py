"""Private immutable extended obstacle snapshot for the source-to-ear curve search."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from hardware.cad.a12.generate import REPO, sha
from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.repaired import packet
from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
OUT = ROOT / "generated"
HARNESS = ROOT.parent
WINDOW = [[154, 90, 3], [198, 139, 37]]


def capture():
    if (ROOT / "capture.json").exists():
        raise ValueError("Preserve existing capture; use a new trial folder")
    INPUTS.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    native, other, hashes = snapshot()
    actual = packet(
        {
            "P03": REPO / "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined",
            "E28": REPO / "hardware/electronics/rail_disconnect/revision28/generated/r58-joint-work",
        }
    )
    native.update(actual)
    hashes.update(actual["source_sha256"])
    ear = HARNESS / "generated/receiver-ear/analysis.json"
    proof = HARNESS / "generated/receiver-ear/verification.json"
    er, ev = json.loads(ear.read_text()), json.loads(proof.read_text())
    assert ev["all_local_ear_checks_clear"] and not ev["changed_inputs"]
    assert er["component_count"] == 77
    for group in ["source_sha256", "evidence_sha256", "evidence_inputs_sha256"]:
        for p, h in ev.get(group, {}).items():
            assert sha(REPO / p) == h, ("Stale ear evidence", p)
            hashes[p] = h
    hashes.update(er["source_sha256"])
    e19 = HARNESS / "generated/receiver-awg18/analysis.json"
    old = json.loads(e19.read_text())
    # Parent ear proof independently establishes exact equality of all inherited footprints.
    other["envelopes"] = [
        b for b in other["envelopes"] if not b[0].startswith(("e19_", "disconnect_"))
    ] + old["current_E19_component_packet"]["bodies"]
    other["boards"] = [b for b in other["boards"] if b[0] not in ("disconnect_carrier", "dsp_carrier")]
    other["ear_board"] = {
        "datum": [30, 42, 6.5],
        "outline_relative_mm": er["actual_outline_relative_mm"],
        "thickness_range_mm": [1.44, 1.76],
    }
    # Own J13 contact reserve is intentionally excluded, not inherited boards/parts.
    other["excluded_own_J13_contact_body"] = "e19_J13"
    native["cylinders"].append(
        ["provisional_H9_head", 182, 97.2, 8.1, 5.6, 2.31, "Project M2 head envelope; actual source pending"]
    )
    physical = {"native": native, "other": other, "H9_provisional_not_actual_source": True}
    (INPUTS / "electronics.json").write_text(json.dumps(physical, indent=2) + "\n")
    files = {
        HARNESS / "source-exit-search/selected-refined-pair.json": "selected-source.json",
        HARNESS / "output-wire-6715.json": "wire.json",
        ear: "ear-analysis.json",
        proof: "ear-verification.json",
        e19: "e19-inherited-analysis.json",
    }
    for p, n in files.items():
        shutil.copy2(p, INPUTS / n)
        hashes[str(p.relative_to(REPO))] = sha(p)
    # Capture every original source into its repository-relative location. SCAD includes remain relative.
    for relative, h in hashes.items():
        p = REPO / relative
        if sha(p) != h:
            raise ValueError("Source changed during capture:" + relative)
        dst = INPUTS / "context" / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
    case = INPUTS / "context/hardware/cad/a12/thermal-integration.scad"
    source = "include <" + str(case) + '>\ntrial="case";\n'
    source += "module window(){translate([154,90,3])cube([44,49,34]);}\nmodule case_parts(){retained_thermal_shell();thermal_controls();thermal_metal_base();lower_shell_fasteners();}\n"
    source += 'if(trial=="case")intersection(){window();case_parts();}\n'
    source += (
        'if(trial=="witness")intersection(){case_parts();translate([163.9,109.9,23])cube([.2,.2,.2]);}\n'
    )
    (OUT / "obstacles.scad").write_text(source)
    # Hardware is complete, not clipped at the source-only window.
    for p, n in [
        (HARNESS.parent / "returns/generated/returns-assembly.stl", "return.stl"),
        (HARNESS.parent / "positive_links/generated/positive-links.stl", "positive.stl"),
    ]:
        if not p.exists() and n == "return.stl":
            candidates = list((HARNESS.parent / "returns/generated").glob("*ASSEMBLY*.stl"))
            if len(candidates) != 1:
                raise ValueError("Locate actual full return assembly STL")
            p = candidates[0]
        shutil.copy2(p, INPUTS / n)
        hashes[str(p.relative_to(REPO))] = sha(p)
    report = dict(
        scope=__doc__,
        window_mm=WINDOW,
        original_source_sha256=hashes,
        captured_inputs_sha256={str(p.relative_to(INPUTS)): sha(p) for p in INPUTS.rglob("*") if p.is_file()},
        full_original_source_still_matches=all(sha(REPO / p) == h for p, h in hashes.items()),
        physical_fit_verified=False,
    )
    (ROOT / "capture.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Captured", len(hashes), "source files", flush=True)


def native(executable):
    report = json.loads((ROOT / "capture.json").read_text())
    cases = {}
    for name in ["case", "witness"]:
        target = INPUTS / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="local_obstacles_only"']
        cmd += ["-D", 'trial="' + name + '"', "-o", str(target), str(OUT / "obstacles.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        log = p.stdout + p.stderr
        (OUT / (name + ".log")).write_text(log)
        accepted = (
            p.returncode == 0
            and target.exists()
            and "NoError" in log
            and not any(x in log for x in ["WARNING", "ERROR"])
        )
        stats = binary_stl(target) if target.exists() else {}
        accepted = accepted and (
            abs(stats.get("volume_mm3", 0) - 0.008) < 1e-6
            if name == "witness"
            else stats.get("volume_mm3", 0) > 1
        )
        cases[name] = dict(accepted=accepted, returncode=p.returncode, command=cmd, **stats)
        print(name, accepted, stats.get("volume_mm3"), flush=True)
    report["native_cases"] = cases
    report["native_obstacles_accepted"] = all(r["accepted"] for r in cases.values())
    report["captured_inputs_sha256"] = {
        str(p.relative_to(INPUTS)): sha(p) for p in INPUTS.rglob("*") if p.is_file()
    }
    (ROOT / "capture.json").write_text(json.dumps(report, indent=2) + "\n")
    if not report["native_obstacles_accepted"]:
        raise ValueError("Rejected extended obstacles")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", type=Path)
    args = parser.parse_args()
    if not (ROOT / "capture.json").exists():
        capture()
    if args.openscad:
        native(args.openscad)
