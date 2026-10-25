#!/usr/bin/env python3
"""Render A07/E07/E18/E19/E20/E23 solids and collision envelopes.

Requires OpenSCAD and trimesh/numpy/Pillow in the invoking Python environment.
Only local files and subprocesses are used. No hardware validation is implied.
"""

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from . import generate as panel
from .paths import ARTIFACTS, update_previews

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


def check_mounting_faces(path, regions):
    """Accept only exporter remnants on explicitly intended mounting faces.

    No general collision tolerance is applied. Every triangle must lie on one
    named mounting plane and within its fixing footprint, to 0.00001mm. The
    separate envelope check still rejects volumetric intersections at 1e-7mm.
    """
    import numpy as np
    import trimesh

    mesh = trimesh.load_mesh(path, process=False)
    triangles = mesh.triangles
    assert len(triangles), "Expected the native intersection mesh"
    covered = np.zeros(len(triangles), dtype=bool)
    maximum = 0.0
    matched = []
    tolerance = 1e-5
    for name, x, y, z, width in regions:
        inside = np.all(
            (triangles[:, :, 0] >= x - width / 2 - tolerance)
            & (triangles[:, :, 0] <= x + width / 2 + tolerance)
            & (triangles[:, :, 1] >= y - width / 2 - tolerance)
            & (triangles[:, :, 1] <= y + width / 2 + tolerance),
            axis=1,
        )
        deviation = np.max(np.abs(triangles[:, :, 2] - z), axis=1)
        hit = inside & (deviation <= tolerance)
        if np.any(hit):
            maximum = max(maximum, float(np.max(deviation[hit])))
            matched.append(name)
        covered |= hit
    if not np.all(covered):
        raise RuntimeError(f"Intersection outside intended mounting faces: {mesh.bounds.tolist()}")
    return dict(
        intersection="intended mounting-face contact only",
        contact_faces=matched,
        numerical_plane_tolerance_mm=tolerance,
        maximum_plane_deviation_mm=maximum,
        intersection_triangles=len(triangles),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", default="openscad")
    parser.add_argument(
        "--update-previews",
        action="store_true",
        help="Update tracked documentation previews after successful checks",
    )
    args = parser.parse_args()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
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
    carrier_root = ROOT.parent / "electronics/processor_carrier"
    carrier_packet = json.loads((carrier_root / "generated/placement.json").read_text())
    assert (
        carrier_packet["pcb_sha256"]
        == hashlib.sha256((carrier_root / "processor_carrier.kicad_pcb").read_bytes()).hexdigest()
    ), "Stale processor carrier PCB packet"
    led_root = ROOT.parent / "electronics/led_driver"
    led_packet = json.loads((led_root / "generated/placement.json").read_text())
    assert (
        led_packet["pcb_sha256"]
        == hashlib.sha256((led_root / "led_driver.kicad_pcb").read_bytes()).hexdigest()
    ), "Stale LED driver PCB packet"
    assert led_packet["pcb_routed"] and led_packet["copper_layers"] == 6
    input_root = ROOT.parent / "electronics/input_protection"
    input_packet = json.loads((OUT / "input-power-placement.json").read_text())
    assert (
        input_packet["pcb_sha256"]
        == hashlib.sha256((input_root / "input_protection.kicad_pcb").read_bytes()).hexdigest()
    )
    assert input_packet["revision"] == "A07/E23" and input_packet["pcb_routed"]
    report = dict(
        revision="A07/" + packet["revision"] + "/E18/E19/E20/E23",
        renderer=(version.stdout + version.stderr).strip(),
        solids={},
        checks={},
    )
    model = ROOT / "enclosure.scad"
    OUT.mkdir(exist_ok=True)
    (OUT / "solid-validation.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-cad-") as temporary:
        temp = Path(temporary)

        def run(name, extra, expect_empty=False, backend="Manifold", mounting_faces=None):
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
                    if process.returncode == 0 and mounting_faces:
                        destination = Path(extra[extra.index("-o") + 1])
                        return check_mounting_faces(destination, mounting_faces)
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
            path = ARTIFACTS / (part + ".stl")
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
        daughter_faces = [
            (f"daughter_landing_{index}", x, panel.D - y, 8.1, 5.5)
            for index, (x, y) in enumerate(control_packet["mount_centers_layout_mm"], 1)
        ]
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
        control_result = run(
            "control_clearance",
            ["-o", str(temp / "control-collision.stl"), "-D", 'part="control_collision"'],
            True,
            mounting_faces=daughter_faces,
        )
        report["checks"]["control_clearance"] = dict(
            result=control_result.get("intersection", "empty intersection"),
            contact_evidence=control_result if "intersection" in control_result else {},
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
        carrier_faces = daughter_faces + [
            (f"carrier_boss_{index}", x, panel.D - y, 6.5, 7.2)
            for index, (x, y) in enumerate(carrier_packet["mount_centers_layout_mm"], 1)
        ]
        carrier_result = run(
            "carrier_clearance",
            ["-o", str(temp / "carrier-collision.stl"), "-D", 'part="carrier_collision"'],
            True,
            mounting_faces=carrier_faces,
        )
        report["checks"]["carrier_clearance"] = dict(
            result=carrier_result.get("intersection", "empty intersection"),
            contact_evidence=carrier_result if "intersection" in carrier_result else {},
            pcb_sha256=carrier_packet["pcb_sha256"],
            pcb_routed=True,
            source="native E19 footprint, socket/module, solder-tail, fixing and USB allocations",
            against=[
                "base/panel/lever bracket",
                "other board/component/port reserves",
                "conservative switch lead bounds",
                "scene-board envelope",
            ],
            physical_fit_verified=False,
            limitation="conditional part/assembly bounds; complete converter/power/LED/sensor/SD placement, pigtail routing and physical fit unfinished",
        )
        led_faces = [
            (f"led_boss_{i}", x, panel.D - y, 6.5, 7.2)
            for i, (x, y) in enumerate(led_packet["mount_centers_layout_mm"], 1)
        ]
        led_result = run(
            "led_clearance",
            ["-o", str(temp / "led-collision.stl"), "-D", 'part="led_collision"'],
            True,
            mounting_faces=led_faces,
        )
        report["checks"]["led_clearance"] = dict(
            result=led_result.get("intersection", "empty intersection"),
            contact_evidence=led_result if "intersection" in led_result else {},
            pcb_sha256=led_packet["pcb_sha256"],
            pcb_routed=True,
            source="native E20 footprint, header/harness, solder-tail and fixing bounds",
            against=[
                "base/panel/lever bracket",
                "other board/component/port reserves",
                "switch and untrimmed lead bounds",
                "scene-board envelope",
            ],
            physical_fit_verified=False,
            full_unit_power_budget_closed=False,
            limitation="conditional part/assembly bounds; emitter boards, harness routing, power integration and physical fit unfinished",
        )
        input_result = run(
            "input_placement",
            ["-o", str(temp / "input-collision.stl"), "-D", 'part="input_collision"'],
            True,
            mounting_faces=[
                [f"input_H{i}", x, panel.D - y, 7.9, 7.2]
                for i, (x, y) in enumerate(input_packet["mount_centers_layout_mm"], 1)
            ],
        )
        report["checks"]["input_power_placement"] = dict(
            result=input_result.get("intersection", "empty intersection"),
            contact_evidence=input_result if "intersection" in input_result else {},
            pcb_sha256=input_packet["pcb_sha256"],
            pcb_routed=True,
            placement_packet_sha256=hashlib.sha256(
                (OUT / "input-power-placement.json").read_bytes()
            ).hexdigest(),
            source="actual E23 notched PCB, component/lead/harness and fixing bounds; candidate jack/actuator reserves",
            against=[
                "base and rear I/O plate",
                "top panel and lever bracket",
                "other board/component/port reserves",
                "scene-board envelope",
            ],
            physical_fit_verified=False,
            full_unit_power_budget_closed=False,
            limitation="conditional part/assembly dimensions; exact plug mating, actuator access, mounts, harness and physical fit unqualified",
        )
        run("panel_dxf", ["-o", str(ARTIFACTS / "panel.dxf"), "-D", 'part="panel_2d"'])
        for name, settings in [
            ("assembly", []),
            ("assembly-pulled", ["-D", "lever_angle=35"]),
            (
                "internals",
                ["-D", "show_controls=false", "-D", "show_panel=false", "-D", "show_internals=true"],
            ),
            ("output-board", ["-D", 'part="output_board"']),
            ("control-board", ["-D", 'part="control_board"']),
            ("processor-board", ["-D", 'part="carrier_board"']),
            ("led-board", ["-D", 'part="led_board"']),
            ("input-board", ["-D", 'part="input_board"']),
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
                    str(ARTIFACTS / (name + ".png")),
                    *settings,
                ],
            )
        (OUT / "solid-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    if args.update_previews:
        update_previews(
            [
                "assembly",
                "internals",
                "output-board",
                "control-board",
                "processor-board",
                "led-board",
                "input-board",
            ]
        )
    print(
        "A07/E07/E18/E19/E20/E23 solids, output/control/processor/LED/input placement and lever checks passed. Physical fit and complete power integration remain unverified."
    )


if __name__ == "__main__":
    main()
