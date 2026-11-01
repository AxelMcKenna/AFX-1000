"""Independently check the external-base/retained-carrier nominal integration."""

import argparse
import json
import struct
import subprocess
from pathlib import Path

from .generate import OUT, REPO, ROOT, sha
from .generate import main as generate
from .verify import stl_volume


def carrier_integrity(path):
    """Reject disconnected carrier fragments and nonclosed triangle boundaries."""
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + 50 * count and count > 0
    vertices, edges, parent = {}, {}, list(range(count))
    active, duplicate_vertex_faces = [], 0

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for index in range(count):
        row = struct.unpack_from("<12fH", data, 84 + 50 * index)
        ids = []
        for start in (3, 6, 9):
            point = tuple(row[start : start + 3])
            ids.append(vertices.setdefault(point, len(vertices)))
        if len(set(ids)) != 3:
            # Binary STL converts coordinates to float32. Exact duplicate
            # vertices create zero-area export faces; these carry no material
            # and must not create artificial mesh components or edge counts.
            duplicate_vertex_faces += 1
            continue
        active.append(index)
        for offset in range(3):
            edge = tuple(sorted((ids[offset], ids[(offset + 1) % 3])))
            adjacent = edges.setdefault(edge, [])
            if adjacent:
                parent[find(index)] = find(adjacent[0])
            adjacent.append(index)
    components = len({find(index) for index in active})
    nonmanifold = sum(len(adjacent) != 2 for adjacent in edges.values())
    assert components == 1 and nonmanifold == 0, (components, nonmanifold)
    return dict(
        connected_triangle_edge_components=components,
        boundary_or_nonmanifold_edges=nonmanifold,
        triangles=count,
        exact_float32_vertex_matching=True,
        excluded_duplicate_vertex_zero_area_faces=duplicate_vertex_faces,
        raw_stl_contains_only_nondegenerate_faces=duplicate_vertex_faces == 0,
        structural_strength_verified=False,
    )


def verify(executable):
    generate()
    allocation = json.loads((OUT / "allocation.json").read_text())
    sources = dict(allocation["source_sha256"])
    for path in [
        ROOT / "thermal-integration.scad",
        ROOT / "verify_thermal_integration.py",
        ROOT / "verify.py",
        ROOT / "thermal/generated/thermal-base.scad",
        ROOT / "thermal/generated/interface.json",
        ROOT / "returns/generated/returns.scad",
        *sorted((ROOT / "returns/generated").glob("*.stl")),
        # Bind the generated files actually included by integration.scad.
        # The separate repaired-components packet is not consumed here.
        OUT / "components.scad",
        OUT / "interface.scad",
    ]:
        sources[str(path.relative_to(REPO))] = sha(path)
    artifacts = REPO / "build/artifacts/cad/a12/thermal-integration"
    artifacts.mkdir(parents=True, exist_ok=True)
    checks = {}
    for part in [
        "shell",
        "base_shell_collision",
        "base_electronics_collision",
        "base_controls_collision",
        "returns_shell_collision",
        "returns_controls_collision",
        "returns_base_collision",
        "returns_hardware",
        "returns_positive_control",
        "lower_shell_fasteners",
        "lower_fastener_shell_collision",
        "lower_fastener_base_collision",
        "lower_fastener_electronics_collision",
        "lower_fastener_controls_collision",
        "undersized_countersink_positive_control",
        "unmodified_shell_positive_control",
    ]:
        target = artifacts / (part + ".stl")
        target.unlink(missing_ok=True)
        command = [
            str(executable),
            "--hardwarnings",
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
            "-D",
            'part="thermal_only"',
            "-D",
            f'thermal_part="{part}"',
            "-o",
            str(target),
            str(ROOT / "thermal-integration.scad"),
        ]
        run = subprocess.run(command, capture_output=True, text=True, timeout=60)
        log = run.stdout + run.stderr
        logfile = OUT / ("thermal-integration-" + part + ".log")
        logfile.write_text(log)
        assert "WARNING" not in log and "ERROR" not in log, log
        if part in {
            "shell",
            "unmodified_shell_positive_control",
            "returns_hardware",
            "returns_positive_control",
            "lower_shell_fasteners",
            "undersized_countersink_positive_control",
        }:
            assert run.returncode == 0 and target.exists(), log
            volume = stl_volume(target)
            if part == "returns_positive_control":
                assert abs(volume - 1) < 0.00001, (part, volume)
            elif part == "undersized_countersink_positive_control":
                assert volume > 0.01, (part, volume)
            else:
                assert volume > 1, (part, volume)
            checks[part] = dict(volume_mm3=volume, stl_sha256=sha(target))
            if part == "shell":
                checks[part]["integrity"] = carrier_integrity(target)
        else:
            assert run.returncode == 1 and "Current top level object is empty." in log, (part, log)
            target.unlink(missing_ok=True)
            checks[part] = dict(result="empty intersection")
        checks[part]["log_sha256"] = sha(logfile)
    assert all(sha(REPO / name) == expected for name, expected in sources.items()), (
        "Integration source changed during native run; repeat after the edit"
    )
    report = dict(
        revision="A12-development",
        scope="Nominal external metal base and return hardware against retained plastic carrier and controls; inherited electronics against base only",
        checks=checks,
        source_sha256=sources,
        actual_p03_component_integration=False,
        actual_e28_component_integration=False,
        return_bar_and_harness_integration=False,
        return_hardware_nominal_shell_controls_base_integration=True,
        shell_fastener_geometry_verified=False,
        lower_shell_fastener_nominal_envelope_integration=True,
        lower_shell_fastener_tolerance_and_engagement_verified=False,
        structural_retention_verified=False,
        thermal_qualified=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (OUT / "thermal-integration-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("A12: nominal retained carrier/base checks passed; physical and complete board integration open")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", required=True, type=Path)
    verify(parser.parse_args().openscad.resolve())
