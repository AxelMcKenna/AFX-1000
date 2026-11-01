"""Strict local native parts/interfaces; records failure, never rewrites inputs."""

import argparse
import collections
import hashlib
import json
import math
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = Path("/Users/axelmckrnna/Applications/OpenSCAD-2026.10.27.app/Contents/MacOS/OpenSCAD")
CASES = {
    "base_part": "part",
    "cap_part": "part",
    "ports_pair_margin": "empty",
    "force_solder_post_margin": "empty",
    "force_solder_bridge_margin": "empty",
    "ports_other_strain_margin": "empty",
    "own_PCB_seats": "empty",
    "mount_gauge_min_bores": "empty",
    "force_gauge_min_bores": "empty",
    "wire_outside_grip_collision": "empty",
    "hardware_receiving_threads": "empty",
    "hardware_matched_nominal_PCB": "empty",
    "base_cap_nonseat_overlap": "empty",
    "old_mount_bore_witness": "witness",
    "old_force_bore_witness": "witness",
    "intentional_grip_contact_witness": "witness",
    "uncut_thread_pilots_witness": "witness",
    "control_contact_point": "control",
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mesh(p):
    raw = p.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84 + 50 * count or not count:
        raise ValueError("Missing/wrong binary STL")
    edges = collections.Counter()
    faces, volumes, vertices = [], [], []
    zero = 0
    for i in range(count):
        row = struct.unpack_from("<12fH", raw, 84 + i * 50)
        a, b, c = tuple(row[3:6]), tuple(row[6:9]), tuple(row[9:12])
        if not all(math.isfinite(v) for p in [a, b, c] for v in p):
            raise ValueError("Nonfinite STL")
        u, v = [b[j] - a[j] for j in range(3)], [c[j] - a[j] for j in range(3)]
        cross = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        zero += sum(x * x for x in cross) == 0
        faces.append((a, b, c))
        vertices.extend([a, b, c])
        for x, y in [(a, b), (b, c), (c, a)]:
            edges[(x, y)] += 1
        volumes.append(
            (
                a[0] * (b[1] * c[2] - b[2] * c[1])
                + a[1] * (b[2] * c[0] - b[0] * c[2])
                + a[2] * (b[0] * c[1] - b[1] * c[0])
            )
            / 6
        )
    closed = all(n == 1 and edges[(b, a)] == 1 for (a, b), n in edges.items())
    adjacency = collections.defaultdict(set)
    for a, b, c in faces:
        for x, y in [(a, b), (b, c), (c, a)]:
            adjacency[x].add(y)
            adjacency[y].add(x)
    pending = set(adjacency)
    components = 0
    while pending:
        components += 1
        todo = [pending.pop()]
        while todo:
            for v in adjacency[todo.pop()]:
                if v in pending:
                    pending.remove(v)
                    todo.append(v)
    volume = math.fsum(volumes)
    return dict(
        triangles=count,
        volume_mm3=volume,
        min_mm=[min(p[i] for p in vertices) for i in range(3)],
        max_mm=[max(p[i] for p in vertices) for i in range(3)],
        closed_oriented_boundary=closed,
        zero_area_triangles=zero,
        connected_components=components,
        valid=closed and zero == 0 and volume > 0,
    )


def run(out):
    if out.exists():
        raise RuntimeError("New native output required")
    source_files = [
        ROOT / "ports.json",
        ROOT / "ports-v2.json",
        ROOT / "mechanics.py",
        ROOT / "mechanical-v2/geometry.scad",
        ROOT / "mechanical-v2/datums.json",
        Path(__file__),
        ENGINE,
    ]
    bindings = {str(p): sha(p) for p in source_files}
    version = subprocess.run([str(ENGINE), "--version"], capture_output=True, text=True, check=False)
    if version.returncode:
        raise ValueError("Native engine version check failed")
    out.mkdir()
    records = {}
    for name, role in CASES.items():
        target = out / (name + ".stl")
        cmd = [
            str(ENGINE),
            "--backend=Manifold",
            "--hardwarnings",
            "--export-format",
            "binstl",
            "-D",
            'case_name="' + name + '"',
            "-o",
            str(target),
            str(ROOT / "mechanical-v2/geometry.scad"),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        log = out / (name + ".log")
        log.write_text(result.stdout + result.stderr)
        text = result.stdout + result.stderr
        row = dict(
            role=role,
            command=cmd,
            returncode=result.returncode,
            log_sha256=sha(log),
            STL_sha256=sha(target) if target.exists() else None,
        )
        if role == "empty":
            row["passed"] = (
                result.returncode == 1 and "Current top level object is empty" in text and not target.exists()
            )
        elif result.returncode == 0 and target.exists():
            row["mesh"] = mesh(target)
            row["passed"] = (
                row["mesh"]["valid"]
                and "Status:     NoError" in text
                and "WARNING" not in text
                and "ERROR" not in text
            )
            if role == "part":
                row["passed"] &= row["mesh"]["connected_components"] == 1
            if role == "control":
                row["passed"] &= abs(row["mesh"]["volume_mm3"] - 0.008) < 2e-6
        else:
            row["passed"] = False
        records[name] = row
        (out / "verification.json").write_text(
            json.dumps(dict(complete=False, cases=records, source_sha256=bindings), indent=2) + "\n"
        )
        print(name, row["passed"], flush=True)
    changed = [str(p) for p in source_files if sha(p) != bindings[str(p)]]
    report = dict(
        revision="NC265-local-native-mechanics",
        engine_version_stdout=version.stdout,
        engine_version_stderr=version.stderr,
        source_sha256=bindings,
        cases=records,
        complete=True,
        changed_inputs=changed,
        local_modeled_candidate_clear=not changed and all(r["passed"] for r in records.values()),
        scope="Actual local prototype only; matched nominal PCB hardware, explicit max receiving gauges, no remaining259components/fullunit",
        intended_thread_contacts_and_wire_compression_do_NOT_prove_strength=True,
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
    )
    (out / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    raise SystemExit(not report["local_modeled_candidate_clear"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
