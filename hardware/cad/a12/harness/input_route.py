"""Conditional 3D input-feed route, using actual native terminal identities.

The mated wire-exit positions below are requirements awaiting the manufacturer's
dimensioned drawing. A clear route is not approval of these assumed positions,
the crimps, wire forming tolerance, retention or fault/temperature performance.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

from ..generate import REPO, sha
from ..generate import ROOT as A12
from ..generate import main as generate_base
from ..repaired import main as generate_repaired
from ..verify import stl_volume
from .analyze import INLET, OUT, POWER, ROOT, analyze


def point(t, start, finish, lift):
    blend = t**3 * (10 - 15 * t + 6 * t * t)
    first = 30 * t * t * (1 - t) ** 2
    second = 60 * t * (1 - t) * (1 - 2 * t)
    dx, dy, dz = [b - a for a, b in zip(start, finish, strict=True)]
    position = [
        start[0] + dx * blend,
        start[1] + dy * t,
        start[2] + dz * blend + lift * math.sin(math.pi * t) ** 2,
    ]
    velocity = [dx * first, dy, dz * first + lift * math.pi * math.sin(2 * math.pi * t)]
    acceleration = [
        dx * second,
        0,
        dz * second + 2 * lift * math.pi**2 * math.cos(2 * math.pi * t),
    ]
    cross = [
        velocity[1] * acceleration[2] - velocity[2] * acceleration[1],
        velocity[2] * acceleration[0] - velocity[0] * acceleration[2],
        velocity[0] * acceleration[1] - velocity[1] * acceleration[0],
    ]
    speed = math.sqrt(sum(v * v for v in velocity))
    normal = math.sqrt(sum(v * v for v in cross))
    radius = speed**3 / normal if normal else math.inf
    return position, radius


def generate():
    generate_base()
    bodies = generate_repaired()
    feed = analyze()
    contract = json.loads((A12 / "interface.json").read_text())
    sources = dict(json.loads((A12 / "generated/allocation.json").read_text())["source_sha256"])
    sources.update(bodies["source_sha256"])
    sources.update(feed["source_sha256"])
    for path in [
        Path(__file__),
        ROOT / "input-route.scad",
        A12 / "repaired-integration.scad",
        A12 / "verify.py",
    ]:
        sources[str(path.relative_to(REPO))] = sha(path)
    for pcb, reference, angle in [(INLET, "J2", 0), (POWER, "J101", 180)]:
        tree = read_sexpr(pcb.read_text())
        footprint = next(
            fp
            for fp in children(tree, "footprint")
            if any(p[1:3] == ["Reference", reference] for p in children(fp, "property"))
        )
        pose = first(footprint, "at")
        assert float(pose[3] if len(pose) > 3 else 0) % 360 == angle
        assert first(footprint, "layer")[1] == "F.Cu"
    # Nominal mated exits: 22 mm in the header's mating direction, with a
    # centre 3.85 mm above the board face. These are explicit unapproved
    # interface requirements, not dimensions inferred from a catalog picture.
    power_z = contract["power_candidate"]["datum"][2]
    power_t = contract["power_candidate"]["thickness"]
    wire_diameter = feed["wire_diameter_interval_mm"][1]
    position_allowance = 0.65
    tessellation_allowance = 0.01
    clearance = 0.25
    rows = []
    paths = []
    samples = 4000
    for pin, lift in [("1", 2.7), ("2", -2.7)]:
        source = feed["source_connector_pad_centers"][pin]
        destination = feed["destination_connector_pad_centers"][pin]
        assert source["net"] == destination["net"]
        start = [*source["center_housing_xy_mm"], 7.9 + 1.6 + 3.85]
        finish = [*destination["center_housing_xy_mm"], power_z + power_t + 3.85]
        start[1] += 22
        finish[1] -= 22
        assert finish[1] > start[1]
        dense = [point(index / samples, start, finish, lift) for index in range(samples + 1)]
        points = [item[0] for item in dense]
        minimum_radius = min(item[1] for item in dense)
        # Large numerical margin is required; no sampled tight bend is waved
        # through as an exact bound on the continuous or manufactured curve.
        required_radius = feed["conservative_wire_centerline_bend_radius_allocation_mm"]
        assert minimum_radius >= 1.2 * required_radius
        length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
        assert length < 100, "Free span exceeds the earlier entire-conductor screening length"
        rows.append(
            dict(
                pin=pin,
                net=source["net"],
                start_mm=start,
                finish_mm=finish,
                opposing_crossover_lift_mm=lift,
                sampled_minimum_centerline_radius_mm=minimum_radius,
                sampled_free_span_length_mm=length,
                required_centerline_radius_mm=required_radius,
                curve_samples=samples + 1,
                cut_length_mm=None,
            )
        )
        # Native capsules at 0.5% parameter increments. The added .01 mm
        # geometric reserve exceeds the local chord sag for this smooth route;
        # it is not a wire-forming process tolerance.
        paths.append(points[::20])
    separation = min(math.dist(a, b) for a in paths[0] for b in paths[1])
    required_separation = wire_diameter + 2 * (position_allowance + tessellation_allowance) + clearance
    native_separation = required_separation / math.cos(math.pi / 24) ** 2
    assert separation > native_separation
    report = dict(
        revision="A12-H01-3D-candidate",
        scope="Two individual input wires; nominal mated-exit requirements and swept position allowance",
        wire_diameter_maximum_mm=wire_diameter,
        isotropic_center_position_allowance_mm=position_allowance,
        tessellation_allowance_mm=tessellation_allowance,
        clearance_allocation_mm=clearance,
        nominal_exit_offset_from_header_pad_mm=22,
        nominal_exit_height_above_pcb_face_mm=3.85,
        exit_dimensions_are_manufacturer_approved=False,
        terminal_orientations_required_degrees={"inlet_J2": 0, "power_J101": 180},
        sampled_wire_center_separation_mm=separation,
        required_wire_center_separation_mm=required_separation,
        circumscribed_native_sphere_segments=24,
        circumscribed_native_required_separation_mm=native_separation,
        routes=rows,
        source_sha256=sources,
        actual_cut_lengths_and_strip_allowances_frozen=False,
        retention_and_forming_fixture_implemented=False,
        physical_fit_verified=False,
        electrical_thermal_and_fault_qualification=False,
        fabrication_released=False,
        build_ready=False,
    )
    assert all(sha(REPO / name) == value for name, value in sources.items()), (
        "Route inputs changed during generation"
    )
    OUT.mkdir(exist_ok=True)
    (OUT / "input-route.json").write_text(json.dumps(report, indent=2) + "\n")
    diameter = wire_diameter + 2 * (position_allowance + tessellation_allowance)
    (OUT / "input-route.scad").write_text(
        "// Conditional wire-exit geometry. No manufacturer/physical fit approval.\n"
        + "input_wire_paths="
        + json.dumps(paths)
        + ";\n"
        + "input_wire_envelope_diameter="
        + str(diameter)
        + ";\n"
    )
    return report


def verify(executable):
    report = generate()
    sources = report["source_sha256"]
    paths = [
        ROOT / "generated/input-route.scad",
        A12 / "generated/repaired-components.scad",
        A12 / "generated/components.scad",
        A12 / "generated/interface.scad",
        A12 / "thermal-integration.scad",
        A12 / "thermal/generated/thermal-base.scad",
        A12 / "returns/generated/returns.scad",
        *sorted((A12 / "returns/generated").glob("*.stl")),
    ]
    sources.update({str(path.relative_to(REPO)): sha(path) for path in paths})
    output = REPO / "build/artifacts/cad/a12/input-harness"
    output.mkdir(parents=True, exist_ok=True)
    checks = {}
    for part in [
        "wires",
        "wire_pair_collision",
        "wire_case_collision",
        "wire_electronics_collision",
        "wire_positive_control",
    ]:
        target = output / (part + ".stl")
        target.unlink(missing_ok=True)
        command = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for value in [
            'part="harness_only"',
            'thermal_part="harness_only"',
            'repaired_part="harness_only"',
            f'input_route_part="{part}"',
        ]:
            command += ["-D", value]
        command += ["-o", str(target), str(ROOT / "input-route.scad")]
        run = subprocess.run(command, capture_output=True, text=True, timeout=60)
        log = run.stdout + run.stderr
        logfile = OUT / ("input-route-" + part + ".log")
        logfile.write_text(log)
        assert "WARNING" not in log and "ERROR" not in log, (part, log)
        if run.returncode == 1 and "Current top level object is empty." in log:
            assert part.endswith("collision"), (part, "Required geometry is missing")
            target.unlink(missing_ok=True)
            checks[part] = dict(result="empty intersection", collision=False)
        else:
            assert run.returncode == 0 and target.exists(), (part, log)
            volume = stl_volume(target)
            assert volume > 0, (part, "Degenerate native geometry")
            if not part.endswith("collision"):
                assert volume > 0.001, (part, "Required geometry is too small")
            checks[part] = dict(
                result="collision found" if part.endswith("collision") else "nonempty native geometry",
                collision=part.endswith("collision"),
                volume_mm3=volume,
                stl_sha256=sha(target),
            )
        checks[part]["log_sha256"] = sha(logfile)
        print(part, checks[part]["result"], flush=True)
    assert all(sha(REPO / name) == value for name, value in sources.items()), (
        "Geometry/source changed during native checks"
    )
    report.update(
        checks=checks, declared_envelopes_clear=not any(row["collision"] for row in checks.values())
    )
    (OUT / "input-route-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path)
    args = parser.parse_args()
    if args.openscad:
        result = verify(args.openscad.resolve())
        if not result["declared_envelopes_clear"]:
            raise SystemExit(2)
    else:
        generate()
