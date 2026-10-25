"""Export compact A11 fit stations and verify rigid geometry without printing."""

import argparse
import csv
import datetime
import hashlib
import json
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from hardware.cad.a11.generate import schedule

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
A11 = ROOT.parent / "a11"
OUT = REPO / "build/artifacts/cad/a11-fitkit"
EVIDENCE = REPO / "hardware/validation/mechanical-fit"
STATIONS = ("quantize", "auto", "pad_0", "pad_1", "scene_2")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    buttons, knobs = schedule()
    rows = []
    for name in STATIONS:
        index = next(i for i, b in enumerate(buttons) if b[0] == name)
        for part in ("key", "holder", "panel", "guide"):
            rows.append(dict(name=name + "-" + part, part=part, index=index, quantity=1))
    rows.append(dict(name="retaining-clip", part="clip", index=0, quantity=8))
    seen = set()
    for index, knob in enumerate(knobs):
        shape = tuple(knob[3:5])
        if shape in seen:
            continue
        seen.add(shape)
        rows.append(dict(name=f"knob-{shape[0]:g}x{shape[1]:g}", part="knob", index=index, quantity=1))
    for part in ("selector_cap", "selector_panel", "selector_guide", "pot_panel", "pot_guide"):
        rows.append(
            dict(name=part.replace("_", "-"), part=part, index=0, quantity=2 if part == "selector_cap" else 1)
        )
    return rows


def source_hashes():
    files = list(A11.rglob("*.scad")) + [
        A11 / "generate.py",
        A11 / "generated/controls.csv",
        A11 / "generated/control-schedule.json",
        ROOT / "fixture.scad",
        ROOT / "build.py",
        ROOT / "README.md",
        ROOT / "MEASUREMENTS.csv",
        ROOT / "PURCHASED.csv",
        REPO / "tests/tooling/test_a11_fitkit.py",
    ]
    return {str(p.relative_to(REPO)): sha(p) for p in sorted(files)}


def connected_solids(mesh):
    parents = list(range(len(mesh.faces)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for a, b in mesh.face_adjacency:
        parents[root(int(a))] = root(int(b))
    return len({root(i) for i in range(len(parents))})


def inspect_mesh(path):
    import trimesh

    mesh = trimesh.load_mesh(path)
    solids = connected_solids(mesh)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0 and solids == 1, path
    assert all(float(v) <= 150 for v in mesh.extents), ("Exceeds compact test envelope", path)
    assert abs(float(mesh.bounds[0][2])) <= 1e-5, ("Print face is not Z=0", path)
    return dict(
        watertight=True,
        winding_consistent=True,
        connected_solids=solids,
        triangles=len(mesh.faces),
        size_mm=[round(float(x), 4) for x in mesh.extents],
        volume_mm3=round(float(mesh.volume), 4),
        sha256=sha(path),
    )


def native(executable, name, part, index=0, check=False):
    folder = OUT / ("checks" if check else "STL")
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / (name + ".stl")
    command = [
        str(executable),
        "--hardwarnings",
        "--backend",
        "CGAL" if check or part == "holder" else "Manifold",
        "--export-format",
        "binstl",
        "-D",
        "part=" + json.dumps(part),
        "-D",
        f"index={index}",
        "-o",
        str(destination),
        str(ROOT / "fixture.scad"),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    log = result.stdout + result.stderr
    (OUT / "logs").mkdir(exist_ok=True)
    (OUT / "logs" / (name + ".txt")).write_text(log)
    if check and result.returncode == 1 and "Current top level object is empty." in log:
        destination.unlink(missing_ok=True)
        return dict(result="empty intersection")
    if result.returncode:
        raise RuntimeError(name + ": " + log[-3000:])
    return destination


def inspect_contact(path, plane, regions):
    """Accept named, zero-depth seats only, never a positive-volume allowance."""
    import numpy as np
    import trimesh

    mesh = trimesh.load_mesh(path, process=False)
    triangles = mesh.triangles
    assert len(triangles), path
    deviation = np.abs(triangles[:, :, 2] - plane)
    assert np.all(deviation <= 1e-5), ("Volumetric or wrong-height interference", path)
    covered = np.zeros(len(triangles), dtype=bool)
    for x, y, width, depth in regions:
        covered |= np.all(
            (triangles[:, :, 0] >= x - 1e-5)
            & (triangles[:, :, 0] <= x + width + 1e-5)
            & (triangles[:, :, 1] >= y - 1e-5)
            & (triangles[:, :, 1] <= y + depth + 1e-5),
            axis=1,
        )
    assert np.all(covered), ("Contact outside named seating regions", path)
    return dict(
        result="intended planar seating only",
        plane_z_mm=plane,
        plane_tolerance_mm=1e-5,
        maximum_plane_deviation_mm=float(np.max(deviation)),
        triangles=len(triangles),
    )


def verify_record(record):
    assert record["physical_fit_verified"] is False and record["build_ready"] is False
    assert record["unique_stl_files"] == len(inventory()) == 30
    assert record["printed_copies"] == sum(p["quantity"] for p in inventory()) == 38
    verify_sources(record)
    assert set(record["source_sha256"]) == set(source_hashes()), "Source set changed"
    for station in STATIONS:
        assert record["checks"][station + "-motion"]["result"] == "empty intersection"
        for suffix in ("seat", "stop"):
            result = record["checks"][station + "-" + suffix]
            assert result["result"] in ("empty intersection", "intended planar seating only")
    assert record["checks"]["selector"]["result"] == "empty intersection"


def verify_sources(record, repo=REPO):
    for name, expected in record["source_sha256"].items():
        assert sha(repo / name) == expected, ("Stale fit-kit source", name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", required=True, type=Path)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "verification.json").unlink(missing_ok=True)
    start = source_hashes()
    parts = inventory()

    def export(part):
        path = native(args.openscad, part["name"], part["part"], part["index"])
        return part["name"], inspect_mesh(path)

    with ThreadPoolExecutor(max_workers=3) as pool:
        meshes = dict(pool.map(export, parts))
    checks = {}
    buttons, _ = schedule()
    for station in STATIONS:
        index = next(i for i, b in enumerate(buttons) if b[0] == station)
        b = buttons[index]
        result = native(args.openscad, station + "-motion", "moving_interference", index, True)
        assert isinstance(result, dict), ("Moving interference", station)
        checks[station + "-motion"] = result
        for suffix, part, plane, regions in [
            ("seat", "holder_guide_contact", -1.4, [(x - 2.1, y - 2.1, 4.2, 4.2) for x, y in b[8]]),
            ("stop", "stop_contact", 2.0, [(-19, -15, 38, 30)]),
        ]:
            result = native(args.openscad, station + "-" + suffix, part, index, True)
            checks[station + "-" + suffix] = (
                result if isinstance(result, dict) else inspect_contact(result, plane, regions)
            )
    result = native(args.openscad, "selector", "selector_interference", check=True)
    assert isinstance(result, dict), "Selector interference"
    checks["selector"] = result
    assert start == source_hashes(), "Sources changed during native build"
    record = dict(
        revision="A11 compact fit kit",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope="Rigid mesh, full button-travel and named contact checks; no physical print, feel or electronics qualification",
        unique_stl_files=len(parts),
        printed_copies=sum(p["quantity"] for p in parts),
        source_sha256=start,
        meshes=meshes,
        checks=checks,
        physical_print_performed=False,
        physical_fit_verified=False,
        spring_contact_force_verified=False,
        purchased_part_terminal_numbers_verified=False,
        material_strength_and_retention_verified=False,
        build_ready=False,
    )
    verify_record(record)
    with (OUT / "parts.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["name", "part", "index", "quantity"])
        writer.writeheader()
        writer.writerows(parts)
    (EVIDENCE / "verification.json").write_text(json.dumps(record, indent=2) + "\n")
    package = OUT / "RMX-A11-compact-fit-kit.zip"
    files = {"STL/" + p.name: p for p in (OUT / "STL").glob("*.stl")}
    files.update({"parts.csv": OUT / "parts.csv", "validation.json": EVIDENCE / "verification.json"})
    for name in ("README.md", "MEASUREMENTS.csv", "PURCHASED.csv"):
        files[name] = ROOT / name
    for name in ("fixture.scad", "build.py"):
        files["CAD/a11_fitkit/" + name] = ROOT / name
    for path in A11.rglob("*.scad"):
        files["CAD/a11/" + str(path.relative_to(A11))] = path
    for path in (OUT / "logs").glob("*.txt"):
        files["Native-Checks/logs/" + path.name] = path
    for path in (OUT / "checks").glob("*.stl"):
        files["Native-Checks/contacts/" + path.name] = path
    files["Tests/test_a11_fitkit.py"] = REPO / "tests/tooling/test_a11_fitkit.py"
    manifest = dict(
        files_sha256={name: sha(path) for name, path in sorted(files.items())},
        physical_fit_verified=False,
        build_ready=False,
    )
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, "RMX-A11-compact-fit-kit/" + name)
        archive.writestr("RMX-A11-compact-fit-kit/manifest.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        for name, expected in manifest["files_sha256"].items():
            assert hashlib.sha256(archive.read("RMX-A11-compact-fit-kit/" + name)).hexdigest() == expected
    (EVIDENCE / "package.json").write_text(
        json.dumps(
            dict(
                archive=str(package.relative_to(REPO)),
                bytes=package.stat().st_size,
                sha256=sha(package),
                manifest_entries=len(files),
                build_ready=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        f"A11 compact kit: {len(parts)} closed solids/{record['printed_copies']} copies; {len(checks)} native motion/contact checks pass. No physical print or fit performed."
    )


if __name__ == "__main__":
    main()
