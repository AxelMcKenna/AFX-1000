"""Native solids, independent portable integrity and explicit unresolved holds."""

import argparse
import json
import math
import struct
import subprocess

from .analyze import analytical, geometry_screen
from .generate import OUT, REPO, ROOT, load, sha


def binary_stl(path):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + 50 * count and count > 0
    terms = []
    xyz = []
    for i in range(count):
        row = struct.unpack_from("<12fH", data, 84 + 50 * i)
        a, b, c = row[3:6], row[6:9], row[9:12]
        xyz.extend([a, b, c])
        terms.append(
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )
    return dict(
        volume_mm3=abs(math.fsum(terms)) / 6,
        triangles=count,
        min_mm=[min(p[i] for p in xyz) for i in range(3)],
        max_mm=[max(p[i] for p in xyz) for i in range(3)],
    )


def checks_scad(geometry):
    rows = []
    for row in geometry["bottom_courtyards"]:
        x, y, xx, yy = row["courtyard_global_mm"]
        rows.append([x, y, 3.3, xx - x, yy - y, 3.0])
    return (
        """include <thermal-base.scad>
part="collision";
module native_bottom_components(){for(r="""
        + json.dumps(rows)
        + """)translate([r[0],r[1],r[2]])cube([r[3],r[4],r[5]]);}
module hardware(){thermal_metal_base();thermal_pads(6.3);}
if(part=="collision")intersection(){hardware();native_bottom_components();}
if(part=="positive_control")intersection(){hardware();translate([271,135,5])cube([1,1,1]);}
"""
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", required=True)
    args = parser.parse_args()
    d = load()
    analysis = json.loads((OUT / "analysis.json").read_text())
    # Re-evaluate portable analytical values; no stale saved numerical-screen pass.
    current = analytical(d)
    assert all(analysis[k] == v for k, v in current.items())
    geometry = geometry_screen(d)
    assert geometry == analysis["actual_geometry_screen"], "P03 changed; regenerate analysis before checking"
    assert analysis["actual_support_copper_screen"][
        "all_ten_nominal_metal_faces_free_of_actual_native_copper"
    ]
    (OUT / "collision.scad").write_text(checks_scad(geometry))
    native = {}
    for part, source in [
        ("base", "preview.scad"),
        ("collision", "collision.scad"),
        ("positive_control", "collision.scad"),
    ]:
        target = OUT / (f"native-{part}.stl")
        target.unlink(missing_ok=True)
        command = [
            args.openscad,
            "--hardwarnings",
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
            "-D",
            f'part="{part}"',
            "-o",
            str(target),
            str(OUT / source),
        ]
        run = subprocess.run(command, capture_output=True, text=True, timeout=120)
        log = run.stdout + run.stderr
        (OUT / f"native-{part}.log").write_text(log)
        assert "WARNING" not in log and "ERROR" not in log, log
        if part == "collision":
            assert run.returncode == 1 and "Current top level object is empty." in log, log
            target.unlink(missing_ok=True)
            native[part] = dict(
                result="empty actual-native-bottom-prism intersection", returncode=run.returncode
            )
        else:
            assert run.returncode == 0 and "NoError" in log and target.exists(), log
            native[part] = dict(
                result="valid native manifold", returncode=run.returncode, **binary_stl(target)
            )
            if part == "positive_control":
                assert native[part]["volume_mm3"] > 0.9
    cad = json.loads((OUT / "cad-verification.json").read_text())
    relative = abs(cad["base_volume_mm3"] - native["base"]["volume_mm3"]) / cad["base_volume_mm3"]
    assert relative < 0.0005, ("Independent SCAD/STEP volume mismatch", relative)
    assert geometry["actual_native_prism_screen_pass"], geometry
    # Self receipts deliberately exclude themselves. Generated geometry is evidence,
    # not source; native P03 source is separately bound so another layout cannot inherit a pass.
    source_files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in (".py", ".json", ".md")]
    source_files.append(REPO / "tests/tooling/test_power_thermal.py")
    p03 = REPO / "hardware/electronics/power_distribution/p03"
    source_files += [
        p03 / "power_p03.kicad_pcb",
        p03 / "spec.py",
        p03 / "board.py",
        p03 / "components.json",
        p03 / "generated/placement.json",
    ]
    construction = p03 / "construction.json"
    if construction.exists():
        contract = json.loads(construction.read_text())
        assert contract["pcb_sha256"] == geometry["native_p03_sha256"], (
            "Construction requirement/PCB mismatch"
        )
        source_files.append(construction)
        for path, expected in contract.get("source_sha256", {}).items():
            assert sha(REPO / path) == expected, "Stale construction dependency: " + path
            source_files.append(REPO / path)
    for p in p03.glob("generated/*thermal*.json"):
        source_files.append(p)
    for p in p03.glob("generated/*heat*.json"):
        source_files.append(p)
        ledger = json.loads(p.read_text())
        for path, expected in ledger.get("source_sha256", {}).items():
            from pathlib import Path

            dependency = Path(path)
            if not dependency.is_absolute():
                dependency = REPO / dependency
            dependency.relative_to(REPO)
            assert sha(dependency) == expected, "Stale heat-ledger dependency: " + path
            source_files.append(dependency)
    version = subprocess.run([args.openscad, "--version"], capture_output=True, text=True, check=True)
    assert sha(p03 / "power_p03.kicad_pcb") == geometry["native_p03_sha256"], (
        "P03 changed during native checks; reject and rerun"
    )
    report = dict(
        revision=d["revision"],
        native_engine=(version.stdout + version.stderr).strip(),
        native_checks=native,
        independent_scad_step_relative_volume_difference=relative,
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(set(source_files))},
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in sorted(OUT.iterdir())
            if p.is_file() and p.name not in ("verification.json", "verify-log.txt")
        },
        actual_native_p03_courtyard_and_support_screen_pass=True,
        all_ten_nominal_support_faces_free_of_actual_saved_copper=True,
        scope="Bounds/prisms at PCBbottom6.3,3mm bottomcomponent envelope; no full enclosure or assembly electrical-clearance/tolerance proof. Exact STEP volume and independent Manifold solid cross-checked.",
        convection_coefficient_measured=False,
        all_package_junction_paths_verified=False,
        electrical_isolation_verified=False,
        compression_life_verified=False,
        physical_tests_performed=0,
        physical_fit_verified=False,
        thermal_qualified=False,
        fabrication_released=False,
        build_ready=False,
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if not k.endswith("_sha256")}, indent=2))


if __name__ == "__main__":
    main()
