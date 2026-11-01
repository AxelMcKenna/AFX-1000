"""Independent saved native-mesh, topology and shared-axis arithmetic review."""

import collections
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]


def read(p):
    return json.loads(p.read_text())


def mesh(p, topology=False):
    raw = p.read_bytes()
    n = struct.unpack_from("<I", raw, 80)[0]
    assert len(raw) == 84 + 50 * n
    volume = []
    edges = collections.Counter()
    adjacent = collections.defaultdict(set)
    for i in range(n):
        f = struct.unpack_from("<12fH", raw, 84 + 50 * i)
        a, b, c = tuple(f[3:6]), tuple(f[6:9]), tuple(f[9:12])
        volume.append(
            (
                a[0] * (b[1] * c[2] - b[2] * c[1])
                + a[1] * (b[2] * c[0] - b[0] * c[2])
                + a[2] * (b[0] * c[1] - b[1] * c[0])
            )
            / 6
        )
        if topology:
            assert len({a, b, c}) == 3
            for x, y in [(a, b), (b, c), (c, a)]:
                edges[tuple(sorted((x, y)))] += 1
                adjacent[x].add(y)
                adjacent[y].add(x)
    components = None
    if topology:
        assert all(count == 2 for count in edges.values())
        pending = set(adjacent)
        components = 0
        while pending:
            todo = [pending.pop()]
            components += 1
            while todo:
                node = todo.pop()
                new = adjacent[node] & pending
                pending -= new
                todo.extend(new)
    return abs(math.fsum(volume)), components


def main():
    v = read(ROOT / "generated/verification.json")
    a = read(ROOT / "generated/analysis.json")
    assert len(v["cases"]) == 23 and not v["changed_inputs"]
    assert v["prototype_space_checks_clear"]
    assert {
        "floating_fan_hole_collision",
        "floating_tray_hole_collision",
        "fixed_axis_rejected_witness",
        "remaining_pin_hardware_collision",
        "old_pins_blocked_witness",
    } <= v["cases"].keys()
    checked = 0
    for key in ["source_sha256", "artifact_sha256"]:
        for n, h in v[key].items():
            assert hashlib.sha256((REPO / n).read_bytes()).hexdigest() == h, n
            checked += 1
    expected = {"tray_geometry": 1, "guard_geometry": 2, "spacer_geometry": 4}
    topology = {}
    positive = empty = 0
    for name, row in v["cases"].items():
        p = ROOT / "generated" / (name + ".stl")
        log = (ROOT / "generated" / (name + ".log")).read_text()
        assert row["clear"] and not any(t in log for t in ["WARNING", "ERROR"])
        if name.endswith("collision"):
            assert row["empty"] and row["returncode"] == 1
            assert not p.exists() and "Current top level object is empty." in log
            empty += 1
        else:
            assert row["returncode"] == 0 and "NoError" in log
            vol, components = mesh(p, name in expected)
            assert math.isclose(vol, row["statistics"]["volume_mm3"], rel_tol=2e-8, abs_tol=2e-6)
            if name.endswith("positive_control"):
                assert math.isclose(vol, 0.008, abs_tol=2e-6)
            if name in expected:
                assert components == expected[name]
                topology[name] = dict(closed_boundaries=components, collapsed_triangles=0, bad_shared_edges=0)
            positive += 1
    assert (positive, empty) == (11, 12)
    assert a["original_pins"] == 1037 and a["remaining_whole_pins"] == 960
    assert len(a["removed_pin_centres_mm"]) == a["removed_whole_pins"] == 77
    q = a["shared_axis_construction"]
    assert math.isclose(q["maximum_relative_hole_offset_each_XY_mm"], 0.55, abs_tol=1e-12)
    for x in [-0.55, 0.55]:
        for y in [-0.55, 0.55]:
            bolt = (x / 2, y / 2)
            for centre, diameter in [((x, y), 4.2), ((0, 0), 4.4)]:
                radial = math.hypot(bolt[0] - centre[0], bolt[1] - centre[1]) + 3.1 / (
                    2 * math.cos(math.pi / 128)
                )
                assert radial < diameter / 2 * math.cos(math.pi / 96)
    for key in [
        "actual_enlarged_base_integrated",
        "physical_qualified",
        "thermal_qualified",
        "fabrication_released",
    ]:
        assert v[key] is False
    out = dict(
        scope=__doc__,
        source_artifact_hashes_checked=checked,
        actual_positive_meshes_reintegrated=positive,
        raw_empty_results=empty,
        part_topology=topology,
        shared_axis_same_bolt_both_frames_independently_checked=True,
        fixed_axis_rejected_volume_mm3=v["cases"]["fixed_axis_rejected_witness"]["statistics"]["volume_mm3"],
        actual_enlarged_base_integrated=False,
        physical_qualified=False,
        installed_cooling_qualified=False,
    )
    (ROOT / "independent-review.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
