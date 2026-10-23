#!/usr/bin/env python3
"""Render A04/E07/E18 solids, reviews, and collision envelopes; verify each solid.

Requires OpenSCAD and trimesh/numpy/Pillow in the invoking Python environment.
Only local files and subprocesses are used. No hardware validation is implied.
"""

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def check_solid(path, backend):
    import trimesh

    mesh = trimesh.load_mesh(path)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise RuntimeError(
            f"{path.name}: invalid mesh (watertight={mesh.is_watertight}, volume={mesh.volume})"
        )
    # Watertightness alone permits multiple disconnected printable pieces.
    parent = list(range(len(mesh.faces)))

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for a, b in mesh.face_adjacency:
        parent[root(int(a))] = root(int(b))
    connected = len({root(i) for i in range(len(parent))})
    if connected != 1:
        raise RuntimeError(f"{path.name}: {connected} disconnected solids")
    return dict(
        backend=backend,
        watertight=True,
        winding_consistent=True,
        connected_solids=1,
        triangles=len(mesh.faces),
        volume_mm3=round(float(mesh.volume), 3),
        size_mm=[round(float(v), 3) for v in mesh.extents],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", default="openscad")
    args = parser.parse_args()
    version = subprocess.run([args.openscad, "--version"], capture_output=True, text=True, check=True)
    output_root = ROOT.parent / "electronics/output_stage"
    packet = json.loads((output_root / "generated/placement.json").read_text())
    assert (
        packet["pcb_sha256"]
        == hashlib.sha256((output_root / "output_stage.kicad_pcb").read_bytes()).hexdigest()
    ), "Stale PCB placement packet"
    control_root = ROOT.parent / "electronics/control_inputs"
    control_packet = json.loads((control_root / "generated/placement.json").read_text())
    assert (
        control_packet["pcb_sha256"]
        == hashlib.sha256((control_root / "control_inputs.kicad_pcb").read_bytes()).hexdigest()
    ), "Stale control input PCB packet"
    report = dict(
        revision="A04/" + packet["revision"] + "/E18",
        renderer=(version.stdout + version.stderr).strip(),
        solids={},
        checks={},
    )
    model = ROOT / "enclosure.scad"
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-cad-") as temporary:
        temp = Path(temporary)

        def run(name, extra, expect_empty=False, backend="Manifold"):
            summary = temp / (name + ".json")
            command = [
                args.openscad,
                "--hardwarnings",
                "--backend",
                backend,
                "--summary",
                "all",
                "--summary-file",
                str(summary),
                *extra,
                str(model),
            ]
            process = subprocess.run(command, capture_output=True, text=True)
            log = process.stdout + process.stderr
            if expect_empty:
                if process.returncode != 1 or "Current top level object is empty." not in log:
                    raise RuntimeError(f"{name} must be empty; got {process.returncode}:\n{log}")
            elif process.returncode:
                raise RuntimeError(f"{name} failed:\n{log}")
            return json.loads(summary.read_text()) if summary.is_file() else {}

        for part in [
            "base",
            "panel",
            "rear_panel",
            "lever_bracket",
            "lever_arm",
            "fit_coupon",
            "strip_backer",
        ]:
            path = OUT / (part + ".stl")
            # Use CGAL for printable exports: the 2026.10.15 Manifold exporter
            # leaves zero-thickness remnants on some coplanar junctions here.
            # Validate the actual exported STL rather than trusting backend status.
            backend = "CGAL"
            run(part, ["--export-format", "binstl", "-o", str(path), "-D", f'part="{part}"'], backend=backend)
            result = check_solid(path, backend)
            report["solids"][part] = result
            print(
                f"{part}: one closed solid, {result['triangles']} triangles, {result['volume_mm3']:.1f} mm3",
                flush=True,
            )
        run(
            "lever_clearance", ["-o", str(temp / "lever-collision.stl"), "-D", 'part="lever_collision"'], True
        )
        report["checks"]["lever_clearance"] = dict(
            result="empty intersection",
            range_degrees=[0, 35],
            interval_degrees=1,
            expansion_mm=0.1,
            method="per-convex-primitive hull between adjacent expanded poses; chord error <0.001 mm at R25",
            against=[
                "base including mounts",
                "top panel",
                "bracket including stops",
                "listed internal envelopes",
            ],
            limitation="excludes spring, fasteners, wiring, and component detail outside reserves",
        )
        run(
            "output_clearance",
            ["-o", str(temp / "output-collision.stl"), "-D", 'part="output_collision"'],
            True,
        )
        report["checks"]["output_clearance"] = dict(
            result="empty intersection",
            against=[
                "actual base including floor recess/insert bosses",
                "top panel",
                "other board/component/port reserves",
                "scene PCB including 0.2mm vertical allowance",
                "switch and conservative untrimmed lead reserves",
                "lever bracket",
            ],
            source="native " + packet["revision"] + " PCB-derived component and solder envelopes",
            pcb_routed=packet["pcb_routed"],
            physical_fit_verified=False,
            limitation="conditional part/assembly limits; excludes insert process, wire bends, final converter/input/power placement and physical fit",
        )
        run(
            "control_clearance",
            ["-o", str(temp / "control-collision.stl"), "-D", 'part="control_collision"'],
            True,
        )
        report["checks"]["control_clearance"] = dict(
            result="empty intersection",
            against=[
                "base/panel/lever bracket",
                "other boards and component/port envelopes",
                "switch and lead reserves",
                "scene-board envelope",
            ],
            source="native E18 PCB-derived courtyard, lead, spacer and screw-head bounds",
            pcb_sha256=control_packet["pcb_sha256"],
            pcb_routed=True,
            physical_fit_verified=False,
            limitation="connector/harness, height, spacer/screw and carrier-drill targets unqualified; excludes remaining electronics",
        )
        run("panel_dxf", ["-o", str(OUT / "panel.dxf"), "-D", 'part="panel_2d"'])
        for name, settings in [
            ("assembly", []),
            ("assembly-pulled", ["-D", "lever_angle=35"]),
            (
                "internals",
                ["-D", "show_controls=false", "-D", "show_panel=false", "-D", "show_internals=true"],
            ),
            ("output-board", ["-D", 'part="output_board"']),
            ("control-board", ["-D", 'part="control_board"']),
        ]:
            run(
                name,
                [
                    "--preview",
                    "--imgsize",
                    "1800,1100",
                    "--camera",
                    "440,-330,400,167,78,18",
                    "--autocenter",
                    "--viewall",
                    "--projection",
                    "o",
                    "--colorscheme",
                    "Tomorrow Night",
                    "-o",
                    str(OUT / (name + ".png")),
                    *settings,
                ],
            )
        (OUT / "solid-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "A04/E07/E18 solid/mesh, output/control placement and conservative lever checks passed. Physical fit remains unverified."
    )


if __name__ == "__main__":
    main()
